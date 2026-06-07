cmake_minimum_required(VERSION 3.16)
project(czr004-ltm CXX)

set(LACAM2_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../external/lacam2")
set(COMPAT_HEADER "${CMAKE_CURRENT_LIST_DIR}/../compat/lacam2_windows_compat.hpp")

add_subdirectory("${LACAM2_ROOT}/lacam2" lacam2_build)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  # LaCAM2 declares DistTable::get(uint,uint) inline in the header but defines it
  # out-of-line in dist_table.cpp. MSVC links this, while GCC/Clang may discard
  # the symbol from the static library unless inline functions are retained.
  target_compile_options(lacam2 PRIVATE -fkeep-inline-functions)
endif()

add_library(czr004_ltm ltm.cpp ltm.hpp)
target_compile_features(czr004_ltm PUBLIC cxx_std_17)
target_include_directories(czr004_ltm PUBLIC "${CMAKE_CURRENT_LIST_DIR}")
target_link_libraries(czr004_ltm PUBLIC lacam2)

add_library(
  czr004_ntm
  ../ntm/laur_ltm_runtime.cpp
  ../ntm/laur_ltm_runtime.hpp
  ../ntm/laur_ltm_features.cpp
  ../ntm/laur_ltm_features.hpp
)
target_compile_features(czr004_ntm PUBLIC cxx_std_17)
target_include_directories(
  czr004_ntm
  PUBLIC
    "${CMAKE_CURRENT_LIST_DIR}"
    "${CMAKE_CURRENT_LIST_DIR}/../ntm"
)
target_link_libraries(czr004_ntm PUBLIC czr004_ltm)

add_executable(phase1_ltm_smoke phase1_ltm_smoke.cpp)
target_compile_features(phase1_ltm_smoke PUBLIC cxx_std_17)
target_link_libraries(phase1_ltm_smoke PRIVATE czr004_ltm)

add_executable(phase4_laur_update_smoke phase4_laur_update_smoke.cpp)
target_compile_features(phase4_laur_update_smoke PUBLIC cxx_std_17)
target_link_libraries(phase4_laur_update_smoke PRIVATE czr004_ltm)

add_executable(phase5_laur_runtime_smoke ../ntm/phase5_laur_runtime_smoke.cpp)
target_compile_features(phase5_laur_runtime_smoke PUBLIC cxx_std_17)
target_link_libraries(phase5_laur_runtime_smoke PRIVATE czr004_ntm)

add_executable(phase4_laur_record ../tools/phase4_laur_record.cpp)
target_compile_features(phase4_laur_record PUBLIC cxx_std_17)
target_link_libraries(phase4_laur_record PRIVATE czr004_ltm)

add_executable(phase4_laur_probe ../tools/phase4_laur_probe.cpp)
target_compile_features(phase4_laur_probe PUBLIC cxx_std_17)
target_link_libraries(phase4_laur_probe PRIVATE czr004_ltm)

add_executable(phase1a_batch ../tools/phase1a_batch.cpp)
target_compile_features(phase1a_batch PUBLIC cxx_std_17)
target_link_libraries(phase1a_batch PRIVATE czr004_ntm)

if(MSVC)
  target_compile_options(lacam2 PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(czr004_ltm PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(czr004_ntm PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase1_ltm_smoke PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase4_laur_update_smoke PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase5_laur_runtime_smoke PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase4_laur_record PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase4_laur_probe PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase1a_batch PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
endif()
