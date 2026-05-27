#pragma once

#include "laur_ltm_runtime.hpp"

#include "../ltm/ltm.hpp"

#include <lacam2.hpp>

#include <vector>

namespace czr004::ntm {

LaurFeatureVector build_laur_features(
    const Instance& instance,
    const czr004::ltm::DirectedTrafficMap& traffic_map,
    const std::vector<czr004::ltm::TraceEvent>& trace_events,
    const czr004::ltm::LtmIterationStats& stats);

}  // namespace czr004::ntm
