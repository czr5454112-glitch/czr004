#include "ltm.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <functional>
#include <limits>
#include <queue>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace czr004::ltm {

namespace {

double finite_or_large(double value)
{
  return std::isfinite(value) ? value : 1e12;
}

bool is_better_solution(const Solution& candidate, const Solution& incumbent)
{
  if (candidate.empty()) return false;
  if (incumbent.empty()) return true;
  return get_sum_of_loss(candidate) < get_sum_of_loss(incumbent);
}

uint info_uint_value(const std::string& info, const std::string& key)
{
  std::istringstream stream(info);
  std::string line;
  const auto prefix = key + "=";
  while (std::getline(stream, line)) {
    if (line.rfind(prefix, 0) != 0) continue;
    try {
      return static_cast<uint>(std::stoul(line.substr(prefix.size())));
    } catch (...) {
      return 0;
    }
  }
  return 0;
}

}  // namespace

void PibtTraceCollector::clear() { events_.clear(); }

void PibtTraceCollector::record_committed(uint agent_id, const Vertex* from,
                                          const Vertex* to, const Vertex* goal)
{
  events_.push_back(TraceEvent{TraceEventKind::Committed, agent_id, from->id,
                               to->id, from == goal && to == goal});
}

void PibtTraceCollector::record_blocked(uint agent_id, const Vertex* from,
                                        const Vertex* to, const Vertex* goal)
{
  events_.push_back(TraceEvent{TraceEventKind::Blocked, agent_id, from->id,
                               to->id, from == goal && to == goal});
}

TraceSummary PibtTraceCollector::summary() const
{
  TraceSummary summary;
  for (const auto& event : events_) {
    if (event.kind == TraceEventKind::Committed) {
      ++summary.committed;
    } else {
      ++summary.blocked;
    }
  }
  return summary;
}

DirectedTrafficMap::DirectedTrafficMap(const Graph& graph, double lower_bound,
                                       double upper_bound)
    : graph_(graph),
      lower_bound_(lower_bound),
      upper_bound_(upper_bound),
      raw_counts_(),
      normalized_weights_(),
      flow_raw_counts_(),
      normalized_flow_weights_()
{
  for (const auto* from : graph_.V) {
    for (const auto* to : from->neighbor) {
      raw_counts_[key(from->id, to->id)] = 0.0;
      normalized_weights_[key(from->id, to->id)] = 1.0;
      flow_raw_counts_[key(from->id, to->id)] = 0.0;
      normalized_flow_weights_[key(from->id, to->id)] = 0.0;
    }
  }
}

void DirectedTrafficMap::reset()
{
  for (auto& [_, count] : raw_counts_) count = 0.0;
  for (auto& [_, count] : flow_raw_counts_) count = 0.0;
  dual_channel_cost_enabled_ = false;
  goal_projection_mode_ = GoalProjectionMode::None;
  flow_shield_beta_ = 0.0;
  max_flow_shield_ = 0.0;
  last_update_stats_ = DualChannelUpdateStats();
  renormalize();
  renormalize_flow();
}

void DirectedTrafficMap::update_from_trace(const std::vector<TraceEvent>& events)
{
  update_from_trace(events, UpdateParams::additive());
}

void DirectedTrafficMap::update_from_trace(const std::vector<TraceEvent>& events,
                                           const UpdateParams& params)
{
  update_from_trace(events, params, nullptr);
}

void DirectedTrafficMap::update_from_trace(const std::vector<TraceEvent>& events,
                                           const UpdateParams& params,
                                           const Instance* instance)
{
  const auto effective = params.force_additive ? UpdateParams::additive() : params;
  last_update_stats_ = DualChannelUpdateStats();
  if (effective.enable_dual_channel) {
    if (instance == nullptr) {
      throw std::runtime_error(
          "dual-channel LTM update requires an Instance for goal progress");
    }
    dual_channel_cost_enabled_ = true;
    lambda_cong_ = effective.lambda_cong;
    lambda_flow_ = effective.lambda_flow;
    min_edge_cost_ = effective.min_edge_cost;
    max_edge_cost_ = effective.max_edge_cost;
    goal_projection_mode_ = effective.goal_projection_mode;
    flow_shield_beta_ = effective.flow_shield_beta;
    max_flow_shield_ = effective.max_flow_shield;
    apply_dual_decay(effective);
    auto distances = DistTable(instance);
    for (const auto& event : events) {
      increment_dual_event(event, effective, *instance, distances);
    }
    renormalize(effective);
    renormalize_flow();
    return;
  }

  dual_channel_cost_enabled_ = false;
  goal_projection_mode_ = GoalProjectionMode::None;
  flow_shield_beta_ = 0.0;
  max_flow_shield_ = 0.0;
  apply_decay(effective);
  for (const auto& event : events) increment_event(event, effective);
  renormalize(effective);
}

bool DirectedTrafficMap::has_edge(uint from_id, uint to_id) const
{
  return raw_counts_.find(key(from_id, to_id)) != raw_counts_.end();
}

double DirectedTrafficMap::raw_count(uint from_id, uint to_id) const
{
  const auto it = raw_counts_.find(key(from_id, to_id));
  return it == raw_counts_.end() ? 0.0 : it->second;
}

double DirectedTrafficMap::normalized_weight(uint from_id, uint to_id) const
{
  const auto it = normalized_weights_.find(key(from_id, to_id));
  return it == normalized_weights_.end() ? upper_bound_ : it->second;
}

double DirectedTrafficMap::flow_raw_count(uint from_id, uint to_id) const
{
  const auto it = flow_raw_counts_.find(key(from_id, to_id));
  return it == flow_raw_counts_.end() ? 0.0 : it->second;
}

double DirectedTrafficMap::normalized_flow_weight(uint from_id, uint to_id) const
{
  const auto it = normalized_flow_weights_.find(key(from_id, to_id));
  return it == normalized_flow_weights_.end() ? 0.0 : it->second;
}

double DirectedTrafficMap::traversal_cost(uint from_id, uint to_id) const
{
  return traversal_cost(0, from_id, to_id, nullptr);
}

double DirectedTrafficMap::traversal_cost(uint agent_id, uint from_id,
                                          uint to_id,
                                          DistTable* base_distances) const
{
  if (!has_edge(from_id, to_id)) return WeightedDistanceTable::INF;
  if (dual_channel_cost_enabled_) {
    const auto congestion = normalized_weight(from_id, to_id);
    const auto flow = normalized_flow_weight(from_id, to_id);
    auto progress = 0.0;
    if ((goal_projection_mode_ == GoalProjectionMode::AgentProgress ||
         goal_projection_mode_ == GoalProjectionMode::FlowShield) &&
        base_distances != nullptr) {
      const auto from_dist = base_distances->get(agent_id, from_id);
      const auto to_dist = base_distances->get(agent_id, to_id);
      if (from_dist < base_distances->V_size &&
          to_dist < base_distances->V_size && from_dist > to_dist) {
        progress = static_cast<double>(from_dist - to_dist);
      }
    }

    auto raw_cost = 1.0 + lambda_cong_ * congestion - lambda_flow_ * flow;
    if (goal_projection_mode_ == GoalProjectionMode::AgentProgress) {
      raw_cost = 1.0 + lambda_cong_ * congestion -
                 lambda_flow_ * flow * progress;
    } else if (goal_projection_mode_ == GoalProjectionMode::FlowShield) {
      const auto shield = std::clamp(flow_shield_beta_ * flow * progress, 0.0,
                                     max_flow_shield_);
      raw_cost = 1.0 + lambda_cong_ * congestion * (1.0 - shield);
    }
    if (!std::isfinite(raw_cost)) return WeightedDistanceTable::INF;
    const auto lo = std::min(min_edge_cost_, max_edge_cost_);
    const auto hi = std::max(min_edge_cost_, max_edge_cost_);
    return std::min(std::max(raw_cost, lo), hi);
  }
  return 1.0 + normalized_weight(from_id, to_id);
}

uint DirectedTrafficMap::nonzero_raw_edges() const
{
  uint count = 0;
  for (const auto& [_, raw] : raw_counts_) {
    if (raw > 0.0) ++count;
  }
  return count;
}

uint DirectedTrafficMap::nonzero_flow_edges() const
{
  uint count = 0;
  for (const auto& [_, raw] : flow_raw_counts_) {
    if (raw > 0.0) ++count;
  }
  return count;
}

double DirectedTrafficMap::max_raw_count() const
{
  double value = 0.0;
  for (const auto& [_, raw] : raw_counts_) value = std::max(value, raw);
  return value;
}

double DirectedTrafficMap::max_normalized_weight() const
{
  double value = 0.0;
  for (const auto& [_, weight] : normalized_weights_) {
    value = std::max(value, weight);
  }
  return value;
}

double DirectedTrafficMap::max_flow_raw_count() const
{
  double value = 0.0;
  for (const auto& [_, raw] : flow_raw_counts_) value = std::max(value, raw);
  return value;
}

double DirectedTrafficMap::max_normalized_flow_weight() const
{
  double value = 0.0;
  for (const auto& [_, weight] : normalized_flow_weights_) {
    value = std::max(value, weight);
  }
  return value;
}

TrafficCostAudit DirectedTrafficMap::cost_audit() const
{
  return cost_audit(nullptr);
}

TrafficCostAudit DirectedTrafficMap::cost_audit(const Instance* instance) const
{
  TrafficCostAudit audit;
  const auto lo = std::min(min_edge_cost_, max_edge_cost_);
  const auto hi = std::max(min_edge_cost_, max_edge_cost_);
  auto base_distances =
      instance == nullptr ? std::unique_ptr<DistTable>() :
                            std::make_unique<DistTable>(instance);
  const auto agent_count = instance == nullptr ? 1 : instance->N;
  for (uint agent_id = 0; agent_id < agent_count; ++agent_id) {
    for (const auto* from : graph_.V) {
      for (const auto* to : from->neighbor) {
        const auto cost = traversal_cost(agent_id, from->id, to->id,
                                         base_distances.get());
        audit.all_finite = audit.all_finite && std::isfinite(cost);
        if (std::isfinite(cost)) {
          audit.min_cost = std::min(audit.min_cost, cost);
          audit.max_cost = std::max(audit.max_cost, cost);
        }
        if (dual_channel_cost_enabled_ &&
            (cost < lo - 1.0e-12 || cost > hi + 1.0e-12)) {
          audit.within_configured_bounds = false;
        }
      }
    }
  }
  if (audit.min_cost == std::numeric_limits<double>::infinity()) {
    audit.min_cost = std::numeric_limits<double>::quiet_NaN();
  }
  if (audit.max_cost == -std::numeric_limits<double>::infinity()) {
    audit.max_cost = std::numeric_limits<double>::quiet_NaN();
  }
  return audit;
}

TrafficSnapshot DirectedTrafficMap::snapshot(uint topk_edges) const
{
  TrafficSnapshot out;
  out.nonzero_edges = nonzero_raw_edges();
  out.max_raw = max_raw_count();
  out.max_normalized = max_normalized_weight();
  out.flow_nonzero_edges = nonzero_flow_edges();
  out.max_flow_raw = max_flow_raw_count();
  out.max_normalized_flow = max_normalized_flow_weight();

  auto raw_edges = std::vector<TrafficEdgeSnapshot>();
  auto normalized_edges = std::vector<TrafficEdgeSnapshot>();
  for (const auto* from : graph_.V) {
    for (const auto* to : from->neighbor) {
      const auto raw = raw_count(from->id, to->id);
      const auto weight = normalized_weight(from->id, to->id);
      const auto flow_raw = flow_raw_count(from->id, to->id);
      const auto flow_weight = normalized_flow_weight(from->id, to->id);
      if (raw > 0.0 || flow_raw > 0.0) {
        raw_edges.push_back(TrafficEdgeSnapshot{from->id, to->id, raw, weight,
                                                flow_raw, flow_weight});
        normalized_edges.push_back(
            TrafficEdgeSnapshot{from->id, to->id, raw, weight, flow_raw,
                                flow_weight});
      }
    }
  }

  const auto raw_less = [](const auto& lhs, const auto& rhs) {
    if (lhs.raw != rhs.raw) return lhs.raw > rhs.raw;
    if (lhs.from_id != rhs.from_id) return lhs.from_id < rhs.from_id;
    return lhs.to_id < rhs.to_id;
  };
  const auto weight_less = [](const auto& lhs, const auto& rhs) {
    if (lhs.weight != rhs.weight) return lhs.weight > rhs.weight;
    if (lhs.raw != rhs.raw) return lhs.raw > rhs.raw;
    if (lhs.from_id != rhs.from_id) return lhs.from_id < rhs.from_id;
    return lhs.to_id < rhs.to_id;
  };
  std::sort(raw_edges.begin(), raw_edges.end(), raw_less);
  std::sort(normalized_edges.begin(), normalized_edges.end(), weight_less);

  if (topk_edges > 0) {
    if (raw_edges.size() > topk_edges) raw_edges.resize(topk_edges);
    if (normalized_edges.size() > topk_edges) {
      normalized_edges.resize(topk_edges);
    }
  }
  out.raw_topk = std::move(raw_edges);
  out.normalized_topk = std::move(normalized_edges);
  return out;
}

std::uint64_t DirectedTrafficMap::key(uint from_id, uint to_id)
{
  return (static_cast<std::uint64_t>(from_id) << 32) |
         static_cast<std::uint64_t>(to_id);
}

void DirectedTrafficMap::apply_decay(const UpdateParams& params)
{
  if (params.force_additive || params.rho_decay >= 1.0) return;
  const auto decay = std::clamp(params.rho_decay, 0.0, 1.0);
  for (auto& [_, count] : raw_counts_) count *= decay;
}

void DirectedTrafficMap::apply_dual_decay(const UpdateParams& params)
{
  const auto cong_decay = std::clamp(params.rho_cong_decay, 0.0, 1.0);
  const auto flow_decay = std::clamp(params.rho_flow_decay, 0.0, 1.0);
  if (cong_decay < 1.0) {
    for (auto& [_, count] : raw_counts_) count *= cong_decay;
  }
  if (flow_decay < 1.0) {
    for (auto& [_, count] : flow_raw_counts_) count *= flow_decay;
  }
}

void DirectedTrafficMap::increment_event(const TraceEvent& event,
                                         const UpdateParams& params)
{
  if (event.from_id == event.to_id) {
    if (event.at_goal) return;
    const auto* from = graph_.V[event.from_id];
    const auto delta =
        params.force_additive ? 1.0 : params.alpha_wait_spillover;
    for (const auto* to : from->neighbor) increment_edge(from->id, to->id, delta);
    return;
  }

  auto delta = 1.0;
  if (!params.force_additive) {
    if (event.kind == TraceEventKind::Committed) {
      delta = params.alpha_commit;
    } else if (event.kind == TraceEventKind::Blocked) {
      delta = params.alpha_block;
    }
  }
  increment_edge(event.from_id, event.to_id, delta);

  if (!params.force_additive && params.enable_contraflow_penalty &&
      params.contraflow_penalty > 0.0 &&
      has_edge(event.to_id, event.from_id)) {
    increment_edge(event.to_id, event.from_id, params.contraflow_penalty);
  }
}

void DirectedTrafficMap::increment_dual_event(const TraceEvent& event,
                                              const UpdateParams& params,
                                              const Instance& instance,
                                              DistTable& distances)
{
  if (params.alpha_flow_commit_progress <= 0.0 &&
      params.alpha_flow_wait_progress <= 0.0 &&
      params.alpha_cong_commit_progress ==
          params.alpha_cong_commit_nonprogress &&
      params.alpha_cong_wait_progress == params.alpha_cong_wait_nonprogress) {
    increment_event(event, params);
    return;
  }

  auto progress = 0.0;
  auto has_progress_info = false;
  if (event.agent_id < instance.N && event.from_id < graph_.V.size() &&
      event.to_id < graph_.V.size()) {
    const auto from_dist = distances.get(event.agent_id, event.from_id);
    const auto to_dist = distances.get(event.agent_id, event.to_id);
    if (from_dist < graph_.V.size() && to_dist < graph_.V.size()) {
      has_progress_info = true;
      if (from_dist > to_dist) {
        progress = static_cast<double>(from_dist - to_dist);
      }
    }
  }

  if (event.from_id == event.to_id) {
    if (event.at_goal) return;
    const auto* from = graph_.V[event.from_id];
    for (const auto* to : from->neighbor) {
      auto edge_progress = 0.0;
      if (event.agent_id < instance.N) {
        const auto from_dist = distances.get(event.agent_id, from->id);
        const auto to_dist = distances.get(event.agent_id, to->id);
        if (from_dist < graph_.V.size() && to_dist < graph_.V.size() &&
            from_dist > to_dist) {
          edge_progress = static_cast<double>(from_dist - to_dist);
        }
      }
      if (edge_progress > 0.0) {
        ++last_update_stats_.wait_progress_edges;
        increment_edge(from->id, to->id, params.alpha_cong_wait_progress);
        increment_flow_edge(from->id, to->id,
                            params.alpha_flow_wait_progress * edge_progress);
      } else {
        ++last_update_stats_.wait_nonprogress_edges;
        increment_edge(from->id, to->id, params.alpha_cong_wait_nonprogress);
      }
    }
    return;
  }

  if (event.kind == TraceEventKind::Committed) {
    if (has_progress_info && progress > 0.0) {
      ++last_update_stats_.committed_progress_events;
      increment_edge(event.from_id, event.to_id,
                     params.alpha_cong_commit_progress);
      increment_flow_edge(event.from_id, event.to_id,
                          params.alpha_flow_commit_progress * progress);
    } else {
      ++last_update_stats_.committed_nonprogress_events;
      increment_edge(event.from_id, event.to_id,
                     params.alpha_cong_commit_nonprogress);
    }
    return;
  }

  if (event.kind == TraceEventKind::Blocked) {
    ++last_update_stats_.blocked_events;
    increment_edge(event.from_id, event.to_id, params.alpha_cong_block);
  }
}

void DirectedTrafficMap::increment_edge(uint from_id, uint to_id, double delta)
{
  if (delta <= 0.0) return;
  const auto k = key(from_id, to_id);
  const auto it = raw_counts_.find(k);
  if (it != raw_counts_.end()) {
    it->second += delta;
    ++last_update_stats_.congestion_update_count;
    last_update_stats_.congestion_delta_total += delta;
  }
}

void DirectedTrafficMap::increment_flow_edge(uint from_id, uint to_id,
                                             double delta)
{
  if (delta <= 0.0) return;
  const auto k = key(from_id, to_id);
  const auto it = flow_raw_counts_.find(k);
  if (it != flow_raw_counts_.end()) {
    it->second += delta;
    ++last_update_stats_.flow_update_count;
    last_update_stats_.flow_delta_total += delta;
  }
}

void DirectedTrafficMap::renormalize()
{
  renormalize(UpdateParams::additive());
}

void DirectedTrafficMap::renormalize(const UpdateParams& params)
{
  const auto max_count = max_raw_count();
  if (max_count <= 0.0) {
    for (auto& [edge, weight] : normalized_weights_) {
      weight = std::min(std::max(1.0, lower_bound_), upper_bound_);
    }
    return;
  }

  (void)params;

  for (const auto& [edge, raw] : raw_counts_) {
    const auto scaled = lower_bound_ + (raw / max_count) *
                                           (upper_bound_ - lower_bound_);
    normalized_weights_[edge] =
        std::min(std::max(scaled, lower_bound_), upper_bound_);
  }
}

void DirectedTrafficMap::renormalize_flow()
{
  const auto max_count = max_flow_raw_count();
  if (max_count <= 0.0) {
    for (auto& [_, weight] : normalized_flow_weights_) weight = 0.0;
    return;
  }

  for (const auto& [edge, raw] : flow_raw_counts_) {
    const auto scaled = lower_bound_ + (raw / max_count) *
                                           (upper_bound_ - lower_bound_);
    normalized_flow_weights_[edge] =
        std::min(std::max(scaled, lower_bound_), upper_bound_);
  }
}

WeightedDistanceTable::WeightedDistanceTable(const Instance* instance,
                                             const DirectedTrafficMap* ltm)
    : instance_(instance),
      ltm_(ltm),
      base_distances_(instance),
      reverse_neighbors_(instance->G.size()),
      table_(instance->N, std::vector<double>(instance->G.size(), INF)),
      solved_(instance->N, false)
{
  for (const auto* from : instance_->G.V) {
    for (const auto* to : from->neighbor) {
      reverse_neighbors_[to->id].push_back(const_cast<Vertex*>(from));
    }
  }
}

double WeightedDistanceTable::get(uint agent_id, uint vertex_id)
{
  if (!solved_[agent_id]) solve_agent(agent_id);
  return table_[agent_id][vertex_id];
}

double WeightedDistanceTable::get(uint agent_id, const Vertex* vertex)
{
  return get(agent_id, vertex->id);
}

void WeightedDistanceTable::solve_agent(uint agent_id)
{
  using QueueItem = std::pair<double, uint>;
  auto open = std::priority_queue<QueueItem, std::vector<QueueItem>,
                                  std::greater<QueueItem> >();

  const auto* goal = instance_->goals[agent_id];
  table_[agent_id][goal->id] = 0.0;
  open.push({0.0, goal->id});

  while (!open.empty()) {
    const auto [dist, current_id] = open.top();
    open.pop();
    if (dist > table_[agent_id][current_id]) continue;

    for (const auto* predecessor : reverse_neighbors_[current_id]) {
      const auto edge_cost =
          ltm_->traversal_cost(agent_id, predecessor->id, current_id,
                               &base_distances_);
      const auto candidate = dist + edge_cost;
      if (candidate >= table_[agent_id][predecessor->id]) continue;
      table_[agent_id][predecessor->id] = candidate;
      open.push({candidate, predecessor->id});
    }
  }

  solved_[agent_id] = true;
}

struct LtmHNode {
  const Config C;
  LtmHNode* parent;
  std::set<LtmHNode*> neighbor;
  double g;
  const double h;
  double f;
  std::vector<double> priorities;
  std::vector<uint> order;
  std::queue<LNode*> search_tree;

  LtmHNode(const Config& config, WeightedDistanceTable& distances,
           LtmHNode* parent_node, double g_value, double h_value)
      : C(config),
        parent(parent_node),
        neighbor(),
        g(g_value),
        h(h_value),
        f(g + h),
        priorities(config.size()),
        order(config.size(), 0),
        search_tree(std::queue<LNode*>())
  {
    search_tree.push(new LNode());
    if (parent != nullptr) parent->neighbor.insert(this);

    const auto n = C.size();
    if (parent == nullptr) {
      for (uint i = 0; i < n; ++i) {
        priorities[i] = finite_or_large(distances.get(i, C[i])) / n;
      }
    } else {
      for (uint i = 0; i < n; ++i) {
        if (distances.get(i, C[i]) != 0.0) {
          priorities[i] = parent->priorities[i] + 1.0;
        } else {
          priorities[i] = parent->priorities[i] -
                          static_cast<int>(parent->priorities[i]);
        }
      }
    }

    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](uint i, uint j) {
      return priorities[i] > priorities[j];
    });
  }

  ~LtmHNode()
  {
    while (!search_tree.empty()) {
      delete search_tree.front();
      search_tree.pop();
    }
  }
};

class OneShotLtmPlanner {
 public:
  OneShotLtmPlanner(const Instance* instance, const Deadline* deadline,
                    std::mt19937* random_engine, const DirectedTrafficMap* ltm,
                    PibtTraceCollector* collector, Objective objective,
                    uint node_budget, int verbose)
      : ins(instance),
        deadline(deadline),
        MT(random_engine),
        ltm(ltm),
        collector(collector),
        objective(objective),
        node_budget(node_budget),
        verbose(verbose),
        N(ins->N),
        V_size(ins->G.size()),
        D(ins, ltm),
        loop_cnt(0),
        low_level_pibt_calls(0),
        C_next(N),
        tie_breakers(V_size, 0),
        A(N, nullptr),
        occupied_now(V_size, nullptr),
        occupied_next(V_size, nullptr)
  {
  }

  Solution solve(std::string& additional_info)
  {
    for (uint i = 0; i < N; ++i) A[i] = new Agent(i);

    auto open = std::stack<LtmHNode*>();
    auto explored = std::unordered_map<Config, LtmHNode*, ConfigHasher>();
    auto* h_init =
        new LtmHNode(ins->starts, D, nullptr, 0.0, get_h_value(ins->starts));
    open.push(h_init);
    explored[h_init->C] = h_init;

    auto c_new = Config(N, nullptr);
    LtmHNode* h_goal = nullptr;
    auto solution = Solution();

    while (!open.empty() && !is_expired(deadline) &&
           (node_budget == 0 || loop_cnt < node_budget)) {
      ++loop_cnt;
      auto* h = open.top();

      if (h->search_tree.empty()) {
        open.pop();
        continue;
      }

      if (h_goal != nullptr && h->f >= h_goal->f) {
        open.pop();
        continue;
      }

      if (h_goal == nullptr && is_same_config(h->C, ins->goals)) {
        h_goal = h;
        break;
      }

      auto* l = h->search_tree.front();
      h->search_tree.pop();
      expand_lowlevel_tree(h, l);

      const auto ok = get_new_config(h, l);
      delete l;
      if (!ok) continue;

      for (auto* agent : A) c_new[agent->id] = agent->v_next;
      for (uint i = 0; i < N; ++i) {
        collector->record_committed(i, h->C[i], c_new[i], ins->goals[i]);
      }

      const auto iter = explored.find(c_new);
      if (iter != explored.end()) {
        rewrite(h, iter->second, h_goal, open);
        if (h_goal == nullptr || iter->second->f < h_goal->f) {
          open.push(iter->second);
        }
      } else {
        auto* h_new = new LtmHNode(c_new, D, h, h->g + get_edge_cost(h->C, c_new),
                                   get_h_value(c_new));
        explored[h_new->C] = h_new;
        if (h_goal == nullptr || h_new->f < h_goal->f) open.push(h_new);
      }
    }

    if (h_goal != nullptr) {
      auto* h = h_goal;
      while (h != nullptr) {
        solution.push_back(h->C);
        h = h->parent;
      }
      std::reverse(solution.begin(), solution.end());
    }

    std::ostringstream oss;
    oss << "ltm_one_shot_loop_cnt=" << loop_cnt << "\n";
    oss << "ltm_one_shot_node_budget=" << node_budget << "\n";
    oss << "ltm_one_shot_num_node_gen=" << explored.size() << "\n";
    oss << "ltm_one_shot_low_level_pibt_calls=" << low_level_pibt_calls << "\n";
    oss << "ltm_one_shot_solved=" << !solution.empty() << "\n";
    additional_info += oss.str();

    for (auto* agent : A) delete agent;
    for (auto& item : explored) delete item.second;

    return solution;
  }

 private:
  const Instance* ins;
  const Deadline* deadline;
  std::mt19937* MT;
  const DirectedTrafficMap* ltm;
  PibtTraceCollector* collector;
  Objective objective;
  uint node_budget;
  int verbose;

  const uint N;
  const uint V_size;
  WeightedDistanceTable D;
  uint loop_cnt;
  uint low_level_pibt_calls;
  std::vector<std::array<Vertex*, 5> > C_next;
  std::vector<float> tie_breakers;
  Agents A;
  Agents occupied_now;
  Agents occupied_next;

  template <typename... Body>
  void solver_info(const int level, Body&&... body)
  {
    if (verbose < level) return;
    std::cout << "elapsed:" << std::setw(6) << elapsed_ms(deadline) << "ms"
              << "  loop_cnt:" << std::setw(8) << loop_cnt << "\t";
    info(level, verbose, (body)...);
  }

  void expand_lowlevel_tree(LtmHNode* h, LNode* l)
  {
    if (l->depth >= N) return;
    const auto i = h->order[l->depth];
    auto candidates = h->C[i]->neighbor;
    candidates.push_back(h->C[i]);
    if (MT != nullptr) std::shuffle(candidates.begin(), candidates.end(), *MT);
    for (auto* v : candidates) h->search_tree.push(new LNode(l, i, v));
  }

  bool get_new_config(LtmHNode* h, LNode* l)
  {
    for (auto* agent : A) {
      if (agent->v_now != nullptr && occupied_now[agent->v_now->id] == agent) {
        occupied_now[agent->v_now->id] = nullptr;
      }
      if (agent->v_next != nullptr) {
        occupied_next[agent->v_next->id] = nullptr;
        agent->v_next = nullptr;
      }

      agent->v_now = h->C[agent->id];
      occupied_now[agent->v_now->id] = agent;
    }

    for (uint k = 0; k < l->depth; ++k) {
      const auto i = l->who[k];
      const auto loc = l->where[k]->id;

      if (occupied_next[loc] != nullptr) return false;
      const auto loc_pre = h->C[i]->id;
      if (occupied_next[loc_pre] != nullptr && occupied_now[loc] != nullptr &&
          occupied_next[loc_pre]->id == occupied_now[loc]->id) {
        return false;
      }

      A[i]->v_next = l->where[k];
      occupied_next[loc] = A[i];
    }

    for (auto k : h->order) {
      auto* agent = A[k];
      if (agent->v_next == nullptr && !funcPIBT(agent)) return false;
    }
    return true;
  }

  bool funcPIBT(Agent* ai)
  {
    ++low_level_pibt_calls;
    const auto i = ai->id;
    const auto k_size = ai->v_now->neighbor.size();

    for (uint k = 0; k < k_size; ++k) {
      auto* u = ai->v_now->neighbor[k];
      C_next[i][k] = u;
      if (MT != nullptr) tie_breakers[u->id] = get_random_float(MT);
    }
    C_next[i][k_size] = ai->v_now;

    std::sort(C_next[i].begin(), C_next[i].begin() + k_size + 1,
              [&](Vertex* const v, Vertex* const u) {
                return D.get(i, v) + tie_breakers[v->id] <
                       D.get(i, u) + tie_breakers[u->id];
              });

    auto* swap_agent = swap_possible_and_required(ai);
    if (swap_agent != nullptr) {
      std::reverse(C_next[i].begin(), C_next[i].begin() + k_size + 1);
    }

    auto rejected_better = std::vector<Vertex*>();
    for (uint k = 0; k < k_size + 1; ++k) {
      auto* u = C_next[i][k];

      if (occupied_next[u->id] != nullptr) {
        rejected_better.push_back(u);
        continue;
      }

      auto*& ak = occupied_now[u->id];
      if (ak != nullptr && ak->v_next == ai->v_now) {
        rejected_better.push_back(u);
        continue;
      }

      occupied_next[u->id] = ai;
      ai->v_next = u;

      if (ak != nullptr && ak != ai && ak->v_next == nullptr &&
          !funcPIBT(ak)) {
        rejected_better.push_back(u);
        continue;
      }

      for (const auto* blocked : rejected_better) {
        collector->record_blocked(i, ai->v_now, blocked, ins->goals[i]);
      }

      if (k == 0 && swap_agent != nullptr && swap_agent->v_next == nullptr &&
          occupied_next[ai->v_now->id] == nullptr) {
        swap_agent->v_next = ai->v_now;
        occupied_next[swap_agent->v_next->id] = swap_agent;
      }
      return true;
    }

    occupied_next[ai->v_now->id] = ai;
    ai->v_next = ai->v_now;
    return false;
  }

  Agent* swap_possible_and_required(Agent* ai)
  {
    const auto i = ai->id;
    if (C_next[i][0] == ai->v_now) return nullptr;

    auto* aj = occupied_now[C_next[i][0]->id];
    if (aj != nullptr && aj->v_next == nullptr &&
        is_swap_required(ai->id, aj->id, ai->v_now, aj->v_now) &&
        is_swap_possible(aj->v_now, ai->v_now)) {
      return aj;
    }

    for (auto* u : ai->v_now->neighbor) {
      auto* ak = occupied_now[u->id];
      if (ak == nullptr || C_next[i][0] == ak->v_now) continue;
      if (is_swap_required(ak->id, ai->id, ai->v_now, C_next[i][0]) &&
          is_swap_possible(C_next[i][0], ai->v_now)) {
        return ak;
      }
    }

    return nullptr;
  }

  bool is_swap_required(const uint pusher, const uint puller,
                        Vertex* v_pusher_origin, Vertex* v_puller_origin)
  {
    auto* v_pusher = v_pusher_origin;
    auto* v_puller = v_puller_origin;
    Vertex* tmp = nullptr;
    while (D.get(pusher, v_puller) < D.get(pusher, v_pusher)) {
      auto n = v_puller->neighbor.size();
      for (auto* u : v_puller->neighbor) {
        auto* a = occupied_now[u->id];
        if (u == v_pusher ||
            (u->neighbor.size() == 1 && a != nullptr &&
             ins->goals[a->id] == u)) {
          --n;
        } else {
          tmp = u;
        }
      }
      if (n >= 2) return false;
      if (n <= 0) break;
      v_pusher = v_puller;
      v_puller = tmp;
    }

    return (D.get(puller, v_pusher) < D.get(puller, v_puller)) &&
           (D.get(pusher, v_pusher) == 0.0 ||
            D.get(pusher, v_puller) < D.get(pusher, v_pusher));
  }

  bool is_swap_possible(Vertex* v_pusher_origin, Vertex* v_puller_origin)
  {
    auto* v_pusher = v_pusher_origin;
    auto* v_puller = v_puller_origin;
    Vertex* tmp = nullptr;
    while (v_puller != v_pusher_origin) {
      auto n = v_puller->neighbor.size();
      for (auto* u : v_puller->neighbor) {
        auto* a = occupied_now[u->id];
        if (u == v_pusher ||
            (u->neighbor.size() == 1 && a != nullptr &&
             ins->goals[a->id] == u)) {
          --n;
        } else {
          tmp = u;
        }
      }
      if (n >= 2) return true;
      if (n <= 0) return false;
      v_pusher = v_puller;
      v_puller = tmp;
    }
    return false;
  }

  void rewrite(LtmHNode* h_from, LtmHNode* h_to, LtmHNode* h_goal,
               std::stack<LtmHNode*>& open)
  {
    h_from->neighbor.insert(h_to);

    auto queue = std::queue<LtmHNode*>({h_from});
    while (!queue.empty()) {
      auto* n_from = queue.front();
      queue.pop();
      for (auto* n_to : n_from->neighbor) {
        const auto g_val = n_from->g + get_edge_cost(n_from->C, n_to->C);
        if (g_val < n_to->g) {
          n_to->g = g_val;
          n_to->f = n_to->g + n_to->h;
          n_to->parent = n_from;
          queue.push(n_to);
          if (h_goal != nullptr && n_to->f < h_goal->f) open.push(n_to);
        }
      }
    }
  }

  double get_edge_cost(const Config& c1, const Config& c2) const
  {
    if (objective == Objective::OBJ_SUM_OF_LOSS) {
      double cost = 0.0;
      for (uint i = 0; i < N; ++i) {
        if (c1[i] != ins->goals[i] || c2[i] != ins->goals[i]) cost += 1.0;
      }
      return cost;
    }
    return 1.0;
  }

  double get_h_value(const Config& config)
  {
    double cost = 0.0;
    if (objective == Objective::OBJ_MAKESPAN) {
      for (uint i = 0; i < N; ++i) {
        cost = std::max(cost, finite_or_large(D.get(i, config[i])));
      }
    } else if (objective == Objective::OBJ_SUM_OF_LOSS) {
      for (uint i = 0; i < N; ++i) {
        cost += finite_or_large(D.get(i, config[i]));
      }
    }
    return cost;
  }
};

LtmOneShotProbeResult run_one_shot_update_probe(
    const Instance& instance, const DirectedTrafficMap& traffic_before,
    const std::vector<TraceEvent>& trace_events,
    const LtmOneShotProbeOptions& options)
{
  auto probe_map = traffic_before;
  probe_map.update_from_trace(trace_events, options.update_params, &instance);

  auto result = LtmOneShotProbeResult();
  auto deadline = Deadline(options.short_budget_ms);
  auto random_engine = std::mt19937(options.seed);
  auto collector = PibtTraceCollector();
  auto one_shot =
      OneShotLtmPlanner(&instance, &deadline, &random_engine, &probe_map,
                        &collector, options.objective, options.node_budget,
                        options.verbose);

  std::string additional_info;
  const auto started = std::chrono::steady_clock::now();
  const auto solution = one_shot.solve(additional_info);
  const auto ended = std::chrono::steady_clock::now();

  auto dist_table = DistTable(instance);
  result.lower_bound_sol = get_sum_of_costs_lower_bound(instance, dist_table);
  result.solution_found = !solution.empty();
  result.feasible =
      result.solution_found && is_feasible_solution(instance, solution, 1);
  result.sum_of_loss = result.solution_found ? get_sum_of_loss(solution) : 0;
  result.sum_of_loss_ratio =
      (result.solution_found && result.lower_bound_sol > 0)
          ? static_cast<double>(result.sum_of_loss) /
                static_cast<double>(result.lower_bound_sol)
          : std::numeric_limits<double>::quiet_NaN();
  result.runtime_ms =
      std::chrono::duration<double, std::milli>(ended - started).count();
  result.returned_solutions_count = result.solution_found ? 1 : 0;
  result.expanded_nodes =
      info_uint_value(additional_info, "ltm_one_shot_num_node_gen");
  result.high_level_expansions =
      info_uint_value(additional_info, "ltm_one_shot_loop_cnt");
  result.low_level_pibt_calls =
      info_uint_value(additional_info, "ltm_one_shot_low_level_pibt_calls");
  result.trace_summary = collector.summary();
  return result;
}

LtmRunResult solve_with_ltm(const Instance& instance, const LtmOptions& options)
{
  auto result = LtmRunResult(instance.G, 0.0, 10.0);
  auto deadline = Deadline(options.time_limit_ms);
  auto random_engine = std::mt19937(options.seed);
  auto dist_table = DistTable(instance);
  const auto lower_bound_sol =
      get_sum_of_costs_lower_bound(instance, dist_table);

  for (uint iteration = 0;
       iteration < options.max_iterations && !is_expired(&deadline);
       ++iteration) {
    auto collector = PibtTraceCollector();
    const auto has_incumbent_before = !result.best_solution.empty();
    const auto best_ratio_before =
        (has_incumbent_before && lower_bound_sol > 0)
            ? static_cast<double>(get_sum_of_loss(result.best_solution)) /
                  static_cast<double>(lower_bound_sol)
            : 0.0;
    auto traffic_before_map = std::shared_ptr<const DirectedTrafficMap>();
    if (options.retain_iteration_traffic_maps) {
      traffic_before_map =
          std::make_shared<DirectedTrafficMap>(result.traffic_map);
    }
    const auto traffic_before =
        result.traffic_map.snapshot(options.checkpoint_topk_edges);
    const auto node_budget =
        (iteration == 0 || result.best_solution.empty())
            ? 0
            : options.node_budget_factor *
                  static_cast<uint>(std::max(1, get_makespan(result.best_solution)));

    auto one_shot = OneShotLtmPlanner(
        &instance, &deadline, &random_engine, &result.traffic_map, &collector,
        options.objective, node_budget, options.verbose);

    std::string iteration_info;
    const auto solution = one_shot.solve(iteration_info);
    result.additional_info += "ltm_iteration=" + std::to_string(iteration) +
                              "\n" + iteration_info;
    result.last_node_budget = node_budget;
    result.iterations = iteration + 1;

    const auto solution_found = !solution.empty();
    if (solution_found &&
        !std::isfinite(result.time_to_first_solution_ms)) {
      result.time_to_first_solution_ms = deadline.elapsed_ms();
    }
    const auto sum_of_loss =
        solution_found ? get_sum_of_loss(solution) : 0;
    const auto ratio =
        (solution_found && lower_bound_sol > 0)
            ? static_cast<double>(sum_of_loss) /
                  static_cast<double>(lower_bound_sol)
            : std::numeric_limits<double>::quiet_NaN();

    const auto improved_incumbent =
        is_better_solution(solution, result.best_solution);
    if (improved_incumbent) {
      result.best_solution = solution;
    }
    const auto best_ratio_after =
        (!result.best_solution.empty() && lower_bound_sol > 0)
            ? static_cast<double>(get_sum_of_loss(result.best_solution)) /
                  static_cast<double>(lower_bound_sol)
            : 0.0;

    const auto summary = collector.summary();
    result.trace_summary.committed += summary.committed;
    result.trace_summary.blocked += summary.blocked;

    auto update_params = options.update_params;
    if (options.update_policy) {
      LtmIterationStats stats;
      stats.iteration = iteration;
      stats.node_budget = node_budget;
      stats.has_incumbent_before = has_incumbent_before;
      stats.improved_incumbent = improved_incumbent;
      stats.best_ratio_before = best_ratio_before;
      stats.best_ratio_after = best_ratio_after;
      stats.returned_solutions_count_so_far =
          result.best_solution.empty() ? 0 : 1;
      stats.expanded_nodes_this_iteration =
          info_uint_value(iteration_info, "ltm_one_shot_num_node_gen");
      stats.low_level_pibt_calls_this_iteration =
          info_uint_value(iteration_info, "ltm_one_shot_low_level_pibt_calls");
      stats.elapsed_ms = deadline.elapsed_ms();
      stats.time_remaining_sec =
          std::max(0.0, options.time_limit_ms - stats.elapsed_ms) / 1000.0;
      stats.max_iterations = options.max_iterations;

      LtmUpdateContext context;
      context.instance = &instance;
      context.traffic_before = &result.traffic_map;
      context.trace_events = &collector.events();
      context.stats = stats;
      const auto policy_started = std::chrono::steady_clock::now();
      update_params = options.update_policy(context);
      const auto policy_ended = std::chrono::steady_clock::now();
      result.additional_info +=
          "ltm_update_policy_total_ms=" +
          std::to_string(std::chrono::duration<double, std::milli>(
                             policy_ended - policy_started)
                             .count()) +
          "\n";
    }

    const auto update_apply_started = std::chrono::steady_clock::now();
    result.traffic_map.update_from_trace(collector.events(), update_params,
                                         &instance);
    const auto update_apply_ended = std::chrono::steady_clock::now();
    result.additional_info +=
        "ltm_update_apply_ms=" +
        std::to_string(std::chrono::duration<double, std::milli>(
                           update_apply_ended - update_apply_started)
                           .count()) +
        "\n";
    const auto& update_stats = result.traffic_map.last_update_stats();
    result.dual_channel_update_stats.congestion_update_count +=
        update_stats.congestion_update_count;
    result.dual_channel_update_stats.flow_update_count +=
        update_stats.flow_update_count;
    result.dual_channel_update_stats.congestion_delta_total +=
        update_stats.congestion_delta_total;
    result.dual_channel_update_stats.flow_delta_total +=
        update_stats.flow_delta_total;
    result.dual_channel_update_stats.committed_progress_events +=
        update_stats.committed_progress_events;
    result.dual_channel_update_stats.committed_nonprogress_events +=
        update_stats.committed_nonprogress_events;
    result.dual_channel_update_stats.blocked_events +=
        update_stats.blocked_events;
    result.dual_channel_update_stats.wait_progress_edges +=
        update_stats.wait_progress_edges;
    result.dual_channel_update_stats.wait_nonprogress_edges +=
        update_stats.wait_nonprogress_edges;
    auto traffic_after_map = std::shared_ptr<const DirectedTrafficMap>();
    if (options.retain_iteration_traffic_maps) {
      traffic_after_map =
          std::make_shared<DirectedTrafficMap>(result.traffic_map);
    }
    const auto traffic_after =
        result.traffic_map.snapshot(options.checkpoint_topk_edges);

    if (options.iteration_callback) {
      LtmIterationCheckpoint checkpoint;
      checkpoint.iteration = iteration;
      checkpoint.node_budget = node_budget;
      checkpoint.solution_found_this_iteration = solution_found;
      checkpoint.sum_of_loss_this_iteration = sum_of_loss;
      checkpoint.lower_bound_sol = lower_bound_sol;
      checkpoint.sum_of_loss_ratio_this_iteration = ratio;
      checkpoint.expanded_nodes_this_iteration =
          info_uint_value(iteration_info, "ltm_one_shot_num_node_gen");
      checkpoint.high_level_expansions_this_iteration =
          info_uint_value(iteration_info, "ltm_one_shot_loop_cnt");
      checkpoint.low_level_pibt_calls_this_iteration =
          info_uint_value(iteration_info, "ltm_one_shot_low_level_pibt_calls");
      checkpoint.has_incumbent_before = has_incumbent_before;
      checkpoint.improved_incumbent = improved_incumbent;
      checkpoint.best_ratio_before = best_ratio_before;
      checkpoint.best_ratio_after = best_ratio_after;
      checkpoint.returned_solutions_count_so_far =
          result.best_solution.empty() ? 0 : 1;
      checkpoint.elapsed_ms = deadline.elapsed_ms();
      checkpoint.time_remaining_sec =
          std::max(0.0, options.time_limit_ms - checkpoint.elapsed_ms) / 1000.0;
      checkpoint.update_params = update_params;
      checkpoint.trace_events = collector.events();
      checkpoint.traffic_before = traffic_before;
      checkpoint.traffic_after = traffic_after;
      checkpoint.traffic_before_map = traffic_before_map;
      checkpoint.traffic_after_map = traffic_after_map;
      options.iteration_callback(checkpoint);
    }

    if (solution.empty() && collector.events().empty()) break;
  }

  result.timeout = is_expired(&deadline);
  result.additional_info +=
      "ltm_iterations=" + std::to_string(result.iterations) + "\n";
  result.additional_info +=
      "ltm_trace_committed=" +
      std::to_string(result.trace_summary.committed) + "\n";
  result.additional_info +=
      "ltm_trace_blocked=" + std::to_string(result.trace_summary.blocked) +
      "\n";
  result.additional_info += "ltm_nonzero_edges=" +
                            std::to_string(result.traffic_map.nonzero_raw_edges()) +
                            "\n";
  return result;
}

}  // namespace czr004::ltm
