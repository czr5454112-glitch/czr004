cmake_minimum_required(VERSION 3.16)
project(czr004-phase0-smoke CXX)

set(LACAM2_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../external/lacam2")
set(COMPAT_HEADER "${CMAKE_CURRENT_LIST_DIR}/../compat/lacam2_windows_compat.hpp")

add_subdirectory("${LACAM2_ROOT}/lacam2" lacam2_build)

add_executable(phase0_smoke phase0_smoke.cpp)
target_compile_features(phase0_smoke PUBLIC cxx_std_17)
target_link_libraries(phase0_smoke PRIVATE lacam2)

if(MSVC)
  target_compile_options(lacam2 PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase0_smoke PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
endif()
