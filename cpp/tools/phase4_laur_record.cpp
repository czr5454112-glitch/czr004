#include "ltm.hpp"

#include <lacam2.hpp>

#include <chrono>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>

namespace {

struct Args {
  std::string map;
  std::string scen;
  std::string map_name;
  std::string split = "train";
  std::string run_id;
  std::string checkpoint_jsonl;
  std::string trace_jsonl;
  std::string traffic_snapshot_root;
  std::string branch;
  std::string commit;
  std::string dirty;
  uint agents = 0;
  uint seed = 0;
  double time_limit_sec = 3.0;
  uint max_iterations = 4;
  uint checkpoint_topk_edges = 16;
  int verbose = 0;
  bool export_raw_trace = true;
  bool export_checkpoints = true;
  bool force_additive = false;
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
  args.checkpoint_jsonl = require("checkpoint-jsonl");
  args.trace_jsonl = require("trace-jsonl");
  args.traffic_snapshot_root = require("traffic-snapshot-root");
  args.branch = values.count("branch") ? values["branch"] : "";
  args.commit = values.count("commit") ? values["commit"] : "";
  args.dirty = values.count("dirty") ? values["dirty"] : "";

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
  if (values.count("checkpoint-topk-edges") &&
      !parse_uint(values["checkpoint-topk-edges"],
                  &args.checkpoint_topk_edges)) {
    throw std::runtime_error("invalid --checkpoint-topk-edges");
  }
  if (values.count("verbose")) args.verbose = std::stoi(values["verbose"]);

  args.export_raw_trace = flags.count("export-raw-trace") > 0 ||
                          values.count("export-raw-trace") == 0;
  args.export_checkpoints = flags.count("export-checkpoints") > 0 ||
                            values.count("export-checkpoints") == 0;
  args.force_additive = flags.count("force-additive") > 0;

  if (args.split != "train" && args.split != "validation" &&
      args.split != "test") {
    throw std::runtime_error("--split must be train, validation, or test");
  }
  return args;
}

std::string safe_filename(const std::string& value)
{
  std::string out;
  out.reserve(value.size());
  for (const unsigned char ch : value) {
    if (std::isalnum(ch) || ch == '-' || ch == '_' || ch == '.') {
      out.push_back(static_cast<char>(ch));
    } else {
      out.push_back('_');
    }
  }
  return out.empty() ? "checkpoint" : out;
}

std::string default_run_id(const Args& args)
{
  if (!args.run_id.empty()) return args.run_id;
  std::ostringstream out;
  out << args.map_name << "__a" << args.agents << "__s" << args.seed
      << "__phase4c";
  return out.str();
}

std::string checkpoint_id_for(const std::string& run_id, uint iteration)
{
  std::ostringstream out;
  out << run_id << "__iter" << iteration;
  return out.str();
}

std::string kind_string(czr004::ltm::TraceEventKind kind)
{
  return kind == czr004::ltm::TraceEventKind::Committed ? "committed"
                                                        : "blocked";
}

std::string propagation_kind(const czr004::ltm::TraceEvent& event)
{
  if (event.from_id != event.to_id) return "none";
  return event.at_goal ? "goal_wait_ignored" : "wait_propagated";
}

std::string blocked_reason_category_string(
    czr004::ltm::BlockedReasonCategory reason)
{
  switch (reason) {
    case czr004::ltm::BlockedReasonCategory::None:
      return "none";
    case czr004::ltm::BlockedReasonCategory::VertexConflict:
      return "vertex_conflict";
    case czr004::ltm::BlockedReasonCategory::EdgeSwap:
      return "edge_swap";
    case czr004::ltm::BlockedReasonCategory::PriorityBlock:
      return "priority_block";
    case czr004::ltm::BlockedReasonCategory::BacktrackOrInheritance:
      return "backtrack_or_inheritance";
    case czr004::ltm::BlockedReasonCategory::Unknown:
      return "unknown";
  }
  return "unknown";
}

void write_raw_topk(std::ostream& out,
                    const std::vector<czr004::ltm::TrafficEdgeSnapshot>& edges)
{
  out << "[";
  for (std::size_t i = 0; i < edges.size(); ++i) {
    if (i > 0) out << ",";
    out << "{\"from_id\":" << edges[i].from_id;
    out << ",\"to_id\":" << edges[i].to_id;
    out << ",\"raw\":" << json_number_or_null(edges[i].raw);
    out << "}";
  }
  out << "]";
}

void write_normalized_topk(
    std::ostream& out,
    const std::vector<czr004::ltm::TrafficEdgeSnapshot>& edges)
{
  out << "[";
  for (std::size_t i = 0; i < edges.size(); ++i) {
    if (i > 0) out << ",";
    out << "{\"from_id\":" << edges[i].from_id;
    out << ",\"to_id\":" << edges[i].to_id;
    out << ",\"weight\":" << json_number_or_null(edges[i].weight);
    out << "}";
  }
  out << "]";
}

void write_snapshot_edges(
    std::ostream& out,
    const std::vector<czr004::ltm::TrafficEdgeSnapshot>& edges)
{
  out << "[";
  for (std::size_t i = 0; i < edges.size(); ++i) {
    if (i > 0) out << ",";
    out << "{\"from_id\":" << edges[i].from_id;
    out << ",\"to_id\":" << edges[i].to_id;
    out << ",\"raw\":" << json_number_or_null(edges[i].raw);
    out << ",\"weight\":" << json_number_or_null(edges[i].weight);
    out << "}";
  }
  out << "]";
}

void write_snapshot_json(
    const std::filesystem::path& path, const std::string& run_id,
    const std::string& checkpoint_id,
    const czr004::ltm::LtmIterationCheckpoint& checkpoint)
{
  std::filesystem::create_directories(path.parent_path());
  std::ofstream out(path);
  if (!out) throw std::runtime_error("cannot write traffic snapshot");

  out << "{";
  out << "\"schema_version\":\"phase4_laur_traffic_snapshot_v1\"";
  out << ",\"run_id\":" << json_string(run_id);
  out << ",\"checkpoint_id\":" << json_string(checkpoint_id);
  out << ",\"iteration\":" << checkpoint.iteration;
  out << ",\"before\":{";
  out << "\"nonzero_edges\":" << checkpoint.traffic_before.nonzero_edges;
  out << ",\"max_raw\":" << json_number_or_null(checkpoint.traffic_before.max_raw);
  out << ",\"max_normalized\":"
      << json_number_or_null(checkpoint.traffic_before.max_normalized);
  out << ",\"raw_topk\":";
  write_snapshot_edges(out, checkpoint.traffic_before.raw_topk);
  out << ",\"normalized_topk\":";
  write_snapshot_edges(out, checkpoint.traffic_before.normalized_topk);
  out << "}";
  out << ",\"after\":{";
  out << "\"nonzero_edges\":" << checkpoint.traffic_after.nonzero_edges;
  out << ",\"max_raw\":" << json_number_or_null(checkpoint.traffic_after.max_raw);
  out << ",\"max_normalized\":"
      << json_number_or_null(checkpoint.traffic_after.max_normalized);
  out << ",\"raw_topk\":";
  write_snapshot_edges(out, checkpoint.traffic_after.raw_topk);
  out << ",\"normalized_topk\":";
  write_snapshot_edges(out, checkpoint.traffic_after.normalized_topk);
  out << "}";
  out << "}\n";
}

struct TraceCounts {
  uint committed = 0;
  uint blocked = 0;
  uint wait = 0;
  uint goal_wait_ignored = 0;
  uint blocked_unique_edges = 0;
  uint topk_blocked_edges = 0;
  double topk_blocked_edge_concentration = 0.0;
  double blocked_edge_entropy = 0.0;
};

TraceCounts count_trace_events(
    const std::vector<czr004::ltm::TraceEvent>& events,
    const std::vector<czr004::ltm::TrafficEdgeSnapshot>& raw_after_topk)
{
  TraceCounts counts;
  std::set<std::pair<uint, uint>> topk_after_edges;
  for (const auto& edge : raw_after_topk) {
    topk_after_edges.insert({edge.from_id, edge.to_id});
  }
  std::map<std::pair<uint, uint>, uint> blocked_edges;
  for (const auto& event : events) {
    if (event.kind == czr004::ltm::TraceEventKind::Committed) {
      ++counts.committed;
    } else {
      ++counts.blocked;
      const auto edge = std::make_pair(event.from_id, event.to_id);
      ++blocked_edges[edge];
      if (topk_after_edges.count(edge) > 0) {
        ++counts.topk_blocked_edges;
      }
    }
    if (event.from_id == event.to_id) {
      if (event.at_goal) {
        ++counts.goal_wait_ignored;
      } else {
        ++counts.wait;
      }
    }
  }
  counts.blocked_unique_edges = static_cast<uint>(blocked_edges.size());
  if (counts.blocked > 0) {
    counts.topk_blocked_edge_concentration =
        static_cast<double>(counts.topk_blocked_edges) /
        static_cast<double>(counts.blocked);
    for (const auto& item : blocked_edges) {
      const auto probability =
          static_cast<double>(item.second) / static_cast<double>(counts.blocked);
      if (probability > 0.0) {
        counts.blocked_edge_entropy -= probability * std::log(probability);
      }
    }
  }
  return counts;
}

void write_trace_rows(std::ostream& out, const Args& args,
                      const std::string& run_id,
                      const std::string& checkpoint_id,
                      const czr004::ltm::LtmIterationCheckpoint& checkpoint)
{
  for (std::size_t index = 0; index < checkpoint.trace_events.size(); ++index) {
    const auto& event = checkpoint.trace_events[index];
    const auto is_wait = event.from_id == event.to_id;
    out << "{";
    out << "\"schema_version\":\"phase4_laur_trace_event_v1\"";
    out << ",\"run_id\":" << json_string(run_id);
    out << ",\"checkpoint_id\":" << json_string(checkpoint_id);
    out << ",\"iteration\":" << checkpoint.iteration;
    out << ",\"event_index\":" << index;
    out << ",\"kind\":" << json_string(kind_string(event.kind));
    out << ",\"agent_id\":" << event.agent_id;
    out << ",\"from_id\":" << event.from_id;
    out << ",\"to_id\":" << event.to_id;
    out << ",\"at_goal\":" << (event.at_goal ? "true" : "false");
    out << ",\"is_wait\":" << (is_wait ? "true" : "false");
    out << ",\"propagation_kind\":"
        << json_string(propagation_kind(event));
    out << ",\"propagated_to_id\":null";
    out << ",\"map_name\":" << json_string(args.map_name);
    out << ",\"agents\":" << args.agents;
    out << ",\"seed\":" << args.seed;
    out << "}\n";
  }
}

void write_pibt_failure_audit(
    std::ostream& out,
    const std::vector<czr004::ltm::PibtFailureAudit>& audits)
{
  out << "[";
  for (std::size_t index = 0; index < audits.size(); ++index) {
    const auto& audit = audits[index];
    if (index > 0) out << ",";
    auto reason_histogram = std::map<std::string, uint>();
    auto rank_histogram = std::map<uint, uint>();
    auto reasons = std::vector<std::string>();
    auto exact_subreason = std::string();
    for (const auto& failed : audit.failed_candidates) {
      const auto reason = blocked_reason_category_string(failed.reason);
      reasons.push_back(reason);
      ++reason_histogram[reason];
      ++rank_histogram[failed.candidate_rank];
      if (exact_subreason.empty() &&
          !failed.exact_priority_block_subreason.empty()) {
        exact_subreason = failed.exact_priority_block_subreason;
      }
    }

    out << "{";
    out << "\"audit_precision\":" << json_string(audit.audit_precision);
    out << ",\"pibt_return_false_agent_id\":" << audit.agent_id;
    out << ",\"pibt_return_false_from_id\":" << audit.from_id;
    out << ",\"pibt_return_false_at_goal\":"
        << (audit.at_goal ? "true" : "false");
    out << ",\"pibt_return_false_candidate_count\":"
        << audit.failed_candidates.size();
    out << ",\"exact_priority_block_subreason\":"
        << json_string(exact_subreason);
    out << ",\"all_failed_candidate_reasons_when_pibt_returns_false\":[";
    for (std::size_t i = 0; i < reasons.size(); ++i) {
      if (i > 0) out << ",";
      out << json_string(reasons[i]);
    }
    out << "]";
    out << ",\"failed_candidate_rank_histogram_when_pibt_returns_false\":{";
    auto first_rank = true;
    for (const auto& [rank, count] : rank_histogram) {
      if (!first_rank) out << ",";
      first_rank = false;
      out << json_string(std::to_string(rank)) << ":" << count;
    }
    out << "}";
    out << ",\"failed_candidate_reason_histogram_when_pibt_returns_false\":{";
    auto first_reason = true;
    for (const auto& [reason, count] : reason_histogram) {
      if (!first_reason) out << ",";
      first_reason = false;
      out << json_string(reason) << ":" << count;
    }
    out << "}";
    out << ",\"first_failed_candidate_reason\":"
        << json_string(reasons.empty() ? "" : reasons.front());
    out << ",\"last_failed_candidate_reason\":"
        << json_string(reasons.empty() ? "" : reasons.back());
    out << "}";
  }
  out << "]";
}

void write_checkpoint_row(
    std::ostream& out, const Args& args, const std::string& run_id,
    const std::string& checkpoint_id, const std::filesystem::path& snapshot_path,
    const czr004::ltm::LtmIterationCheckpoint& checkpoint)
{
  const auto counts =
      count_trace_events(checkpoint.trace_events, checkpoint.traffic_after.raw_topk);

  out << "{";
  out << "\"schema_version\":\"phase4_laur_checkpoint_v1\"";
  out << ",\"run_id\":" << json_string(run_id);
  out << ",\"checkpoint_id\":" << json_string(checkpoint_id);
  out << ",\"split\":" << json_string(args.split);
  out << ",\"map_name\":" << json_string(args.map_name);
  out << ",\"map_path\":" << json_string(args.map);
  out << ",\"scen_path\":" << json_string(args.scen);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"time_limit_sec\":" << json_number_or_null(args.time_limit_sec);
  out << ",\"max_iterations\":" << args.max_iterations;
  out << ",\"iteration\":" << checkpoint.iteration;
  out << ",\"node_budget\":" << checkpoint.node_budget;
  out << ",\"solution_found_this_iteration\":"
      << (checkpoint.solution_found_this_iteration ? "true" : "false");
  out << ",\"sum_of_loss_this_iteration\":"
      << (checkpoint.solution_found_this_iteration
              ? std::to_string(checkpoint.sum_of_loss_this_iteration)
              : "null");
  out << ",\"lower_bound_sol\":" << checkpoint.lower_bound_sol;
  out << ",\"sum_of_loss_ratio_this_iteration\":"
      << json_number_or_null(checkpoint.sum_of_loss_ratio_this_iteration);
  out << ",\"expanded_nodes_this_iteration\":"
      << checkpoint.expanded_nodes_this_iteration;
  out << ",\"high_level_expansions_this_iteration\":"
      << checkpoint.high_level_expansions_this_iteration;
  out << ",\"low_level_pibt_calls_this_iteration\":"
      << checkpoint.low_level_pibt_calls_this_iteration;
  out << ",\"trace_event_count\":" << checkpoint.trace_events.size();
  out << ",\"pibt_failure_audit\":";
  write_pibt_failure_audit(out, checkpoint.pibt_failure_audits);
  out << ",\"committed_count\":" << counts.committed;
  out << ",\"blocked_count\":" << counts.blocked;
  out << ",\"wait_event_count\":" << counts.wait;
  out << ",\"goal_wait_ignored_count\":" << counts.goal_wait_ignored;
  out << ",\"blocked_unique_edge_count\":" << counts.blocked_unique_edges;
  out << ",\"topk_blocked_edge_count\":" << counts.topk_blocked_edges;
  out << ",\"topk_blocked_edge_concentration\":"
      << json_number_or_null(counts.topk_blocked_edge_concentration);
  out << ",\"blocked_edge_entropy\":"
      << json_number_or_null(counts.blocked_edge_entropy);
  out << ",\"traffic_before_nonzero_edges\":"
      << checkpoint.traffic_before.nonzero_edges;
  out << ",\"traffic_after_nonzero_edges\":"
      << checkpoint.traffic_after.nonzero_edges;
  out << ",\"traffic_before_max_raw\":"
      << json_number_or_null(checkpoint.traffic_before.max_raw);
  out << ",\"traffic_after_max_raw\":"
      << json_number_or_null(checkpoint.traffic_after.max_raw);
  out << ",\"traffic_after_max_normalized\":"
      << json_number_or_null(checkpoint.traffic_after.max_normalized);
  out << ",\"raw_before_topk\":";
  write_raw_topk(out, checkpoint.traffic_before.raw_topk);
  out << ",\"raw_after_topk\":";
  write_raw_topk(out, checkpoint.traffic_after.raw_topk);
  out << ",\"normalized_after_topk\":";
  write_normalized_topk(out, checkpoint.traffic_after.normalized_topk);
  out << ",\"trace_path\":" << json_string(args.trace_jsonl);
  out << ",\"traffic_snapshot_path\":" << json_string(snapshot_path.string());
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

    std::filesystem::create_directories(
        std::filesystem::path(args.checkpoint_jsonl).parent_path());
    std::filesystem::create_directories(
        std::filesystem::path(args.trace_jsonl).parent_path());
    std::filesystem::create_directories(args.traffic_snapshot_root);

    std::ofstream checkpoint_out(args.checkpoint_jsonl, std::ios::app);
    if (!checkpoint_out) {
      throw std::runtime_error("cannot open checkpoint JSONL");
    }
    std::ofstream trace_out(args.trace_jsonl, std::ios::app);
    if (!trace_out) throw std::runtime_error("cannot open trace JSONL");

    const auto instance = Instance(args.scen, args.map, args.agents);
    if (!instance.is_valid(args.verbose)) {
      throw std::runtime_error("invalid MAPF instance");
    }

    czr004::ltm::LtmOptions options;
    options.objective = Objective::OBJ_SUM_OF_LOSS;
    options.time_limit_ms = args.time_limit_sec * 1000.0;
    options.max_iterations = args.max_iterations;
    options.node_budget_factor = 10;
    options.verbose = args.verbose;
    options.seed = args.seed;
    options.checkpoint_topk_edges = args.checkpoint_topk_edges;
    options.update_params = czr004::ltm::UpdateParams::additive();
    options.update_params.force_additive = args.force_additive;
    options.iteration_callback =
        [&](const czr004::ltm::LtmIterationCheckpoint& checkpoint) {
          const auto checkpoint_id = checkpoint_id_for(run_id, checkpoint.iteration);
          const auto snapshot_path =
              std::filesystem::path(args.traffic_snapshot_root) /
              (safe_filename(checkpoint_id) + ".json");
          if (args.export_checkpoints) {
            write_snapshot_json(snapshot_path, run_id, checkpoint_id, checkpoint);
            write_checkpoint_row(checkpoint_out, args, run_id, checkpoint_id,
                                 snapshot_path, checkpoint);
          }
          if (args.export_raw_trace) {
            write_trace_rows(trace_out, args, run_id, checkpoint_id, checkpoint);
          }
        };

    const auto started = std::chrono::steady_clock::now();
    const auto result = czr004::ltm::solve_with_ltm(instance, options);
    const auto ended = std::chrono::steady_clock::now();
    const auto runtime_ms =
        std::chrono::duration<double, std::milli>(ended - started).count();

    const auto success = !result.best_solution.empty();
    const auto feasible =
        success && is_feasible_solution(instance, result.best_solution, 1);
    std::cout << "phase4_laur_record"
              << " run_id=" << run_id
              << " map=" << args.map_name
              << " agents=" << args.agents
              << " seed=" << args.seed
              << " iterations=" << result.iterations
              << " success=" << success
              << " feasible=" << feasible
              << " runtime_ms=" << runtime_ms
              << " checkpoint_jsonl=" << args.checkpoint_jsonl
              << " trace_jsonl=" << args.trace_jsonl << std::endl;

    return 0;
  } catch (const std::exception& e) {
    std::cerr << "phase4_laur_record: " << e.what() << std::endl;
    return 1;
  }
}
