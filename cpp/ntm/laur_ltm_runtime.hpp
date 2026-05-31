#pragma once

#include "../ltm/ltm.hpp"

#include <string>
#include <vector>

namespace czr004::ntm {

struct LaurRuntimeOptions {
  bool enabled = false;
  bool force_additive = true;
  bool safety_enabled = true;
  bool post_first_solution_only = true;
  bool bottleneck_trigger_only = false;
  bool ood_guard_enabled = false;
  uint update_period_restarts = 1;
  double ood_z_threshold = 5.0;
  std::string model_path;
};

struct LaurFeatureVector {
  std::vector<double> values;
  std::vector<std::string> names;
};

struct LaurPrediction {
  czr004::ltm::UpdateParams params = czr004::ltm::UpdateParams::additive();
  std::string rule_id = "additive_ltm";
  std::string selected_rule_before_guard = "additive_ltm";
  std::string selected_rule_after_guard = "additive_ltm";
  std::string selected_rule_source = "additive_fallback";
  double safety_harmful_prob = 1.0;
  double predicted_delta_ratio = 0.0;
  double inference_ms = 0.0;
  double feature_max_abs_z = 0.0;
  double feature_mean_abs_z = 0.0;
  uint feature_outside_3sigma_count = 0;
  uint feature_outside_5sigma_count = 0;
  double ood_z_threshold = 0.0;
  bool ood_guard_triggered = false;
  bool enabled = false;
};

bool is_supported_laur_rule_id(const std::string& rule_id);
czr004::ltm::UpdateParams update_params_for_laur_rule_id(
    const std::string& rule_id);

class LaurLtmRuntime {
 public:
  bool load(const LaurRuntimeOptions& options);
  LaurPrediction predict(const LaurFeatureVector& features) const;

 private:
  struct RuleSpec {
    std::string rule_id = "additive_ltm";
    czr004::ltm::UpdateParams params = czr004::ltm::UpdateParams::additive();
  };

  struct RecoverySpec {
    double map_width = 0.0;
    double map_height = 0.0;
    double obstacle_ratio_min = -1.0;
    double obstacle_ratio_max = 2.0;
    double agents = 0.0;
    std::string rule_id = "additive_ltm";
    double support_mean_delta = 0.0;
    uint support_rows = 0;
    std::string source = "";
  };

  struct FeatureStatOverride {
    std::string feature_name;
    double mean = 0.0;
    double stdev = 1.0;
  };

  LaurRuntimeOptions options_;
  bool loaded_ = false;
  bool has_mlp_ = false;
  std::vector<std::string> feature_names_;
  std::vector<double> feature_mean_;
  std::vector<double> feature_std_;
  std::vector<double> layer0_weight_;
  std::vector<double> layer0_bias_;
  std::vector<double> rule_head_weight_;
  std::vector<double> rule_head_bias_;
  std::vector<double> safety_head_weight_;
  std::vector<double> safety_head_bias_;
  std::vector<double> delta_head_weight_;
  std::vector<double> delta_head_bias_;
  std::vector<RuleSpec> rules_;
  std::vector<RecoverySpec> recovery_specs_;
  std::vector<FeatureStatOverride> ood_stat_overrides_;
  uint input_dim_ = 0;
  uint hidden_dim_ = 0;

  LaurPrediction additive_prediction(double inference_ms, bool enabled) const;
  bool load_model_directory(const std::string& model_path);
};

}  // namespace czr004::ntm
