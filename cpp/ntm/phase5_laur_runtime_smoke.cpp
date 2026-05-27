#include "laur_ltm_features.hpp"
#include "laur_ltm_runtime.hpp"

#include <cmath>
#include <iostream>
#include <string>
#include <vector>

namespace {

bool is_additive(const czr004::ltm::UpdateParams& params)
{
  return params.force_additive && std::fabs(params.alpha_commit - 1.0) <= 1.0e-12 &&
         std::fabs(params.alpha_block - 1.0) <= 1.0e-12 &&
         std::fabs(params.alpha_wait_spillover - 1.0) <= 1.0e-12 &&
         std::fabs(params.rho_decay - 1.0) <= 1.0e-12 &&
         !params.enable_contraflow_penalty && !params.enable_local_saturation;
}

bool expect(bool condition, const std::string& message)
{
  if (condition) return true;
  std::cerr << "phase5_laur_runtime_smoke: " << message << "\n";
  return false;
}

czr004::ltm::TraceEvent event(czr004::ltm::TraceEventKind kind,
                              const Vertex* from, const Vertex* to,
                              bool at_goal)
{
  return czr004::ltm::TraceEvent{kind, 0, from->id, to->id, at_goal};
}

}  // namespace

int main(int argc, char** argv)
{
  const auto model_path =
      argc >= 2 ? std::string(argv[1]) : std::string();
  const auto instance = Instance("assets/loop.scen", "assets/loop.map", 3);
  if (!instance.is_valid(1)) {
    std::cerr << "phase5_laur_runtime_smoke: invalid loop instance\n";
    return 1;
  }

  const auto* from = instance.G.V.front();
  const auto* to = from->neighbor.front();
  const auto trace_events = std::vector<czr004::ltm::TraceEvent>{
      event(czr004::ltm::TraceEventKind::Committed, from, to, false),
      event(czr004::ltm::TraceEventKind::Blocked, from, from, false),
      event(czr004::ltm::TraceEventKind::Committed, from, from, true),
  };

  auto traffic_map = czr004::ltm::DirectedTrafficMap(instance.G);
  czr004::ltm::LtmIterationStats stats;
  stats.iteration = 2;
  stats.node_budget = 32;
  stats.has_incumbent_before = true;
  stats.best_ratio_before = 1.25;
  stats.returned_solutions_count_so_far = 1;
  stats.time_remaining_sec = 2.5;
  stats.max_iterations = 4;
  const auto features =
      czr004::ntm::build_laur_features(instance, traffic_map, trace_events, stats);
  if (!expect(features.values.size() == features.names.size(),
              "feature values/names size mismatch")) {
    return 2;
  }
  if (!expect(features.values.size() >= 30, "too few runtime features")) return 3;

  auto runtime = czr004::ntm::LaurLtmRuntime();
  czr004::ntm::LaurRuntimeOptions disabled;
  disabled.enabled = false;
  disabled.force_additive = false;
  if (!expect(runtime.load(disabled), "disabled runtime failed to load")) return 4;
  auto prediction = runtime.predict(features);
  if (!expect(!prediction.enabled, "disabled prediction should report disabled")) return 5;
  if (!expect(prediction.rule_id == "additive_ltm", "disabled rule must be additive")) {
    return 6;
  }
  if (!expect(is_additive(prediction.params), "disabled params must be additive")) {
    return 7;
  }

  czr004::ntm::LaurRuntimeOptions force_additive;
  force_additive.enabled = true;
  force_additive.force_additive = true;
  force_additive.model_path = model_path;
  if (!expect(runtime.load(force_additive),
              "force-additive runtime failed to load additive config")) {
    return 8;
  }
  prediction = runtime.predict(features);
  if (!expect(prediction.enabled, "force-additive prediction should report enabled")) {
    return 9;
  }
  if (!expect(prediction.rule_id == "additive_ltm",
              "force-additive rule must be additive")) {
    return 10;
  }
  if (!expect(is_additive(prediction.params),
              "force-additive params must be additive")) {
    return 11;
  }

  czr004::ntm::LaurRuntimeOptions additive_only;
  additive_only.enabled = true;
  additive_only.force_additive = false;
  additive_only.model_path = model_path;
  if (!expect(runtime.load(additive_only),
              "additive-only runtime failed to load config")) {
    return 12;
  }
  prediction = runtime.predict(features);
  if (!expect(prediction.enabled, "additive-only prediction should report enabled")) {
    return 13;
  }
  if (!expect(prediction.rule_id == "additive_ltm",
              "additive-only config must select additive rule")) {
    return 14;
  }
  if (!expect(is_additive(prediction.params),
              "additive-only config params must be additive")) {
    return 15;
  }

  std::cout << "phase5_laur_runtime_smoke ok" << std::endl;
  return 0;
}
