#pragma once

#include <lacam2.hpp>

#include <cstdint>
#include <limits>
#include <string>
#include <unordered_map>

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

  bool has_edge(uint from_id, uint to_id) const;
  double raw_count(uint from_id, uint to_id) const;
  double normalized_weight(uint from_id, uint to_id) const;
  double traversal_cost(uint from_id, uint to_id) const;
  uint nonzero_raw_edges() const;
  double max_raw_count() const;
  double max_normalized_weight() const;
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
  void increment_event(const TraceEvent& event);
  void increment_edge(uint from_id, uint to_id, double delta);
  void renormalize();
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

}  // namespace czr004::ltm
