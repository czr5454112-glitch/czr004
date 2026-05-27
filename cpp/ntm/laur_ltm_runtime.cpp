#include "laur_ltm_runtime.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
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
  prediction.safety_harmful_prob = enabled ? 0.0 : 1.0;
  prediction.predicted_delta_ratio = 0.0;
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
  }

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
