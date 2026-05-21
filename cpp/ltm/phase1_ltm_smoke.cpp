#include "ltm.hpp"

#include <cmath>
#include <iostream>
#include <random>

using czr004::ltm::DirectedTrafficMap;
using czr004::ltm::LtmOptions;
using czr004::ltm::PibtTraceCollector;
using czr004::ltm::WeightedDistanceTable;
using czr004::ltm::solve_with_ltm;

namespace {

bool run_update_semantics_check(const Instance& instance)
{
  DirectedTrafficMap map(instance.G);
  PibtTraceCollector collector;

  const auto* start = instance.starts[0];
  const auto* neighbor = start->neighbor.front();
  const auto* goal = instance.goals[0];

  collector.record_committed(0, start, neighbor, goal);
  collector.record_blocked(0, start, start, goal);
  collector.record_committed(0, goal, goal, goal);
  map.update_from_trace(collector.events());

  if (map.raw_count(start->id, neighbor->id) <= 0.0) {
    std::cerr << "phase1_ltm_smoke: committed move was not counted\n";
    return false;
  }

  bool propagated_wait = false;
  for (const auto* to : start->neighbor) {
    if (map.raw_count(start->id, to->id) > 0.0) propagated_wait = true;
  }
  if (!propagated_wait) {
    std::cerr << "phase1_ltm_smoke: non-goal wait was not propagated\n";
    return false;
  }

  for (const auto* to : goal->neighbor) {
    if (map.raw_count(goal->id, to->id) > 0.0) {
      std::cerr << "phase1_ltm_smoke: goal wait should be ignored\n";
      return false;
    }
  }

  WeightedDistanceTable distances(&instance, &map);
  const auto d = distances.get(0, start);
  if (!std::isfinite(d)) {
    std::cerr << "phase1_ltm_smoke: weighted distance is not finite\n";
    return false;
  }

  return true;
}

bool run_solver_case(const std::string& label, const std::string& scen_filename,
                     const std::string& map_filename, uint agents)
{
  const auto instance = Instance(scen_filename, map_filename, agents);
  if (!instance.is_valid(1)) {
    std::cerr << "phase1_ltm_smoke: invalid instance for " << label << "\n";
    return false;
  }

  std::string baseline_info;
  Deadline baseline_deadline(3000);
  std::mt19937 baseline_mt(0);
  const auto baseline_solution =
      solve(instance, baseline_info, 0, &baseline_deadline, &baseline_mt,
            Objective::OBJ_SUM_OF_LOSS);

  if (baseline_solution.empty() ||
      !is_feasible_solution(instance, baseline_solution, 1)) {
    std::cerr << "phase1_ltm_smoke: baseline solve failed for " << label
              << "\n";
    return false;
  }

  LtmOptions options;
  options.time_limit_ms = 3000;
  options.max_iterations = 3;
  options.node_budget_factor = 10;
  options.seed = 0;
  options.objective = Objective::OBJ_SUM_OF_LOSS;

  const auto ltm_result = solve_with_ltm(instance, options);
  if (ltm_result.best_solution.empty()) {
    std::cerr << "phase1_ltm_smoke: LTM solve failed for " << label << "\n";
    return false;
  }
  if (!is_feasible_solution(instance, ltm_result.best_solution, 1)) {
    std::cerr << "phase1_ltm_smoke: LTM solution is infeasible for " << label
              << "\n";
    return false;
  }

  std::cout << "phase1_ltm_case ok"
            << " label=" << label
            << " agents=" << agents
            << " baseline_sum_of_loss=" << get_sum_of_loss(baseline_solution)
            << " ltm_sum_of_loss=" << get_sum_of_loss(ltm_result.best_solution)
            << " iterations=" << ltm_result.iterations
            << " committed=" << ltm_result.trace_summary.committed
            << " blocked=" << ltm_result.trace_summary.blocked
            << " nonzero_edges=" << ltm_result.traffic_map.nonzero_raw_edges()
            << " max_weight="
            << ltm_result.traffic_map.max_normalized_weight() << std::endl;

  return true;
}

}  // namespace

int main()
{
  const auto scen_filename = "assets/loop.scen";
  const auto map_filename = "assets/loop.map";
  const auto instance = Instance(scen_filename, map_filename, 3);
  if (!instance.is_valid(1)) {
    std::cerr << "phase1_ltm_smoke: invalid instance\n";
    return 1;
  }

  if (!run_update_semantics_check(instance)) return 2;

  if (!run_solver_case("loop", "assets/loop.scen", "assets/loop.map", 3)) {
    return 3;
  }

  if (!run_solver_case("random-32-32-10",
                       "assets/random-32-32-10-random-1.scen",
                       "assets/random-32-32-10.map", 3)) {
    return 4;
  }

  std::cout << "phase1_ltm_smoke ok" << std::endl;

  return 0;
}
