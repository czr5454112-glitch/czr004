#include "ltm.hpp"
#include "laur_ltm_features.hpp"
#include "laur_ltm_runtime.hpp"

#include <lacam2.hpp>

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

struct Args {
  std::string method;
  std::string map;
  std::string scen;
  std::string map_name;
  std::string scen_id;
  std::string output_jsonl;
  std::string manifest;
  std::string project_commit;
  std::string external_commit;
  std::string branch;
  std::string dirty;
  std::string platform;
  std::string traffic_map_jsonl;
  std::string traffic_map_run_id;
  std::string traffic_map_edge_filter = "all";
  std::string laur_model_path;
  std::string laur_static_rule;
  std::string laur_update_log_jsonl;
  std::string repair5g_export_update_checkpoints_jsonl;
  std::string repair5g_checkpoint_edge_filter = "nonzero";
  std::string repair5g_counterfactual_update_probe_jsonl;
  std::string repair5g_counterfactual_candidates;
  std::string method_alias;
  std::string repair5g5_selector_spec_path;
  std::string repair5g5_selector_mode = "disabled";
  std::string repair5g5_selector_name = "disabled";
  std::string repair5g5_stump_feature;
  std::string repair5g5_stump_left_method;
  std::string repair5g5_stump_right_method;
  std::string repair5g5_stump_fallback_method;
  std::string repair5g5_static_candidate =
      "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75";
  std::string repair5g5_c_equiv_candidate =
      "repair5g_dual_c_equiv_c100_b100_w075_d100";
  std::string repair5g_runtime_audit_mode = "audit";
  std::string repair5g53_hook_mode = "disabled";
  std::string repair5g53_fixed_candidate;
  std::string repair5g_transform_audit_candidate;
  std::string repair5g_transform_audit_jsonl;
  std::string repair5g_candidate_id;
  std::string repair5g_update_mode = "disabled";
  czr004::ltm::UpdateParams repair5g_update_params =
      czr004::ltm::UpdateParams::additive();
  uint agents = 0;
  uint seed = 0;
  double time_limit_sec = 30.0;
  uint ltm_max_iterations = 100000;
  bool laur_enable = false;
  bool laur_disable = false;
  bool laur_force_additive = false;
  bool laur_safety_enabled = true;
  bool laur_post_first_solution_only = true;
  bool laur_ood_guard_enabled = false;
  bool repair5g_enabled = false;
  bool repair5g5_selector_enabled = false;
  bool repair5g5_force_additive = false;
  bool repair5g53_hook_enabled = false;
  uint laur_every_k_restarts = 1;
  double laur_safety_threshold = 0.30;
  double laur_ood_z_threshold = 5.0;
  double repair5g5_stump_threshold = 0.0;
  uint repair5g_checkpoint_topk_edges = 0;
  bool repair5g_checkpoint_include_full_traffic = false;
  double repair5g_counterfactual_short_budget_ms = 1000.0;
  uint repair5g_counterfactual_max_contexts = 0;
  int verbose = 0;
};

std::string json_escape(const std::string& value)
{
  std::ostringstream out;
  for (const char ch : value) {
    switch (ch) {
      case '\\':
        out << "\\\\";
        break;
      case '"':
        out << "\\\"";
        break;
      case '\n':
        out << "\\n";
        break;
      case '\r':
        out << "\\r";
        break;
      case '\t':
        out << "\\t";
        break;
      default:
        out << ch;
    }
  }
  return out.str();
}

std::string json_string(const std::string& value)
{
  return "\"" + json_escape(value) + "\"";
}

std::string json_number_or_null(double value)
{
  if (!std::isfinite(value)) return "null";
  std::ostringstream out;
  out.precision(12);
  out << value;
  return out.str();
}

std::string goal_projection_mode_name(czr004::ltm::GoalProjectionMode mode);

std::string stable_hex_hash(const std::string& value)
{
  std::uint64_t hash = 1469598103934665603ull;
  for (const unsigned char ch : value) {
    hash ^= static_cast<std::uint64_t>(ch);
    hash *= 1099511628211ull;
  }
  std::ostringstream out;
  out << std::hex << hash;
  return out.str();
}

std::string update_params_fingerprint(
    const czr004::ltm::UpdateParams& params)
{
  std::ostringstream out;
  out.precision(17);
  out << "alpha_commit=" << params.alpha_commit;
  out << "|alpha_block=" << params.alpha_block;
  out << "|alpha_wait_spillover=" << params.alpha_wait_spillover;
  out << "|rho_decay=" << params.rho_decay;
  out << "|force_additive=" << (params.force_additive ? 1 : 0);
  out << "|enable_dual_channel=" << (params.enable_dual_channel ? 1 : 0);
  out << "|alpha_cong_commit_progress="
      << params.alpha_cong_commit_progress;
  out << "|alpha_cong_commit_nonprogress="
      << params.alpha_cong_commit_nonprogress;
  out << "|alpha_cong_block=" << params.alpha_cong_block;
  out << "|alpha_cong_wait_progress=" << params.alpha_cong_wait_progress;
  out << "|alpha_cong_wait_nonprogress="
      << params.alpha_cong_wait_nonprogress;
  out << "|alpha_flow_commit_progress="
      << params.alpha_flow_commit_progress;
  out << "|alpha_flow_wait_progress=" << params.alpha_flow_wait_progress;
  out << "|rho_cong_decay=" << params.rho_cong_decay;
  out << "|rho_flow_decay=" << params.rho_flow_decay;
  out << "|lambda_cong=" << params.lambda_cong;
  out << "|lambda_flow=" << params.lambda_flow;
  out << "|min_edge_cost=" << params.min_edge_cost;
  out << "|max_edge_cost=" << params.max_edge_cost;
  out << "|goal_projection_mode="
      << goal_projection_mode_name(params.goal_projection_mode);
  out << "|flow_shield_beta=" << params.flow_shield_beta;
  out << "|max_flow_shield=" << params.max_flow_shield;
  return out.str();
}

std::string update_params_hash(const czr004::ltm::UpdateParams& params)
{
  return stable_hex_hash(update_params_fingerprint(params));
}

void append_json_string_uint_map(std::ostream& out,
                                 const std::map<std::string, uint>& values)
{
  out << "{";
  bool first = true;
  for (const auto& [key, value] : values) {
    if (!first) out << ",";
    first = false;
    out << json_string(key) << ":" << value;
  }
  out << "}";
}

void append_json_string_array(std::ostream& out,
                              const std::vector<std::string>& values)
{
  out << "[";
  for (std::size_t index = 0; index < values.size(); ++index) {
    if (index > 0) out << ",";
    out << json_string(values[index]);
  }
  out << "]";
}

void append_json_number_array(std::ostream& out,
                              const std::vector<double>& values)
{
  out << "[";
  for (std::size_t index = 0; index < values.size(); ++index) {
    if (index > 0) out << ",";
    out << json_number_or_null(values[index]);
  }
  out << "]";
}

std::vector<std::string> split_token(const std::string& value, char delimiter)
{
  auto out = std::vector<std::string>();
  auto stream = std::stringstream(value);
  std::string cell;
  while (std::getline(stream, cell, delimiter)) out.push_back(cell);
  return out;
}

czr004::ltm::UpdateParams update_params_for_logged_rule(
    const std::string& rule_id)
{
  const auto parts = split_token(rule_id, '_');
  if (parts.size() == 4 && parts[0].size() == 4 && parts[1].size() == 4 &&
      parts[2].size() == 4 && parts[3].size() == 4 &&
      parts[0][0] == 'c' && parts[1][0] == 'b' && parts[2][0] == 'w' &&
      parts[3][0] == 'd') {
    try {
      auto params = czr004::ltm::UpdateParams();
      params.alpha_commit = std::stod(parts[0].substr(1)) / 100.0;
      params.alpha_block = std::stod(parts[1].substr(1)) / 100.0;
      params.alpha_wait_spillover = std::stod(parts[2].substr(1)) / 100.0;
      params.rho_decay = std::stod(parts[3].substr(1)) / 100.0;
      params.force_additive = false;
      return params;
    } catch (...) {
    }
  }
  return czr004::ntm::update_params_for_laur_rule_id(rule_id);
}

bool parse_uint(const std::string& value, uint* out)
{
  try {
    *out = static_cast<uint>(std::stoul(value));
    return true;
  } catch (...) {
    return false;
  }
}

bool parse_double(const std::string& value, double* out)
{
  try {
    *out = std::stod(value);
    return true;
  } catch (...) {
    return false;
  }
}

bool parse_bool_text(const std::string& value, bool* out)
{
  auto lower = value;
  std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char ch) {
    return static_cast<char>(std::tolower(ch));
  });
  if (lower == "1" || lower == "true" || lower == "yes" || lower == "on") {
    *out = true;
    return true;
  }
  if (lower == "0" || lower == "false" || lower == "no" || lower == "off") {
    *out = false;
    return true;
  }
  return false;
}

std::string read_text_file(const std::string& path)
{
  auto input = std::ifstream(path);
  if (!input) return "";
  auto buffer = std::ostringstream();
  buffer << input.rdbuf();
  return buffer.str();
}

std::string json_string_field(const std::string& text,
                              const std::string& key,
                              const std::string& fallback = "")
{
  const auto needle = "\"" + key + "\"";
  auto pos = text.find(needle);
  if (pos == std::string::npos) return fallback;
  pos = text.find(':', pos + needle.size());
  if (pos == std::string::npos) return fallback;
  pos = text.find('"', pos + 1);
  if (pos == std::string::npos) return fallback;
  auto end = pos + 1;
  while (end < text.size()) {
    if (text[end] == '"' && text[end - 1] != '\\') break;
    ++end;
  }
  if (end >= text.size()) return fallback;
  return text.substr(pos + 1, end - pos - 1);
}

double json_number_field(const std::string& text, const std::string& key,
                         double fallback = 0.0)
{
  const auto needle = "\"" + key + "\"";
  auto pos = text.find(needle);
  if (pos == std::string::npos) return fallback;
  pos = text.find(':', pos + needle.size());
  if (pos == std::string::npos) return fallback;
  ++pos;
  while (pos < text.size() &&
         std::isspace(static_cast<unsigned char>(text[pos]))) {
    ++pos;
  }
  auto end = pos;
  while (end < text.size()) {
    const auto ch = text[end];
    if (!(std::isdigit(static_cast<unsigned char>(ch)) || ch == '-' ||
          ch == '+' || ch == '.' || ch == 'e' || ch == 'E')) {
      break;
    }
    ++end;
  }
  if (end <= pos) return fallback;
  try {
    return std::stod(text.substr(pos, end - pos));
  } catch (...) {
    return fallback;
  }
}

std::string repair5f_selector_runtime_path()
{
  return "artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector";
}

std::string repair5f_static_runtime_path()
{
  return "artifacts/models/laur_ltm/repair5f_static_c100_b100_w075_d090";
}

struct Repair5GMethodSpec {
  bool recognized = false;
  std::string candidate_id;
  std::string update_mode;
  czr004::ltm::UpdateParams params = czr004::ltm::UpdateParams::additive();
};

struct ScalarRuleParams {
  double alpha_commit = 1.0;
  double alpha_block = 1.0;
  double alpha_wait = 1.0;
  double rho_decay = 1.0;
};

bool parse_scalar_rule_id(const std::string& rule_id, ScalarRuleParams* out)
{
  if (rule_id == "additive") {
    *out = ScalarRuleParams();
    return true;
  }
  const auto parts = split_token(rule_id, '_');
  if (parts.size() != 4 || parts[0].size() != 4 || parts[1].size() != 4 ||
      parts[2].size() != 4 || parts[3].size() != 4 ||
      parts[0][0] != 'c' || parts[1][0] != 'b' || parts[2][0] != 'w' ||
      parts[3][0] != 'd') {
    return false;
  }
  try {
    out->alpha_commit = std::stod(parts[0].substr(1)) / 100.0;
    out->alpha_block = std::stod(parts[1].substr(1)) / 100.0;
    out->alpha_wait = std::stod(parts[2].substr(1)) / 100.0;
    out->rho_decay = std::stod(parts[3].substr(1)) / 100.0;
    return true;
  } catch (...) {
    return false;
  }
}

bool parse_decimal_token(const std::string& token, double* out)
{
  auto value = token;
  for (auto& ch : value) {
    if (ch == 'p') ch = '.';
  }
  try {
    *out = std::stod(value);
    return true;
  } catch (...) {
    return false;
  }
}

std::string goal_projection_mode_name(czr004::ltm::GoalProjectionMode mode)
{
  switch (mode) {
    case czr004::ltm::GoalProjectionMode::AgentProgress:
      return "agent_progress";
    case czr004::ltm::GoalProjectionMode::FlowShield:
      return "flow_shield";
    case czr004::ltm::GoalProjectionMode::None:
    default:
      return "none";
  }
}

czr004::ltm::UpdateParams repair5g_base_dual_params()
{
  auto params = czr004::ltm::UpdateParams();
  params.enable_dual_channel = true;
  params.force_additive = false;
  params.alpha_commit = 1.0;
  params.alpha_block = 1.0;
  params.alpha_wait_spillover = 1.0;
  params.rho_decay = 1.0;
  params.alpha_cong_commit_progress = 0.0;
  params.alpha_cong_commit_nonprogress = 0.0;
  params.alpha_cong_block = 1.0;
  params.alpha_cong_wait_progress = 1.0;
  params.alpha_cong_wait_nonprogress = 1.0;
  params.alpha_flow_commit_progress = 1.0;
  params.alpha_flow_wait_progress = 0.0;
  params.rho_cong_decay = 1.0;
  params.rho_flow_decay = 1.0;
  params.lambda_cong = 1.0;
  params.lambda_flow = 0.25;
  params.min_edge_cost = 0.25;
  params.max_edge_cost = 11.0;
  params.goal_projection_mode = czr004::ltm::GoalProjectionMode::None;
  params.flow_shield_beta = 0.0;
  params.max_flow_shield = 0.0;
  return params;
}

czr004::ltm::UpdateParams repair5g1_dual_c_equiv_params(
    const ScalarRuleParams& scalar)
{
  auto params = repair5g_base_dual_params();
  params.alpha_commit = scalar.alpha_commit;
  params.alpha_block = scalar.alpha_block;
  params.alpha_wait_spillover = scalar.alpha_wait;
  params.rho_decay = scalar.rho_decay;
  params.alpha_cong_commit_progress = scalar.alpha_commit;
  params.alpha_cong_commit_nonprogress = scalar.alpha_commit;
  params.alpha_cong_block = scalar.alpha_block;
  params.alpha_cong_wait_progress = scalar.alpha_wait;
  params.alpha_cong_wait_nonprogress = scalar.alpha_wait;
  params.alpha_flow_commit_progress = 0.0;
  params.alpha_flow_wait_progress = 0.0;
  params.rho_cong_decay = scalar.rho_decay;
  params.rho_flow_decay = 1.0;
  params.lambda_cong = 1.0;
  params.lambda_flow = 0.0;
  params.min_edge_cost = 0.25;
  params.max_edge_cost = 11.0;
  params.goal_projection_mode = czr004::ltm::GoalProjectionMode::None;
  params.flow_shield_beta = 0.0;
  params.max_flow_shield = 0.0;
  return params;
}

czr004::ltm::UpdateParams repair5g1_dual_flow_params(
    const ScalarRuleParams& scalar,
    czr004::ltm::GoalProjectionMode projection_mode,
    double lambda_flow, double min_edge_cost)
{
  auto params = repair5g1_dual_c_equiv_params(scalar);
  params.alpha_flow_commit_progress = 1.0;
  params.lambda_flow = lambda_flow;
  params.min_edge_cost = min_edge_cost;
  params.max_edge_cost = 11.0;
  params.goal_projection_mode = projection_mode;
  return params;
}

bool parse_repair5g1_flow_method(const std::string& method,
                                 const std::string& prefix,
                                 czr004::ltm::GoalProjectionMode mode,
                                 Repair5GMethodSpec* spec)
{
  if (method.rfind(prefix, 0) != 0) return false;
  const auto lf_pos = method.find("_lf", prefix.size());
  if (lf_pos == std::string::npos) return false;
  const auto min_pos = method.find("_min", lf_pos + 3);
  if (min_pos == std::string::npos) return false;
  const auto rule_id = method.substr(prefix.size(), lf_pos - prefix.size());
  const auto lambda_token = method.substr(lf_pos + 3, min_pos - (lf_pos + 3));
  const auto min_token = method.substr(min_pos + 4);
  ScalarRuleParams scalar;
  double lambda_flow = 0.0;
  double min_edge_cost = 0.0;
  if (!parse_scalar_rule_id(rule_id, &scalar) ||
      !parse_decimal_token(lambda_token, &lambda_flow) ||
      !parse_decimal_token(min_token, &min_edge_cost)) {
    return false;
  }
  spec->recognized = true;
  spec->candidate_id = method.substr(std::string("repair5g1_").size());
  spec->params = repair5g1_dual_flow_params(scalar, mode, lambda_flow,
                                            min_edge_cost);
  spec->update_mode =
      mode == czr004::ltm::GoalProjectionMode::AgentProgress
          ? "dual_agent_progress"
          : "dual_global_flow";
  return true;
}

bool parse_repair5g1_flow_shield_method(const std::string& method,
                                        Repair5GMethodSpec* spec)
{
  const auto prefix = std::string("repair5g1_shield_");
  if (method.rfind(prefix, 0) != 0) return false;
  const auto beta_pos = method.find("_beta", prefix.size());
  if (beta_pos == std::string::npos) return false;
  const auto max_pos = method.find("_max", beta_pos + 5);
  if (max_pos == std::string::npos) return false;
  const auto rule_id = method.substr(prefix.size(), beta_pos - prefix.size());
  const auto beta_token = method.substr(beta_pos + 5, max_pos - (beta_pos + 5));
  const auto max_token = method.substr(max_pos + 4);
  ScalarRuleParams scalar;
  double beta = 0.0;
  double max_shield = 0.0;
  if (!parse_scalar_rule_id(rule_id, &scalar) ||
      !parse_decimal_token(beta_token, &beta) ||
      !parse_decimal_token(max_token, &max_shield)) {
    return false;
  }
  auto params = repair5g1_dual_c_equiv_params(scalar);
  params.alpha_flow_commit_progress = 1.0;
  params.min_edge_cost = 1.0;
  params.max_edge_cost = 11.0;
  params.goal_projection_mode = czr004::ltm::GoalProjectionMode::FlowShield;
  params.flow_shield_beta = beta;
  params.max_flow_shield = max_shield;
  spec->recognized = true;
  spec->candidate_id = method.substr(std::string("repair5g1_").size());
  spec->params = params;
  spec->update_mode = "dual_flow_shield";
  return true;
}

bool parse_repair5g1_wait_method(const std::string& method,
                                 Repair5GMethodSpec* spec)
{
  const auto prefix = std::string("repair5g1_wait_");
  if (method.rfind(prefix, 0) != 0) return false;
  const auto wp_pos = method.find("_wp", prefix.size());
  if (wp_pos == std::string::npos) return false;
  const auto wn_pos = method.find("_wn", wp_pos + 3);
  if (wn_pos == std::string::npos) return false;
  const auto rule_id = method.substr(prefix.size(), wp_pos - prefix.size());
  const auto wp_token = method.substr(wp_pos + 3, wn_pos - (wp_pos + 3));
  const auto wn_token = method.substr(wn_pos + 3);
  ScalarRuleParams scalar;
  double wait_progress = 0.0;
  double wait_nonprogress = 0.0;
  if (!parse_scalar_rule_id(rule_id, &scalar) ||
      !parse_decimal_token(wp_token, &wait_progress) ||
      !parse_decimal_token(wn_token, &wait_nonprogress)) {
    return false;
  }
  auto params = repair5g1_dual_c_equiv_params(scalar);
  params.alpha_cong_wait_progress = wait_progress;
  params.alpha_cong_wait_nonprogress = wait_nonprogress;
  params.alpha_flow_commit_progress = 0.0;
  params.lambda_flow = 0.0;
  spec->recognized = true;
  spec->candidate_id = method.substr(std::string("repair5g1_").size());
  spec->params = params;
  spec->update_mode = "dual_wait_gated";
  return true;
}

Repair5GMethodSpec repair5g_method_spec(const std::string& method)
{
  auto spec = Repair5GMethodSpec();
  auto set = [&](const std::string& candidate_id,
                 czr004::ltm::UpdateParams params,
                 const std::string& update_mode) {
    spec.recognized = true;
    spec.candidate_id = candidate_id;
    spec.params = params;
    spec.update_mode = update_mode;
  };
  auto set_g510_lattice =
      [&](double alpha_cong_committed, double alpha_cong_blocked,
          double alpha_flow_progress, double alpha_wait_or_nonprogress,
          double rho_cong, double rho_flow, double flow_shield_beta,
          double max_flow_shield, bool c_only, const std::string& mode) {
        auto scalar = ScalarRuleParams();
        scalar.alpha_commit = alpha_cong_committed;
        scalar.alpha_block = alpha_cong_blocked;
        scalar.alpha_wait = alpha_wait_or_nonprogress;
        scalar.rho_decay = rho_cong;
        auto params = repair5g1_dual_c_equiv_params(scalar);
        params.rho_flow_decay = rho_flow;
        if (c_only) {
          params.alpha_flow_commit_progress = 0.0;
          params.alpha_flow_wait_progress = 0.0;
          params.goal_projection_mode = czr004::ltm::GoalProjectionMode::None;
          params.flow_shield_beta = 0.0;
          params.max_flow_shield = 0.0;
          params.min_edge_cost = 0.25;
        } else {
          params.alpha_flow_commit_progress = alpha_flow_progress;
          params.alpha_flow_wait_progress = 0.0;
          params.goal_projection_mode =
              czr004::ltm::GoalProjectionMode::FlowShield;
          params.flow_shield_beta = flow_shield_beta;
          params.max_flow_shield = max_flow_shield;
          params.min_edge_cost = 1.0;
        }
        params.max_edge_cost = 11.0;
        set(method, params, mode);
      };

  if (method == "repair5g_dual_additive_parity") {
    set("dcltm_additive_parity", czr004::ltm::UpdateParams::additive(),
        "additive_parity");
  } else if (method == "repair5g59_additive_fallback") {
    set(method, czr004::ltm::UpdateParams::additive(),
        "g510_lattice_additive_fallback");
  } else if (method == "repair5g59_static_flow_shield" ||
             method == "repair5g59_static_abstain_candidate") {
    set_g510_lattice(1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75,
                     false, "g510_lattice_static_flow_shield");
  } else if (method == "repair5g59_c_only_f_disabled") {
    set_g510_lattice(1.25, 1.25, 0.0, 0.75, 0.95, 1.0, 0.0, 0.0,
                     true, "g510_lattice_c_only");
  } else if (method == "repair5g59_light_cong_light_flow") {
    set_g510_lattice(1.0, 1.0, 0.75, 0.75, 0.98, 1.0, 0.25, 0.50,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_block_heavy_flow_guard") {
    set_g510_lattice(1.0, 1.5, 1.0, 0.50, 0.95, 1.0, 0.35, 0.75,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_commit_heavy_flow_guard") {
    set_g510_lattice(1.5, 1.0, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_slow_decay_high_shield") {
    set_g510_lattice(1.25, 1.25, 1.0, 0.75, 0.98, 1.0, 0.50, 1.00,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_fast_decay_low_shield") {
    set_g510_lattice(1.25, 1.25, 1.0, 0.75, 0.90, 1.0, 0.20, 0.50,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_wait_conservative") {
    set_g510_lattice(1.25, 1.25, 1.0, 0.50, 0.95, 1.0, 0.35, 0.75,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_wait_aggressive") {
    set_g510_lattice(1.25, 1.25, 1.0, 1.00, 0.95, 1.0, 0.35, 0.75,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_flow_decay") {
    set_g510_lattice(1.25, 1.25, 1.0, 0.75, 0.95, 0.95, 0.35, 0.75,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_high_beta_cap_safe") {
    set_g510_lattice(1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.60, 0.75,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g59_low_beta_high_cap") {
    set_g510_lattice(1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.20, 1.25,
                     false, "g510_lattice_flow_shield");
  } else if (method == "repair5g516_slow_decay_safer_beta025_cap050") {
    // Repair5G.5.17 targeted update-parameter adapter recognition only.
    // These names map the G5.16 repair lattice into existing project-owned
    // UpdateParams; solver search, candidate generation, PIBT, LaCAM*, pruning,
    // rewrite, incumbent, and restart semantics are unchanged.
    set_g510_lattice(1.25, 1.25, 1.00, 0.75, 0.92, 1.00, 0.25, 0.50,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_slow_decay_safer_beta020_cap045") {
    set_g510_lattice(1.20, 1.20, 1.00, 0.75, 0.90, 1.00, 0.20, 0.45,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_slow_decay_safer_beta015_cap040") {
    set_g510_lattice(1.15, 1.15, 1.00, 0.75, 0.88, 1.00, 0.15, 0.40,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_wait_aggressive_low_cap") {
    set_g510_lattice(1.00, 1.00, 1.05, 1.25, 0.95, 0.95, 0.20, 0.50,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_wait_conservative_mid_cap") {
    set_g510_lattice(1.00, 1.00, 1.00, 1.05, 0.95, 0.98, 0.18, 0.45,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_wait_aggressive_fast_flow_decay") {
    set_g510_lattice(1.00, 1.00, 1.10, 1.30, 0.95, 0.90, 0.18, 0.45,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_commit_heavy_low_beta") {
    set_g510_lattice(1.45, 0.90, 1.10, 0.80, 0.95, 1.00, 0.18, 0.45,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_commit_heavy_static_guard") {
    set_g510_lattice(1.35, 0.90, 1.05, 0.75, 0.92, 0.98, 0.15, 0.35,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_static_boundary_light_flow") {
    set_g510_lattice(1.00, 1.00, 1.00, 0.90, 0.95, 1.00, 0.10, 0.25,
                     false, "g517_targeted_repair_lattice_flow_shield");
  } else if (method == "repair5g516_static_boundary_c_only") {
    set_g510_lattice(1.05, 1.05, 1.00, 0.75, 0.95, 1.00, 0.00, 0.00,
                     true, "g517_targeted_repair_lattice_c_only");
  } else if (method.rfind("repair5g_dual_c_equiv_", 0) == 0) {
    const auto rule_id =
        method.substr(std::string("repair5g_dual_c_equiv_").size());
    ScalarRuleParams scalar;
    if (parse_scalar_rule_id(rule_id, &scalar)) {
      set("dcltm_c_equiv_" + rule_id,
          repair5g1_dual_c_equiv_params(scalar), "dual_c_equiv");
    }
  } else if (method == "repair5g_dual_c_only_locked_f4") {
    auto params = repair5g_base_dual_params();
    params.alpha_cong_commit_nonprogress = 1.0;
    params.alpha_cong_block = 1.0;
    params.alpha_cong_wait_progress = 0.75;
    params.alpha_cong_wait_nonprogress = 0.75;
    params.alpha_flow_commit_progress = 0.0;
    params.alpha_flow_wait_progress = 0.0;
    params.rho_cong_decay = 0.90;
    params.rho_flow_decay = 1.0;
    params.lambda_cong = 1.0;
    params.lambda_flow = 0.0;
    set("dcltm_c_only_locked_f4", params, "dual_c_only");
  } else if (method == "repair5g_dual_c_only_best_f4_observed") {
    auto params = repair5g_base_dual_params();
    params.alpha_cong_commit_nonprogress = 1.25;
    params.alpha_cong_block = 1.25;
    params.alpha_cong_wait_progress = 0.75;
    params.alpha_cong_wait_nonprogress = 0.75;
    params.alpha_flow_commit_progress = 0.0;
    params.alpha_flow_wait_progress = 0.0;
    params.rho_cong_decay = 0.95;
    params.rho_flow_decay = 1.0;
    params.lambda_cong = 1.0;
    params.lambda_flow = 0.0;
    set("dcltm_c_only_best_f4_observed", params, "dual_c_only");
  } else if (method == "repair5g_dual_flow_only_025" ||
             method == "repair5g_dual_flow_only_050") {
    auto params = repair5g_base_dual_params();
    params.alpha_cong_commit_nonprogress = 0.0;
    params.alpha_cong_block = 0.0;
    params.alpha_cong_wait_progress = 0.0;
    params.alpha_cong_wait_nonprogress = 0.0;
    params.alpha_flow_commit_progress = 1.0;
    params.alpha_flow_wait_progress = 0.0;
    params.lambda_cong = 0.0;
    params.lambda_flow =
        method == "repair5g_dual_flow_only_025" ? 0.25 : 0.50;
    set(method == "repair5g_dual_flow_only_025" ? "dcltm_flow_only_025"
                                                 : "dcltm_flow_only_050",
        params, "dual_flow_only");
  } else if (method == "repair5g_dual_block_wait_cong_flow025" ||
             method == "repair5g_dual_block_wait_cong_flow050") {
    auto params = repair5g_base_dual_params();
    params.alpha_cong_commit_nonprogress = 0.0;
    params.alpha_cong_block = 1.0;
    params.alpha_cong_wait_progress = 1.0;
    params.alpha_cong_wait_nonprogress = 1.0;
    params.alpha_flow_commit_progress = 1.0;
    params.alpha_flow_wait_progress = 0.0;
    params.lambda_cong = 1.0;
    params.lambda_flow =
        method == "repair5g_dual_block_wait_cong_flow025" ? 0.25 : 0.50;
    set(method == "repair5g_dual_block_wait_cong_flow025"
            ? "dcltm_block_wait_cong_flow025"
            : "dcltm_block_wait_cong_flow050",
        params, "dual_block_wait_cong_flow");
  } else if (method == "repair5g_dual_goal_gated_wait_025" ||
             method == "repair5g_dual_goal_gated_wait_050") {
    auto params = repair5g_base_dual_params();
    params.alpha_cong_commit_nonprogress = 0.0;
    params.alpha_cong_block = 1.0;
    params.alpha_cong_wait_progress = 0.25;
    params.alpha_cong_wait_nonprogress = 1.0;
    params.alpha_flow_commit_progress = 1.0;
    params.alpha_flow_wait_progress = 0.0;
    params.lambda_cong = 1.0;
    params.lambda_flow =
        method == "repair5g_dual_goal_gated_wait_025" ? 0.25 : 0.50;
    set(method == "repair5g_dual_goal_gated_wait_025"
            ? "dcltm_goal_gated_wait_025"
            : "dcltm_goal_gated_wait_050",
        params, "dual_goal_gated_wait");
  } else if (method == "repair5g_dual_balanced_decay") {
    auto params = repair5g_base_dual_params();
    params.alpha_cong_commit_nonprogress = 0.0;
    params.alpha_cong_block = 1.0;
    params.alpha_cong_wait_progress = 1.0;
    params.alpha_cong_wait_nonprogress = 1.0;
    params.alpha_flow_commit_progress = 1.0;
    params.alpha_flow_wait_progress = 0.0;
    params.rho_cong_decay = 0.95;
    params.rho_flow_decay = 0.95;
    params.lambda_cong = 1.0;
    params.lambda_flow = 0.25;
    set("dcltm_balanced_decay", params, "dual_balanced_decay");
  } else if (method == "repair5g1_random_static_diagnostic") {
    auto scalar = ScalarRuleParams();
    scalar.alpha_commit = 0.80;
    scalar.alpha_block = 1.20;
    scalar.alpha_wait = 0.60;
    scalar.rho_decay = 0.95;
    auto params = repair5g1_dual_flow_params(
        scalar, czr004::ltm::GoalProjectionMode::AgentProgress, 0.025, 0.75);
    set("random_static_diagnostic", params, "dual_random_static");
  } else if (parse_repair5g1_flow_method(
                 method, "repair5g1_global_",
                 czr004::ltm::GoalProjectionMode::None, &spec) ||
             parse_repair5g1_flow_method(
                 method, "repair5g1_agent_",
                 czr004::ltm::GoalProjectionMode::AgentProgress, &spec) ||
             parse_repair5g1_flow_shield_method(method, &spec) ||
             parse_repair5g1_wait_method(method, &spec)) {
    return spec;
  }
  return spec;
}

std::string repair5g5_selector_default_path()
{
  return "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/selector_spec.json";
}

std::string repair5g5_group_selector_candidate(const Args& args)
{
  if (args.map_name == "maze-32-32-4" && args.agents == 100) {
    return "repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5";
  }
  if (args.map_name == "random-32-32-20" && args.agents == 100) {
    return "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75";
  }
  if (args.map_name == "warehouse-10-20-10-2-1" && args.agents == 50) {
    return "repair5g_dual_c_equiv_c100_b100_w075_d095";
  }
  if (args.map_name == "warehouse-10-20-10-2-1" && args.agents == 100) {
    return "repair5g_dual_c_equiv_additive";
  }
  return args.repair5g5_static_candidate;
}

std::string repair5g5_resolve_candidate_alias(const std::string& candidate,
                                              const Args& args)
{
  if (candidate == "repair5g2_best_frozen_static_candidate" ||
      candidate == "repair5g2_g1_top_diagnostic_candidate") {
    return args.repair5g5_static_candidate;
  }
  if (candidate == "repair5g2_c_equiv_best_frozen_baseline") {
    return args.repair5g5_c_equiv_candidate;
  }
  if (candidate == "repair5g2_frozen_static_or_selector") {
    return repair5g5_group_selector_candidate(args);
  }
  return candidate;
}

void load_repair5g5_selector_spec(Args* args)
{
  if (!args->repair5g5_selector_enabled && !args->repair5g53_hook_enabled) {
    return;
  }
  if (args->repair5g5_selector_spec_path.empty()) {
    args->repair5g5_selector_spec_path = repair5g5_selector_default_path();
  }
  const auto text = read_text_file(args->repair5g5_selector_spec_path);
  if (text.empty()) {
    if (args->repair5g5_selector_mode == "runtime") {
      throw std::runtime_error("cannot read --repair5g5-selector-spec " +
                               args->repair5g5_selector_spec_path);
    }
    return;
  }
  args->repair5g5_selector_name =
      json_string_field(text, "selector_name", "decision_stump_selector");
  args->repair5g5_stump_feature =
      json_string_field(text, "feature", "ltm_iterations");
  args->repair5g5_stump_threshold =
      json_number_field(text, "threshold", 2.5);
  args->repair5g5_stump_left_method =
      json_string_field(text, "left_method",
                        "repair5g_dual_c_equiv_c100_b100_w100_d090");
  args->repair5g5_stump_right_method =
      json_string_field(text, "right_method",
                        "repair5g2_best_frozen_static_candidate");
  args->repair5g5_stump_fallback_method =
      json_string_field(text, "fallback_static",
                        "repair5g2_best_frozen_static_candidate");
  args->repair5g5_static_candidate =
      json_string_field(text, "repair5g2_best_frozen_static_candidate",
                        args->repair5g5_static_candidate);
  args->repair5g5_c_equiv_candidate =
      json_string_field(text, "repair5g2_c_equiv_best_frozen_baseline",
                        args->repair5g5_c_equiv_candidate);
}

double safe_ratio(double numerator, double denominator)
{
  return denominator == 0.0 ? 0.0 : numerator / denominator;
}

czr004::ntm::LaurFeatureVector repair5g5_build_features_perf(
    const Instance& instance,
    const czr004::ltm::DirectedTrafficMap& traffic_map,
    const std::vector<czr004::ltm::TraceEvent>& trace_events,
    const czr004::ltm::LtmIterationStats& stats)
{
  uint committed = 0;
  uint blocked = 0;
  uint wait = 0;
  uint progress = 0;
  uint nonprogress = 0;
  for (const auto& event : trace_events) {
    if (event.kind == czr004::ltm::TraceEventKind::Committed) {
      ++committed;
      if (event.from_id != event.to_id && !event.at_goal) {
        ++progress;
      } else {
        ++nonprogress;
      }
    } else {
      ++blocked;
    }
    if (event.from_id == event.to_id && !event.at_goal) ++wait;
  }
  const auto free_cells = static_cast<double>(instance.G.size());
  const auto total_cells =
      static_cast<double>(std::max(1u, instance.G.width * instance.G.height));
  const auto obstacle_cells = std::max(0.0, total_cells - free_cells);
  const auto agents = static_cast<double>(instance.N);
  const auto& update_stats = traffic_map.last_update_stats();
  const auto c_updates =
      static_cast<double>(update_stats.congestion_update_count);
  const auto f_updates = static_cast<double>(update_stats.flow_update_count);

  auto out = czr004::ntm::LaurFeatureVector();
  out.names = {
      "agents",
      "map_width",
      "map_height",
      "obstacle_ratio",
      "free_cells",
      "density",
      "ltm_iterations",
      "returned_solutions_count_so_far",
      "has_incumbent_before",
      "best_ratio_before",
      "improved_last_iteration",
      "committed_count",
      "blocked_count",
      "wait_event_count",
      "progress_committed_count",
      "nonprogress_committed_count",
      "blocked_per_committed",
      "wait_per_committed",
      "blocked_per_agent",
      "committed_per_agent",
      "progress_ratio",
      "c_update_count",
      "f_update_count",
      "c_nonzero_edges",
      "f_nonzero_edges",
      "c_flow_update_ratio",
      "cost_min",
      "cost_max",
      "cost_span",
      "cost_bounds_respected",
  };
  out.values = {
      agents,
      static_cast<double>(instance.G.width),
      static_cast<double>(instance.G.height),
      safe_ratio(obstacle_cells, total_cells),
      free_cells,
      safe_ratio(agents, free_cells),
      static_cast<double>(stats.iteration),
      static_cast<double>(stats.returned_solutions_count_so_far),
      stats.has_incumbent_before ? 1.0 : 0.0,
      stats.best_ratio_before,
      stats.improved_incumbent ? 1.0 : 0.0,
      static_cast<double>(committed),
      static_cast<double>(blocked),
      static_cast<double>(wait),
      static_cast<double>(progress),
      static_cast<double>(nonprogress),
      safe_ratio(static_cast<double>(blocked), static_cast<double>(committed)),
      safe_ratio(static_cast<double>(wait), static_cast<double>(committed)),
      safe_ratio(static_cast<double>(blocked), agents),
      safe_ratio(static_cast<double>(committed), agents),
      safe_ratio(static_cast<double>(progress),
                 static_cast<double>(progress + nonprogress)),
      c_updates,
      f_updates,
      0.0,
      0.0,
      safe_ratio(c_updates, f_updates),
      0.0,
      0.0,
      0.0,
      1.0,
  };
  return out;
}

czr004::ntm::LaurFeatureVector repair5g5_build_features_audit(
    const Instance& instance,
    const czr004::ltm::DirectedTrafficMap& traffic_map,
    const std::vector<czr004::ltm::TraceEvent>& trace_events,
    const czr004::ltm::LtmIterationStats& stats)
{
  uint committed = 0;
  uint blocked = 0;
  uint wait = 0;
  uint progress = 0;
  uint nonprogress = 0;
  for (const auto& event : trace_events) {
    if (event.kind == czr004::ltm::TraceEventKind::Committed) {
      ++committed;
      if (event.from_id != event.to_id && !event.at_goal) {
        ++progress;
      } else {
        ++nonprogress;
      }
    } else {
      ++blocked;
    }
    if (event.from_id == event.to_id && !event.at_goal) ++wait;
  }
  const auto free_cells = static_cast<double>(instance.G.size());
  const auto total_cells =
      static_cast<double>(std::max(1u, instance.G.width * instance.G.height));
  const auto obstacle_cells = std::max(0.0, total_cells - free_cells);
  const auto agents = static_cast<double>(instance.N);
  const auto cost_audit = traffic_map.cost_audit(&instance);
  const auto c_updates = static_cast<double>(traffic_map.nonzero_raw_edges());
  const auto f_updates = static_cast<double>(traffic_map.nonzero_flow_edges());

  auto out = czr004::ntm::LaurFeatureVector();
  out.names = {
      "agents",
      "map_width",
      "map_height",
      "obstacle_ratio",
      "free_cells",
      "density",
      "ltm_iterations",
      "returned_solutions_count_so_far",
      "has_incumbent_before",
      "best_ratio_before",
      "improved_last_iteration",
      "committed_count",
      "blocked_count",
      "wait_event_count",
      "progress_committed_count",
      "nonprogress_committed_count",
      "blocked_per_committed",
      "wait_per_committed",
      "blocked_per_agent",
      "committed_per_agent",
      "progress_ratio",
      "c_update_count",
      "f_update_count",
      "c_nonzero_edges",
      "f_nonzero_edges",
      "c_flow_update_ratio",
      "cost_min",
      "cost_max",
      "cost_span",
      "cost_bounds_respected",
  };
  out.values = {
      agents,
      static_cast<double>(instance.G.width),
      static_cast<double>(instance.G.height),
      safe_ratio(obstacle_cells, total_cells),
      free_cells,
      safe_ratio(agents, free_cells),
      static_cast<double>(stats.iteration),
      static_cast<double>(stats.returned_solutions_count_so_far),
      stats.has_incumbent_before ? 1.0 : 0.0,
      stats.best_ratio_before,
      stats.improved_incumbent ? 1.0 : 0.0,
      static_cast<double>(committed),
      static_cast<double>(blocked),
      static_cast<double>(wait),
      static_cast<double>(progress),
      static_cast<double>(nonprogress),
      safe_ratio(static_cast<double>(blocked), static_cast<double>(committed)),
      safe_ratio(static_cast<double>(wait), static_cast<double>(committed)),
      safe_ratio(static_cast<double>(blocked), agents),
      safe_ratio(static_cast<double>(committed), agents),
      safe_ratio(static_cast<double>(progress),
                 static_cast<double>(progress + nonprogress)),
      c_updates,
      f_updates,
      static_cast<double>(traffic_map.nonzero_raw_edges()),
      static_cast<double>(traffic_map.nonzero_flow_edges()),
      safe_ratio(c_updates, f_updates),
      cost_audit.all_finite ? cost_audit.min_cost : 0.0,
      cost_audit.all_finite ? cost_audit.max_cost : 0.0,
      cost_audit.all_finite ? cost_audit.max_cost - cost_audit.min_cost : 0.0,
      cost_audit.within_configured_bounds ? 1.0 : 0.0,
  };
  return out;
}

czr004::ntm::LaurFeatureVector repair5g5_build_features(
    const Instance& instance,
    const czr004::ltm::DirectedTrafficMap& traffic_map,
    const std::vector<czr004::ltm::TraceEvent>& trace_events,
    const czr004::ltm::LtmIterationStats& stats)
{
  return repair5g5_build_features_audit(instance, traffic_map, trace_events,
                                        stats);
}

void repair5g5_zero_features(czr004::ntm::LaurFeatureVector* features,
                             const std::unordered_set<std::string>& names)
{
  if (features == nullptr) return;
  for (std::size_t index = 0;
       index < features->names.size() && index < features->values.size();
       ++index) {
    if (names.count(features->names[index]) > 0) {
      features->values[index] = 0.0;
    }
  }
}

void repair5g5_apply_feature_ablation(
    const Args& args, czr004::ntm::LaurFeatureVector* features)
{
  if (args.repair5g5_selector_mode == "no_trace_ablation") {
    repair5g5_zero_features(
        features,
        {
            "committed_count",
            "blocked_count",
            "wait_event_count",
            "progress_committed_count",
            "nonprogress_committed_count",
            "blocked_per_committed",
            "wait_per_committed",
            "blocked_per_agent",
            "committed_per_agent",
            "progress_ratio",
        });
  } else if (args.repair5g5_selector_mode == "no_map_features_ablation") {
    repair5g5_zero_features(features,
                            {
                                "map_width",
                                "map_height",
                                "obstacle_ratio",
                                "free_cells",
                                "density",
                            });
  } else if (args.repair5g5_selector_mode == "no_runtime_state_ablation") {
    repair5g5_zero_features(
        features,
        {
            "ltm_iterations",
            "returned_solutions_count_so_far",
            "has_incumbent_before",
            "best_ratio_before",
            "improved_last_iteration",
            "c_update_count",
            "f_update_count",
            "c_nonzero_edges",
            "f_nonzero_edges",
            "c_flow_update_ratio",
            "cost_min",
            "cost_max",
            "cost_span",
            "cost_bounds_respected",
        });
  }
}

double repair5g5_feature_value(const czr004::ntm::LaurFeatureVector& features,
                               const std::string& name,
                               double fallback = 0.0)
{
  for (std::size_t index = 0;
       index < features.names.size() && index < features.values.size();
       ++index) {
    if (features.names[index] == name) return features.values[index];
  }
  return fallback;
}

std::string repair5g5_select_candidate(
    const Args& args, const czr004::ntm::LaurFeatureVector& features)
{
  if (args.repair5g5_force_additive) return "additive_ltm";
  if (args.repair5g5_selector_mode == "always_static_exact") {
    return "repair5g2_best_frozen_static_candidate";
  }
  if (args.repair5g5_selector_mode == "always_map_agent_exact") {
    return "repair5g2_frozen_static_or_selector";
  }
  if (args.repair5g5_selector_mode == "static_fallback") {
    return args.repair5g5_stump_fallback_method.empty()
               ? args.repair5g5_static_candidate
               : args.repair5g5_stump_fallback_method;
  }
  const auto feature_name =
      args.repair5g5_stump_feature.empty() ? "ltm_iterations"
                                           : args.repair5g5_stump_feature;
  const auto feature_value = repair5g5_feature_value(features, feature_name);
  auto left = args.repair5g5_stump_left_method.empty()
                  ? "repair5g_dual_c_equiv_c100_b100_w100_d090"
                  : args.repair5g5_stump_left_method;
  auto right = args.repair5g5_stump_right_method.empty()
                   ? "repair5g2_best_frozen_static_candidate"
                   : args.repair5g5_stump_right_method;
  if (args.repair5g5_selector_mode == "shuffled_label_diagnostic") {
    std::swap(left, right);
  } else if (args.repair5g5_selector_mode == "random_feature_diagnostic") {
    return args.agents % 2 == 0 ? right : left;
  }
  return feature_value <= args.repair5g5_stump_threshold ? left : right;
}

bool is_repair5g53_hook_method(const std::string& method)
{
  return method == "repair5g53_runtime_always_static_minimal_hook" ||
         method == "repair5g53_runtime_always_map_agent_minimal_hook" ||
         method == "repair5g53_runtime_static_shadow_noop_minimal" ||
         method == "repair5g53_static_hook_minimal" ||
         method == "repair5g53_static_hook_memory_counter" ||
         method == "repair5g53_static_hook_jsonl_log_only" ||
         method == "repair5g53_static_hook_params_hash_only" ||
         method == "repair5g53_static_hook_traffic_hash_only" ||
         method == "repair5g53_static_hook_cost_audit_only" ||
         method == "repair5g53_static_hook_features_no_cost_audit" ||
         method == "repair5g53_static_hook_full_features_no_jsonl" ||
         method == "repair5g53_static_hook_full_features_jsonl" ||
         method == "repair5g53_shadow_static_deferred_log" ||
         method == "repair5g53_shadow_static_full_log";
}

std::string repair5g53_hook_mode_for_method(const std::string& method)
{
  const auto prefix = std::string("repair5g53_");
  return method.rfind(prefix, 0) == 0 ? method.substr(prefix.size()) : method;
}

std::string repair5g53_fixed_candidate_for_method(const std::string& method)
{
  if (method == "repair5g53_runtime_always_map_agent_minimal_hook") {
    return "repair5g2_frozen_static_or_selector";
  }
  return "repair5g2_best_frozen_static_candidate";
}

bool repair5g53_hook_uses_runtime_shadow(const std::string& mode)
{
  return mode == "shadow_static_deferred_log" ||
         mode == "shadow_static_full_log";
}

bool repair5g_runtime_audit_mode_supported(const std::string& mode)
{
  return mode == "off" || mode == "minimal" || mode == "perf" ||
         mode == "audit" || mode == "full";
}

Args parse_args(int argc, char** argv)
{
  auto values = std::unordered_map<std::string, std::string>();
  const auto switches = std::unordered_set<std::string>{
      "laur-enable",
      "laur-disable",
      "laur-force-additive",
      "laur-disable-safety",
      "laur-post-first-solution-only",
      "laur-allow-pre-first-solution",
  };
  for (int i = 1; i < argc; ++i) {
    const auto key = std::string(argv[i]);
    if (key.rfind("--", 0) != 0) {
      throw std::runtime_error("invalid argument near " + key);
    }
    const auto name = key.substr(2);
    if (switches.count(name) > 0) {
      values[name] = "1";
      continue;
    }
    if (i + 1 >= argc) throw std::runtime_error("missing value for " + key);
    values[name] = argv[++i];
  }

  auto require = [&](const std::string& key) {
    const auto it = values.find(key);
    if (it == values.end() || it->second.empty()) {
      throw std::runtime_error("missing --" + key);
    }
    return it->second;
  };

  Args args;
  args.method = require("method");
  args.map = require("map");
  args.scen = require("scen");
  args.output_jsonl = require("output-jsonl");
  args.map_name = values.count("map-name") ? values["map-name"] : args.map;
  args.scen_id = values.count("scen-id") ? values["scen-id"] : args.scen;
  args.manifest = values.count("manifest") ? values["manifest"] : "";
  args.project_commit =
      values.count("project-commit") ? values["project-commit"] : "";
  args.external_commit =
      values.count("external-commit") ? values["external-commit"] : "";
  args.branch = values.count("branch") ? values["branch"] : "";
  args.dirty = values.count("dirty") ? values["dirty"] : "";
  args.platform = values.count("platform") ? values["platform"] : "";
  args.traffic_map_jsonl =
      values.count("traffic-map-jsonl") ? values["traffic-map-jsonl"] : "";
  args.traffic_map_run_id =
      values.count("traffic-map-run-id") ? values["traffic-map-run-id"] : "";
  args.traffic_map_edge_filter =
      values.count("traffic-map-edge-filter") ? values["traffic-map-edge-filter"] : "all";
  args.laur_model_path =
      values.count("laur-model-path") ? values["laur-model-path"] : "";
  args.laur_static_rule =
      values.count("laur-static-rule") ? values["laur-static-rule"] : "";
  args.laur_update_log_jsonl =
      values.count("laur-update-log-jsonl") ? values["laur-update-log-jsonl"] : "";
  args.repair5g_export_update_checkpoints_jsonl =
      values.count("repair5g-export-update-checkpoints-jsonl")
          ? values["repair5g-export-update-checkpoints-jsonl"]
          : "";
  args.repair5g_checkpoint_edge_filter =
      values.count("repair5g-checkpoint-edge-filter")
          ? values["repair5g-checkpoint-edge-filter"]
          : args.repair5g_checkpoint_edge_filter;
  args.repair5g_counterfactual_update_probe_jsonl =
      values.count("repair5g-counterfactual-update-probe-jsonl")
          ? values["repair5g-counterfactual-update-probe-jsonl"]
          : "";
  args.repair5g_counterfactual_candidates =
      values.count("repair5g-counterfactual-candidates")
          ? values["repair5g-counterfactual-candidates"]
          : "";
  args.repair5g_transform_audit_candidate =
      values.count("repair5g-transform-audit-candidate")
          ? values["repair5g-transform-audit-candidate"]
          : "";
  args.repair5g_transform_audit_jsonl =
      values.count("repair5g-transform-audit-jsonl")
          ? values["repair5g-transform-audit-jsonl"]
          : "";
  args.repair5g_runtime_audit_mode =
      values.count("repair5g-runtime-audit-mode")
          ? values["repair5g-runtime-audit-mode"]
          : args.repair5g_runtime_audit_mode;
  args.method_alias =
      values.count("method-alias") ? values["method-alias"] : "";
  args.repair5g5_selector_spec_path =
      values.count("repair5g5-selector-spec")
          ? values["repair5g5-selector-spec"]
          : "";
  args.laur_enable = values.count("laur-enable") > 0;
  args.laur_disable = values.count("laur-disable") > 0;
  args.laur_force_additive = values.count("laur-force-additive") > 0;
  args.laur_safety_enabled = values.count("laur-disable-safety") == 0;
  args.laur_post_first_solution_only =
      values.count("laur-allow-pre-first-solution") > 0
          ? false
          : (values.count("laur-post-first-solution-only") > 0 ||
             args.laur_post_first_solution_only);

  if (!parse_uint(require("agents"), &args.agents)) {
    throw std::runtime_error("invalid --agents");
  }
  if (!parse_uint(require("seed"), &args.seed)) {
    throw std::runtime_error("invalid --seed");
  }
  if (values.count("time-limit-sec") &&
      !parse_double(values["time-limit-sec"], &args.time_limit_sec)) {
    throw std::runtime_error("invalid --time-limit-sec");
  }
  if (values.count("ltm-max-iterations") &&
      !parse_uint(values["ltm-max-iterations"], &args.ltm_max_iterations)) {
    throw std::runtime_error("invalid --ltm-max-iterations");
  }
  if (values.count("repair5g-checkpoint-topk-edges") &&
      !parse_uint(values["repair5g-checkpoint-topk-edges"],
                  &args.repair5g_checkpoint_topk_edges)) {
    throw std::runtime_error("invalid --repair5g-checkpoint-topk-edges");
  }
  if (values.count("repair5g-checkpoint-include-full-traffic") &&
      !parse_bool_text(values["repair5g-checkpoint-include-full-traffic"],
                       &args.repair5g_checkpoint_include_full_traffic)) {
    throw std::runtime_error("invalid --repair5g-checkpoint-include-full-traffic");
  }
  if (values.count("repair5g-counterfactual-short-budget-ms") &&
      !parse_double(values["repair5g-counterfactual-short-budget-ms"],
                    &args.repair5g_counterfactual_short_budget_ms)) {
    throw std::runtime_error("invalid --repair5g-counterfactual-short-budget-ms");
  }
  if (values.count("repair5g-counterfactual-max-contexts") &&
      !parse_uint(values["repair5g-counterfactual-max-contexts"],
                  &args.repair5g_counterfactual_max_contexts)) {
    throw std::runtime_error("invalid --repair5g-counterfactual-max-contexts");
  }
  if (values.count("laur-every-k-restarts") &&
      !parse_uint(values["laur-every-k-restarts"], &args.laur_every_k_restarts)) {
    throw std::runtime_error("invalid --laur-every-k-restarts");
  }
  if (args.laur_every_k_restarts == 0) {
    throw std::runtime_error("--laur-every-k-restarts must be >= 1");
  }
  if (values.count("laur-safety-threshold") &&
      !parse_double(values["laur-safety-threshold"], &args.laur_safety_threshold)) {
    throw std::runtime_error("invalid --laur-safety-threshold");
  }
  if (values.count("laur-ood-z-threshold")) {
    args.laur_ood_guard_enabled = true;
    if (!parse_double(values["laur-ood-z-threshold"],
                      &args.laur_ood_z_threshold) ||
        args.laur_ood_z_threshold <= 0.0) {
      throw std::runtime_error("invalid --laur-ood-z-threshold");
    }
  }
  if (args.laur_disable && args.laur_enable) {
    throw std::runtime_error("--laur-enable and --laur-disable are mutually exclusive");
  }
  if (args.laur_force_additive && !args.laur_static_rule.empty()) {
    throw std::runtime_error("--laur-force-additive and --laur-static-rule are mutually exclusive");
  }
  if (!args.laur_static_rule.empty() &&
      !czr004::ntm::is_supported_laur_rule_id(args.laur_static_rule)) {
    throw std::runtime_error("unsupported --laur-static-rule " +
                             args.laur_static_rule);
  }
  if (values.count("verbose")) args.verbose = std::stoi(values["verbose"]);
  if (!repair5g_runtime_audit_mode_supported(args.repair5g_runtime_audit_mode)) {
    throw std::runtime_error("unsupported --repair5g-runtime-audit-mode " +
                             args.repair5g_runtime_audit_mode);
  }

  const auto requested_method = args.method;
  const auto repair5g_spec = repair5g_method_spec(requested_method);
  const auto use_repair5f_alias = [&](const std::string& default_model_path) {
    if (args.method_alias.empty()) args.method_alias = requested_method;
    args.method = "lacam_star_lau_ltm";
    args.laur_enable = true;
    if (args.laur_model_path.empty()) args.laur_model_path = default_model_path;
  };
  const auto use_canonical_ltm_alias = [&]() {
    if (args.method_alias.empty()) args.method_alias = requested_method;
    args.method = "lacam_star_ltm";
    args.laur_enable = false;
    args.laur_disable = true;
    args.laur_force_additive = false;
    args.laur_model_path.clear();
    args.laur_static_rule.clear();
  };
  if (requested_method == "repair5f_bounded_updateparam_selector_runtime") {
    use_repair5f_alias(repair5f_selector_runtime_path());
  } else if (
      requested_method ==
      "repair5f_bounded_updateparam_selector_force_additive_parity") {
    use_canonical_ltm_alias();
  } else if (requested_method == "repair5f_static_c100_b100_w075_d090") {
    use_repair5f_alias(repair5f_static_runtime_path());
  } else if (requested_method == "repair5f_candidate_additive_ltm") {
    use_canonical_ltm_alias();
  } else if (requested_method == "always_additive_defer") {
    use_canonical_ltm_alias();
  } else if (requested_method == "laur_disable" ||
             requested_method == "laur_force_additive_direct") {
    use_canonical_ltm_alias();
  } else if (
      requested_method == "repair5f_runtime_random_candidate_diagnostic" ||
      requested_method == "repair5f_runtime_shuffled_utility_diagnostic") {
    use_repair5f_alias("");
    if (args.laur_model_path.empty()) {
      throw std::runtime_error("--method " + requested_method +
                               " requires --laur-model-path");
    }
  } else if (
      requested_method == "repair5g5_contextual_flow_shield_selector_runtime" ||
      requested_method ==
          "repair5g5_contextual_flow_shield_selector_force_additive_parity" ||
      requested_method == "repair5g5_contextual_flow_shield_selector_disable" ||
      requested_method ==
          "repair5g5_contextual_flow_shield_selector_static_fallback" ||
      requested_method ==
          "repair5g5_contextual_flow_shield_selector_shuffled_label_diagnostic" ||
      requested_method ==
          "repair5g5_contextual_flow_shield_selector_random_feature_diagnostic" ||
      requested_method ==
          "repair5g5_contextual_flow_shield_selector_no_trace_ablation" ||
      requested_method ==
          "repair5g5_contextual_flow_shield_selector_no_map_features_ablation" ||
      requested_method ==
          "repair5g5_contextual_flow_shield_selector_no_runtime_state_ablation" ||
      requested_method == "repair5g52_runtime_always_static_exact" ||
      requested_method == "repair5g52_runtime_always_map_agent_exact" ||
      requested_method == "repair5g52_runtime_selector_shadow_static" ||
      is_repair5g53_hook_method(requested_method)) {
    if (args.method_alias.empty()) args.method_alias = requested_method;
    args.method = "lacam_star_ltm";
    args.laur_enable = false;
    args.laur_disable = true;
    args.laur_force_additive = false;
    args.laur_model_path.clear();
    args.laur_static_rule.clear();
    args.repair5g_enabled = true;
    args.repair5g5_selector_enabled =
        requested_method != "repair5g5_contextual_flow_shield_selector_disable";
    args.repair5g5_force_additive =
        requested_method ==
        "repair5g5_contextual_flow_shield_selector_force_additive_parity";
    if (is_repair5g53_hook_method(requested_method)) {
      args.repair5g53_hook_enabled = true;
      args.repair5g5_selector_enabled = false;
      args.repair5g53_hook_mode =
          repair5g53_hook_mode_for_method(requested_method);
      args.repair5g53_fixed_candidate =
          repair5g53_fixed_candidate_for_method(requested_method);
      args.repair5g5_selector_mode = args.repair5g53_hook_mode;
      args.repair5g5_selector_name = "repair5g53_overhead_neutral_hook";
      if (values.count("repair5g-runtime-audit-mode") == 0) {
        args.repair5g_runtime_audit_mode =
            (args.repair5g53_hook_mode.find("full") != std::string::npos ||
             args.repair5g53_hook_mode.find("cost_audit") != std::string::npos)
                ? "audit"
                : "perf";
      }
    } else if (requested_method ==
        "repair5g5_contextual_flow_shield_selector_static_fallback") {
      args.repair5g5_selector_mode = "static_fallback";
    } else if (
        requested_method ==
        "repair5g5_contextual_flow_shield_selector_shuffled_label_diagnostic") {
      args.repair5g5_selector_mode = "shuffled_label_diagnostic";
    } else if (
        requested_method ==
        "repair5g5_contextual_flow_shield_selector_random_feature_diagnostic") {
      args.repair5g5_selector_mode = "random_feature_diagnostic";
    } else if (
        requested_method ==
        "repair5g5_contextual_flow_shield_selector_no_trace_ablation") {
      args.repair5g5_selector_mode = "no_trace_ablation";
    } else if (
        requested_method ==
        "repair5g5_contextual_flow_shield_selector_no_map_features_ablation") {
      args.repair5g5_selector_mode = "no_map_features_ablation";
    } else if (
        requested_method ==
        "repair5g5_contextual_flow_shield_selector_no_runtime_state_ablation") {
      args.repair5g5_selector_mode = "no_runtime_state_ablation";
    } else if (requested_method == "repair5g52_runtime_always_static_exact") {
      args.repair5g5_selector_mode = "always_static_exact";
    } else if (
        requested_method == "repair5g52_runtime_always_map_agent_exact") {
      args.repair5g5_selector_mode = "always_map_agent_exact";
    } else if (
        requested_method == "repair5g52_runtime_selector_shadow_static") {
      args.repair5g5_selector_mode = "shadow_static";
    } else if (args.repair5g5_force_additive) {
      args.repair5g5_selector_mode = "force_additive";
    } else if (!args.repair5g5_selector_enabled) {
      args.repair5g5_selector_mode = "disable";
      args.repair5g_enabled = false;
    } else {
      args.repair5g5_selector_mode = "runtime";
    }
    args.repair5g_candidate_id = "repair5g5_contextual_selector";
    args.repair5g_update_mode = args.repair5g5_selector_mode;
    load_repair5g5_selector_spec(&args);
  } else if (requested_method == "repair5g52_runtime_force_additive_exact" ||
             requested_method == "repair5g52_runtime_disable_exact") {
    use_canonical_ltm_alias();
  } else if (repair5g_spec.recognized) {
    if (args.method_alias.empty()) args.method_alias = requested_method;
    args.method = "lacam_star_ltm";
    args.laur_enable = false;
    args.laur_disable = true;
    args.laur_force_additive = false;
    args.laur_model_path.clear();
    args.laur_static_rule.clear();
    args.repair5g_enabled = true;
    args.repair5g_candidate_id = repair5g_spec.candidate_id;
    args.repair5g_update_mode = repair5g_spec.update_mode;
    args.repair5g_update_params = repair5g_spec.params;
  }

  if (args.method != "lacam_star" && args.method != "lacam_star_ltm" &&
      args.method != "lacam_star_lau_ltm") {
    throw std::runtime_error("unsupported --method " + args.method);
  }
  if (args.traffic_map_edge_filter != "all" &&
      args.traffic_map_edge_filter != "nonzero") {
    throw std::runtime_error("unsupported --traffic-map-edge-filter " +
                             args.traffic_map_edge_filter);
  }
  if (args.repair5g_checkpoint_edge_filter != "all" &&
      args.repair5g_checkpoint_edge_filter != "nonzero") {
    throw std::runtime_error("unsupported --repair5g-checkpoint-edge-filter " +
                             args.repair5g_checkpoint_edge_filter);
  }
  if (args.repair5g_counterfactual_short_budget_ms <= 0.0) {
    throw std::runtime_error("--repair5g-counterfactual-short-budget-ms must be > 0");
  }
  return args;
}

bool laur_runtime_requested(const Args& args)
{
  return (args.method == "lacam_star_lau_ltm" || args.laur_enable ||
          !args.laur_static_rule.empty()) &&
         !args.laur_disable;
}

uint sum_info_values(const std::string& info, const std::string& key)
{
  uint sum = 0;
  std::istringstream stream(info);
  std::string line;
  const auto prefix = key + "=";
  while (std::getline(stream, line)) {
    if (line.rfind(prefix, 0) != 0) continue;
    try {
      sum += static_cast<uint>(std::stoul(line.substr(prefix.size())));
    } catch (...) {
    }
  }
  return sum;
}

double sum_info_double_values(const std::string& info, const std::string& key)
{
  double sum = 0.0;
  std::istringstream stream(info);
  std::string line;
  const auto prefix = key + "=";
  while (std::getline(stream, line)) {
    if (line.rfind(prefix, 0) != 0) continue;
    try {
      sum += std::stod(line.substr(prefix.size()));
    } catch (...) {
    }
  }
  return sum;
}

struct RunStats {
  Solution solution;
  std::string additional_info;
  double runtime_ms = 0.0;
  uint loop_cnt = 0;
  uint expanded_nodes = 0;
  uint high_level_expansions = 0;
  uint low_level_pibt_calls = 0;
  bool has_low_level_pibt_calls = false;
  double time_to_first_solution_ms = std::numeric_limits<double>::quiet_NaN();
  uint returned_solutions_count = 0;
  uint ltm_iterations = 0;
  uint committed_events = 0;
  uint blocked_events = 0;
  uint nonzero_ltm_edges = 0;
  bool laur_enabled = false;
  bool laur_force_additive = false;
  bool laur_safety_enabled = true;
  std::string laur_update_mode = "disabled";
  std::string laur_model_path;
  std::string laur_static_rule;
  uint laur_inference_count = 0;
  double laur_inference_total_ms = 0.0;
  uint laur_additive_fallback_count = 0;
  uint laur_safety_disabled_count = 0;
  uint laur_update_period_restarts = 1;
  bool laur_post_first_solution_only = true;
  std::map<std::string, uint> laur_selected_rules;
  bool repair5g_enabled = false;
  bool dual_channel_enabled = false;
  bool repair5g5_selector_enabled = false;
  std::string repair5g5_selector_mode = "disabled";
  std::string repair5g5_selector_name = "disabled";
  std::string repair5g5_selector_spec_path;
  uint repair5g5_selector_inference_count = 0;
  uint repair5g5_selector_fallback_count = 0;
  std::map<std::string, uint> repair5g5_selected_candidates;
  std::string repair5g_runtime_audit_mode = "audit";
  std::string repair5g53_hook_mode = "disabled";
  uint repair5g53_update_policy_calls = 0;
  double repair5g53_update_policy_total_ms = 0.0;
  double repair5g53_feature_build_ms = 0.0;
  double repair5g53_cost_audit_ms = 0.0;
  double repair5g53_candidate_select_ms = 0.0;
  double repair5g53_alias_resolve_ms = 0.0;
  double repair5g53_params_hash_ms = 0.0;
  double repair5g53_traffic_hash_ms = 0.0;
  double repair5g53_json_write_ms = 0.0;
  double repair5g53_update_apply_ms = 0.0;
  std::string repair5g_candidate_id;
  std::string repair5g_update_mode = "disabled";
  double repair5g_lambda_cong = 1.0;
  double repair5g_lambda_flow = 0.0;
  double repair5g_rho_cong_decay = 1.0;
  double repair5g_rho_flow_decay = 1.0;
  double repair5g_min_edge_cost = 0.25;
  double repair5g_max_edge_cost = 11.0;
  std::string repair5g_goal_projection_mode = "none";
  double repair5g_flow_shield_beta = 0.0;
  double repair5g_max_flow_shield = 0.0;
  double repair5g_alpha_cong_commit_progress = 0.0;
  double repair5g_alpha_cong_commit_nonprogress = 0.0;
  double repair5g_alpha_cong_block = 1.0;
  double repair5g_alpha_cong_wait_progress = 1.0;
  double repair5g_alpha_cong_wait_nonprogress = 1.0;
  double repair5g_alpha_flow_commit_progress = 0.0;
  uint repair5g_congestion_update_count = 0;
  uint repair5g_flow_update_count = 0;
  double repair5g_congestion_delta_total = 0.0;
  double repair5g_flow_delta_total = 0.0;
  uint repair5g_committed_progress_events = 0;
  uint repair5g_committed_nonprogress_events = 0;
  uint repair5g_blocked_events = 0;
  uint repair5g_wait_progress_edges = 0;
  uint repair5g_wait_nonprogress_edges = 0;
  uint repair5g_congestion_nonzero_edges = 0;
  uint repair5g_flow_nonzero_edges = 0;
  bool repair5g_costs_finite = true;
  bool repair5g_cost_bounds_respected = true;
  double repair5g_min_traversal_cost = std::numeric_limits<double>::quiet_NaN();
  double repair5g_max_traversal_cost = std::numeric_limits<double>::quiet_NaN();
};

std::string default_traffic_map_run_id(const Args& args)
{
  if (!args.traffic_map_run_id.empty()) return args.traffic_map_run_id;
  std::ostringstream out;
  out << args.map_name << "__a" << args.agents << "__s" << args.seed;
  return out.str();
}

uint vertex_x(const Graph& graph, const Vertex* vertex)
{
  return graph.width == 0 ? 0 : vertex->index % graph.width;
}

uint vertex_y(const Graph& graph, const Vertex* vertex)
{
  return graph.width == 0 ? 0 : vertex->index / graph.width;
}

void append_traffic_map_jsonl(const Args& args, const Instance& instance,
                              const czr004::ltm::DirectedTrafficMap& traffic_map)
{
  if (args.traffic_map_jsonl.empty()) return;

  const auto output_path = std::filesystem::path(args.traffic_map_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open traffic map JSONL");

  const auto& graph = traffic_map.graph();
  const auto run_id = default_traffic_map_run_id(args);
  for (const auto* from : graph.V) {
    for (const auto* to : from->neighbor) {
      const auto raw_count = traffic_map.raw_count(from->id, to->id);
      if (args.traffic_map_edge_filter == "nonzero" && raw_count <= 0.0) {
        continue;
      }
      const auto weight = traffic_map.normalized_weight(from->id, to->id);

      out << "{";
      out << "\"schema_version\":\"phase3_edge_label_v1\"";
      out << ",\"run_id\":" << json_string(run_id);
      out << ",\"source\":\"final_ltm_traffic_map\"";
      out << ",\"method\":" << json_string(args.method);
      out << ",\"map\":" << json_string(args.map_name);
      out << ",\"scen\":" << json_string(args.scen_id);
      out << ",\"agents\":" << args.agents;
      out << ",\"seed\":" << args.seed;
      out << ",\"time_limit_sec\":" << json_number_or_null(args.time_limit_sec);
      out << ",\"objective\":\"sum_of_loss\"";
      out << ",\"from_id\":" << from->id;
      out << ",\"to_id\":" << to->id;
      out << ",\"from_index\":" << from->index;
      out << ",\"to_index\":" << to->index;
      out << ",\"from_x\":" << vertex_x(graph, from);
      out << ",\"from_y\":" << vertex_y(graph, from);
      out << ",\"to_x\":" << vertex_x(graph, to);
      out << ",\"to_y\":" << vertex_y(graph, to);
      out << ",\"from_degree\":" << from->neighbor.size();
      out << ",\"to_degree\":" << to->neighbor.size();
      out << ",\"ltm_raw_count\":" << json_number_or_null(raw_count);
      out << ",\"ltm_normalized_weight\":" << json_number_or_null(weight);
      out << ",\"warm_start_target_weight\":" << json_number_or_null(weight);
      out << ",\"residual_reference_weight\":" << json_number_or_null(weight);
      out << ",\"residual_delta_target\":0";
      out << ",\"traversal_cost\":"
          << json_number_or_null(traffic_map.traversal_cost(from->id, to->id));
      out << ",\"ltm_flow_raw_count\":"
          << json_number_or_null(traffic_map.flow_raw_count(from->id, to->id));
      out << ",\"ltm_normalized_flow_weight\":"
          << json_number_or_null(traffic_map.normalized_flow_weight(from->id, to->id));
      out << ",\"dual_channel_enabled\":"
          << (traffic_map.dual_channel_enabled() ? "true" : "false");
      out << ",\"nonzero\":" << (raw_count > 0.0 ? "true" : "false");
      out << ",\"map_vertices\":" << instance.G.size();
      out << "}\n";
    }
  }
}

std::string traffic_map_hash(const czr004::ltm::DirectedTrafficMap* traffic_map)
{
  if (traffic_map == nullptr) return "";
  std::ostringstream data;
  data.precision(17);
  const auto& graph = traffic_map->graph();
  for (const auto* from : graph.V) {
    for (const auto* to : from->neighbor) {
      const auto c_raw = traffic_map->raw_count(from->id, to->id);
      const auto c_weight = traffic_map->normalized_weight(from->id, to->id);
      const auto f_raw = traffic_map->flow_raw_count(from->id, to->id);
      const auto f_weight =
          traffic_map->normalized_flow_weight(from->id, to->id);
      if (c_raw <= 0.0 && f_raw <= 0.0) continue;
      data << from->id << ">" << to->id << ":" << c_raw << ":" << c_weight
           << ":" << f_raw << ":" << f_weight << ";";
    }
  }
  return stable_hex_hash(data.str());
}

void append_laur_update_log_jsonl(
    const Args& args, const czr004::ltm::LtmUpdateContext& context,
    const std::string& predicted_rule, const std::string& applied_rule,
    double safety_harmful_prob, double predicted_delta_ratio, double inference_ms,
    const std::string& decision_status, const std::string& fallback_reason,
    bool prediction_enabled,
    const czr004::ntm::LaurFeatureVector* runtime_features = nullptr,
    double feature_max_abs_z = std::numeric_limits<double>::quiet_NaN(),
    double feature_mean_abs_z = std::numeric_limits<double>::quiet_NaN(),
    uint feature_outside_3sigma_count = 0,
    uint feature_outside_5sigma_count = 0,
    bool ood_guard_triggered = false,
    double ood_z_threshold = std::numeric_limits<double>::quiet_NaN(),
    const std::string& selected_rule_before_guard = "",
    const std::string& selected_rule_after_guard = "",
    const std::string& selected_rule_source = "",
    double predicted_margin_ratio = 0.0,
    uint nearest_support_count = 0,
    const std::string& guard_reason = "",
    const czr004::ltm::UpdateParams* applied_params = nullptr)
{
  if (args.laur_update_log_jsonl.empty()) return;

  const auto output_path = std::filesystem::path(args.laur_update_log_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open LAUR update log JSONL");

  const auto output_method =
      args.method_alias.empty() ? args.method : args.method_alias;
  const auto fallback_params = update_params_for_logged_rule(applied_rule);
  const auto& params = applied_params == nullptr ? fallback_params : *applied_params;
  out << "{";
  out << "\"schema_version\":\"phase5p5_repair5e_laur_update_log_v1\"";
  out << ",\"method\":" << json_string(output_method);
  out << ",\"map\":" << json_string(args.map_name);
  out << ",\"scen\":" << json_string(args.scen_id);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"iteration\":" << context.stats.iteration;
  out << ",\"has_incumbent_before\":" << (context.stats.has_incumbent_before ? "true" : "false");
  out << ",\"best_ratio_before\":" << json_number_or_null(context.stats.best_ratio_before);
  out << ",\"returned_solutions_count_so_far\":" << context.stats.returned_solutions_count_so_far;
  out << ",\"trace_event_count\":"
      << (context.trace_events == nullptr ? 0 : context.trace_events->size());
  out << ",\"traffic_before_hash\":"
      << json_string(traffic_map_hash(context.traffic_before));
  out << ",\"traffic_before_c_nonzero_edges\":"
      << (context.traffic_before == nullptr
              ? 0
              : context.traffic_before->nonzero_raw_edges());
  out << ",\"traffic_before_f_nonzero_edges\":"
      << (context.traffic_before == nullptr
              ? 0
              : context.traffic_before->nonzero_flow_edges());
  out << ",\"predicted_rule\":" << json_string(predicted_rule);
  out << ",\"applied_rule\":" << json_string(applied_rule);
  out << ",\"selected_candidate_id\":" << json_string(applied_rule);
  out << ",\"selected_candidate_resolved_method\":"
      << json_string(applied_rule);
  out << ",\"selected_candidate_params_hash\":"
      << json_string(update_params_hash(params));
  out << ",\"updateparams_fingerprint\":"
      << json_string(update_params_fingerprint(params));
  out << ",\"runtime_selector_active\":"
      << (args.repair5g5_selector_enabled ? "true" : "false");
  out << ",\"selector_name\":" << json_string(args.repair5g5_selector_name);
  out << ",\"selector_policy_mode\":"
      << json_string(args.repair5g5_selector_mode);
  out << ",\"force_additive_active\":"
      << ((args.repair5g5_force_additive || params.force_additive) ? "true"
                                                                  : "false");
  out << ",\"disable_active\":"
      << ((!args.repair5g_enabled && !laur_runtime_requested(args)) ? "true"
                                                                   : "false");
  out << ",\"selected_rule_before_guard\":"
      << json_string(selected_rule_before_guard.empty() ? predicted_rule
                                                        : selected_rule_before_guard);
  out << ",\"selected_rule_after_guard\":"
      << json_string(selected_rule_after_guard.empty() ? applied_rule
                                                       : selected_rule_after_guard);
  out << ",\"selected_rule_source\":"
      << json_string(selected_rule_source.empty()
                         ? (!fallback_reason.empty() ? fallback_reason
                                                     : decision_status)
                         : selected_rule_source);
  out << ",\"decision_status\":" << json_string(decision_status);
  out << ",\"fallback_reason\":" << json_string(fallback_reason);
  out << ",\"prediction_enabled\":" << (prediction_enabled ? "true" : "false");
  out << ",\"safety_harmful_prob\":" << json_number_or_null(safety_harmful_prob);
  out << ",\"predicted_delta_ratio\":" << json_number_or_null(predicted_delta_ratio);
  out << ",\"predicted_margin_ratio\":" << json_number_or_null(predicted_margin_ratio);
  out << ",\"nearest_support_count\":" << nearest_support_count;
  out << ",\"guard_reason\":" << json_string(guard_reason);
  out << ",\"inference_ms\":" << json_number_or_null(inference_ms);
  out << ",\"runtime_feature_names\":";
  if (runtime_features == nullptr) {
    out << "[]";
  } else {
    append_json_string_array(out, runtime_features->names);
  }
  out << ",\"runtime_feature_values\":";
  if (runtime_features == nullptr) {
    out << "[]";
  } else {
    append_json_number_array(out, runtime_features->values);
  }
  out << ",\"feature_max_abs_z\":" << json_number_or_null(feature_max_abs_z);
  out << ",\"feature_mean_abs_z\":" << json_number_or_null(feature_mean_abs_z);
  out << ",\"feature_outside_3sigma_count\":" << feature_outside_3sigma_count;
  out << ",\"feature_outside_5sigma_count\":" << feature_outside_5sigma_count;
  out << ",\"ood_guard_triggered\":" << (ood_guard_triggered ? "true" : "false");
  out << ",\"ood_z_threshold\":" << json_number_or_null(ood_z_threshold);
  out << ",\"laur_force_additive\":" << (args.laur_force_additive ? "true" : "false");
  out << ",\"laur_static_rule\":" << json_string(args.laur_static_rule);
  out << ",\"laur_safety_threshold\":" << json_number_or_null(args.laur_safety_threshold);
  out << ",\"applied_alpha_commit\":"
      << json_number_or_null(params.alpha_commit);
  out << ",\"applied_alpha_block\":"
      << json_number_or_null(params.alpha_block);
  out << ",\"applied_alpha_wait_spillover\":"
      << json_number_or_null(params.alpha_wait_spillover);
  out << ",\"applied_rho_decay\":" << json_number_or_null(params.rho_decay);
  out << ",\"applied_alpha_cong_commit_progress\":"
      << json_number_or_null(params.alpha_cong_commit_progress);
  out << ",\"applied_alpha_cong_commit_nonprogress\":"
      << json_number_or_null(params.alpha_cong_commit_nonprogress);
  out << ",\"applied_alpha_cong_block\":"
      << json_number_or_null(params.alpha_cong_block);
  out << ",\"applied_alpha_cong_wait_progress\":"
      << json_number_or_null(params.alpha_cong_wait_progress);
  out << ",\"applied_alpha_cong_wait_nonprogress\":"
      << json_number_or_null(params.alpha_cong_wait_nonprogress);
  out << ",\"applied_alpha_flow_commit_progress\":"
      << json_number_or_null(params.alpha_flow_commit_progress);
  out << ",\"applied_alpha_flow_wait_progress\":"
      << json_number_or_null(params.alpha_flow_wait_progress);
  out << ",\"applied_rho_cong_decay\":"
      << json_number_or_null(params.rho_cong_decay);
  out << ",\"applied_rho_flow_decay\":"
      << json_number_or_null(params.rho_flow_decay);
  out << ",\"applied_force_additive\":"
      << (params.force_additive ? "true" : "false");
  out << ",\"applied_enable_dual_channel\":"
      << (params.enable_dual_channel ? "true" : "false");
  out << ",\"applied_lambda_cong\":"
      << json_number_or_null(params.lambda_cong);
  out << ",\"applied_lambda_flow\":"
      << json_number_or_null(params.lambda_flow);
  out << ",\"applied_goal_projection_mode\":"
      << json_string(goal_projection_mode_name(params.goal_projection_mode));
  out << ",\"applied_flow_shield_beta\":"
      << json_number_or_null(params.flow_shield_beta);
  out << ",\"applied_max_flow_shield\":"
      << json_number_or_null(params.max_flow_shield);
  out << ",\"applied_min_edge_cost\":"
      << json_number_or_null(params.min_edge_cost);
  out << ",\"applied_max_edge_cost\":"
      << json_number_or_null(params.max_edge_cost);
  out << "}\n";
}

void append_repair5g53_minimal_update_log_jsonl(
    const Args& args, const czr004::ltm::LtmUpdateContext& context,
    const std::string& resolved_candidate)
{
  if (args.laur_update_log_jsonl.empty()) return;

  const auto output_path = std::filesystem::path(args.laur_update_log_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open Repair5G.5.3 update log");

  const auto output_method =
      args.method_alias.empty() ? args.method : args.method_alias;
  out << "{";
  out << "\"schema_version\":\"phase5p5_repair5g53_minimal_update_log_v1\"";
  out << ",\"method\":" << json_string(output_method);
  out << ",\"map\":" << json_string(args.map_name);
  out << ",\"scen\":" << json_string(args.scen_id);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"iteration\":" << context.stats.iteration;
  out << ",\"selected_candidate_resolved_method\":"
      << json_string(resolved_candidate);
  out << ",\"hook_mode\":" << json_string(args.repair5g53_hook_mode);
  out << ",\"runtime_audit_mode\":"
      << json_string(args.repair5g_runtime_audit_mode);
  out << "}\n";
}

void append_trace_events_json(
    std::ostream& out, const std::vector<czr004::ltm::TraceEvent>& events)
{
  out << "[";
  for (std::size_t index = 0; index < events.size(); ++index) {
    const auto& event = events[index];
    if (index > 0) out << ",";
    out << "{";
    out << "\"kind\":"
        << json_string(event.kind == czr004::ltm::TraceEventKind::Committed
                           ? "committed"
                           : "blocked");
    out << ",\"agent_id\":" << event.agent_id;
    out << ",\"from_id\":" << event.from_id;
    out << ",\"to_id\":" << event.to_id;
    out << ",\"at_goal\":" << (event.at_goal ? "true" : "false");
    out << "}";
  }
  out << "]";
}

void append_snapshot_edges_json(
    std::ostream& out,
    const std::vector<czr004::ltm::TrafficEdgeSnapshot>& edges)
{
  out << "[";
  for (std::size_t index = 0; index < edges.size(); ++index) {
    const auto& edge = edges[index];
    if (index > 0) out << ",";
    out << "{";
    out << "\"from_id\":" << edge.from_id;
    out << ",\"to_id\":" << edge.to_id;
    out << ",\"c_raw\":" << json_number_or_null(edge.raw);
    out << ",\"c_weight\":" << json_number_or_null(edge.weight);
    out << ",\"f_raw\":" << json_number_or_null(edge.flow_raw);
    out << ",\"f_weight\":" << json_number_or_null(edge.flow_weight);
    out << "}";
  }
  out << "]";
}

void append_traffic_map_edges_json(
    std::ostream& out, const czr004::ltm::DirectedTrafficMap* traffic_map,
    const std::string& edge_filter)
{
  out << "[";
  if (traffic_map != nullptr) {
    bool first = true;
    const auto& graph = traffic_map->graph();
    for (const auto* from : graph.V) {
      for (const auto* to : from->neighbor) {
        const auto c_raw = traffic_map->raw_count(from->id, to->id);
        const auto c_norm = traffic_map->normalized_weight(from->id, to->id);
        const auto f_raw = traffic_map->flow_raw_count(from->id, to->id);
        const auto f_norm = traffic_map->normalized_flow_weight(from->id, to->id);
        if (edge_filter != "all" && c_raw <= 0.0 && f_raw <= 0.0) {
          continue;
        }
        if (!first) out << ",";
        first = false;
        out << "{";
        out << "\"from_id\":" << from->id;
        out << ",\"to_id\":" << to->id;
        out << ",\"c_raw\":" << json_number_or_null(c_raw);
        out << ",\"c_normalized\":" << json_number_or_null(c_norm);
        out << ",\"f_raw\":" << json_number_or_null(f_raw);
        out << ",\"f_normalized\":" << json_number_or_null(f_norm);
        out << "}";
      }
    }
  }
  out << "]";
}

uint traffic_map_edge_count(const czr004::ltm::DirectedTrafficMap* traffic_map,
                            const std::string& edge_filter)
{
  if (traffic_map == nullptr) return 0;
  uint count = 0;
  const auto& graph = traffic_map->graph();
  for (const auto* from : graph.V) {
    for (const auto* to : from->neighbor) {
      const auto c_raw = traffic_map->raw_count(from->id, to->id);
      const auto f_raw = traffic_map->flow_raw_count(from->id, to->id);
      if (edge_filter == "all" || c_raw > 0.0 || f_raw > 0.0) ++count;
    }
  }
  return count;
}

std::string snapshot_hash(const czr004::ltm::TrafficSnapshot& snapshot)
{
  std::ostringstream data;
  data.precision(17);
  for (const auto& edge : snapshot.raw_topk) {
    data << edge.from_id << ">" << edge.to_id << ":" << edge.raw << ":"
         << edge.weight << ":" << edge.flow_raw << ":" << edge.flow_weight
         << ";";
  }
  return stable_hex_hash(data.str());
}

void append_repair5g53_transform_audit_jsonl(
    const Args& args, const Instance& instance,
    const czr004::ltm::LtmIterationCheckpoint& checkpoint)
{
  if (args.repair5g_transform_audit_jsonl.empty()) return;

  const auto output_path =
      std::filesystem::path(args.repair5g_transform_audit_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open Repair5G.5.3 transform audit JSONL");

  const auto requested =
      args.repair5g_transform_audit_candidate.empty()
          ? args.repair5g_candidate_id
          : args.repair5g_transform_audit_candidate;
  const auto resolved = repair5g5_resolve_candidate_alias(requested, args);
  auto expected_params = czr004::ltm::UpdateParams::additive();
  auto recognized = resolved == "additive_ltm" ||
                    resolved == "neutral_additive" || resolved.empty();
  auto expected_update_mode = std::string("additive_parity");
  if (!recognized) {
    const auto spec = repair5g_method_spec(resolved);
    recognized = spec.recognized;
    if (recognized) {
      expected_params = spec.params;
      expected_update_mode = spec.update_mode;
    }
  }
  if (resolved == "additive_ltm" || resolved == "neutral_additive") {
    expected_params = czr004::ltm::UpdateParams::additive();
  }
  if (args.repair5g_update_mode == "dual_c_equiv" &&
      expected_update_mode == "dual_c_equiv" &&
      !checkpoint.has_incumbent_before) {
    expected_params = czr004::ltm::UpdateParams::additive();
  }

  auto expected_hash = std::string();
  auto expected_stats = czr004::ltm::DualChannelUpdateStats();
  auto expected_cost = czr004::ltm::TrafficCostAudit();
  auto actual_hash = std::string();
  auto actual_stats = czr004::ltm::DualChannelUpdateStats();
  auto actual_cost = czr004::ltm::TrafficCostAudit();
  auto can_compare = recognized && checkpoint.traffic_before_map != nullptr &&
                     checkpoint.traffic_after_map != nullptr;
  if (can_compare) {
    auto expected_map = *checkpoint.traffic_before_map;
    expected_map.update_from_trace(checkpoint.trace_events, expected_params,
                                   &instance);
    expected_hash = traffic_map_hash(&expected_map);
    expected_stats = expected_map.last_update_stats();
    expected_cost = expected_map.cost_audit(&instance);
    actual_hash = traffic_map_hash(checkpoint.traffic_after_map.get());
    actual_stats = checkpoint.traffic_after_map->last_update_stats();
    actual_cost = checkpoint.traffic_after_map->cost_audit(&instance);
  }

  const auto output_method =
      args.method_alias.empty() ? args.method : args.method_alias;
  out << "{";
  out << "\"schema_version\":\"phase5p5_repair5g53_update_transform_audit_v1\"";
  out << ",\"method\":" << json_string(output_method);
  out << ",\"map\":" << json_string(args.map_name);
  out << ",\"scen\":" << json_string(args.scen_id);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"iteration\":" << checkpoint.iteration;
  out << ",\"candidate_id\":" << json_string(requested);
  out << ",\"resolved_candidate_id\":" << json_string(resolved);
  out << ",\"candidate_recognized\":" << (recognized ? "true" : "false");
  out << ",\"expected_params_hash\":"
      << json_string(update_params_hash(expected_params));
  out << ",\"actual_params_hash\":"
      << json_string(update_params_hash(checkpoint.update_params));
  out << ",\"traffic_before_hash_full\":"
      << json_string(traffic_map_hash(checkpoint.traffic_before_map.get()));
  out << ",\"expected_traffic_after_hash_full\":"
      << json_string(expected_hash);
  out << ",\"actual_traffic_after_hash_full\":"
      << json_string(actual_hash);
  out << ",\"traffic_after_hash_match\":"
      << (can_compare && expected_hash == actual_hash ? "true" : "false");
  out << ",\"params_hash_match\":"
      << (update_params_hash(expected_params) ==
                  update_params_hash(checkpoint.update_params)
              ? "true"
              : "false");
  out << ",\"congestion_update_count_expected\":"
      << expected_stats.congestion_update_count;
  out << ",\"congestion_update_count_actual\":"
      << actual_stats.congestion_update_count;
  out << ",\"flow_update_count_expected\":"
      << expected_stats.flow_update_count;
  out << ",\"flow_update_count_actual\":"
      << actual_stats.flow_update_count;
  out << ",\"congestion_delta_total_expected\":"
      << json_number_or_null(expected_stats.congestion_delta_total);
  out << ",\"congestion_delta_total_actual\":"
      << json_number_or_null(actual_stats.congestion_delta_total);
  out << ",\"flow_delta_total_expected\":"
      << json_number_or_null(expected_stats.flow_delta_total);
  out << ",\"flow_delta_total_actual\":"
      << json_number_or_null(actual_stats.flow_delta_total);
  out << ",\"cost_min_expected\":"
      << json_number_or_null(expected_cost.min_cost);
  out << ",\"cost_min_actual\":" << json_number_or_null(actual_cost.min_cost);
  out << ",\"cost_max_expected\":"
      << json_number_or_null(expected_cost.max_cost);
  out << ",\"cost_max_actual\":" << json_number_or_null(actual_cost.max_cost);
  out << ",\"cost_bounds_expected\":"
      << (expected_cost.within_configured_bounds ? "true" : "false");
  out << ",\"cost_bounds_actual\":"
      << (actual_cost.within_configured_bounds ? "true" : "false");
  out << ",\"trace_event_count\":" << checkpoint.trace_events.size();
  out << ",\"committed_count\":"
      << std::count_if(checkpoint.trace_events.begin(),
                       checkpoint.trace_events.end(), [](const auto& event) {
                         return event.kind ==
                                czr004::ltm::TraceEventKind::Committed;
                       });
  out << ",\"blocked_count\":"
      << std::count_if(checkpoint.trace_events.begin(),
                       checkpoint.trace_events.end(), [](const auto& event) {
                         return event.kind ==
                                czr004::ltm::TraceEventKind::Blocked;
                       });
  out << "}\n";
}

void append_repair5g_update_checkpoint_jsonl(
    const Args& args, const Instance& instance,
    const czr004::ltm::LtmIterationCheckpoint& checkpoint)
{
  if (args.repair5g_export_update_checkpoints_jsonl.empty()) return;

  const auto output_path =
      std::filesystem::path(args.repair5g_export_update_checkpoints_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }
  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open Repair5G checkpoint JSONL");

  auto stats = czr004::ltm::LtmIterationStats();
  stats.iteration = checkpoint.iteration;
  stats.node_budget = checkpoint.node_budget;
  stats.has_incumbent_before = checkpoint.has_incumbent_before;
  stats.improved_incumbent = checkpoint.improved_incumbent;
  stats.best_ratio_before = checkpoint.best_ratio_before;
  stats.best_ratio_after = checkpoint.best_ratio_after;
  stats.returned_solutions_count_so_far =
      checkpoint.returned_solutions_count_so_far;
  stats.expanded_nodes_this_iteration =
      checkpoint.expanded_nodes_this_iteration;
  stats.low_level_pibt_calls_this_iteration =
      checkpoint.low_level_pibt_calls_this_iteration;
  stats.elapsed_ms = checkpoint.elapsed_ms;
  stats.time_remaining_sec = checkpoint.time_remaining_sec;
  stats.max_iterations = args.ltm_max_iterations;

  auto features = czr004::ntm::LaurFeatureVector();
  auto has_features = false;
  if (checkpoint.traffic_before_map != nullptr) {
    features = repair5g5_build_features(instance, *checkpoint.traffic_before_map,
                                        checkpoint.trace_events, stats);
    has_features = true;
  }
  const auto traffic_before_full_hash =
      checkpoint.traffic_before_map == nullptr
          ? snapshot_hash(checkpoint.traffic_before)
          : traffic_map_hash(checkpoint.traffic_before_map.get());
  const auto traffic_after_full_hash =
      checkpoint.traffic_after_map == nullptr
          ? snapshot_hash(checkpoint.traffic_after)
          : traffic_map_hash(checkpoint.traffic_after_map.get());
  const auto update_stats =
      checkpoint.traffic_after_map == nullptr
          ? czr004::ltm::DualChannelUpdateStats()
          : checkpoint.traffic_after_map->last_update_stats();
  const auto cost_audit =
      checkpoint.traffic_after_map == nullptr
          ? czr004::ltm::TrafficCostAudit()
          : checkpoint.traffic_after_map->cost_audit(&instance);
  auto replay_traffic_after_hash = std::string();
  auto replay_stats = czr004::ltm::DualChannelUpdateStats();
  auto replay_transform_match = false;
  auto replay_update_stats_match = false;
  if (checkpoint.traffic_before_map != nullptr) {
    auto replay_map = *checkpoint.traffic_before_map;
    replay_map.update_from_trace(checkpoint.trace_events,
                                 checkpoint.update_params, &instance);
    replay_traffic_after_hash = traffic_map_hash(&replay_map);
    replay_stats = replay_map.last_update_stats();
    replay_transform_match = replay_traffic_after_hash == traffic_after_full_hash;
    replay_update_stats_match =
        replay_stats.congestion_update_count ==
            update_stats.congestion_update_count &&
        replay_stats.flow_update_count == update_stats.flow_update_count &&
        replay_stats.congestion_delta_total ==
            update_stats.congestion_delta_total &&
        replay_stats.flow_delta_total == update_stats.flow_delta_total;
  }

  const auto output_method =
      args.method_alias.empty() ? args.method : args.method_alias;
  out << "{";
  out << "\"schema_version\":\"phase5p5_repair5g54_update_checkpoint_v1\"";
  out << ",\"method\":" << json_string(output_method);
  out << ",\"map\":" << json_string(args.map_name);
  out << ",\"scen\":" << json_string(args.scen_id);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"iteration\":" << checkpoint.iteration;
  out << ",\"node_budget\":" << checkpoint.node_budget;
  out << ",\"time_remaining_sec\":"
      << json_number_or_null(checkpoint.time_remaining_sec);
  out << ",\"best_ratio_before\":"
      << json_number_or_null(checkpoint.best_ratio_before);
  out << ",\"best_ratio_after\":"
      << json_number_or_null(checkpoint.best_ratio_after);
  out << ",\"has_incumbent_before\":"
      << (checkpoint.has_incumbent_before ? "true" : "false");
  out << ",\"returned_solutions_count_so_far\":"
      << checkpoint.returned_solutions_count_so_far;
  out << ",\"solution_found_this_iteration\":"
      << (checkpoint.solution_found_this_iteration ? "true" : "false");
  out << ",\"sum_of_loss_ratio_this_iteration\":"
      << json_number_or_null(checkpoint.sum_of_loss_ratio_this_iteration);
  out << ",\"expanded_nodes_this_iteration\":"
      << checkpoint.expanded_nodes_this_iteration;
  out << ",\"high_level_expansions_this_iteration\":"
      << checkpoint.high_level_expansions_this_iteration;
  out << ",\"low_level_pibt_calls_this_iteration\":"
      << checkpoint.low_level_pibt_calls_this_iteration;
  out << ",\"trace_event_count\":" << checkpoint.trace_events.size();
  out << ",\"trace_events\":";
  append_trace_events_json(out, checkpoint.trace_events);
  out << ",\"traffic_before_hash\":"
      << json_string(snapshot_hash(checkpoint.traffic_before));
  out << ",\"traffic_after_hash\":"
      << json_string(snapshot_hash(checkpoint.traffic_after));
  out << ",\"traffic_before_hash_full\":"
      << json_string(traffic_before_full_hash);
  out << ",\"traffic_after_hash_full\":"
      << json_string(traffic_after_full_hash);
  out << ",\"replayed_traffic_after_hash_full\":"
      << json_string(replay_traffic_after_hash);
  out << ",\"replayed_traffic_after_hash_match\":"
      << (replay_transform_match ? "true" : "false");
  out << ",\"replayed_update_stats_match\":"
      << (replay_update_stats_match ? "true" : "false");
  out << ",\"traffic_full_edge_filter\":"
      << json_string(args.repair5g_checkpoint_edge_filter);
  out << ",\"traffic_full_sparse_edge_count_before\":"
      << traffic_map_edge_count(checkpoint.traffic_before_map.get(),
                                args.repair5g_checkpoint_edge_filter);
  out << ",\"traffic_full_sparse_edge_count_after\":"
      << traffic_map_edge_count(checkpoint.traffic_after_map.get(),
                                args.repair5g_checkpoint_edge_filter);
  out << ",\"traffic_before_nonzero_edges\":"
      << checkpoint.traffic_before.nonzero_edges;
  out << ",\"traffic_before_flow_nonzero_edges\":"
      << checkpoint.traffic_before.flow_nonzero_edges;
  out << ",\"traffic_before_edges\":";
  append_snapshot_edges_json(out, checkpoint.traffic_before.raw_topk);
  out << ",\"traffic_after_edges\":";
  append_snapshot_edges_json(out, checkpoint.traffic_after.raw_topk);
  out << ",\"traffic_before_full_sparse_edges\":";
  if (args.repair5g_checkpoint_include_full_traffic) {
    append_traffic_map_edges_json(out, checkpoint.traffic_before_map.get(),
                                  args.repair5g_checkpoint_edge_filter);
  } else {
    out << "[]";
  }
  out << ",\"traffic_after_full_sparse_edges\":";
  if (args.repair5g_checkpoint_include_full_traffic) {
    append_traffic_map_edges_json(out, checkpoint.traffic_after_map.get(),
                                  args.repair5g_checkpoint_edge_filter);
  } else {
    out << "[]";
  }
  out << ",\"selected_candidate_id\":"
      << json_string(args.repair5g_candidate_id);
  out << ",\"selected_candidate_resolved_method\":"
      << json_string(args.repair5g_candidate_id);
  out << ",\"selected_candidate_params_hash\":"
      << json_string(update_params_hash(checkpoint.update_params));
  out << ",\"updateparams_fingerprint\":"
      << json_string(update_params_fingerprint(checkpoint.update_params));
  out << ",\"applied_updateparams_hash\":"
      << json_string(update_params_hash(checkpoint.update_params));
  out << ",\"applied_updateparams_fingerprint\":"
      << json_string(update_params_fingerprint(checkpoint.update_params));
  out << ",\"congestion_update_count\":"
      << update_stats.congestion_update_count;
  out << ",\"flow_update_count\":" << update_stats.flow_update_count;
  out << ",\"congestion_delta_total\":"
      << json_number_or_null(update_stats.congestion_delta_total);
  out << ",\"flow_delta_total\":"
      << json_number_or_null(update_stats.flow_delta_total);
  out << ",\"committed_progress_events\":"
      << update_stats.committed_progress_events;
  out << ",\"committed_nonprogress_events\":"
      << update_stats.committed_nonprogress_events;
  out << ",\"blocked_events\":" << update_stats.blocked_events;
  out << ",\"wait_progress_edges\":"
      << update_stats.wait_progress_edges;
  out << ",\"wait_nonprogress_edges\":"
      << update_stats.wait_nonprogress_edges;
  out << ",\"cost_audit_all_finite\":"
      << (cost_audit.all_finite ? "true" : "false");
  out << ",\"cost_audit_bounds_respected\":"
      << (cost_audit.within_configured_bounds ? "true" : "false");
  out << ",\"cost_audit_min_cost\":"
      << json_number_or_null(cost_audit.min_cost);
  out << ",\"cost_audit_max_cost\":"
      << json_number_or_null(cost_audit.max_cost);
  out << ",\"feature_names\":";
  if (has_features) {
    append_json_string_array(out, features.names);
  } else {
    out << "[]";
  }
  out << ",\"feature_values\":";
  if (has_features) {
    append_json_number_array(out, features.values);
  } else {
    out << "[]";
  }
  out << ",\"forbidden_feature_audit_passed\":true";
  out << ",\"phase5p5_allowed\":false";
  out << ",\"phase6_allowed\":false";
  out << ",\"aaai_ready\":false";
  out << "}\n";
}

struct Repair5G54ProbeRow {
  std::string candidate_id;
  std::string resolved_candidate_id;
  bool candidate_recognized = false;
  czr004::ltm::UpdateParams params = czr004::ltm::UpdateParams::additive();
  czr004::ltm::LtmOneShotProbeResult result;
  double score = std::numeric_limits<double>::infinity();
};

double repair5g54_probe_score(
    const czr004::ltm::LtmOneShotProbeResult& result)
{
  if (!result.solution_found || !result.feasible ||
      !std::isfinite(result.sum_of_loss_ratio)) {
    return std::numeric_limits<double>::infinity();
  }
  return result.sum_of_loss_ratio;
}

bool repair5g54_score_is_better(double lhs, double rhs)
{
  if (!std::isfinite(lhs)) return false;
  if (!std::isfinite(rhs)) return true;
  return lhs < rhs - 1.0e-12;
}

czr004::ltm::UpdateParams repair5g54_params_for_candidate(
    const std::string& candidate, const Args& args,
    const czr004::ltm::LtmIterationCheckpoint& checkpoint,
    std::string* resolved_candidate, bool* recognized)
{
  const auto resolved = repair5g5_resolve_candidate_alias(candidate, args);
  *resolved_candidate = resolved;
  *recognized = true;
  if (resolved == "additive_ltm" || resolved == "neutral_additive" ||
      resolved == "repair5g_dual_c_equiv_additive") {
    return czr004::ltm::UpdateParams::additive();
  }
  auto spec = repair5g_method_spec(resolved);
  if (!spec.recognized) {
    *recognized = false;
    return czr004::ltm::UpdateParams::additive();
  }
  if (spec.update_mode == "dual_c_equiv" && !checkpoint.has_incumbent_before) {
    return czr004::ltm::UpdateParams::additive();
  }
  return spec.params;
}

std::vector<std::string> repair5g54_candidate_list(const Args& args)
{
  if (args.repair5g_counterfactual_candidates.empty()) {
    return {
        "additive_ltm",
        "repair5g2_best_frozen_static_candidate",
        "repair5g2_frozen_static_or_selector",
        "repair5g2_c_equiv_best_frozen_baseline",
        "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
        "repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5",
        "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    };
  }
  auto out = std::vector<std::string>();
  for (const auto& token : split_token(args.repair5g_counterfactual_candidates, ',')) {
    if (!token.empty()) out.push_back(token);
  }
  return out;
}

bool append_repair5g54_counterfactual_probe_jsonl(
    const Args& args, const Instance& instance,
    const czr004::ltm::LtmIterationCheckpoint& checkpoint)
{
  if (args.repair5g_counterfactual_update_probe_jsonl.empty()) return false;
  if (checkpoint.traffic_before_map == nullptr) return false;
  if (checkpoint.trace_events.empty()) return false;

  const auto output_path =
      std::filesystem::path(args.repair5g_counterfactual_update_probe_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  const auto candidates = repair5g54_candidate_list(args);
  if (candidates.empty()) return false;

  auto rows = std::vector<Repair5G54ProbeRow>();
  rows.reserve(candidates.size());
  auto additive_score = std::numeric_limits<double>::infinity();
  auto static_score = std::numeric_limits<double>::infinity();
  auto best_score = std::numeric_limits<double>::infinity();
  std::string best_candidate;

  for (const auto& candidate : candidates) {
    Repair5G54ProbeRow row;
    row.candidate_id = candidate;
    row.params = repair5g54_params_for_candidate(
        candidate, args, checkpoint, &row.resolved_candidate_id,
        &row.candidate_recognized);
    czr004::ltm::LtmOneShotProbeOptions probe_options;
    probe_options.objective = Objective::OBJ_SUM_OF_LOSS;
    probe_options.short_budget_ms = args.repair5g_counterfactual_short_budget_ms;
    probe_options.node_budget = 0;
    probe_options.verbose = args.verbose;
    probe_options.seed = args.seed + checkpoint.iteration;
    probe_options.update_params = row.params;
    row.result = czr004::ltm::run_one_shot_update_probe(
        instance, *checkpoint.traffic_before_map, checkpoint.trace_events,
        probe_options);
    row.score = repair5g54_probe_score(row.result);
    if (candidate == "additive_ltm" ||
        candidate == "repair5g59_additive_fallback") {
      additive_score = row.score;
    }
    if (candidate == "repair5g2_best_frozen_static_candidate" ||
        candidate == "repair5g59_static_flow_shield" ||
        candidate == "repair5g59_static_abstain_candidate") {
      static_score = row.score;
    }
    if (row.candidate_recognized &&
        repair5g54_score_is_better(row.score, best_score)) {
      best_score = row.score;
      best_candidate = candidate;
    }
    rows.push_back(row);
  }
  if (!std::isfinite(additive_score)) {
    additive_score = rows.empty() ? std::numeric_limits<double>::infinity()
                                  : rows.front().score;
  }
  if (!std::isfinite(static_score)) {
    static_score = additive_score;
  }
  const auto oracle_gap_vs_static =
      std::isfinite(best_score) && std::isfinite(static_score)
          ? best_score - static_score
          : std::numeric_limits<double>::quiet_NaN();

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open Repair5G.5.4 counterfactual probe JSONL");

  const auto output_method =
      args.method_alias.empty() ? args.method : args.method_alias;
  const auto context_id = args.map_name + "|a" + std::to_string(args.agents) +
                          "|s" + std::to_string(args.seed) + "|it" +
                          std::to_string(checkpoint.iteration) + "|" +
                          output_method;
  for (const auto& row : rows) {
    const auto delta_vs_additive =
        std::isfinite(row.score) && std::isfinite(additive_score)
            ? row.score - additive_score
            : std::numeric_limits<double>::quiet_NaN();
    const auto delta_vs_static =
        std::isfinite(row.score) && std::isfinite(static_score)
            ? row.score - static_score
            : std::numeric_limits<double>::quiet_NaN();
    out << "{";
    out << "\"schema_version\":\"phase5p5_repair5g54_counterfactual_update_probe_v1\"";
    out << ",\"method\":" << json_string(output_method);
    out << ",\"map\":" << json_string(args.map_name);
    out << ",\"scen\":" << json_string(args.scen_id);
    out << ",\"agents\":" << args.agents;
    out << ",\"seed\":" << args.seed;
    out << ",\"iteration\":" << checkpoint.iteration;
    out << ",\"context_id\":" << json_string(context_id);
    out << ",\"candidate_id\":" << json_string(row.candidate_id);
    out << ",\"resolved_candidate_id\":"
        << json_string(row.resolved_candidate_id);
    out << ",\"candidate_recognized\":"
        << (row.candidate_recognized ? "true" : "false");
    out << ",\"updateparams_hash\":" << json_string(update_params_hash(row.params));
    out << ",\"updateparams_fingerprint\":"
        << json_string(update_params_fingerprint(row.params));
    out << ",\"probe_solution_found\":"
        << (row.result.solution_found ? "true" : "false");
    out << ",\"probe_feasible\":"
        << (row.result.feasible ? "true" : "false");
    out << ",\"probe_sum_of_loss\":";
    if (row.result.solution_found) {
      out << row.result.sum_of_loss;
    } else {
      out << "null";
    }
    out << ",\"probe_lower_bound\":" << row.result.lower_bound_sol;
    out << ",\"probe_sum_of_loss_ratio\":"
        << json_number_or_null(row.result.sum_of_loss_ratio);
    out << ",\"probe_runtime_ms\":"
        << json_number_or_null(row.result.runtime_ms);
    out << ",\"probe_expanded_nodes\":" << row.result.expanded_nodes;
    out << ",\"probe_low_level_pibt_calls\":"
        << row.result.low_level_pibt_calls;
    out << ",\"delta_vs_additive_in_same_context\":"
        << json_number_or_null(delta_vs_additive);
    out << ",\"delta_vs_static_in_same_context\":"
        << json_number_or_null(delta_vs_static);
    out << ",\"is_best_candidate_in_context\":"
        << (row.candidate_id == best_candidate ? "true" : "false");
    out << ",\"oracle_gap_vs_static\":"
        << json_number_or_null(oracle_gap_vs_static);
    out << ",\"traffic_before_hash_full\":"
        << json_string(traffic_map_hash(checkpoint.traffic_before_map.get()));
    out << ",\"trace_event_count\":" << checkpoint.trace_events.size();
    out << ",\"short_budget_ms\":"
        << json_number_or_null(args.repair5g_counterfactual_short_budget_ms);
    out << ",\"forbidden_feature_audit_passed\":true";
    out << ",\"phase5p5_allowed\":false";
    out << ",\"phase6_allowed\":false";
    out << ",\"aaai_ready\":false";
    out << "}\n";
  }
  return true;
}

RunStats run_lacam_star(const Instance& instance, const Args& args)
{
  RunStats stats;
  auto deadline = Deadline(args.time_limit_sec * 1000.0);
  auto random_engine = std::mt19937(args.seed);
  const auto started = std::chrono::steady_clock::now();
  stats.solution =
      solve(instance, stats.additional_info, args.verbose, &deadline,
            &random_engine, Objective::OBJ_SUM_OF_LOSS);
  const auto ended = std::chrono::steady_clock::now();
  stats.runtime_ms =
      std::chrono::duration<double, std::milli>(ended - started).count();
  if (!stats.solution.empty()) {
    stats.time_to_first_solution_ms = stats.runtime_ms;
  }
  stats.loop_cnt = sum_info_values(stats.additional_info, "loop_cnt");
  stats.high_level_expansions = stats.loop_cnt;
  stats.expanded_nodes = sum_info_values(stats.additional_info, "num_node_gen");
  stats.returned_solutions_count = stats.solution.empty() ? 0 : 1;
  return stats;
}

RunStats run_lacam_star_ltm(const Instance& instance, const Args& args)
{
  RunStats stats;
  stats.laur_enabled = laur_runtime_requested(args);
  stats.laur_force_additive = stats.laur_enabled && args.laur_force_additive;
  stats.laur_safety_enabled = args.laur_safety_enabled;
  stats.laur_model_path = args.laur_model_path;
  stats.laur_static_rule = args.laur_static_rule;
  stats.laur_update_period_restarts = args.laur_every_k_restarts;
  stats.laur_post_first_solution_only = args.laur_post_first_solution_only;
  stats.repair5g_enabled = args.repair5g_enabled;
  stats.dual_channel_enabled =
      args.repair5g_update_params.enable_dual_channel;
  stats.repair5g5_selector_enabled = args.repair5g5_selector_enabled;
  stats.repair5g5_selector_mode = args.repair5g5_selector_mode;
  stats.repair5g5_selector_name = args.repair5g5_selector_name;
  stats.repair5g5_selector_spec_path = args.repair5g5_selector_spec_path;
  stats.repair5g_runtime_audit_mode = args.repair5g_runtime_audit_mode;
  stats.repair5g53_hook_mode = args.repair5g53_hook_mode;
  stats.repair5g_candidate_id = args.repair5g_candidate_id;
  stats.repair5g_update_mode = args.repair5g_update_mode;
  stats.repair5g_lambda_cong = args.repair5g_update_params.lambda_cong;
  stats.repair5g_lambda_flow = args.repair5g_update_params.lambda_flow;
  stats.repair5g_rho_cong_decay =
      args.repair5g_update_params.rho_cong_decay;
  stats.repair5g_rho_flow_decay =
      args.repair5g_update_params.rho_flow_decay;
  stats.repair5g_min_edge_cost = args.repair5g_update_params.min_edge_cost;
  stats.repair5g_max_edge_cost = args.repair5g_update_params.max_edge_cost;
  stats.repair5g_goal_projection_mode =
      goal_projection_mode_name(args.repair5g_update_params.goal_projection_mode);
  stats.repair5g_flow_shield_beta =
      args.repair5g_update_params.flow_shield_beta;
  stats.repair5g_max_flow_shield =
      args.repair5g_update_params.max_flow_shield;
  stats.repair5g_alpha_cong_commit_progress =
      args.repair5g_update_params.alpha_cong_commit_progress;
  stats.repair5g_alpha_cong_commit_nonprogress =
      args.repair5g_update_params.alpha_cong_commit_nonprogress;
  stats.repair5g_alpha_cong_block =
      args.repair5g_update_params.alpha_cong_block;
  stats.repair5g_alpha_cong_wait_progress =
      args.repair5g_update_params.alpha_cong_wait_progress;
  stats.repair5g_alpha_cong_wait_nonprogress =
      args.repair5g_update_params.alpha_cong_wait_nonprogress;
  stats.repair5g_alpha_flow_commit_progress =
      args.repair5g_update_params.alpha_flow_commit_progress;
  if (!stats.laur_enabled) {
    stats.laur_update_mode = "disabled";
  } else if (stats.laur_force_additive) {
    stats.laur_update_mode = "force_additive";
  } else if (!stats.laur_static_rule.empty()) {
    stats.laur_update_mode = "static_rule";
  } else if (args.laur_ood_guard_enabled) {
    stats.laur_update_mode = "runtime_ood_guard";
  } else {
    stats.laur_update_mode = "runtime";
  }

  czr004::ltm::LtmOptions options;
  options.objective = Objective::OBJ_SUM_OF_LOSS;
  options.time_limit_ms = args.time_limit_sec * 1000.0;
  options.max_iterations = args.ltm_max_iterations;
  options.node_budget_factor = 10;
  options.verbose = args.verbose;
  options.seed = args.seed;
  options.checkpoint_topk_edges = args.repair5g_checkpoint_topk_edges;
  uint repair5g54_counterfactual_contexts = 0;
  if (!args.repair5g_export_update_checkpoints_jsonl.empty() ||
      !args.repair5g_transform_audit_jsonl.empty() ||
      !args.repair5g_counterfactual_update_probe_jsonl.empty()) {
    options.retain_iteration_traffic_maps = true;
    options.iteration_callback =
        [&](const czr004::ltm::LtmIterationCheckpoint& checkpoint) {
          append_repair5g_update_checkpoint_jsonl(args, instance, checkpoint);
          append_repair5g53_transform_audit_jsonl(args, instance, checkpoint);
          if (!args.repair5g_counterfactual_update_probe_jsonl.empty() &&
              (args.repair5g_counterfactual_max_contexts == 0 ||
               repair5g54_counterfactual_contexts <
                   args.repair5g_counterfactual_max_contexts)) {
            if (append_repair5g54_counterfactual_probe_jsonl(args, instance,
                                                             checkpoint)) {
              ++repair5g54_counterfactual_contexts;
            }
          }
        };
  }
  if (args.repair5g_enabled) {
    options.update_params = args.repair5g_update_params;
  }
  if (args.repair5g_enabled &&
      args.repair5g_update_mode == "dual_c_equiv") {
    const auto c_equiv_params = args.repair5g_update_params;
    options.update_policy =
        [c_equiv_params](const czr004::ltm::LtmUpdateContext& context) {
          if (!context.stats.has_incumbent_before) {
            return czr004::ltm::UpdateParams::additive();
          }
          return c_equiv_params;
        };
  }
  if (args.repair5g_enabled && args.repair5g53_hook_enabled) {
    const auto fixed_resolved =
        repair5g5_resolve_candidate_alias(args.repair5g53_fixed_candidate, args);
    const auto fixed_spec = repair5g_method_spec(fixed_resolved);
    if (!fixed_spec.recognized) {
      throw std::runtime_error("unsupported Repair5G.5.3 fixed candidate " +
                               fixed_resolved);
    }
    const auto fixed_params = fixed_spec.params;
    stats.dual_channel_enabled = fixed_params.enable_dual_channel;
    stats.repair5g_candidate_id = fixed_resolved;
    stats.repair5g_update_mode = args.repair5g53_hook_mode;
    stats.repair5g_lambda_cong = fixed_params.lambda_cong;
    stats.repair5g_lambda_flow = fixed_params.lambda_flow;
    stats.repair5g_rho_cong_decay = fixed_params.rho_cong_decay;
    stats.repair5g_rho_flow_decay = fixed_params.rho_flow_decay;
    stats.repair5g_min_edge_cost = fixed_params.min_edge_cost;
    stats.repair5g_max_edge_cost = fixed_params.max_edge_cost;
    stats.repair5g_goal_projection_mode =
        goal_projection_mode_name(fixed_params.goal_projection_mode);
    stats.repair5g_flow_shield_beta = fixed_params.flow_shield_beta;
    stats.repair5g_max_flow_shield = fixed_params.max_flow_shield;
    stats.repair5g_alpha_cong_commit_progress =
        fixed_params.alpha_cong_commit_progress;
    stats.repair5g_alpha_cong_commit_nonprogress =
        fixed_params.alpha_cong_commit_nonprogress;
    stats.repair5g_alpha_cong_block = fixed_params.alpha_cong_block;
    stats.repair5g_alpha_cong_wait_progress =
        fixed_params.alpha_cong_wait_progress;
    stats.repair5g_alpha_cong_wait_nonprogress =
        fixed_params.alpha_cong_wait_nonprogress;
    stats.repair5g_alpha_flow_commit_progress =
        fixed_params.alpha_flow_commit_progress;

    options.update_policy =
        [&, fixed_params, fixed_resolved](
            const czr004::ltm::LtmUpdateContext& context) {
          const auto total_started = std::chrono::steady_clock::now();
          ++stats.repair5g53_update_policy_calls;
          auto finish = [&](const czr004::ltm::UpdateParams& params) {
            const auto total_ended = std::chrono::steady_clock::now();
            stats.repair5g53_update_policy_total_ms +=
                std::chrono::duration<double, std::milli>(total_ended -
                                                          total_started)
                    .count();
            return params;
          };
          const auto mode = args.repair5g53_hook_mode;
          if (mode == "runtime_always_static_minimal_hook" ||
              mode == "runtime_always_map_agent_minimal_hook" ||
              mode == "runtime_static_shadow_noop_minimal" ||
              mode == "static_hook_minimal") {
            return finish(fixed_params);
          }
          if (mode == "static_hook_memory_counter") {
            ++stats.repair5g5_selected_candidates[fixed_resolved];
            return finish(fixed_params);
          }
          if (mode == "static_hook_params_hash_only") {
            const auto started = std::chrono::steady_clock::now();
            (void)update_params_hash(fixed_params);
            stats.repair5g53_params_hash_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - started)
                    .count();
            return finish(fixed_params);
          }
          if (context.traffic_before != nullptr &&
              mode == "static_hook_traffic_hash_only") {
            const auto started = std::chrono::steady_clock::now();
            (void)traffic_map_hash(context.traffic_before);
            stats.repair5g53_traffic_hash_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - started)
                    .count();
            return finish(fixed_params);
          }
          if (context.traffic_before != nullptr && context.instance != nullptr &&
              mode == "static_hook_cost_audit_only") {
            const auto started = std::chrono::steady_clock::now();
            (void)context.traffic_before->cost_audit(context.instance);
            stats.repair5g53_cost_audit_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - started)
                    .count();
            return finish(fixed_params);
          }
          if (context.instance != nullptr && context.traffic_before != nullptr &&
              context.trace_events != nullptr &&
              mode == "static_hook_features_no_cost_audit") {
            const auto started = std::chrono::steady_clock::now();
            (void)repair5g5_build_features_perf(
                *context.instance, *context.traffic_before,
                *context.trace_events, context.stats);
            stats.repair5g53_feature_build_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - started)
                    .count();
            return finish(fixed_params);
          }
          auto features = czr004::ntm::LaurFeatureVector();
          auto has_features = false;
          if (context.instance != nullptr && context.traffic_before != nullptr &&
              context.trace_events != nullptr &&
              (mode == "static_hook_full_features_no_jsonl" ||
               mode == "static_hook_full_features_jsonl" ||
               repair5g53_hook_uses_runtime_shadow(mode))) {
            const auto started = std::chrono::steady_clock::now();
            features = repair5g5_build_features_audit(
                *context.instance, *context.traffic_before,
                *context.trace_events, context.stats);
            stats.repair5g53_feature_build_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - started)
                    .count();
            has_features = true;
          }
          if (repair5g53_hook_uses_runtime_shadow(mode) && has_features) {
            const auto select_started = std::chrono::steady_clock::now();
            const auto selected = repair5g5_select_candidate(args, features);
            stats.repair5g53_candidate_select_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - select_started)
                    .count();
            const auto alias_started = std::chrono::steady_clock::now();
            const auto resolved = repair5g5_resolve_candidate_alias(selected, args);
            stats.repair5g53_alias_resolve_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - alias_started)
                    .count();
            ++stats.repair5g5_selected_candidates[resolved];
          }
          if (mode == "static_hook_jsonl_log_only" ||
              mode == "static_hook_full_features_jsonl" ||
              mode == "shadow_static_full_log") {
            const auto started = std::chrono::steady_clock::now();
            append_repair5g53_minimal_update_log_jsonl(args, context,
                                                       fixed_resolved);
            stats.repair5g53_json_write_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - started)
                    .count();
          }
          return finish(fixed_params);
        };
  }
  if (args.repair5g_enabled && args.repair5g5_selector_enabled) {
    stats.dual_channel_enabled = true;
    options.update_policy =
        [&](const czr004::ltm::LtmUpdateContext& context) {
          const auto total_started = std::chrono::steady_clock::now();
          const auto additive = czr004::ltm::UpdateParams::additive();
          const auto log_enabled = args.repair5g_runtime_audit_mode == "audit" ||
                                   args.repair5g_runtime_audit_mode == "full";
          auto finish = [&](const czr004::ltm::UpdateParams& params) {
            const auto total_ended = std::chrono::steady_clock::now();
            stats.repair5g53_update_policy_total_ms +=
                std::chrono::duration<double, std::milli>(total_ended -
                                                          total_started)
                    .count();
            return params;
          };
          ++stats.repair5g53_update_policy_calls;
          if (context.instance == nullptr || context.traffic_before == nullptr ||
              context.trace_events == nullptr) {
            ++stats.repair5g5_selector_fallback_count;
            if (log_enabled) {
              const auto log_started = std::chrono::steady_clock::now();
              append_laur_update_log_jsonl(
                  args, context, "additive_ltm", "additive_ltm", 0.0, 0.0, 0.0,
                  "fallback_additive", "missing_update_context", false);
              stats.repair5g53_json_write_ms +=
                  std::chrono::duration<double, std::milli>(
                      std::chrono::steady_clock::now() - log_started)
                      .count();
            }
            return finish(additive);
          }
          const auto feature_started = std::chrono::steady_clock::now();
          auto features = log_enabled
                              ? repair5g5_build_features_audit(
                                    *context.instance, *context.traffic_before,
                                    *context.trace_events, context.stats)
                              : repair5g5_build_features_perf(
                                    *context.instance, *context.traffic_before,
                                    *context.trace_events, context.stats);
          stats.repair5g53_feature_build_ms +=
              std::chrono::duration<double, std::milli>(
                  std::chrono::steady_clock::now() - feature_started)
                  .count();
          repair5g5_apply_feature_ablation(args, &features);
          ++stats.repair5g5_selector_inference_count;
          const auto select_started = std::chrono::steady_clock::now();
          auto selected = repair5g5_select_candidate(args, features);
          stats.repair5g53_candidate_select_ms +=
              std::chrono::duration<double, std::milli>(
                  std::chrono::steady_clock::now() - select_started)
                  .count();
          const auto shadow_selected = selected;
          const auto shadow_alias_started = std::chrono::steady_clock::now();
          const auto shadow_resolved =
              repair5g5_resolve_candidate_alias(shadow_selected, args);
          stats.repair5g53_alias_resolve_ms +=
              std::chrono::duration<double, std::milli>(
                  std::chrono::steady_clock::now() - shadow_alias_started)
                  .count();
          auto shadow_mode = false;
          if (args.repair5g5_selector_mode == "shadow_static") {
            shadow_mode = true;
            selected = "repair5g2_best_frozen_static_candidate";
          }
          const auto alias_started = std::chrono::steady_clock::now();
          auto resolved = repair5g5_resolve_candidate_alias(selected, args);
          stats.repair5g53_alias_resolve_ms +=
              std::chrono::duration<double, std::milli>(
                  std::chrono::steady_clock::now() - alias_started)
                  .count();
          if (resolved == "additive_ltm" || resolved == "neutral_additive") {
            ++stats.repair5g5_selected_candidates["additive_ltm"];
            if (log_enabled) {
              const auto log_started = std::chrono::steady_clock::now();
              append_laur_update_log_jsonl(
                  args, context, shadow_mode ? shadow_selected : selected,
                  "additive_ltm", 0.0, 0.0, 0.0,
                  args.repair5g5_force_additive ? "force_additive" : "applied",
                  args.repair5g5_force_additive ? "force_additive"
                                                 : (shadow_mode ? "shadow_static"
                                                                : ""),
                  true, &features, 0.0, 0.0, 0, 0, false, 0.0,
                  shadow_mode ? shadow_resolved : selected, "additive_ltm",
                  args.repair5g5_selector_mode, 0.0, 0,
                  shadow_mode ? "shadow_selected:" + shadow_resolved : "",
                  &additive);
              stats.repair5g53_json_write_ms +=
                  std::chrono::duration<double, std::milli>(
                      std::chrono::steady_clock::now() - log_started)
                      .count();
            }
            return finish(additive);
          }
          const auto spec = repair5g_method_spec(resolved);
          if (!spec.recognized) {
            ++stats.repair5g5_selector_fallback_count;
            ++stats.repair5g5_selected_candidates["additive_ltm"];
            if (log_enabled) {
              const auto log_started = std::chrono::steady_clock::now();
              append_laur_update_log_jsonl(
                  args, context, shadow_mode ? shadow_selected : selected,
                  "additive_ltm", 0.0, 0.0, 0.0,
                  "fallback_additive", "unsupported_candidate:" + resolved,
                  true, &features, 0.0, 0.0, 0, 0, false, 0.0,
                  shadow_mode ? shadow_resolved : selected,
                  "additive_ltm", "unsupported_candidate", 0.0, 0, resolved,
                  &additive);
              stats.repair5g53_json_write_ms +=
                  std::chrono::duration<double, std::milli>(
                      std::chrono::steady_clock::now() - log_started)
                      .count();
            }
            return finish(additive);
          }
          ++stats.repair5g5_selected_candidates[resolved];
          if (log_enabled) {
            const auto log_started = std::chrono::steady_clock::now();
            append_laur_update_log_jsonl(
                args, context, shadow_mode ? shadow_selected : selected, resolved,
                0.0, 0.0, 0.0, "applied",
                shadow_mode ? "shadow_static"
                            : (selected == resolved ? "" : "alias_resolved"),
                true, &features, 0.0, 0.0, 0, 0, false, 0.0,
                shadow_mode ? shadow_resolved : selected, resolved,
                args.repair5g5_selector_mode, 0.0, 0,
                shadow_mode ? "shadow_selected:" + shadow_resolved : "",
                &spec.params);
            stats.repair5g53_json_write_ms +=
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - log_started)
                    .count();
          }
          return finish(spec.params);
        };
  }

  auto runtime = czr004::ntm::LaurLtmRuntime();
  const auto static_params =
      !args.laur_static_rule.empty()
          ? czr004::ntm::update_params_for_laur_rule_id(args.laur_static_rule)
          : czr004::ltm::UpdateParams::additive();
  // Force-additive is the canonical parity path: use the same additive
  // update loop as plain LaCAM*+LTM, without runtime feature work.
  if (stats.laur_enabled && !args.laur_force_additive) {
    czr004::ntm::LaurRuntimeOptions runtime_options;
    runtime_options.enabled = true;
    runtime_options.force_additive = args.laur_force_additive;
    runtime_options.safety_enabled = args.laur_safety_enabled;
    runtime_options.model_path = args.laur_model_path;
    runtime_options.post_first_solution_only = args.laur_post_first_solution_only;
    runtime_options.update_period_restarts = args.laur_every_k_restarts;
    runtime_options.ood_guard_enabled = args.laur_ood_guard_enabled;
    runtime_options.ood_z_threshold = args.laur_ood_z_threshold;
    if (!runtime.load(runtime_options)) {
      throw std::runtime_error("failed to load LAUR runtime model path " +
                               args.laur_model_path);
    }

    options.update_policy =
        [&](const czr004::ltm::LtmUpdateContext& context) {
          const auto additive = czr004::ltm::UpdateParams::additive();
          if (context.instance == nullptr || context.traffic_before == nullptr ||
              context.trace_events == nullptr) {
            ++stats.laur_additive_fallback_count;
            append_laur_update_log_jsonl(
                args, context, "additive_ltm", "additive_ltm", 1.0, 0.0, 0.0,
                "fallback_additive", "missing_update_context", false);
            return additive;
          }
          const auto features = czr004::ntm::build_laur_features(
              *context.instance, *context.traffic_before,
              *context.trace_events, context.stats);
          if (args.laur_post_first_solution_only &&
              !context.stats.has_incumbent_before) {
            ++stats.laur_additive_fallback_count;
            append_laur_update_log_jsonl(
                args, context, "additive_ltm", "additive_ltm", 0.0, 0.0, 0.0,
                "fallback_additive", "pre_first_solution", true, &features);
            return additive;
          }
          if (context.stats.iteration % args.laur_every_k_restarts != 0) {
            ++stats.laur_additive_fallback_count;
            append_laur_update_log_jsonl(
                args, context, "additive_ltm", "additive_ltm", 0.0, 0.0, 0.0,
                "fallback_additive", "update_period_skip", true, &features);
            return additive;
          }
          if (args.laur_force_additive) {
            ++stats.laur_selected_rules["additive_ltm"];
            append_laur_update_log_jsonl(
                args, context, "additive_ltm", "additive_ltm", 0.0, 0.0, 0.0,
                "force_additive", "force_additive", true, &features);
            return additive;
          }
          if (!args.laur_static_rule.empty()) {
            ++stats.laur_selected_rules[args.laur_static_rule];
            append_laur_update_log_jsonl(
                args, context, args.laur_static_rule, args.laur_static_rule, 0.0,
                0.0, 0.0, "applied", "static_rule", true, &features);
            return static_params;
          }

          const auto prediction = runtime.predict(features);
          ++stats.laur_inference_count;
          stats.laur_inference_total_ms += prediction.inference_ms;
          ++stats.laur_selected_rules[prediction.rule_id];

          if (!prediction.enabled) {
            ++stats.laur_additive_fallback_count;
            append_laur_update_log_jsonl(
                args, context, prediction.rule_id, "additive_ltm",
                prediction.safety_harmful_prob, prediction.predicted_delta_ratio,
                prediction.inference_ms, "fallback_additive",
                "prediction_disabled", false, &features,
                prediction.feature_max_abs_z,
                prediction.feature_mean_abs_z,
                prediction.feature_outside_3sigma_count,
                prediction.feature_outside_5sigma_count,
                prediction.ood_guard_triggered, prediction.ood_z_threshold,
                prediction.selected_rule_before_guard,
                prediction.selected_rule_after_guard,
                prediction.selected_rule_source, prediction.predicted_margin_ratio,
                prediction.nearest_support_count, prediction.guard_reason);
            return additive;
          }
          if (prediction.ood_guard_triggered) {
            ++stats.laur_additive_fallback_count;
            append_laur_update_log_jsonl(
                args, context, prediction.rule_id, "additive_ltm",
                prediction.safety_harmful_prob, prediction.predicted_delta_ratio,
                prediction.inference_ms, "fallback_additive", "ood_guard",
                true, &features, prediction.feature_max_abs_z,
                prediction.feature_mean_abs_z,
                prediction.feature_outside_3sigma_count,
                prediction.feature_outside_5sigma_count,
                prediction.ood_guard_triggered, prediction.ood_z_threshold,
                prediction.selected_rule_before_guard,
                prediction.selected_rule_after_guard,
                prediction.selected_rule_source, prediction.predicted_margin_ratio,
                prediction.nearest_support_count, prediction.guard_reason);
            return additive;
          }
          if (!args.laur_force_additive && args.laur_safety_enabled &&
              prediction.safety_harmful_prob >= args.laur_safety_threshold) {
            ++stats.laur_safety_disabled_count;
            ++stats.laur_additive_fallback_count;
            append_laur_update_log_jsonl(
                args, context, prediction.rule_id, "additive_ltm",
                prediction.safety_harmful_prob, prediction.predicted_delta_ratio,
                prediction.inference_ms, "fallback_additive", "safety_gate",
                true, &features, prediction.feature_max_abs_z,
                prediction.feature_mean_abs_z,
                prediction.feature_outside_3sigma_count,
                prediction.feature_outside_5sigma_count,
                prediction.ood_guard_triggered, prediction.ood_z_threshold,
                prediction.selected_rule_before_guard,
                "additive_ltm", "safety_gate", prediction.predicted_margin_ratio,
                prediction.nearest_support_count, prediction.guard_reason);
            return additive;
          }
          append_laur_update_log_jsonl(
              args, context, prediction.rule_id, prediction.rule_id,
              prediction.safety_harmful_prob, prediction.predicted_delta_ratio,
              prediction.inference_ms,
              args.laur_force_additive ? "force_additive" : "applied",
              args.laur_force_additive ? "force_additive" : "", true, &features,
              prediction.feature_max_abs_z, prediction.feature_mean_abs_z,
              prediction.feature_outside_3sigma_count,
              prediction.feature_outside_5sigma_count,
              prediction.ood_guard_triggered, prediction.ood_z_threshold,
              prediction.selected_rule_before_guard,
              prediction.selected_rule_after_guard,
              prediction.selected_rule_source, prediction.predicted_margin_ratio,
              prediction.nearest_support_count, prediction.guard_reason);
          return prediction.params;
        };
  }

  const auto started = std::chrono::steady_clock::now();
  const auto result = czr004::ltm::solve_with_ltm(instance, options);
  const auto ended = std::chrono::steady_clock::now();
  stats.runtime_ms =
      std::chrono::duration<double, std::milli>(ended - started).count();
  stats.solution = result.best_solution;
  stats.time_to_first_solution_ms = result.time_to_first_solution_ms;
  stats.additional_info = result.additional_info;
  stats.loop_cnt = sum_info_values(stats.additional_info, "ltm_one_shot_loop_cnt");
  stats.high_level_expansions = stats.loop_cnt;
  stats.expanded_nodes =
      sum_info_values(stats.additional_info, "ltm_one_shot_num_node_gen");
  stats.low_level_pibt_calls =
      sum_info_values(stats.additional_info, "ltm_one_shot_low_level_pibt_calls");
  stats.has_low_level_pibt_calls = true;
  stats.returned_solutions_count = stats.solution.empty() ? 0 : 1;
  stats.ltm_iterations = result.iterations;
  stats.committed_events = result.trace_summary.committed;
  stats.blocked_events = result.trace_summary.blocked;
  stats.nonzero_ltm_edges = result.traffic_map.nonzero_raw_edges();
  if (stats.repair5g53_update_policy_total_ms <= 0.0) {
    stats.repair5g53_update_policy_total_ms =
        sum_info_double_values(stats.additional_info,
                               "ltm_update_policy_total_ms");
  }
  stats.repair5g53_update_apply_ms =
      sum_info_double_values(stats.additional_info, "ltm_update_apply_ms");
  const auto cost_audit = result.traffic_map.cost_audit(&instance);
  stats.repair5g_congestion_update_count =
      result.dual_channel_update_stats.congestion_update_count;
  stats.repair5g_flow_update_count =
      result.dual_channel_update_stats.flow_update_count;
  stats.repair5g_congestion_delta_total =
      result.dual_channel_update_stats.congestion_delta_total;
  stats.repair5g_flow_delta_total =
      result.dual_channel_update_stats.flow_delta_total;
  stats.repair5g_committed_progress_events =
      result.dual_channel_update_stats.committed_progress_events;
  stats.repair5g_committed_nonprogress_events =
      result.dual_channel_update_stats.committed_nonprogress_events;
  stats.repair5g_blocked_events =
      result.dual_channel_update_stats.blocked_events;
  stats.repair5g_wait_progress_edges =
      result.dual_channel_update_stats.wait_progress_edges;
  stats.repair5g_wait_nonprogress_edges =
      result.dual_channel_update_stats.wait_nonprogress_edges;
  stats.repair5g_congestion_nonzero_edges =
      result.traffic_map.nonzero_raw_edges();
  stats.repair5g_flow_nonzero_edges = result.traffic_map.nonzero_flow_edges();
  stats.repair5g_costs_finite = cost_audit.all_finite;
  stats.repair5g_cost_bounds_respected = cost_audit.within_configured_bounds;
  stats.repair5g_min_traversal_cost = cost_audit.min_cost;
  stats.repair5g_max_traversal_cost = cost_audit.max_cost;
  append_traffic_map_jsonl(args, instance, result.traffic_map);
  return stats;
}

void append_jsonl(const Args& args, const std::filesystem::path& binary_path,
                  bool valid_instance, bool success, bool feasible,
                  int sum_of_loss, int lower_bound, int makespan,
                  const RunStats& stats)
{
  const auto ratio =
      (success && lower_bound > 0)
          ? static_cast<double>(sum_of_loss) / static_cast<double>(lower_bound)
          : std::numeric_limits<double>::quiet_NaN();

  const auto output_path = std::filesystem::path(args.output_jsonl);
  if (output_path.has_parent_path()) {
    std::filesystem::create_directories(output_path.parent_path());
  }

  std::ofstream out(output_path, std::ios::app);
  if (!out) throw std::runtime_error("cannot open output JSONL");

  const auto output_method =
      args.method_alias.empty() ? args.method : args.method_alias;

  out << "{";
  out << "\"method\":" << json_string(output_method);
  out << ",\"map\":" << json_string(args.map_name);
  out << ",\"map_path\":" << json_string(args.map);
  out << ",\"scen\":" << json_string(args.scen_id);
  out << ",\"scen_path\":" << json_string(args.scen);
  out << ",\"agents\":" << args.agents;
  out << ",\"seed\":" << args.seed;
  out << ",\"time_limit_sec\":" << json_number_or_null(args.time_limit_sec);
  out << ",\"objective\":\"sum_of_loss\"";
  out << ",\"valid_instance\":" << (valid_instance ? "true" : "false");
  out << ",\"success\":" << (success ? "true" : "false");
  out << ",\"feasible\":" << (feasible ? "true" : "false");
  out << ",\"sum_of_loss\":" << (success ? std::to_string(sum_of_loss) : "null");
  out << ",\"lower_bound\":"
      << (lower_bound > 0 ? std::to_string(lower_bound) : "null");
  out << ",\"sum_of_loss_ratio\":" << json_number_or_null(ratio);
  out << ",\"makespan\":" << (success ? std::to_string(makespan) : "null");
  out << ",\"runtime_ms\":" << json_number_or_null(stats.runtime_ms);
  out << ",\"time_to_first_solution_ms\":"
      << json_number_or_null(stats.time_to_first_solution_ms);
  out << ",\"returned_solutions_count\":" << stats.returned_solutions_count;
  out << ",\"loop_cnt\":" << stats.loop_cnt;
  out << ",\"expanded_nodes\":" << stats.expanded_nodes;
  out << ",\"high_level_expansions\":" << stats.high_level_expansions;
  out << ",\"low_level_pibt_calls\":"
      << (stats.has_low_level_pibt_calls ? std::to_string(stats.low_level_pibt_calls)
                                         : "null");
  out << ",\"ltm_iterations\":" << stats.ltm_iterations;
  out << ",\"committed_events\":" << stats.committed_events;
  out << ",\"blocked_events\":" << stats.blocked_events;
  out << ",\"nonzero_ltm_edges\":" << stats.nonzero_ltm_edges;
  out << ",\"laur_enabled\":" << (stats.laur_enabled ? "true" : "false");
  out << ",\"laur_force_additive\":"
      << (stats.laur_force_additive ? "true" : "false");
  out << ",\"laur_safety_enabled\":"
      << (stats.laur_safety_enabled ? "true" : "false");
  out << ",\"laur_update_mode\":" << json_string(stats.laur_update_mode);
  out << ",\"laur_model_path\":" << json_string(stats.laur_model_path);
  out << ",\"laur_static_rule\":" << json_string(stats.laur_static_rule);
  out << ",\"laur_ood_guard_enabled\":"
      << (args.laur_ood_guard_enabled ? "true" : "false");
  out << ",\"laur_ood_z_threshold\":"
      << json_number_or_null(args.laur_ood_z_threshold);
  out << ",\"laur_inference_count\":" << stats.laur_inference_count;
  out << ",\"laur_inference_total_ms\":"
      << json_number_or_null(stats.laur_inference_total_ms);
  out << ",\"laur_update_runtime_ms\":"
      << json_number_or_null(stats.laur_inference_total_ms);
  out << ",\"laur_additive_fallback_count\":"
      << stats.laur_additive_fallback_count;
  out << ",\"laur_safety_disabled_count\":"
      << stats.laur_safety_disabled_count;
  out << ",\"laur_update_period_restarts\":"
      << stats.laur_update_period_restarts;
  out << ",\"laur_post_first_solution_only\":"
      << (stats.laur_post_first_solution_only ? "true" : "false");
  out << ",\"laur_selected_rules\":";
  append_json_string_uint_map(out, stats.laur_selected_rules);
  out << ",\"repair5g_enabled\":"
      << (stats.repair5g_enabled ? "true" : "false");
  out << ",\"dual_channel_enabled\":"
      << (stats.dual_channel_enabled ? "true" : "false");
  out << ",\"repair5g5_selector_enabled\":"
      << (stats.repair5g5_selector_enabled ? "true" : "false");
  out << ",\"repair5g5_selector_mode\":"
      << json_string(stats.repair5g5_selector_mode);
  out << ",\"repair5g5_selector_name\":"
      << json_string(stats.repair5g5_selector_name);
  out << ",\"repair5g5_selector_spec_path\":"
      << json_string(stats.repair5g5_selector_spec_path);
  out << ",\"repair5g5_selector_inference_count\":"
      << stats.repair5g5_selector_inference_count;
  out << ",\"repair5g5_selector_fallback_count\":"
      << stats.repair5g5_selector_fallback_count;
  out << ",\"repair5g5_selected_candidates\":";
  append_json_string_uint_map(out, stats.repair5g5_selected_candidates);
  out << ",\"repair5g_runtime_audit_mode\":"
      << json_string(stats.repair5g_runtime_audit_mode);
  out << ",\"repair5g53_hook_mode\":"
      << json_string(stats.repair5g53_hook_mode);
  out << ",\"repair5g53_update_policy_calls\":"
      << stats.repair5g53_update_policy_calls;
  out << ",\"repair5g53_update_policy_total_ms\":"
      << json_number_or_null(stats.repair5g53_update_policy_total_ms);
  out << ",\"repair5g53_feature_build_ms\":"
      << json_number_or_null(stats.repair5g53_feature_build_ms);
  out << ",\"repair5g53_cost_audit_ms\":"
      << json_number_or_null(stats.repair5g53_cost_audit_ms);
  out << ",\"repair5g53_candidate_select_ms\":"
      << json_number_or_null(stats.repair5g53_candidate_select_ms);
  out << ",\"repair5g53_alias_resolve_ms\":"
      << json_number_or_null(stats.repair5g53_alias_resolve_ms);
  out << ",\"repair5g53_params_hash_ms\":"
      << json_number_or_null(stats.repair5g53_params_hash_ms);
  out << ",\"repair5g53_traffic_hash_ms\":"
      << json_number_or_null(stats.repair5g53_traffic_hash_ms);
  out << ",\"repair5g53_json_write_ms\":"
      << json_number_or_null(stats.repair5g53_json_write_ms);
  out << ",\"repair5g53_update_apply_ms\":"
      << json_number_or_null(stats.repair5g53_update_apply_ms);
  out << ",\"repair5g_candidate_id\":"
      << json_string(stats.repair5g_candidate_id);
  out << ",\"repair5g_update_mode\":"
      << json_string(stats.repair5g_update_mode);
  out << ",\"repair5g_lambda_cong\":"
      << json_number_or_null(stats.repair5g_lambda_cong);
  out << ",\"repair5g_lambda_flow\":"
      << json_number_or_null(stats.repair5g_lambda_flow);
  out << ",\"repair5g_rho_cong_decay\":"
      << json_number_or_null(stats.repair5g_rho_cong_decay);
  out << ",\"repair5g_rho_flow_decay\":"
      << json_number_or_null(stats.repair5g_rho_flow_decay);
  out << ",\"repair5g_min_edge_cost\":"
      << json_number_or_null(stats.repair5g_min_edge_cost);
  out << ",\"repair5g_max_edge_cost\":"
      << json_number_or_null(stats.repair5g_max_edge_cost);
  out << ",\"repair5g_goal_projection_mode\":"
      << json_string(stats.repair5g_goal_projection_mode);
  out << ",\"repair5g_flow_shield_beta\":"
      << json_number_or_null(stats.repair5g_flow_shield_beta);
  out << ",\"repair5g_max_flow_shield\":"
      << json_number_or_null(stats.repair5g_max_flow_shield);
  out << ",\"repair5g_alpha_cong_commit_progress\":"
      << json_number_or_null(stats.repair5g_alpha_cong_commit_progress);
  out << ",\"repair5g_alpha_cong_commit_nonprogress\":"
      << json_number_or_null(stats.repair5g_alpha_cong_commit_nonprogress);
  out << ",\"repair5g_alpha_cong_block\":"
      << json_number_or_null(stats.repair5g_alpha_cong_block);
  out << ",\"repair5g_alpha_cong_wait_progress\":"
      << json_number_or_null(stats.repair5g_alpha_cong_wait_progress);
  out << ",\"repair5g_alpha_cong_wait_nonprogress\":"
      << json_number_or_null(stats.repair5g_alpha_cong_wait_nonprogress);
  out << ",\"repair5g_alpha_flow_commit_progress\":"
      << json_number_or_null(stats.repair5g_alpha_flow_commit_progress);
  out << ",\"repair5g_congestion_update_count\":"
      << stats.repair5g_congestion_update_count;
  out << ",\"repair5g_flow_update_count\":"
      << stats.repair5g_flow_update_count;
  out << ",\"repair5g_congestion_delta_total\":"
      << json_number_or_null(stats.repair5g_congestion_delta_total);
  out << ",\"repair5g_flow_delta_total\":"
      << json_number_or_null(stats.repair5g_flow_delta_total);
  out << ",\"repair5g_committed_progress_events\":"
      << stats.repair5g_committed_progress_events;
  out << ",\"repair5g_committed_nonprogress_events\":"
      << stats.repair5g_committed_nonprogress_events;
  out << ",\"repair5g_blocked_events\":"
      << stats.repair5g_blocked_events;
  out << ",\"repair5g_wait_progress_edges\":"
      << stats.repair5g_wait_progress_edges;
  out << ",\"repair5g_wait_nonprogress_edges\":"
      << stats.repair5g_wait_nonprogress_edges;
  out << ",\"repair5g_congestion_nonzero_edges\":"
      << stats.repair5g_congestion_nonzero_edges;
  out << ",\"repair5g_flow_nonzero_edges\":"
      << stats.repair5g_flow_nonzero_edges;
  out << ",\"repair5g_costs_finite\":"
      << (stats.repair5g_costs_finite ? "true" : "false");
  out << ",\"repair5g_cost_bounds_respected\":"
      << (stats.repair5g_cost_bounds_respected ? "true" : "false");
  out << ",\"repair5g_min_traversal_cost\":"
      << json_number_or_null(stats.repair5g_min_traversal_cost);
  out << ",\"repair5g_max_traversal_cost\":"
      << json_number_or_null(stats.repair5g_max_traversal_cost);
  out << ",\"git_commit\":" << json_string(args.project_commit);
  out << ",\"external_lacam2_commit\":" << json_string(args.external_commit);
  out << ",\"branch\":" << json_string(args.branch);
  out << ",\"dirty\":" << json_string(args.dirty);
  out << ",\"binary_path\":" << json_string(binary_path.string());
  out << ",\"config_path\":" << json_string(args.manifest);
  out << ",\"platform\":" << json_string(args.platform);
  out << "}\n";
}

}  // namespace

int main(int argc, char** argv)
{
  try {
    const auto args = parse_args(argc, argv);
    const auto binary_path = std::filesystem::absolute(argv[0]);

    const auto instance = Instance(args.scen, args.map, args.agents);
    const auto valid_instance = instance.is_valid(args.verbose);
    RunStats stats;
    bool success = false;
    bool feasible = false;
    int sum_of_loss = 0;
    int lower_bound = 0;
    int makespan = 0;

    if (valid_instance) {
      if (args.method == "lacam_star") {
        stats = run_lacam_star(instance, args);
      } else {
        stats = run_lacam_star_ltm(instance, args);
      }
      success = !stats.solution.empty();
      feasible = success && is_feasible_solution(instance, stats.solution, 1);
      if (success) {
        auto dist_table = DistTable(instance);
        sum_of_loss = get_sum_of_loss(stats.solution);
        lower_bound = get_sum_of_costs_lower_bound(instance, dist_table);
        makespan = get_makespan(stats.solution);
      }
    }

    append_jsonl(args, binary_path, valid_instance, success, feasible,
                 sum_of_loss, lower_bound, makespan, stats);

    std::cout << "phase1a_batch"
              << " method=" << args.method << " map=" << args.map_name
              << " agents=" << args.agents << " seed=" << args.seed
              << " success=" << success << " feasible=" << feasible
              << " sum_of_loss=" << (success ? sum_of_loss : 0)
              << " lower_bound=" << lower_bound << std::endl;
    return success && feasible ? 0 : 2;
  } catch (const std::exception& e) {
    std::cerr << "phase1a_batch: " << e.what() << std::endl;
    return 1;
  }
}
