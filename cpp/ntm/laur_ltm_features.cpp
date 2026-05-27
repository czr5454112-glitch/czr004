#include "laur_ltm_features.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <unordered_map>

namespace czr004::ntm {

namespace {

constexpr uint kTopKEdges = 16;

std::uint64_t edge_key(uint from_id, uint to_id)
{
  return (static_cast<std::uint64_t>(from_id) << 32) |
         static_cast<std::uint64_t>(to_id);
}

double ratio(double numerator, double denominator)
{
  return denominator == 0.0 ? 0.0 : numerator / denominator;
}

double entropy(const std::vector<double>& values)
{
  double total = 0.0;
  for (const auto value : values) {
    if (value > 0.0) total += value;
  }
  if (total <= 0.0) return 0.0;

  double out = 0.0;
  for (const auto value : values) {
    if (value <= 0.0) continue;
    const auto p = value / total;
    out -= p * std::log(p);
  }
  return out;
}

std::vector<czr004::ltm::TrafficEdgeSnapshot> top_raw_edges(
    const czr004::ltm::DirectedTrafficMap& traffic_map)
{
  auto snapshot = traffic_map.snapshot(kTopKEdges);
  return snapshot.raw_topk;
}

}  // namespace

LaurFeatureVector build_laur_features(
    const Instance& instance,
    const czr004::ltm::DirectedTrafficMap& traffic_map,
    const std::vector<czr004::ltm::TraceEvent>& trace_events,
    const czr004::ltm::LtmIterationStats& stats)
{
  uint committed = 0;
  uint blocked = 0;
  uint wait = 0;
  uint goal_wait = 0;
  auto additive_delta_by_edge = std::unordered_map<std::uint64_t, double>();
  auto blocked_by_edge = std::unordered_map<std::uint64_t, uint>();
  auto event_counts = std::unordered_map<std::uint64_t, uint>();

  for (const auto& event : trace_events) {
    if (event.kind == czr004::ltm::TraceEventKind::Committed) {
      ++committed;
    } else {
      ++blocked;
      ++blocked_by_edge[edge_key(event.from_id, event.to_id)];
    }

    if (event.from_id == event.to_id) {
      if (event.at_goal) {
        ++goal_wait;
        continue;
      }
      ++wait;
      if (event.from_id < instance.G.V.size()) {
        const auto* from = instance.G.V[event.from_id];
        for (const auto* to : from->neighbor) {
          const auto key = edge_key(from->id, to->id);
          additive_delta_by_edge[key] += 1.0;
          ++event_counts[key];
        }
      }
      continue;
    }

    const auto key = edge_key(event.from_id, event.to_id);
    additive_delta_by_edge[key] += 1.0;
    ++event_counts[key];
  }

  auto raw_edges = top_raw_edges(traffic_map);
  double mean_topk_raw_before = 0.0;
  double max_raw_before = 0.0;
  double local_degree_sum = 0.0;
  uint local_degree_count = 0;
  for (const auto& edge : raw_edges) {
    mean_topk_raw_before += edge.raw;
    max_raw_before = std::max(max_raw_before, edge.raw);
    if (edge.from_id < instance.G.V.size()) {
      local_degree_sum += instance.G.V[edge.from_id]->neighbor.size();
      ++local_degree_count;
    }
    if (edge.to_id < instance.G.V.size()) {
      local_degree_sum += instance.G.V[edge.to_id]->neighbor.size();
      ++local_degree_count;
    }
  }
  if (!raw_edges.empty()) {
    mean_topk_raw_before /= static_cast<double>(raw_edges.size());
  }

  double topk_raw_delta_mean = 0.0;
  double topk_raw_delta_max = 0.0;
  uint new_nonzero_edges = 0;
  auto delta_values = std::vector<double>();
  for (const auto& [key, delta] : additive_delta_by_edge) {
    const auto from_id = static_cast<uint>(key >> 32);
    const auto to_id = static_cast<uint>(key & 0xffffffffu);
    topk_raw_delta_mean += delta;
    topk_raw_delta_max = std::max(topk_raw_delta_max, delta);
    delta_values.push_back(delta);
    if (traffic_map.raw_count(from_id, to_id) <= 0.0 && delta > 0.0) {
      ++new_nonzero_edges;
    }
  }
  if (!additive_delta_by_edge.empty()) {
    topk_raw_delta_mean /= static_cast<double>(additive_delta_by_edge.size());
  }

  uint topk_blocked_count = 0;
  for (const auto& [_, count] : blocked_by_edge) {
    topk_blocked_count = std::max(topk_blocked_count, count);
  }

  auto event_count_values = std::vector<double>();
  event_count_values.reserve(event_counts.size());
  for (const auto& [_, count] : event_counts) {
    event_count_values.push_back(static_cast<double>(count));
  }

  auto weights = std::vector<double>();
  uint saturated_edge_count = 0;
  for (const auto& edge : traffic_map.snapshot(0).normalized_topk) {
    if (edge.raw <= 0.0) continue;
    weights.push_back(edge.weight);
    if (edge.weight >= traffic_map.upper_bound() - 1.0e-12) {
      ++saturated_edge_count;
    }
  }

  const auto free_cells = static_cast<double>(instance.G.size());
  const auto total_cells =
      static_cast<double>(std::max(1u, instance.G.width * instance.G.height));
  const auto obstacle_cells = std::max(0.0, total_cells - free_cells);
  const auto agents = static_cast<double>(instance.N);

  auto out = LaurFeatureVector();
  out.names = {
      "agents",
      "free_cells",
      "density",
      "map_width",
      "map_height",
      "obstacle_ratio",
      "iteration",
      "node_budget",
      "elapsed_ms",
      "time_remaining_sec",
      "max_iterations",
      "has_solution_before",
      "best_ratio_before",
      "improved_last_iteration",
      "returned_solutions_count_so_far",
      "committed_count",
      "blocked_count",
      "wait_event_count",
      "goal_wait_ignored_count",
      "blocked_per_committed",
      "wait_per_committed",
      "blocked_per_agent",
      "committed_per_agent",
      "nonzero_edges_before",
      "max_raw_before",
      "mean_topk_raw_before",
      "max_weight_before",
      "topk_raw_delta_mean",
      "topk_raw_delta_max",
      "new_nonzero_edges_count",
      "topk_blocked_edge_concentration",
      "entropy_edge_usage",
      "local_degree_mean_topk",
      "current_additive_max_normalized_weight",
      "weight_entropy",
      "saturated_edge_count",
  };
  out.values = {
      agents,
      free_cells,
      ratio(agents, free_cells),
      static_cast<double>(instance.G.width),
      static_cast<double>(instance.G.height),
      ratio(obstacle_cells, total_cells),
      static_cast<double>(stats.iteration),
      static_cast<double>(stats.node_budget),
      stats.elapsed_ms,
      stats.time_remaining_sec,
      static_cast<double>(stats.max_iterations),
      stats.has_incumbent_before ? 1.0 : 0.0,
      stats.best_ratio_before,
      stats.improved_incumbent ? 1.0 : 0.0,
      static_cast<double>(stats.returned_solutions_count_so_far),
      static_cast<double>(committed),
      static_cast<double>(blocked),
      static_cast<double>(wait),
      static_cast<double>(goal_wait),
      ratio(static_cast<double>(blocked), static_cast<double>(committed)),
      ratio(static_cast<double>(wait), static_cast<double>(committed)),
      ratio(static_cast<double>(blocked), agents),
      ratio(static_cast<double>(committed), agents),
      static_cast<double>(traffic_map.nonzero_raw_edges()),
      max_raw_before,
      mean_topk_raw_before,
      traffic_map.nonzero_raw_edges() > 0 ? traffic_map.max_normalized_weight() : 0.0,
      topk_raw_delta_mean,
      topk_raw_delta_max,
      static_cast<double>(new_nonzero_edges),
      ratio(static_cast<double>(topk_blocked_count), static_cast<double>(blocked)),
      entropy(event_count_values),
      ratio(local_degree_sum, static_cast<double>(local_degree_count)),
      traffic_map.upper_bound(),
      entropy(weights),
      static_cast<double>(saturated_edge_count),
  };
  return out;
}

}  // namespace czr004::ntm
