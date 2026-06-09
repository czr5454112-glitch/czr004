#include "ltm.hpp"

#include <lacam2.hpp>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

struct RuleSpec {
  std::string rule_id;
  czr004::ltm::UpdateParams params;
  double saturation_scale = 1.0;
};

struct Args {
  std::string map;
  std::string scen;
  std::string map_name;
  std::string split = "train";
  std::string run_id;
  std::string probe_output_jsonl;
  std::string branch;
  std::string commit;
  std::string dirty;
  std::vector<std::string> rule_ids;
  uint agents = 0;
  uint seed = 0;
  double time_limit_sec = 3.0;
  uint max_iterations = 4;
  double probe_short_budget_sec = 1.0;
  uint max_checkpoints_per_run = 8;
  uint checkpoint_topk_edges = 16;
  double harmful_delta_ratio_threshold = -0.02;
  int verbose = 0;
};

std::string json_escape(const std::string& value)
{
  std::ostringstream out;
  for (const char ch : value) {
    switch (ch) {
      case '\\':
        out << "\\\\";
        break;
      case '"':
        out << "\\\"";
        break;
      case '\n':
        out << "\\n";
        break;
      case '\r':
        out << "\\r";
        break;
      case '\t':
        out << "\\t";
        break;
      default:
        out << ch;
    }
  }
  return out.str();
}

std::string json_string(const std::string& value)
{
  return "\"" + json_escape(value) + "\"";
}

std::string json_number_or_null(double value)
{
  if (!std::isfinite(value)) return "null";
  std::ostringstream out;
  out.precision(12);
  out << value;
  return out.str();
}

bool parse_uint(const std::string& value, uint* out)
{
  try {
    *out = static_cast<uint>(std::stoul(value));
    return true;
  } catch (...) {
    return false;
  }
}

bool parse_double(const std::string& value, double* out)
{
  try {
    *out = std::stod(value);
    return true;
  } catch (...) {
    return false;
  }
}

std::vector<std::string> split_csv(const std::string& value)
{
  auto out = std::vector<std::string>();
  auto stream = std::istringstream(value);
  std::string item;
  while (std::getline(stream, item, ',')) {
    item.erase(std::remove_if(item.begin(), item.end(),
                              [](char ch) {
                                return std::isspace(
                                    static_cast<unsigned char>(ch));
                              }),
               item.end());
    if (!item.empty()) out.push_back(item);
  }
  return out;
}

Args parse_args(int argc, char** argv)
{
  auto values = std::unordered_map<std::string, std::string>();
  auto flags = std::set<std::string>();
  for (int i = 1; i < argc; ++i) {
    const auto key = std::string(argv[i]);
    if (key.rfind("--", 0) != 0) {
      throw std::runtime_error("invalid argument near " + key);
    }
    const auto name = key.substr(2);
    if (i + 1 < argc && std::string(argv[i + 1]).rfind("--", 0) != 0) {
      values[name] = argv[++i];
    } else {
      flags.insert(name);
    }
  }
  (void)flags;

  auto require = [&](const std::string& key) {
    const auto it = values.find(key);
    if (it == values.end() || it->second.empty()) {
      throw std::runtime_error("missing --" + key);
    }
    return it->second;
  };

  Args args;
  args.map = require("map");
  args.scen = require("scen");
  args.map_name = values.count("map-name")
                      ? values["map-name"]
                      : std::filesystem::path(args.map).stem().string();
  args.split = values.count("split") ? values["split"] : "train";
  args.run_id = values.count("run-id") ? values["run-id"] : "";
  args.probe_output_jsonl = require("probe-output-jsonl");
  args.branch = values.count("branch") ? values["branch"] : "";
  args.commit = values.count("commit") ? values["commit"] : "";
  args.dirty = values.count("dirty") ? values["dirty"] : "";
  args.rule_ids = values.count("rule-set") ? split_csv(values["rule-set"])
                                            : std::vector<std::string>();

  if (!parse_uint(require("agents"), &args.agents)) {
    throw std::runtime_error("invalid --agents");
  }
  if (!parse_uint(require("seed"), &args.seed)) {
    throw std::runtime_error("invalid --seed");
  }
  if (values.count("time-limit-sec") &&
      !parse_double(values["time-limit-sec"], &args.time_limit_sec)) {
    throw std::runtime_error("invalid --time-limit-sec");
  }
  if (values.count("max-iterations") &&
      !parse_uint(values["max-iterations"], &args.max_iterations)) {
    throw std::runtime_error("invalid --max-iterations");
  }
  if (values.count("probe-short-budget-sec") &&
      !parse_double(values["probe-short-budget-sec"],
                    &args.probe_short_budget_sec)) {
    throw std::runtime_error("invalid --probe-short-budget-sec");
  }
  if (values.count("max-checkpoints-per-run") &&
      !parse_uint(values["max-checkpoints-per-run"],
                  &args.max_checkpoints_per_run)) {
    throw std::runtime_error("invalid --max-checkpoints-per-run");
  }
  if (values.count("checkpoint-topk-edges") &&
      !parse_uint(values["checkpoint-topk-edges"],
                  &args.checkpoint_topk_edges)) {
    throw std::runtime_error("invalid --checkpoint-topk-edges");
  }
  if (values.count("harmful-delta-ratio-threshold") &&
      !parse_double(values["harmful-delta-ratio-threshold"],
                    &args.harmful_delta_ratio_threshold)) {
    throw std::runtime_error("invalid --harmful-delta-ratio-threshold");
  }
  if (values.count("verbose")) args.verbose = std::stoi(values["verbose"]);

  if (args.split != "train" && args.split != "validation" &&
      args.split != "test") {
    throw std::runtime_error("--split must be train, validation, or test");
  }
  return args;
}

std::string default_run_id(const Args& args)
{
  if (!args.run_id.empty()) return args.run_id;
  std::ostringstream out;
  out << args.map_name << "__a" << args.agents << "__s" << args.seed
      << "__phase4d_probe";
  return out.str();
}

std::string checkpoint_id_for(const std::string& run_id, uint iteration)
{
  std::ostringstream out;
  out << run_id << "__iter" << iteration;
  return out.str();
}

czr004::ltm::UpdateParams params(double commit, double block, double wait,
                                 double decay)
{
  czr004::ltm::UpdateParams out;
  out.alpha_commit = commit;
  out.alpha_block = block;
  out.alpha_wait_spillover = wait;
  out.rho_decay = decay;
  out.force_additive = false;
  return out;
}

RuleSpec rule_for(const std::string& rule_id)
{
  if (rule_id == "additive_ltm") {
    return RuleSpec{rule_id, czr004::ltm::UpdateParams::additive(), 1.0};
  }
  if (rule_id == "commit_heavy") return RuleSpec{rule_id, params(1.5, 1.0, 1.0, 1.0), 1.0};
  if (rule_id == "block_heavy") return RuleSpec{rule_id, params(1.0, 1.5, 1.0, 1.0), 1.0};
  if (rule_id == "block_light") return RuleSpec{rule_id, params(1.0, 0.5, 1.0, 1.0), 1.0};
  if (rule_id == "wait_light") return RuleSpec{rule_id, params(1.0, 1.0, 0.5, 1.0), 1.0};
  if (rule_id == "wait_heavy") return RuleSpec{rule_id, params(1.0, 1.0, 1.5, 1.0), 1.0};
  if (rule_id == "decay_095") return RuleSpec{rule_id, params(1.0, 1.0, 1.0, 0.95), 1.0};
  if (rule_id == "decay_090") return RuleSpec{rule_id, params(1.0, 1.0, 1.0, 0.90), 1.0};
  throw std::runtime_error("unknown rule_id " + rule_id);
}

std::vector<RuleSpec> rules_for(const std::vector<std::string>& rule_ids)
{
  auto ids = rule_ids;
  if (ids.empty()) {
    ids = {"additive_ltm", "commit_heavy", "block_heavy", "block_light",
           "wait_light", "wait_heavy", "decay_095", "decay_090"};
  }
  if (std::find(ids.begin(), ids.end(), "additive_ltm") == ids.end()) {
    ids.insert(ids.begin(), "additive_ltm");
  }

  auto out = std::vector<RuleSpec>();
  for (const auto& id : ids) out.push_back(rule_for(id));
  return out;
}

double delta_ratio_vs_additive(const czr004::ltm::LtmOneShotProbeResult& rule,
                               const czr004::ltm::LtmOneShotProbeResult& additive)
{
  if (rule.solution_found && additive.solution_found &&
      std::isfinite(rule.sum_of_loss_ratio) &&
      std::isfinite(additive.sum_of_loss_ratio)) {
    return additive.sum_of_loss_ratio - rule.sum_of_loss_ratio;
  }
  if (rule.solution_found && !additive.solution_found) return 1.0;
  if (!rule.solution_found && additive.solution_found) return -1.0;
  return 0.0;
}

bool beats_additive(const czr004::ltm::LtmOneShotProbeResult& rule,
                    const czr004::ltm::LtmOneShotProbeResult& additive,
                    double delta)
{
  if (rule.solution_found != additive.solution_found) return rule.solution_found;
  return delta > 0.0;
}

bool is_harmful(const czr004::ltm::LtmOneShotProbeResult& rule,
                const czr004::ltm::LtmOneShotProbeResult& additive,
                double delta, double threshold)
{
  if (!rule.solution_found && additive.solution_found) return true;
  return delta < threshold;
}

void write_rule_params(std::ostream& out, const RuleSpec& rule)
{
  out << "{";
  out << "\"alpha_commit\":"
      << json_number_or_null(rule.params.force_additive ? 1.0
                                                        : rule.params.alpha_commit);
  out << ",\"alpha_block\":"
      << json_number_or_null(rule.params.force_additive ? 1.0
                                                        : rule.params.alpha_block);
  out << ",\"alpha_wait\":"
      << json_number_or_null(rule.params.force_additive
                                 ? 1.0
                                 : rule.params.alpha_wait_spillover);
  out << ",\"rho_decay\":"
      << json_number_or_null(rule.params.force_additive ? 1.0
                                                        : rule.params.rho_decay);
  out << ",\"saturation_scale\":" << json_number_or_null(rule.saturation_scale);
  out << ",\"contraflow_penalty\":"
      << json_number_or_null(rule.params.enable_contraflow_penalty
                                 ? rule.params.contraflow_penalty
                                 : 0.0);
  out << "}";
}

void write_probe_row(
    std::ostream& out, const Args& args, const std::string& run_id,
    const czr004::ltm::LtmIterationCheckpoint& checkpoint,
    const std::string& checkpoint_id, const RuleSpec& rule,
    const czr004::ltm::LtmOneShotProbeResult& result,
    const czr004::ltm::LtmOneShotProbeResult& additive)
{
  const auto delta = delta_ratio_vs_additive(result, additive);
  const auto beats = beats_additive(result, additive, delta);
  const auto harmful =
      rule.rule_id == "additive_ltm"
          ? false
          : is_harmful(result, additive, delta,
                       args.harmful_delta_ratio_threshold);
  const auto probe_id = checkpoint_id + "__rule_" + rule.rule_id;

  out << "{";
  out << "\"schema_version\":\"phase4_laur_update_label_v1\"";
  out << ",\"run_id\":" << json_string(run_id);
  out << ",\"checkpoint_id\":" << json_string(checkpoint_id);
  out << ",\"probe_id\":" << json_string(probe_id);
  out << ",\"split\":" << json_string(args.split);
  out << ",\"map_name\":" << json_string(args.map_name);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"iteration\":" << checkpoint.iteration;
  out << ",\"rule_id\":" << json_string(rule.rule_id);
  out << ",\"rule_params\":";
  write_rule_params(out, rule);
  out << ",\"probe_short_budget_sec\":"
      << json_number_or_null(args.probe_short_budget_sec);
  out << ",\"solution_found\":" << (result.solution_found ? "true" : "false");
  out << ",\"feasible\":" << (result.feasible ? "true" : "false");
  out << ",\"sum_of_loss\":"
      << (result.solution_found ? std::to_string(result.sum_of_loss) : "null");
  out << ",\"lower_bound_sol\":" << result.lower_bound_sol;
  out << ",\"sum_of_loss_ratio\":"
      << json_number_or_null(result.sum_of_loss_ratio);
  out << ",\"time_to_first_solution_ms\":null";
  out << ",\"returned_solutions_count\":" << result.returned_solutions_count;
  out << ",\"expanded_nodes\":" << result.expanded_nodes;
  out << ",\"high_level_expansions\":" << result.high_level_expansions;
  out << ",\"low_level_pibt_calls\":" << result.low_level_pibt_calls;
  out << ",\"runtime_ms\":" << json_number_or_null(result.runtime_ms);
  out << ",\"additive_solution_found\":"
      << (additive.solution_found ? "true" : "false");
  out << ",\"additive_sum_of_loss\":"
      << (additive.solution_found ? std::to_string(additive.sum_of_loss)
                                  : "null");
  out << ",\"additive_sum_of_loss_ratio\":"
      << json_number_or_null(additive.sum_of_loss_ratio);
  out << ",\"delta_ratio_vs_additive\":" << json_number_or_null(delta);
  out << ",\"beats_additive\":" << (beats ? "true" : "false");
  out << ",\"harmful\":" << (harmful ? "true" : "false");
  out << ",\"base_solution_found_this_iteration\":"
      << (checkpoint.solution_found_this_iteration ? "true" : "false");
  out << ",\"base_sum_of_loss_ratio_this_iteration\":"
      << json_number_or_null(checkpoint.sum_of_loss_ratio_this_iteration);
  out << ",\"trace_event_count\":" << checkpoint.trace_events.size();
  out << ",\"branch\":" << json_string(args.branch);
  out << ",\"commit\":" << json_string(args.commit);
  out << ",\"dirty\":" << json_string(args.dirty);
  out << "}\n";
}

}  // namespace

int main(int argc, char** argv)
{
  try {
    const auto args = parse_args(argc, argv);
    const auto run_id = default_run_id(args);
    const auto rules = rules_for(args.rule_ids);

    std::filesystem::create_directories(
        std::filesystem::path(args.probe_output_jsonl).parent_path());
    std::ofstream probe_out(args.probe_output_jsonl, std::ios::app);
    if (!probe_out) throw std::runtime_error("cannot open probe JSONL");

    const auto instance = Instance(args.scen, args.map, args.agents);
    if (!instance.is_valid(args.verbose)) {
      throw std::runtime_error("invalid MAPF instance");
    }

    auto checkpoints = std::vector<czr004::ltm::LtmIterationCheckpoint>();
    czr004::ltm::LtmOptions options;
    options.objective = Objective::OBJ_SUM_OF_LOSS;
    options.time_limit_ms = args.time_limit_sec * 1000.0;
    options.max_iterations = args.max_iterations;
    options.node_budget_factor = 10;
    options.verbose = args.verbose;
    options.seed = args.seed;
    options.checkpoint_topk_edges = args.checkpoint_topk_edges;
    options.update_params = czr004::ltm::UpdateParams::additive();
    options.retain_iteration_traffic_maps = true;
    options.iteration_callback =
        [&](const czr004::ltm::LtmIterationCheckpoint& checkpoint) {
          checkpoints.push_back(checkpoint);
        };

    const auto base_result = czr004::ltm::solve_with_ltm(instance, options);
    (void)base_result;

    uint probe_rows = 0;
    const auto checkpoint_limit =
        std::min<std::size_t>(checkpoints.size(), args.max_checkpoints_per_run);
    for (std::size_t checkpoint_index = 0; checkpoint_index < checkpoint_limit;
         ++checkpoint_index) {
      const auto& checkpoint = checkpoints[checkpoint_index];
      if (!checkpoint.traffic_before_map) {
        throw std::runtime_error("missing retained traffic map for checkpoint");
      }
      const auto checkpoint_id =
          checkpoint_id_for(run_id, checkpoint.iteration);

      const auto additive_rule = rule_for("additive_ltm");
      czr004::ltm::LtmOneShotProbeOptions probe_options;
      probe_options.objective = Objective::OBJ_SUM_OF_LOSS;
      probe_options.short_budget_ms = args.probe_short_budget_sec * 1000.0;
      probe_options.node_budget = 0;
      probe_options.verbose = args.verbose;
      probe_options.seed = args.seed + checkpoint.iteration;
      probe_options.update_params = additive_rule.params;
      const auto additive = czr004::ltm::run_one_shot_update_probe(
          instance, *checkpoint.traffic_before_map, checkpoint.trace_events,
          probe_options);

      for (const auto& rule : rules) {
        auto result = additive;
        if (rule.rule_id != "additive_ltm") {
          probe_options.seed = args.seed + checkpoint.iteration;
          probe_options.update_params = rule.params;
          result = czr004::ltm::run_one_shot_update_probe(
              instance, *checkpoint.traffic_before_map,
              checkpoint.trace_events, probe_options);
        }
        write_probe_row(probe_out, args, run_id, checkpoint, checkpoint_id,
                        rule, result, additive);
        ++probe_rows;
      }
    }

    std::cout << "phase4_laur_probe"
              << " run_id=" << run_id
              << " map=" << args.map_name
              << " agents=" << args.agents
              << " seed=" << args.seed
              << " checkpoints=" << checkpoint_limit
              << " rules=" << rules.size()
              << " probe_rows=" << probe_rows
              << " probe_output_jsonl=" << args.probe_output_jsonl
              << std::endl;
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "phase4_laur_probe: " << e.what() << std::endl;
    return 1;
  }
}
