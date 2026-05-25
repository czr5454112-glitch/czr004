#include "ltm.hpp"

#include <lacam2.hpp>

#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <random>
#include <sstream>
#include <string>
#include <unordered_map>

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
  uint agents = 0;
  uint seed = 0;
  double time_limit_sec = 30.0;
  uint ltm_max_iterations = 100000;
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

Args parse_args(int argc, char** argv)
{
  auto values = std::unordered_map<std::string, std::string>();
  for (int i = 1; i < argc; ++i) {
    const auto key = std::string(argv[i]);
    if (key.rfind("--", 0) != 0 || i + 1 >= argc) {
      throw std::runtime_error("invalid argument near " + key);
    }
    values[key.substr(2)] = argv[++i];
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
  if (values.count("verbose")) args.verbose = std::stoi(values["verbose"]);

  if (args.method != "lacam_star" && args.method != "lacam_star_ltm") {
    throw std::runtime_error("unsupported --method " + args.method);
  }
  return args;
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
  uint returned_solutions_count = 0;
  uint ltm_iterations = 0;
  uint committed_events = 0;
  uint blocked_events = 0;
  uint nonzero_ltm_edges = 0;
};

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
  stats.loop_cnt = sum_info_values(stats.additional_info, "loop_cnt");
  stats.high_level_expansions = stats.loop_cnt;
  stats.expanded_nodes = sum_info_values(stats.additional_info, "num_node_gen");
  stats.returned_solutions_count = stats.solution.empty() ? 0 : 1;
  return stats;
}

RunStats run_lacam_star_ltm(const Instance& instance, const Args& args)
{
  RunStats stats;
  czr004::ltm::LtmOptions options;
  options.objective = Objective::OBJ_SUM_OF_LOSS;
  options.time_limit_ms = args.time_limit_sec * 1000.0;
  options.max_iterations = args.ltm_max_iterations;
  options.node_budget_factor = 10;
  options.verbose = args.verbose;
  options.seed = args.seed;

  const auto started = std::chrono::steady_clock::now();
  const auto result = czr004::ltm::solve_with_ltm(instance, options);
  const auto ended = std::chrono::steady_clock::now();
  stats.runtime_ms =
      std::chrono::duration<double, std::milli>(ended - started).count();
  stats.solution = result.best_solution;
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

  out << "{";
  out << "\"method\":" << json_string(args.method);
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
  out << ",\"time_to_first_solution_ms\":null";
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
