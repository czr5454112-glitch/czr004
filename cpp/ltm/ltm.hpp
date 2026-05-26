#pragma once

#include <lacam2.hpp>

#include <cstdint>
#include <functional>
#include <limits>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace czr004::ltm {

enum class TraceEventKind { Committed, Blocked };

struct TraceEvent {
  TraceEventKind kind;
  uint agent_id;
  uint from_id;
  uint to_id;
  bool at_goal;
};

struct TraceSummary {
  uint committed = 0;
  uint blocked = 0;
};

struct TrafficEdgeSnapshot {
  uint from_id = 0;
  uint to_id = 0;
  double raw = 0.0;
  double weight = 0.0;
};

struct TrafficSnapshot {
  uint nonzero_edges = 0;
  double max_raw = 0.0;
  double max_normalized = 0.0;
  std::vector<TrafficEdgeSnapshot> raw_topk;
  std::vector<TrafficEdgeSnapshot> normalized_topk;
};

struct UpdateParams {
  double alpha_commit = 1.0;
  double alpha_block = 1.0;
  double alpha_wait_spillover = 1.0;
  double rho_decay = 1.0;
  bool enable_contraflow_penalty = false;
  double contraflow_penalty = 0.0;
  bool enable_local_saturation = false;
  bool force_additive = false;

  static UpdateParams additive()
  {
    UpdateParams params;
    params.alpha_commit = 1.0;
    params.alpha_block = 1.0;
    params.alpha_wait_spillover = 1.0;
    params.rho_decay = 1.0;
    params.enable_contraflow_penalty = false;
    params.contraflow_penalty = 0.0;
    params.enable_local_saturation = false;
    params.force_additive = true;
    return params;
  }
};

class PibtTraceCollector {
 public:
  void clear();
  void record_committed(uint agent_id, const Vertex* from, const Vertex* to,
                        const Vertex* goal);
  void record_blocked(uint agent_id, const Vertex* from, const Vertex* to,
                      const Vertex* goal);

  const std::vector<TraceEvent>& events() const { return events_; }
  TraceSummary summary() const;

 private:
  std::vector<TraceEvent> events_;
};

class DirectedTrafficMap {
 public:
  DirectedTrafficMap(const Graph& graph, double lower_bound = 0.0,
                     double upper_bound = 10.0);

  void reset();
  void update_from_trace(const std::vector<TraceEvent>& events);
  void update_from_trace(const std::vector<TraceEvent>& events,
                         const UpdateParams& params);

  bool has_edge(uint from_id, uint to_id) const;
  double raw_count(uint from_id, uint to_id) const;
  double normalized_weight(uint from_id, uint to_id) const;
  double traversal_cost(uint from_id, uint to_id) const;
  uint nonzero_raw_edges() const;
  double max_raw_count() const;
  double max_normalized_weight() const;
  TrafficSnapshot snapshot(uint topk_edges) const;
  double lower_bound() const { return lower_bound_; }
  double upper_bound() const { return upper_bound_; }
  const Graph& graph() const { return graph_; }

 private:
  const Graph& graph_;
  double lower_bound_;
  double upper_bound_;
  std::unordered_map<std::uint64_t, double> raw_counts_;
  std::unordered_map<std::uint64_t, double> normalized_weights_;

  static std::uint64_t key(uint from_id, uint to_id);
  void apply_decay(const UpdateParams& params);
  void increment_event(const TraceEvent& event, const UpdateParams& params);
  void increment_edge(uint from_id, uint to_id, double delta);
  void renormalize();
  void renormalize(const UpdateParams& params);
};

class WeightedDistanceTable {
 public:
  static constexpr double INF = std::numeric_limits<double>::infinity();

  WeightedDistanceTable(const Instance* instance, const DirectedTrafficMap* ltm);

  double get(uint agent_id, uint vertex_id);
  double get(uint agent_id, const Vertex* vertex);

 private:
  const Instance* instance_;
  const DirectedTrafficMap* ltm_;
  std::vector<std::vector<Vertex*> > reverse_neighbors_;
  std::vector<std::vector<double> > table_;
  std::vector<bool> solved_;

  void solve_agent(uint agent_id);
};

struct LtmOptions {
  Objective objective = Objective::OBJ_SUM_OF_LOSS;
  double time_limit_ms = 3000.0;
  uint max_iterations = 4;
  uint node_budget_factor = 10;
  int verbose = 0;
  uint seed = 0;
  uint checkpoint_topk_edges = 16;
  UpdateParams update_params = UpdateParams::additive();
  bool retain_iteration_traffic_maps = false;
  std::function<void(const struct LtmIterationCheckpoint&)> iteration_callback;
};

struct LtmIterationCheckpoint {
  uint iteration = 0;
  uint node_budget = 0;
  bool solution_found_this_iteration = false;
  int sum_of_loss_this_iteration = 0;
  int lower_bound_sol = 0;
  double sum_of_loss_ratio_this_iteration =
      std::numeric_limits<double>::quiet_NaN();
  uint expanded_nodes_this_iteration = 0;
  uint high_level_expansions_this_iteration = 0;
  uint low_level_pibt_calls_this_iteration = 0;
  std::vector<TraceEvent> trace_events;
  TrafficSnapshot traffic_before;
  TrafficSnapshot traffic_after;
  std::shared_ptr<const DirectedTrafficMap> traffic_before_map;
  std::shared_ptr<const DirectedTrafficMap> traffic_after_map;
};

struct LtmOneShotProbeOptions {
  Objective objective = Objective::OBJ_SUM_OF_LOSS;
  double short_budget_ms = 1000.0;
  uint node_budget = 0;
  int verbose = 0;
  uint seed = 0;
  UpdateParams update_params = UpdateParams::additive();
};

struct LtmOneShotProbeResult {
  bool solution_found = false;
  bool feasible = false;
  int sum_of_loss = 0;
  int lower_bound_sol = 0;
  double sum_of_loss_ratio = std::numeric_limits<double>::quiet_NaN();
  double runtime_ms = 0.0;
  uint returned_solutions_count = 0;
  uint expanded_nodes = 0;
  uint high_level_expansions = 0;
  uint low_level_pibt_calls = 0;
  TraceSummary trace_summary;
};

struct LtmRunResult {
  Solution best_solution;
  DirectedTrafficMap traffic_map;
  std::string additional_info;
  uint iterations = 0;
  uint last_node_budget = 0;
  TraceSummary trace_summary;
  bool timeout = false;

  LtmRunResult(const Graph& graph, double lower_bound, double upper_bound)
      : traffic_map(graph, lower_bound, upper_bound)
  {
  }
};

LtmRunResult solve_with_ltm(const Instance& instance, const LtmOptions& options);
LtmOneShotProbeResult run_one_shot_update_probe(
    const Instance& instance, const DirectedTrafficMap& traffic_before,
    const std::vector<TraceEvent>& trace_events,
    const LtmOneShotProbeOptions& options);

}  // namespace czr004::ltm
