#include "laur_ltm_runtime.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <limits>
#include <sstream>
#include <unordered_map>

namespace czr004::ntm {

namespace {

constexpr double kEps = 1.0e-12;

std::string trim(const std::string& value)
{
  const auto first = value.find_first_not_of(" \t\r\n");
  if (first == std::string::npos) return "";
  const auto last = value.find_last_not_of(" \t\r\n");
  return value.substr(first, last - first + 1);
}

std::vector<std::string> split_csv_line(const std::string& line)
{
  auto out = std::vector<std::string>();
  auto stream = std::stringstream(line);
  std::string cell;
  while (std::getline(stream, cell, ',')) out.push_back(trim(cell));
  return out;
}

std::vector<std::string> split_semicolon_list(const std::string& line)
{
  auto out = std::vector<std::string>();
  auto stream = std::stringstream(line);
  std::string cell;
  while (std::getline(stream, cell, ';')) out.push_back(trim(cell));
  return out;
}

bool parse_bool(const std::string& value)
{
  const auto normalized = trim(value);
  return normalized == "1" || normalized == "true" || normalized == "True" ||
         normalized == "TRUE";
}

double parse_double_or(const std::string& value, double fallback)
{
  try {
    const auto parsed = std::stod(trim(value));
    return std::isfinite(parsed) ? parsed : fallback;
  } catch (...) {
    return fallback;
  }
}

uint parse_uint_or(const std::string& value, uint fallback)
{
  try {
    return static_cast<uint>(std::stoul(trim(value)));
  } catch (...) {
    return fallback;
  }
}

std::vector<double> read_vector_csv(const std::filesystem::path& path)
{
  auto values = std::vector<double>();
  auto in = std::ifstream(path);
  if (!in) return values;
  std::string line;
  while (std::getline(in, line)) {
    for (const auto& cell : split_csv_line(line)) {
      if (!cell.empty()) values.push_back(parse_double_or(cell, 0.0));
    }
  }
  return values;
}

std::vector<std::string> read_lines(const std::filesystem::path& path)
{
  auto values = std::vector<std::string>();
  auto in = std::ifstream(path);
  if (!in) return values;
  std::string line;
  while (std::getline(in, line)) {
    const auto value = trim(line);
    if (!value.empty()) values.push_back(value);
  }
  return values;
}

double sigmoid(double value)
{
  if (value >= 0.0) {
    const auto z = std::exp(-value);
    return 1.0 / (1.0 + z);
  }
  const auto z = std::exp(value);
  return z / (1.0 + z);
}

std::size_t argmax(const std::vector<double>& values)
{
  if (values.empty()) return 0;
  return static_cast<std::size_t>(
      std::distance(values.begin(), std::max_element(values.begin(), values.end())));
}

double dot_row(const std::vector<double>& matrix, uint cols, uint row,
               const std::vector<double>& x)
{
  double value = 0.0;
  const auto offset = static_cast<std::size_t>(row) * cols;
  for (uint col = 0; col < cols; ++col) {
    value += matrix[offset + col] * x[col];
  }
  return value;
}

double lookup_feature(const std::unordered_map<std::string, double>& by_name,
                      const std::string& name, double fallback = 0.0)
{
  const auto it = by_name.find(name);
  return it == by_name.end() ? fallback : it->second;
}

bool close_bucket(double left, double right)
{
  return std::fabs(left - right) <= 0.5;
}

std::unordered_map<std::string, std::size_t> header_index(
    const std::vector<std::string>& header)
{
  auto out = std::unordered_map<std::string, std::size_t>();
  for (std::size_t index = 0; index < header.size(); ++index) {
    out[header[index]] = index;
  }
  return out;
}

std::string cell_at(const std::vector<std::string>& cells,
                    const std::unordered_map<std::string, std::size_t>& index,
                    const std::string& key)
{
  const auto it = index.find(key);
  if (it == index.end() || it->second >= cells.size()) return "";
  return cells[it->second];
}

}  // namespace

bool is_supported_laur_rule_id(const std::string& rule_id)
{
  const auto normalized =
      rule_id == "neutral_additive" ? "additive_ltm" : rule_id;
  return normalized == "additive_ltm" || normalized == "commit_heavy" ||
         normalized == "block_heavy" || normalized == "block_light" ||
         normalized == "wait_light" || normalized == "wait_heavy" ||
         normalized == "decay_095" || normalized == "decay_090";
}

czr004::ltm::UpdateParams update_params_for_laur_rule_id(
    const std::string& rule_id)
{
  const auto normalized =
      rule_id == "neutral_additive" ? "additive_ltm" : rule_id;
  auto params = czr004::ltm::UpdateParams::additive();
  if (normalized == "commit_heavy") {
    params = czr004::ltm::UpdateParams();
    params.alpha_commit = 1.5;
  } else if (normalized == "block_heavy") {
    params = czr004::ltm::UpdateParams();
    params.alpha_block = 1.5;
  } else if (normalized == "block_light") {
    params = czr004::ltm::UpdateParams();
    params.alpha_block = 0.5;
  } else if (normalized == "wait_light") {
    params = czr004::ltm::UpdateParams();
    params.alpha_wait_spillover = 0.5;
  } else if (normalized == "wait_heavy") {
    params = czr004::ltm::UpdateParams();
    params.alpha_wait_spillover = 1.5;
  } else if (normalized == "decay_095") {
    params = czr004::ltm::UpdateParams();
    params.rho_decay = 0.95;
  } else if (normalized == "decay_090") {
    params = czr004::ltm::UpdateParams();
    params.rho_decay = 0.90;
  }
  return params;
}

bool LaurLtmRuntime::load(const LaurRuntimeOptions& options)
{
  options_ = options;
  loaded_ = true;
  has_mlp_ = false;
  feature_names_.clear();
  feature_mean_.clear();
  feature_std_.clear();
  layer0_weight_.clear();
  layer0_bias_.clear();
  rule_head_weight_.clear();
  rule_head_bias_.clear();
  safety_head_weight_.clear();
  safety_head_bias_.clear();
  delta_head_weight_.clear();
  delta_head_bias_.clear();
  rules_.clear();
  recovery_specs_.clear();
  ood_stat_overrides_.clear();
  robust_feature_stats_.clear();
  utility_neighbors_.clear();
  rules_.push_back(RuleSpec{"additive_ltm", czr004::ltm::UpdateParams::additive()});
  input_dim_ = 0;
  hidden_dim_ = 0;

  if (options_.model_path.empty()) return true;
  return load_model_directory(options_.model_path);
}

LaurPrediction LaurLtmRuntime::additive_prediction(double inference_ms,
                                                   bool enabled) const
{
  LaurPrediction prediction;
  prediction.params = czr004::ltm::UpdateParams::additive();
  prediction.rule_id = "additive_ltm";
  prediction.selected_rule_before_guard = "additive_ltm";
  prediction.selected_rule_after_guard = "additive_ltm";
  prediction.selected_rule_source =
      enabled ? (options_.force_additive ? "force_additive" : "additive_fallback")
              : "runtime_disabled";
  prediction.safety_harmful_prob = enabled ? 0.0 : 1.0;
  prediction.predicted_delta_ratio = 0.0;
  prediction.predicted_margin_ratio = 0.0;
  prediction.nearest_support_count = 0;
  prediction.guard_reason = prediction.selected_rule_source;
  prediction.inference_ms = inference_ms;
  prediction.enabled = enabled;
  return prediction;
}

LaurPrediction LaurLtmRuntime::predict(const LaurFeatureVector& features) const
{
  const auto started = std::chrono::steady_clock::now();
  const auto elapsed = [&]() {
    const auto ended = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(ended - started).count();
  };

  if (!loaded_ || !options_.enabled) {
    return additive_prediction(elapsed(), false);
  }
  if (options_.force_additive || !has_mlp_) {
    return additive_prediction(elapsed(), true);
  }

  auto by_name = std::unordered_map<std::string, double>();
  for (std::size_t index = 0; index < features.names.size() &&
                              index < features.values.size();
       ++index) {
    by_name[features.names[index]] = features.values[index];
  }

  auto x = std::vector<double>(input_dim_, 0.0);
  auto guard_x = std::vector<double>(input_dim_, 0.0);
  for (uint index = 0; index < input_dim_; ++index) {
    double value = 0.0;
    if (index < feature_names_.size()) {
      const auto it = by_name.find(feature_names_[index]);
      if (it != by_name.end()) value = it->second;
    } else if (index < features.values.size()) {
      value = features.values[index];
    }
    const auto mean = index < feature_mean_.size() ? feature_mean_[index] : 0.0;
    const auto stdev = index < feature_std_.size() &&
                               std::fabs(feature_std_[index]) > kEps
                           ? feature_std_[index]
                           : 1.0;
    x[index] = (value - mean) / stdev;

    double guard_mean = mean;
    double guard_stdev = stdev;
    if (index < feature_names_.size()) {
      for (const auto& item : ood_stat_overrides_) {
        if (item.feature_name == feature_names_[index]) {
          guard_mean = item.mean;
          guard_stdev = std::fabs(item.stdev) > kEps ? item.stdev : 1.0;
          break;
        }
      }
    }
    guard_x[index] = (value - guard_mean) / guard_stdev;
  }

  uint robust_outside_count = 0;
  uint robust_extreme_count = 0;
  bool robust_missing_required = false;
  std::string guard_reason;
  if (!robust_feature_stats_.empty()) {
    for (const auto& stat : robust_feature_stats_) {
      const auto it = by_name.find(stat.feature_name);
      if (it == by_name.end()) {
        if (stat.required) {
          robust_missing_required = true;
          if (guard_reason.empty()) {
            guard_reason = "missing_required_feature:" + stat.feature_name;
          }
        }
        continue;
      }
      if (stat.rows_non_missing == 0) {
        robust_missing_required = true;
        if (guard_reason.empty()) {
          guard_reason = "invalid_feature_stats:" + stat.feature_name;
        }
        continue;
      }
      const auto robust_scale = std::max(
          {std::fabs(stat.p99 - stat.p01),
           std::fabs(stat.stdev) > kEps ? 2.0 * std::fabs(stat.stdev) : 0.0,
           std::fabs(stat.mad) > kEps ? 6.0 * std::fabs(stat.mad) : 0.0,
           1.0});
      const auto low = stat.p01 - robust_scale;
      const auto high = stat.p99 + robust_scale;
      const auto extreme_low = stat.min_value - 2.0 * robust_scale;
      const auto extreme_high = stat.max_value + 2.0 * robust_scale;
      const auto value = it->second;
      if (value < low || value > high) {
        ++robust_outside_count;
        if (guard_reason.empty()) {
          guard_reason = "robust_threshold:" + stat.feature_name;
        }
      }
      if (value < extreme_low || value > extreme_high) {
        ++robust_extreme_count;
        guard_reason = "extreme_percentile_bound:" + stat.feature_name;
      }
    }
  }

  double max_abs_z = 0.0;
  double sum_abs_z = 0.0;
  uint outside_3sigma = 0;
  uint outside_5sigma = 0;
  for (const auto value : guard_x) {
    const auto abs_z = std::fabs(value);
    max_abs_z = std::max(max_abs_z, abs_z);
    sum_abs_z += abs_z;
    if (abs_z > 3.0) ++outside_3sigma;
    if (abs_z > 5.0) ++outside_5sigma;
  }
  const auto mean_abs_z = x.empty() ? 0.0 : sum_abs_z / x.size();
  const auto attach_ood_metrics = [&](LaurPrediction& prediction) {
    prediction.feature_max_abs_z = max_abs_z;
    prediction.feature_mean_abs_z = mean_abs_z;
    prediction.feature_outside_3sigma_count = outside_3sigma;
    prediction.feature_outside_5sigma_count = outside_5sigma;
    prediction.ood_z_threshold =
        options_.ood_guard_enabled ? options_.ood_z_threshold : 0.0;
    if (!guard_reason.empty() || prediction.guard_reason.empty()) {
      prediction.guard_reason = guard_reason;
    }
  };

  auto hidden = std::vector<double>(hidden_dim_, 0.0);
  for (uint row = 0; row < hidden_dim_; ++row) {
    const auto bias = row < layer0_bias_.size() ? layer0_bias_[row] : 0.0;
    hidden[row] = std::max(0.0, dot_row(layer0_weight_, input_dim_, row, x) + bias);
  }

  const auto rule_count = static_cast<uint>(rules_.size());
  auto logits = std::vector<double>(rule_count, 0.0);
  for (uint row = 0; row < rule_count; ++row) {
    const auto bias = row < rule_head_bias_.size() ? rule_head_bias_[row] : 0.0;
    logits[row] = dot_row(rule_head_weight_, hidden_dim_, row, hidden) + bias;
  }

  const auto selected = std::min(argmax(logits), rules_.size() - 1);
  auto prediction = LaurPrediction();
  prediction.params = rules_[selected].params;
  prediction.rule_id = rules_[selected].rule_id;
  prediction.selected_rule_before_guard = rules_[selected].rule_id;
  prediction.selected_rule_after_guard = rules_[selected].rule_id;
  prediction.selected_rule_source =
      rules_[selected].selected_rule_source.empty()
          ? "runtime_mlp"
          : rules_[selected].selected_rule_source;
  prediction.predicted_delta_ratio = rules_[selected].predicted_delta_ratio;
  prediction.predicted_margin_ratio = rules_[selected].predicted_margin_ratio;
  prediction.nearest_support_count = rules_[selected].nearest_support_count;
  prediction.guard_reason = rules_[selected].guard_reason;
  prediction.enabled = true;
  if (!safety_head_weight_.empty()) {
    const auto bias = safety_head_bias_.empty() ? 0.0 : safety_head_bias_[0];
    prediction.safety_harmful_prob =
        sigmoid(dot_row(safety_head_weight_, hidden_dim_, 0, hidden) + bias);
  } else {
    prediction.safety_harmful_prob = 0.0;
  }
  if (!delta_head_weight_.empty()) {
    const auto bias = delta_head_bias_.empty() ? 0.0 : delta_head_bias_[0];
    prediction.predicted_delta_ratio =
        dot_row(delta_head_weight_, hidden_dim_, 0, hidden) + bias;
  }
  prediction.inference_ms = elapsed();
  attach_ood_metrics(prediction);

  const auto ood_triggered =
      options_.ood_guard_enabled &&
      ((!robust_feature_stats_.empty() &&
        (robust_missing_required || robust_extreme_count > 0 ||
         robust_outside_count >= 2)) ||
       (robust_feature_stats_.empty() && options_.ood_z_threshold > 0.0 &&
        std::isfinite(options_.ood_z_threshold) &&
        max_abs_z >= options_.ood_z_threshold));

  if (ood_triggered) {
    auto guarded = additive_prediction(elapsed(), true);
    guarded.safety_harmful_prob = prediction.safety_harmful_prob;
    guarded.predicted_delta_ratio = prediction.predicted_delta_ratio;
    guarded.predicted_margin_ratio = prediction.predicted_margin_ratio;
    guarded.nearest_support_count = prediction.nearest_support_count;
    guarded.feature_max_abs_z = prediction.feature_max_abs_z;
    guarded.feature_mean_abs_z = prediction.feature_mean_abs_z;
    guarded.feature_outside_3sigma_count =
        prediction.feature_outside_3sigma_count;
    guarded.feature_outside_5sigma_count =
        prediction.feature_outside_5sigma_count;
    guarded.ood_z_threshold = prediction.ood_z_threshold;
    guarded.ood_guard_triggered = true;
    guarded.selected_rule_before_guard = prediction.rule_id;
    guarded.selected_rule_after_guard = "additive_ltm";
    guarded.selected_rule_source = "ood_guard";
    guarded.guard_reason =
        guard_reason.empty() ? "max_abs_z_threshold" : guard_reason;
    return guarded;
  }

  if (!utility_neighbors_.empty()) {
    const UtilityNeighbor* nearest = nullptr;
    double nearest_distance = std::numeric_limits<double>::infinity();
    const auto agents = lookup_feature(by_name, "agents");
    const auto map_width = lookup_feature(by_name, "map_width");
    const auto map_height = lookup_feature(by_name, "map_height");
    const auto obstacle_ratio = lookup_feature(by_name, "obstacle_ratio");
    for (const auto& neighbor : utility_neighbors_) {
      if (neighbor.feature_values.size() < input_dim_) continue;
      if (!close_bucket(agents, neighbor.agents) ||
          !close_bucket(map_width, neighbor.map_width) ||
          !close_bucket(map_height, neighbor.map_height) ||
          obstacle_ratio < neighbor.obstacle_ratio_min ||
          obstacle_ratio > neighbor.obstacle_ratio_max) {
        continue;
      }
      double distance_sq = 0.0;
      uint used = 0;
      for (uint index = 0; index < input_dim_; ++index) {
        const auto feature_name =
            index < feature_names_.size() ? feature_names_[index] : "";
        const auto it = by_name.find(feature_name);
        if (it == by_name.end()) continue;
        const auto stdev = index < feature_std_.size() &&
                                   std::fabs(feature_std_[index]) > kEps
                               ? feature_std_[index]
                               : 1.0;
        const auto diff = (it->second - neighbor.feature_values[index]) / stdev;
        distance_sq += diff * diff;
        ++used;
      }
      if (used == 0) continue;
      const auto distance = std::sqrt(distance_sq / used);
      if (distance < nearest_distance) {
        nearest_distance = distance;
        nearest = &neighbor;
      }
    }

    if (nearest != nullptr && nearest->rule_id != "additive_ltm" &&
        nearest->nearest_support_count >= nearest->min_support_neighbors &&
        nearest->predicted_margin_ratio >= nearest->min_predicted_margin_ratio &&
        nearest_distance <= nearest->max_neighbor_distance &&
        is_supported_laur_rule_id(nearest->rule_id)) {
      prediction.params = update_params_for_laur_rule_id(nearest->rule_id);
      prediction.rule_id = nearest->rule_id;
      prediction.selected_rule_before_guard = nearest->rule_id;
      prediction.selected_rule_after_guard = nearest->rule_id;
      prediction.selected_rule_source =
          nearest->source.empty() ? "repair5e4_closed_loop_utility_selector"
                                  : nearest->source;
      prediction.safety_harmful_prob = std::min(prediction.safety_harmful_prob, 0.0);
      prediction.predicted_margin_ratio = nearest->predicted_margin_ratio;
      prediction.predicted_delta_ratio = -nearest->predicted_margin_ratio;
      prediction.nearest_support_count = nearest->nearest_support_count;
      prediction.guard_reason = "passed";
      return prediction;
    }

    auto deferred = additive_prediction(elapsed(), true);
    deferred.safety_harmful_prob = prediction.safety_harmful_prob;
    deferred.predicted_delta_ratio = prediction.predicted_delta_ratio;
    deferred.predicted_margin_ratio =
        nearest == nullptr ? 0.0 : nearest->predicted_margin_ratio;
    deferred.nearest_support_count =
        nearest == nullptr ? 0 : nearest->nearest_support_count;
    deferred.feature_max_abs_z = prediction.feature_max_abs_z;
    deferred.feature_mean_abs_z = prediction.feature_mean_abs_z;
    deferred.feature_outside_3sigma_count =
        prediction.feature_outside_3sigma_count;
    deferred.feature_outside_5sigma_count =
        prediction.feature_outside_5sigma_count;
    deferred.ood_z_threshold = prediction.ood_z_threshold;
    deferred.selected_rule_before_guard = prediction.rule_id;
    deferred.selected_rule_after_guard = "additive_ltm";
    deferred.selected_rule_source = "repair5e4_no_supported_neighbor_defer";
    deferred.guard_reason =
        nearest == nullptr
            ? "no_neighbor"
            : (nearest_distance > nearest->max_neighbor_distance
                   ? "neighbor_distance_above_threshold"
                   : "insufficient_margin_or_support");
    return deferred;
  }

  if (!recovery_specs_.empty()) {
    const auto agents = lookup_feature(by_name, "agents");
    const auto map_width = lookup_feature(by_name, "map_width");
    const auto map_height = lookup_feature(by_name, "map_height");
    const auto obstacle_ratio = lookup_feature(by_name, "obstacle_ratio");
    const RecoverySpec* match = nullptr;
    for (const auto& spec : recovery_specs_) {
      if (!close_bucket(agents, spec.agents) ||
          !close_bucket(map_width, spec.map_width) ||
          !close_bucket(map_height, spec.map_height) ||
          obstacle_ratio < spec.obstacle_ratio_min ||
          obstacle_ratio > spec.obstacle_ratio_max) {
        continue;
      }
      match = &spec;
      break;
    }

    if (match != nullptr && match->rule_id != "additive_ltm" &&
        match->rule_id != "commit_heavy" &&
        is_supported_laur_rule_id(match->rule_id)) {
      prediction.params = update_params_for_laur_rule_id(match->rule_id);
      prediction.rule_id = match->rule_id;
      prediction.selected_rule_after_guard = match->rule_id;
      prediction.selected_rule_source = "repair5e2_oracle_aligned_rerank";
      prediction.safety_harmful_prob = std::min(prediction.safety_harmful_prob, 0.0);
      return prediction;
    }

    auto deferred = additive_prediction(elapsed(), true);
    deferred.safety_harmful_prob = prediction.safety_harmful_prob;
    deferred.predicted_delta_ratio = prediction.predicted_delta_ratio;
    deferred.feature_max_abs_z = prediction.feature_max_abs_z;
    deferred.feature_mean_abs_z = prediction.feature_mean_abs_z;
    deferred.feature_outside_3sigma_count =
        prediction.feature_outside_3sigma_count;
    deferred.feature_outside_5sigma_count =
        prediction.feature_outside_5sigma_count;
    deferred.ood_z_threshold = prediction.ood_z_threshold;
    deferred.selected_rule_before_guard = prediction.rule_id;
    deferred.selected_rule_after_guard = "additive_ltm";
    deferred.selected_rule_source = "repair5e2_no_supported_nonadditive_defer";
    return deferred;
  }

  return prediction;
}

bool LaurLtmRuntime::load_model_directory(const std::string& model_path)
{
  const auto root = std::filesystem::path(model_path);
  if (!std::filesystem::exists(root) || !std::filesystem::is_directory(root)) {
    return false;
  }

  const auto rules_path = root / "rules.csv";
  if (std::filesystem::exists(rules_path)) {
    auto next_rules = std::vector<RuleSpec>();
    auto in = std::ifstream(rules_path);
    std::string line;
    bool first = true;
    while (std::getline(in, line)) {
      const auto cells = split_csv_line(line);
      if (cells.empty() || cells[0].empty()) continue;
      if (first && cells[0] == "rule_id") {
        first = false;
        continue;
      }
      first = false;

      auto spec = RuleSpec();
      spec.rule_id = cells[0] == "neutral_additive" ? "additive_ltm" : cells[0];
      spec.params = update_params_for_laur_rule_id(spec.rule_id);
      if (cells.size() >= 8) {
        spec.params.alpha_commit = parse_double_or(cells[1], spec.params.alpha_commit);
        spec.params.alpha_block = parse_double_or(cells[2], spec.params.alpha_block);
        spec.params.alpha_wait_spillover =
            parse_double_or(cells[3], spec.params.alpha_wait_spillover);
        spec.params.rho_decay = parse_double_or(cells[4], spec.params.rho_decay);
        spec.params.enable_local_saturation =
            std::fabs(parse_double_or(cells[5], 1.0) - 1.0) > kEps;
        spec.params.contraflow_penalty =
            parse_double_or(cells[6], spec.params.contraflow_penalty);
        spec.params.enable_contraflow_penalty = spec.params.contraflow_penalty > 0.0;
        spec.params.force_additive = parse_bool(cells[7]);
      }
      if (cells.size() >= 11) {
        spec.predicted_delta_ratio = parse_double_or(cells[8], 0.0);
        spec.predicted_margin_ratio = parse_double_or(cells[9], 0.0);
        spec.nearest_support_count = parse_uint_or(cells[10], 0);
      }
      if (cells.size() >= 12) {
        spec.selected_rule_source = cells[11];
      }
      if (cells.size() >= 13) {
        spec.guard_reason = cells[12];
      }
      next_rules.push_back(spec);
    }
    if (!next_rules.empty()) rules_ = std::move(next_rules);
  }

  feature_names_ = read_lines(root / "features.txt");
  feature_mean_ = read_vector_csv(root / "mean.csv");
  feature_std_ = read_vector_csv(root / "std.csv");
  layer0_weight_ = read_vector_csv(root / "layer0_weight.csv");
  layer0_bias_ = read_vector_csv(root / "layer0_bias.csv");
  rule_head_weight_ = read_vector_csv(root / "rule_head_weight.csv");
  rule_head_bias_ = read_vector_csv(root / "rule_head_bias.csv");
  safety_head_weight_ = read_vector_csv(root / "safety_head_weight.csv");
  safety_head_bias_ = read_vector_csv(root / "safety_head_bias.csv");
  delta_head_weight_ = read_vector_csv(root / "delta_head_weight.csv");
  delta_head_bias_ = read_vector_csv(root / "delta_head_bias.csv");

  const auto override_path = root / "ood_feature_stats_override.csv";
  if (std::filesystem::exists(override_path)) {
    auto in = std::ifstream(override_path);
    std::string line;
    bool first = true;
    while (std::getline(in, line)) {
      const auto cells = split_csv_line(line);
      if (cells.size() < 3) continue;
      if (first && cells[0] == "feature_name") {
        first = false;
        continue;
      }
      first = false;
      auto item = FeatureStatOverride();
      item.feature_name = cells[0];
      item.mean = parse_double_or(cells[1], 0.0);
      item.stdev = parse_double_or(cells[2], 1.0);
      if (!item.feature_name.empty() && std::fabs(item.stdev) > kEps) {
        ood_stat_overrides_.push_back(item);
      }
    }
  }

  const auto robust_stats_path = root / "ood_feature_stats_train.csv";
  if (std::filesystem::exists(robust_stats_path)) {
    auto in = std::ifstream(robust_stats_path);
    std::string line;
    if (std::getline(in, line)) {
      const auto header = split_csv_line(line);
      const auto index = header_index(header);
      const auto has_robust_columns =
          index.count("feature_name") > 0 && index.count("p01") > 0 &&
          index.count("p99") > 0 && index.count("min") > 0 &&
          index.count("max") > 0 && index.count("rows_non_missing") > 0;
      if (has_robust_columns) {
        while (std::getline(in, line)) {
          const auto cells = split_csv_line(line);
          auto stat = RobustFeatureStat();
          stat.feature_name = cell_at(cells, index, "feature_name");
          if (stat.feature_name.empty()) continue;
          stat.mean = parse_double_or(cell_at(cells, index, "mean"), 0.0);
          stat.stdev = parse_double_or(cell_at(cells, index, "std"), 1.0);
          if (std::fabs(stat.stdev) <= kEps) stat.stdev = 1.0;
          stat.median = parse_double_or(cell_at(cells, index, "median"), stat.mean);
          stat.mad = parse_double_or(cell_at(cells, index, "mad"), 0.0);
          stat.p01 = parse_double_or(cell_at(cells, index, "p01"), stat.mean);
          stat.p99 = parse_double_or(cell_at(cells, index, "p99"), stat.mean);
          stat.min_value = parse_double_or(cell_at(cells, index, "min"), stat.p01);
          stat.max_value = parse_double_or(cell_at(cells, index, "max"), stat.p99);
          stat.rows_non_missing =
              parse_uint_or(cell_at(cells, index, "rows_non_missing"), 0);
          stat.required =
              cell_at(cells, index, "required").empty()
                  ? true
                  : parse_bool(cell_at(cells, index, "required"));
          robust_feature_stats_.push_back(stat);
        }
      }
    }
  }

  const auto selector_path = root / "repair5e4_utility_selector.csv";
  if (std::filesystem::exists(selector_path)) {
    auto in = std::ifstream(selector_path);
    std::string line;
    if (std::getline(in, line)) {
      const auto header = split_csv_line(line);
      const auto index = header_index(header);
      while (std::getline(in, line)) {
        const auto cells = split_csv_line(line);
        auto item = UtilityNeighbor();
        item.rule_id = cell_at(cells, index, "rule_id");
        if (item.rule_id == "neutral_additive") item.rule_id = "additive_ltm";
        item.map_width = parse_double_or(cell_at(cells, index, "map_width"), 0.0);
        item.map_height = parse_double_or(cell_at(cells, index, "map_height"), 0.0);
        item.obstacle_ratio_min =
            parse_double_or(cell_at(cells, index, "obstacle_ratio_min"), -1.0);
        item.obstacle_ratio_max =
            parse_double_or(cell_at(cells, index, "obstacle_ratio_max"), 2.0);
        item.agents = parse_double_or(cell_at(cells, index, "agents"), 0.0);
        item.predicted_margin_ratio =
            parse_double_or(cell_at(cells, index, "predicted_margin_ratio"), 0.0);
        item.nearest_support_count =
            parse_uint_or(cell_at(cells, index, "nearest_support_count"), 0);
        item.min_support_neighbors =
            parse_uint_or(cell_at(cells, index, "min_support_neighbors"), 5);
        item.min_predicted_margin_ratio =
            parse_double_or(cell_at(cells, index, "min_predicted_margin_ratio"), 0.001);
        item.max_neighbor_distance =
            parse_double_or(cell_at(cells, index, "max_neighbor_distance"), 1.0e9);
        item.source = cell_at(cells, index, "source");
        const auto value_cells = split_semicolon_list(cell_at(cells, index, "feature_values"));
        for (const auto& value : value_cells) {
          item.feature_values.push_back(parse_double_or(value, 0.0));
        }
        if (is_supported_laur_rule_id(item.rule_id) &&
            item.feature_values.size() >= feature_names_.size()) {
          utility_neighbors_.push_back(item);
        }
      }
    }
  }

  const auto recovery_path = root / "repair5e2_recovery_rules.csv";
  if (std::filesystem::exists(recovery_path)) {
    auto in = std::ifstream(recovery_path);
    std::string line;
    bool first = true;
    while (std::getline(in, line)) {
      const auto cells = split_csv_line(line);
      if (cells.size() < 9) continue;
      if (first && cells[0] == "map_width") {
        first = false;
        continue;
      }
      first = false;
      auto spec = RecoverySpec();
      spec.map_width = parse_double_or(cells[0], 0.0);
      spec.map_height = parse_double_or(cells[1], 0.0);
      spec.obstacle_ratio_min = parse_double_or(cells[2], -1.0);
      spec.obstacle_ratio_max = parse_double_or(cells[3], 2.0);
      spec.agents = parse_double_or(cells[4], 0.0);
      spec.rule_id = cells[5] == "neutral_additive" ? "additive_ltm" : cells[5];
      spec.support_mean_delta = parse_double_or(cells[6], 0.0);
      spec.support_rows = static_cast<uint>(std::max(
          0.0, parse_double_or(cells[7], 0.0)));
      spec.source = cells[8];
      if (is_supported_laur_rule_id(spec.rule_id)) {
        recovery_specs_.push_back(spec);
      }
    }
  }

  input_dim_ = static_cast<uint>(feature_names_.size());
  if (input_dim_ == 0 && !feature_mean_.empty()) {
    input_dim_ = static_cast<uint>(feature_mean_.size());
  }
  hidden_dim_ = static_cast<uint>(layer0_bias_.size());
  const auto rule_count = static_cast<uint>(rules_.size());
  has_mlp_ = input_dim_ > 0 && hidden_dim_ > 0 &&
             layer0_weight_.size() == static_cast<std::size_t>(input_dim_) * hidden_dim_ &&
             rule_head_weight_.size() == static_cast<std::size_t>(hidden_dim_) * rule_count &&
             rule_head_bias_.size() == rule_count;
  return true;
}

}  // namespace czr004::ntm
