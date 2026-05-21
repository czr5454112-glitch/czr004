cmake_minimum_required(VERSION 3.16)
project(czr004-ltm CXX)

set(LACAM2_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../external/lacam2")
set(COMPAT_HEADER "${CMAKE_CURRENT_LIST_DIR}/../compat/lacam2_windows_compat.hpp")

add_subdirectory("${LACAM2_ROOT}/lacam2" lacam2_build)

add_library(czr004_ltm ltm.cpp ltm.hpp)
target_compile_features(czr004_ltm PUBLIC cxx_std_17)
target_include_directories(czr004_ltm PUBLIC "${CMAKE_CURRENT_LIST_DIR}")
target_link_libraries(czr004_ltm PUBLIC lacam2)

add_executable(phase1_ltm_smoke phase1_ltm_smoke.cpp)
target_compile_features(phase1_ltm_smoke PUBLIC cxx_std_17)
target_link_libraries(phase1_ltm_smoke PRIVATE czr004_ltm)

if(MSVC)
  target_compile_options(lacam2 PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(czr004_ltm PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
  target_compile_options(phase1_ltm_smoke PRIVATE "/EHsc" "/FI${COMPAT_HEADER}")
endif()
