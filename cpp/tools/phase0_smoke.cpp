#include <lacam2.hpp>

#include <iostream>
#include <random>

// Project-owned smoke entrypoint. Avoids upstream main.cpp argparse -v/--verbose clash.
int main()
{
  const auto scen_filename = "assets/loop.scen";
  const auto map_filename = "assets/loop.map";
  const auto ins = Instance(scen_filename, map_filename, 3);
  if (!ins.is_valid(1)) {
    std::cerr << "phase0_smoke: invalid instance\n";
    return 1;
  }

  std::string additional_info;
  Deadline deadline(3000);
  std::mt19937 mt(0);

  const auto solution =
      solve(ins, additional_info, 1, &deadline, &mt, Objective::OBJ_SUM_OF_LOSS);

  if (solution.empty()) {
    std::cerr << "phase0_smoke: no solution within deadline\n";
    return 2;
  }
  if (!is_feasible_solution(ins, solution, 1)) {
    std::cerr << "phase0_smoke: infeasible solution\n";
    return 3;
  }

  const auto sol = get_sum_of_loss(solution);
  std::cout << "phase0_smoke ok"
            << " steps=" << solution.size() << " sum_of_loss=" << sol
            << std::endl;
  return 0;
}
