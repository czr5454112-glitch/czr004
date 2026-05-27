#include "ltm.hpp"
#include "laur_ltm_features.hpp"
#include "laur_ltm_runtime.hpp"

#include <lacam2.hpp>

#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>

namespace {

struct Args {
  std::string method;
  std::string map;
  std::string scen;
  std::string map_name;
  std::string scen_id;
  std::string output_jsonl;
  std::string manifest;
  std::string project_commit;
  std::string external_commit;
  std::string branch;
  std::string dirty;
  std::string platform;
  std::string traffic_map_jsonl;
  std::string traffic_map_run_id;
  std::string traffic_map_edge_filter = "all";
  std::string laur_model_path;
  std::string laur_static_rule;
  std::string method_alias;
  uint agents = 0;
  uint seed = 0;
  double time_limit_sec = 30.0;
  uint ltm_max_iterations = 100000;
  bool laur_enable = false;
  bool laur_disable = false;
  bool laur_force_additive = false;
  bool laur_safety_enabled = true;
  bool laur_post_first_solution_only = true;
  uint laur_every_k_restarts = 1;
  double laur_safety_threshold = 0.30;
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

void append_json_string_uint_map(std::ostream& out,
                                 const std::map<std::string, uint>& values)
{
  out << "{";
  bool first = true;
  for (const auto& [key, value] : values) {
    if (!first) out << ",";
    first = false;
    out << json_string(key) << ":" << value;
  }
  out << "}";
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

Args parse_args(int argc, char** argv)
{
  auto values = std::unordered_map<std::string, std::string>();
  const auto switches = std::unordered_set<std::string>{
      "laur-enable",
      "laur-disable",
      "laur-force-additive",
      "laur-disable-safety",
      "laur-post-first-solution-only",
      "laur-allow-pre-first-solution",
  };
  for (int i = 1; i < argc; ++i) {
    const auto key = std::string(argv[i]);
    if (key.rfind("--", 0) != 0) {
      throw std::runtime_error("invalid argument near " + key);
    }
    const auto name = key.substr(2);
    if (switches.count(name) > 0) {
      values[name] = "1";
      continue;
    }
    if (i + 1 >= argc) throw std::runtime_error("missing value for " + key);
    values[name] = argv[++i];
  }

  auto require = [&](const std::string& key) {
    const auto it = values.find(key);
    if (it == values.end() || it->second.empty()) {
      throw std::runtime_error("missing --" + key);
    }
    return it->second;
  };

  Args args;
  args.method = require("method");
  args.map = require("map");
  args.scen = require("scen");
  args.output_jsonl = require("output-jsonl");
  args.map_name = values.count("map-name") ? values["map-name"] : args.map;
  args.scen_id = values.count("scen-id") ? values["scen-id"] : args.scen;
  args.manifest = values.count("manifest") ? values["manifest"] : "";
  args.project_commit =
      values.count("project-commit") ? values["project-commit"] : "";
  args.external_commit =
      values.count("external-commit") ? values["external-commit"] : "";
  args.branch = values.count("branch") ? values["branch"] : "";
  args.dirty = values.count("dirty") ? values["dirty"] : "";
  args.platform = values.count("platform") ? values["platform"] : "";
  args.traffic_map_jsonl =
      values.count("traffic-map-jsonl") ? values["traffic-map-jsonl"] : "";
  args.traffic_map_run_id =
      values.count("traffic-map-run-id") ? values["traffic-map-run-id"] : "";
  args.traffic_map_edge_filter =
      values.count("traffic-map-edge-filter") ? values["traffic-map-edge-filter"] : "all";
  args.laur_model_path =
      values.count("laur-model-path") ? values["laur-model-path"] : "";
  args.laur_static_rule =
      values.count("laur-static-rule") ? values["laur-static-rule"] : "";
  args.method_alias =
      values.count("method-alias") ? values["method-alias"] : "";
  args.laur_enable = values.count("laur-enable") > 0;
  args.laur_disable = values.count("laur-disable") > 0;
  args.laur_force_additive = values.count("laur-force-additive") > 0;
  args.laur_safety_enabled = values.count("laur-disable-safety") == 0;
  args.laur_post_first_solution_only =
      values.count("laur-allow-pre-first-solution") > 0
          ? false
          : (values.count("laur-post-first-solution-only") > 0 ||
             args.laur_post_first_solution_only);

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
  if (values.count("ltm-max-iterations") &&
      !parse_uint(values["ltm-max-iterations"], &args.ltm_max_iterations)) {
    throw std::runtime_error("invalid --ltm-max-iterations");
  }
  if (values.count("laur-every-k-restarts") &&
      !parse_uint(values["laur-every-k-restarts"], &args.laur_every_k_restarts)) {
    throw std::runtime_error("invalid --laur-every-k-restarts");
  }
  if (args.laur_every_k_restarts == 0) {
    throw std::runtime_error("--laur-every-k-restarts must be >= 1");
  }
  if (values.count("laur-safety-threshold") &&
      !parse_double(values["laur-safety-threshold"], &args.laur_safety_threshold)) {
    throw std::runtime_error("invalid --laur-safety-threshold");
  }
  if (args.laur_disable && args.laur_enable) {
    throw std::runtime_error("--laur-enable and --laur-disable are mutually exclusive");
  }
  if (args.laur_force_additive && !args.laur_static_rule.empty()) {
    throw std::runtime_error("--laur-force-additive and --laur-static-rule are mutually exclusive");
  }
  if (!args.laur_static_rule.empty() &&
      !czr004::ntm::is_supported_laur_rule_id(args.laur_static_rule)) {
    throw std::runtime_error("unsupported --laur-static-rule " +
                             args.laur_static_rule);
  }
  if (values.count("verbose")) args.verbose = std::stoi(values["verbose"]);

  if (args.method != "lacam_star" && args.method != "lacam_star_ltm" &&
      args.method != "lacam_star_lau_ltm") {
    throw std::runtime_error("unsupported --method " + args.method);
  }
  if (args.traffic_map_edge_filter != "all" &&
      args.traffic_map_edge_filter != "nonzero") {
    throw std::runtime_error("unsupported --traffic-map-edge-filter " +
                             args.traffic_map_edge_filter);
  }
  return args;
}

bool laur_runtime_requested(const Args& args)
{
  return (args.method == "lacam_star_lau_ltm" || args.laur_enable ||
          !args.laur_static_rule.empty()) &&
         !args.laur_disable;
}

uint sum_info_values(const std::string& info, const std::string& key)
{
  uint sum = 0;
  std::istringstream stream(info);
  std::string line;
  const auto prefix = key + "=";
  while (std::getline(stream, line)) {
    if (line.rfind(prefix, 0) != 0) continue;
    try {
      sum += static_cast<uint>(std::stoul(line.substr(prefix.size())));
    } catch (...) {
    }
  }
  return sum;
}

struct RunStats {
  Solution solution;
  std::string additional_info;
  double runtime_ms = 0.0;
  uint loop_cnt = 0;
  uint expanded_nodes = 0;
  uint high_level_expansions = 0;
  uint low_level_pibt_calls = 0;
  bool has_low_level_pibt_calls = false;
  double time_to_first_solution_ms = std::numeric_limits<double>::quiet_NaN();
  uint returned_solutions_count = 0;
  uint ltm_iterations = 0;
  uint committed_events = 0;
  uint blocked_events = 0;
  uint nonzero_ltm_edges = 0;
  bool laur_enabled = false;
  bool laur_force_additive = false;
  bool laur_safety_enabled = true;
  std::string laur_update_mode = "disabled";
  std::string laur_model_path;
  std::string laur_static_rule;
  uint laur_inference_count = 0;
  double laur_inference_total_ms = 0.0;
  uint laur_additive_fallback_count = 0;
  uint laur_safety_disabled_count = 0;
  uint laur_update_period_restarts = 1;
  bool laur_post_first_solution_only = true;
  std::map<std::string, uint> laur_selected_rules;
};

std::string default_traffic_map_run_id(const Args& args)
{
  if (!args.traffic_map_run_id.empty()) return args.traffic_map_run_id;
  std::ostringstream out;
  out << args.map_name << "__a" << args.agents << "__s" << args.seed;
  return out.str();
}

uint vertex_x(const Graph& graph, const Vertex* vertex)
{
  return graph.width == 0 ? 0 : vertex->index % graph.width;
}

uint vertex_y(const Graph& graph, const Vertex* vertex)
{
  return graph.width == 0 ? 0 : vertex->index / graph.width;
}

void append_traffic_map_jsonl(const Args& args, const Instance& instance,
                              const czr004::ltm::DirectedTrafficMap& traffic_map)
{
  if (args.traffic_map_jsonl.empty()) return;

  const auto output_path = std::filesystem::path(args.traffic_map_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open traffic map JSONL");

  const auto& graph = traffic_map.graph();
  const auto run_id = default_traffic_map_run_id(args);
  for (const auto* from : graph.V) {
    for (const auto* to : from->neighbor) {
      const auto raw_count = traffic_map.raw_count(from->id, to->id);
      if (args.traffic_map_edge_filter == "nonzero" && raw_count <= 0.0) {
        continue;
      }
      const auto weight = traffic_map.normalized_weight(from->id, to->id);

      out << "{";
      out << "\"schema_version\":\"phase3_edge_label_v1\"";
      out << ",\"run_id\":" << json_string(run_id);
      out << ",\"source\":\"final_ltm_traffic_map\"";
      out << ",\"method\":" << json_string(args.method);
      out << ",\"map\":" << json_string(args.map_name);
      out << ",\"scen\":" << json_string(args.scen_id);
      out << ",\"agents\":" << args.agents;
      out << ",\"seed\":" << args.seed;
      out << ",\"time_limit_sec\":" << json_number_or_null(args.time_limit_sec);
      out << ",\"objective\":\"sum_of_loss\"";
      out << ",\"from_id\":" << from->id;
      out << ",\"to_id\":" << to->id;
      out << ",\"from_index\":" << from->index;
      out << ",\"to_index\":" << to->index;
      out << ",\"from_x\":" << vertex_x(graph, from);
      out << ",\"from_y\":" << vertex_y(graph, from);
      out << ",\"to_x\":" << vertex_x(graph, to);
      out << ",\"to_y\":" << vertex_y(graph, to);
      out << ",\"from_degree\":" << from->neighbor.size();
      out << ",\"to_degree\":" << to->neighbor.size();
      out << ",\"ltm_raw_count\":" << json_number_or_null(raw_count);
      out << ",\"ltm_normalized_weight\":" << json_number_or_null(weight);
      out << ",\"warm_start_target_weight\":" << json_number_or_null(weight);
      out << ",\"residual_reference_weight\":" << json_number_or_null(weight);
      out << ",\"residual_delta_target\":0";
      out << ",\"traversal_cost\":" << json_number_or_null(1.0 + weight);
      out << ",\"nonzero\":" << (raw_count > 0.0 ? "true" : "false");
      out << ",\"map_vertices\":" << instance.G.size();
      out << "}\n";
    }
  }
}

RunStats run_lacam_star(const Instance& instance, const Args& args)
{
  RunStats stats;
  auto deadline = Deadline(args.time_limit_sec * 1000.0);
  auto random_engine = std::mt19937(args.seed);
  const auto started = std::chrono::steady_clock::now();
  stats.solution =
      solve(instance, stats.additional_info, args.verbose, &deadline,
            &random_engine, Objective::OBJ_SUM_OF_LOSS);
  const auto ended = std::chrono::steady_clock::now();
  stats.runtime_ms =
      std::chrono::duration<double, std::milli>(ended - started).count();
  if (!stats.solution.empty()) {
    stats.time_to_first_solution_ms = stats.runtime_ms;
  }
  stats.loop_cnt = sum_info_values(stats.additional_info, "loop_cnt");
  stats.high_level_expansions = stats.loop_cnt;
  stats.expanded_nodes = sum_info_values(stats.additional_info, "num_node_gen");
  stats.returned_solutions_count = stats.solution.empty() ? 0 : 1;
  return stats;
}

RunStats run_lacam_star_ltm(const Instance& instance, const Args& args)
{
  RunStats stats;
  stats.laur_enabled = laur_runtime_requested(args);
  stats.laur_force_additive = stats.laur_enabled && args.laur_force_additive;
  stats.laur_safety_enabled = args.laur_safety_enabled;
  stats.laur_model_path = args.laur_model_path;
  stats.laur_static_rule = args.laur_static_rule;
  stats.laur_update_period_restarts = args.laur_every_k_restarts;
  stats.laur_post_first_solution_only = args.laur_post_first_solution_only;
  if (!stats.laur_enabled) {
    stats.laur_update_mode = "disabled";
  } else if (stats.laur_force_additive) {
    stats.laur_update_mode = "force_additive";
  } else if (!stats.laur_static_rule.empty()) {
    stats.laur_update_mode = "static_rule";
  } else {
    stats.laur_update_mode = "runtime";
  }

  czr004::ltm::LtmOptions options;
  options.objective = Objective::OBJ_SUM_OF_LOSS;
  options.time_limit_ms = args.time_limit_sec * 1000.0;
  options.max_iterations = args.ltm_max_iterations;
  options.node_budget_factor = 10;
  options.verbose = args.verbose;
  options.seed = args.seed;

  auto runtime = czr004::ntm::LaurLtmRuntime();
  const auto static_params =
      !args.laur_static_rule.empty()
          ? czr004::ntm::update_params_for_laur_rule_id(args.laur_static_rule)
          : czr004::ltm::UpdateParams::additive();
  if (stats.laur_enabled) {
    czr004::ntm::LaurRuntimeOptions runtime_options;
    runtime_options.enabled = true;
    runtime_options.force_additive = args.laur_force_additive;
    runtime_options.safety_enabled = args.laur_safety_enabled;
    runtime_options.model_path = args.laur_model_path;
    runtime_options.post_first_solution_only = args.laur_post_first_solution_only;
    runtime_options.update_period_restarts = args.laur_every_k_restarts;
    if (!runtime.load(runtime_options)) {
      throw std::runtime_error("failed to load LAUR runtime model path " +
                               args.laur_model_path);
    }

    options.update_policy =
        [&](const czr004::ltm::LtmUpdateContext& context) {
          const auto additive = czr004::ltm::UpdateParams::additive();
          if (context.instance == nullptr || context.traffic_before == nullptr ||
              context.trace_events == nullptr) {
            ++stats.laur_additive_fallback_count;
            return additive;
          }
          if (args.laur_post_first_solution_only &&
              !context.stats.has_incumbent_before) {
            ++stats.laur_additive_fallback_count;
            return additive;
          }
          if (context.stats.iteration % args.laur_every_k_restarts != 0) {
            ++stats.laur_additive_fallback_count;
            return additive;
          }
          if (!args.laur_static_rule.empty()) {
            ++stats.laur_selected_rules[args.laur_static_rule];
            return static_params;
          }

          const auto features = czr004::ntm::build_laur_features(
              *context.instance, *context.traffic_before,
              *context.trace_events, context.stats);
          const auto prediction = runtime.predict(features);
          ++stats.laur_inference_count;
          stats.laur_inference_total_ms += prediction.inference_ms;
          ++stats.laur_selected_rules[prediction.rule_id];

          if (!prediction.enabled) {
            ++stats.laur_additive_fallback_count;
            return additive;
          }
          if (!args.laur_force_additive && args.laur_safety_enabled &&
              prediction.safety_harmful_prob >= args.laur_safety_threshold) {
            ++stats.laur_safety_disabled_count;
            ++stats.laur_additive_fallback_count;
            return additive;
          }
          return prediction.params;
        };
  }

  const auto started = std::chrono::steady_clock::now();
  const auto result = czr004::ltm::solve_with_ltm(instance, options);
  const auto ended = std::chrono::steady_clock::now();
  stats.runtime_ms =
      std::chrono::duration<double, std::milli>(ended - started).count();
  stats.solution = result.best_solution;
  stats.time_to_first_solution_ms = result.time_to_first_solution_ms;
  stats.additional_info = result.additional_info;
  stats.loop_cnt = sum_info_values(stats.additional_info, "ltm_one_shot_loop_cnt");
  stats.high_level_expansions = stats.loop_cnt;
  stats.expanded_nodes =
      sum_info_values(stats.additional_info, "ltm_one_shot_num_node_gen");
  stats.low_level_pibt_calls =
      sum_info_values(stats.additional_info, "ltm_one_shot_low_level_pibt_calls");
  stats.has_low_level_pibt_calls = true;
  stats.returned_solutions_count = stats.solution.empty() ? 0 : 1;
  stats.ltm_iterations = result.iterations;
  stats.committed_events = result.trace_summary.committed;
  stats.blocked_events = result.trace_summary.blocked;
  stats.nonzero_ltm_edges = result.traffic_map.nonzero_raw_edges();
  append_traffic_map_jsonl(args, instance, result.traffic_map);
  return stats;
}

void append_jsonl(const Args& args, const std::filesystem::path& binary_path,
                  bool valid_instance, bool success, bool feasible,
                  int sum_of_loss, int lower_bound, int makespan,
                  const RunStats& stats)
{
  const auto ratio =
      (success && lower_bound > 0)
          ? static_cast<double>(sum_of_loss) / static_cast<double>(lower_bound)
          : std::numeric_limits<double>::quiet_NaN();

  const auto output_path = std::filesystem::path(args.output_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open output JSONL");

  const auto output_method =
      args.method_alias.empty() ? args.method : args.method_alias;

  out << "{";
  out << "\"method\":" << json_string(output_method);
  out << ",\"map\":" << json_string(args.map_name);
  out << ",\"map_path\":" << json_string(args.map);
  out << ",\"scen\":" << json_string(args.scen_id);
  out << ",\"scen_path\":" << json_string(args.scen);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"time_limit_sec\":" << json_number_or_null(args.time_limit_sec);
  out << ",\"objective\":\"sum_of_loss\"";
  out << ",\"valid_instance\":" << (valid_instance ? "true" : "false");
  out << ",\"success\":" << (success ? "true" : "false");
  out << ",\"feasible\":" << (feasible ? "true" : "false");
  out << ",\"sum_of_loss\":" << (success ? std::to_string(sum_of_loss) : "null");
  out << ",\"lower_bound\":"
      << (lower_bound > 0 ? std::to_string(lower_bound) : "null");
  out << ",\"sum_of_loss_ratio\":" << json_number_or_null(ratio);
  out << ",\"makespan\":" << (success ? std::to_string(makespan) : "null");
  out << ",\"runtime_ms\":" << json_number_or_null(stats.runtime_ms);
  out << ",\"time_to_first_solution_ms\":"
      << json_number_or_null(stats.time_to_first_solution_ms);
  out << ",\"returned_solutions_count\":" << stats.returned_solutions_count;
  out << ",\"loop_cnt\":" << stats.loop_cnt;
  out << ",\"expanded_nodes\":" << stats.expanded_nodes;
  out << ",\"high_level_expansions\":" << stats.high_level_expansions;
  out << ",\"low_level_pibt_calls\":"
      << (stats.has_low_level_pibt_calls ? std::to_string(stats.low_level_pibt_calls)
                                         : "null");
  out << ",\"ltm_iterations\":" << stats.ltm_iterations;
  out << ",\"committed_events\":" << stats.committed_events;
  out << ",\"blocked_events\":" << stats.blocked_events;
  out << ",\"nonzero_ltm_edges\":" << stats.nonzero_ltm_edges;
  out << ",\"laur_enabled\":" << (stats.laur_enabled ? "true" : "false");
  out << ",\"laur_force_additive\":"
      << (stats.laur_force_additive ? "true" : "false");
  out << ",\"laur_safety_enabled\":"
      << (stats.laur_safety_enabled ? "true" : "false");
  out << ",\"laur_update_mode\":" << json_string(stats.laur_update_mode);
  out << ",\"laur_model_path\":" << json_string(stats.laur_model_path);
  out << ",\"laur_static_rule\":" << json_string(stats.laur_static_rule);
  out << ",\"laur_inference_count\":" << stats.laur_inference_count;
  out << ",\"laur_inference_total_ms\":"
      << json_number_or_null(stats.laur_inference_total_ms);
  out << ",\"laur_update_runtime_ms\":"
      << json_number_or_null(stats.laur_inference_total_ms);
  out << ",\"laur_additive_fallback_count\":"
      << stats.laur_additive_fallback_count;
  out << ",\"laur_safety_disabled_count\":"
      << stats.laur_safety_disabled_count;
  out << ",\"laur_update_period_restarts\":"
      << stats.laur_update_period_restarts;
  out << ",\"laur_post_first_solution_only\":"
      << (stats.laur_post_first_solution_only ? "true" : "false");
  out << ",\"laur_selected_rules\":";
  append_json_string_uint_map(out, stats.laur_selected_rules);
  out << ",\"git_commit\":" << json_string(args.project_commit);
  out << ",\"external_lacam2_commit\":" << json_string(args.external_commit);
  out << ",\"branch\":" << json_string(args.branch);
  out << ",\"dirty\":" << json_string(args.dirty);
  out << ",\"binary_path\":" << json_string(binary_path.string());
  out << ",\"config_path\":" << json_string(args.manifest);
  out << ",\"platform\":" << json_string(args.platform);
  out << "}\n";
}

}  // namespace

int main(int argc, char** argv)
{
  try {
    const auto args = parse_args(argc, argv);
    const auto binary_path = std::filesystem::absolute(argv[0]);

    const auto instance = Instance(args.scen, args.map, args.agents);
    const auto valid_instance = instance.is_valid(args.verbose);
    RunStats stats;
    bool success = false;
    bool feasible = false;
    int sum_of_loss = 0;
    int lower_bound = 0;
    int makespan = 0;

    if (valid_instance) {
      if (args.method == "lacam_star") {
        stats = run_lacam_star(instance, args);
      } else {
        stats = run_lacam_star_ltm(instance, args);
      }
      success = !stats.solution.empty();
      feasible = success && is_feasible_solution(instance, stats.solution, 1);
      if (success) {
        auto dist_table = DistTable(instance);
        sum_of_loss = get_sum_of_loss(stats.solution);
        lower_bound = get_sum_of_costs_lower_bound(instance, dist_table);
        makespan = get_makespan(stats.solution);
      }
    }

    append_jsonl(args, binary_path, valid_instance, success, feasible,
                 sum_of_loss, lower_bound, makespan, stats);

    std::cout << "phase1a_batch"
              << " method=" << args.method << " map=" << args.map_name
              << " agents=" << args.agents << " seed=" << args.seed
              << " success=" << success << " feasible=" << feasible
              << " sum_of_loss=" << (success ? sum_of_loss : 0)
              << " lower_bound=" << lower_bound << std::endl;
    return success && feasible ? 0 : 2;
  } catch (const std::exception& e) {
    std::cerr << "phase1a_batch: " << e.what() << std::endl;
    return 1;
  }
}
