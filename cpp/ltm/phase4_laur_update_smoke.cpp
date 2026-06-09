#include "ltm.hpp"

#include <cmath>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

using czr004::ltm::DirectedTrafficMap;
using czr004::ltm::TraceEvent;
using czr004::ltm::TraceEventKind;
using czr004::ltm::UpdateParams;

namespace {

constexpr double kEps = 1.0e-12;

TraceEvent make_event(TraceEventKind kind, const Vertex* from, const Vertex* to,
                      bool at_goal)
{
  return TraceEvent{kind, 0, from->id, to->id, at_goal};
}

bool close_enough(double lhs, double rhs)
{
  return std::fabs(lhs - rhs) <= kEps;
}

bool expect_close(double actual, double expected, const std::string& label)
{
  if (close_enough(actual, expected)) return true;
  std::cerr << "phase4_laur_update_smoke: " << label << " expected "
            << expected << " got " << actual << "\n";
  return false;
}

const Vertex* first_vertex_with_neighbor(const Graph& graph)
{
  for (const auto* vertex : graph.V) {
    if (!vertex->neighbor.empty()) return vertex;
  }
  return nullptr;
}

std::pair<const Vertex*, const Vertex*> first_bidirectional_edge(const Graph& graph)
{
  for (const auto* from : graph.V) {
    for (const auto* to : from->neighbor) {
      for (const auto* back : to->neighbor) {
        if (back == from) return {from, to};
      }
    }
  }
  return {nullptr, nullptr};
}

bool compare_maps(const Graph& graph, const DirectedTrafficMap& lhs,
                  const DirectedTrafficMap& rhs, const std::string& label)
{
  for (const auto* from : graph.V) {
    for (const auto* to : from->neighbor) {
      const auto lhs_raw = lhs.raw_count(from->id, to->id);
      const auto rhs_raw = rhs.raw_count(from->id, to->id);
      if (!close_enough(lhs_raw, rhs_raw)) {
        std::cerr << "phase4_laur_update_smoke: " << label
                  << " raw mismatch edge " << from->id << "->" << to->id
                  << " lhs=" << lhs_raw << " rhs=" << rhs_raw << "\n";
        return false;
      }

      const auto lhs_weight = lhs.normalized_weight(from->id, to->id);
      const auto rhs_weight = rhs.normalized_weight(from->id, to->id);
      if (!close_enough(lhs_weight, rhs_weight)) {
        std::cerr << "phase4_laur_update_smoke: " << label
                  << " normalized mismatch edge " << from->id << "->"
                  << to->id << " lhs=" << lhs_weight
                  << " rhs=" << rhs_weight << "\n";
        return false;
      }
    }
  }
  return true;
}

bool check_normalized_bounds(const Graph& graph, const DirectedTrafficMap& map,
                             const std::string& label)
{
  for (const auto* from : graph.V) {
    for (const auto* to : from->neighbor) {
      const auto weight = map.normalized_weight(from->id, to->id);
      if (weight < map.lower_bound() - kEps || weight > map.upper_bound() + kEps) {
        std::cerr << "phase4_laur_update_smoke: " << label
                  << " normalized weight out of bounds edge " << from->id
                  << "->" << to->id << " weight=" << weight << "\n";
        return false;
      }
    }
  }
  return true;
}

bool run_force_additive_parity(const Instance& instance)
{
  const auto* from = first_vertex_with_neighbor(instance.G);
  if (from == nullptr) {
    std::cerr << "phase4_laur_update_smoke: graph has no traversable edge\n";
    return false;
  }
  const auto* to = from->neighbor.front();

  const auto events = std::vector<TraceEvent>{
      make_event(TraceEventKind::Committed, from, to, false),
      make_event(TraceEventKind::Blocked, from, from, false),
      make_event(TraceEventKind::Committed, from, from, true),
  };

  DirectedTrafficMap legacy_map(instance.G);
  DirectedTrafficMap additive_map(instance.G);
  DirectedTrafficMap forced_map(instance.G);

  legacy_map.update_from_trace(events);
  additive_map.update_from_trace(events, UpdateParams::additive());

  UpdateParams force_additive;
  force_additive.alpha_commit = 7.0;
  force_additive.alpha_block = 11.0;
  force_additive.alpha_wait_spillover = 13.0;
  force_additive.rho_decay = 0.25;
  force_additive.enable_contraflow_penalty = true;
  force_additive.contraflow_penalty = 17.0;
  force_additive.enable_local_saturation = true;
  force_additive.force_additive = true;
  forced_map.update_from_trace(events, force_additive);

  return compare_maps(instance.G, legacy_map, additive_map, "additive parity") &&
         compare_maps(instance.G, legacy_map, forced_map,
                      "force_additive parity") &&
         check_normalized_bounds(instance.G, additive_map, "additive parity");
}

bool run_legacy_semantics_reference(const Instance& instance)
{
  const auto* from = first_vertex_with_neighbor(instance.G);
  if (from == nullptr) return false;
  const auto* to = from->neighbor.front();

  DirectedTrafficMap map(instance.G);
  map.update_from_trace({
      make_event(TraceEventKind::Committed, from, to, false),
      make_event(TraceEventKind::Blocked, from, from, false),
      make_event(TraceEventKind::Committed, from, from, true),
  });

  if (!expect_close(map.raw_count(from->id, to->id), 2.0,
                    "legacy committed plus wait raw count")) {
    return false;
  }

  for (const auto* neighbor : from->neighbor) {
    const auto expected = neighbor == to ? 2.0 : 1.0;
    if (!expect_close(map.raw_count(from->id, neighbor->id), expected,
                      "legacy wait spillover raw count")) {
      return false;
    }
  }

  return check_normalized_bounds(instance.G, map, "legacy semantics");
}

bool run_parameterized_semantics(const Instance& instance)
{
  const auto* from = first_vertex_with_neighbor(instance.G);
  if (from == nullptr) return false;
  const auto* to = from->neighbor.front();

  UpdateParams alpha_params;
  alpha_params.alpha_commit = 2.5;
  alpha_params.alpha_block = 3.5;
  DirectedTrafficMap alpha_map(instance.G);
  alpha_map.update_from_trace({
      make_event(TraceEventKind::Committed, from, to, false),
      make_event(TraceEventKind::Blocked, from, to, false),
  }, alpha_params);
  if (!expect_close(alpha_map.raw_count(from->id, to->id), 6.0,
                    "commit/block alpha raw count")) {
    return false;
  }

  UpdateParams wait_params;
  wait_params.alpha_wait_spillover = 4.0;
  DirectedTrafficMap wait_map(instance.G);
  wait_map.update_from_trace({
      make_event(TraceEventKind::Blocked, from, from, false),
  }, wait_params);
  for (const auto* neighbor : from->neighbor) {
    if (!expect_close(wait_map.raw_count(from->id, neighbor->id), 4.0,
                      "wait spillover alpha raw count")) {
      return false;
    }
  }

  DirectedTrafficMap goal_wait_map(instance.G);
  goal_wait_map.update_from_trace({
      make_event(TraceEventKind::Committed, from, from, true),
  }, wait_params);
  if (goal_wait_map.nonzero_raw_edges() != 0) {
    std::cerr << "phase4_laur_update_smoke: goal wait should not change raw "
                 "counts\n";
    return false;
  }

  DirectedTrafficMap decay_map(instance.G);
  decay_map.update_from_trace({
      make_event(TraceEventKind::Committed, from, to, false),
  });
  UpdateParams decay_params;
  decay_params.alpha_commit = 2.0;
  decay_params.rho_decay = 0.5;
  decay_map.update_from_trace({
      make_event(TraceEventKind::Committed, from, to, false),
  }, decay_params);
  if (!expect_close(decay_map.raw_count(from->id, to->id), 2.5,
                    "decay before update raw count")) {
    return false;
  }

  const auto [bidir_from, bidir_to] = first_bidirectional_edge(instance.G);
  if (bidir_from == nullptr || bidir_to == nullptr) {
    std::cerr << "phase4_laur_update_smoke: no bidirectional edge for "
                 "contraflow-off check\n";
    return false;
  }
  UpdateParams contraflow_off;
  contraflow_off.contraflow_penalty = 9.0;
  DirectedTrafficMap contraflow_map(instance.G);
  contraflow_map.update_from_trace({
      make_event(TraceEventKind::Committed, bidir_from, bidir_to, false),
  }, contraflow_off);
  if (!expect_close(contraflow_map.raw_count(bidir_to->id, bidir_from->id), 0.0,
                    "contraflow default off reverse raw count")) {
    return false;
  }

  return check_normalized_bounds(instance.G, alpha_map, "alpha params") &&
         check_normalized_bounds(instance.G, wait_map, "wait params") &&
         check_normalized_bounds(instance.G, decay_map, "decay params");
}

}  // namespace

int main()
{
  const auto instance = Instance("assets/loop.scen", "assets/loop.map", 3);
  if (!instance.is_valid(1)) {
    std::cerr << "phase4_laur_update_smoke: invalid loop instance\n";
    return 1;
  }

  if (!run_force_additive_parity(instance)) return 2;
  if (!run_legacy_semantics_reference(instance)) return 3;
  if (!run_parameterized_semantics(instance)) return 4;

  std::cout << "phase4_laur_update_smoke ok" << std::endl;
  return 0;
}
