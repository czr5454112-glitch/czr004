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
  uint update_period_restarts = 1;
  std::string model_path;
};

struct LaurFeatureVector {
  std::vector<double> values;
  std::vector<std::string> names;
};

struct LaurPrediction {
  czr004::ltm::UpdateParams params = czr004::ltm::UpdateParams::additive();
  std::string rule_id = "additive_ltm";
  double safety_harmful_prob = 1.0;
  double predicted_delta_ratio = 0.0;
  double inference_ms = 0.0;
  bool enabled = false;
};

class LaurLtmRuntime {
 public:
  bool load(const LaurRuntimeOptions& options);
  LaurPrediction predict(const LaurFeatureVector& features) const;

 private:
  struct RuleSpec {
    std::string rule_id = "additive_ltm";
    czr004::ltm::UpdateParams params = czr004::ltm::UpdateParams::additive();
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
  uint input_dim_ = 0;
  uint hidden_dim_ = 0;

  LaurPrediction additive_prediction(double inference_ms, bool enabled) const;
  bool load_model_directory(const std::string& model_path);
};

}  // namespace czr004::ntm
