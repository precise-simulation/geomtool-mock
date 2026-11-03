cmake_minimum_required(VERSION 3.21)

project(geomtool_mock LANGUAGES CXX)

include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL" CACHE STRING
    "MSVC runtime library used by the mock" FORCE)

set(OCCT_ROOT "" CACHE PATH "Root of the extracted precise-simulation/OCCT-sdk package")
set(NETGEN_DIR "" CACHE PATH "Root of the extracted precise-simulation/netgen-sdk package")
set(EXPECTED_OCCT_VERSION "8.0.1" CACHE STRING "Expected OCCT SDK version")
set(EXPECTED_NETGEN_VERSION "6.2.2608" CACHE STRING "Expected Netgen SDK version")

if(NOT OCCT_ROOT)
  message(FATAL_ERROR "OCCT_ROOT is required")
endif()
if(NOT NETGEN_DIR)
  message(FATAL_ERROR "NETGEN_DIR is required")
endif()

if(WIN32)
  set(_occt_cmake_dir "${OCCT_ROOT}/cmake")
  set(_occt_include_dir "${OCCT_ROOT}/inc")
else()
  set(_occt_cmake_dir "${OCCT_ROOT}/lib/cmake/opencascade")
  set(_occt_include_dir "${OCCT_ROOT}/include/opencascade")
endif()

if(NOT EXISTS "${_occt_cmake_dir}/OpenCASCADEConfig.cmake")
  message(FATAL_ERROR
    "OCCT_ROOT does not contain the expected SDK CMake package: ${_occt_cmake_dir}")
endif()
if(NOT EXISTS "${_occt_include_dir}/Standard.hxx")
  message(FATAL_ERROR
    "OCCT_ROOT does not contain the expected SDK headers: ${_occt_include_dir}")
endif()
if(NOT EXISTS "${NETGEN_DIR}/cmake/NetgenConfig.cmake")
  message(FATAL_ERROR
    "NETGEN_DIR does not contain cmake/NetgenConfig.cmake: ${NETGEN_DIR}")
endif()

find_package(OpenCASCADE CONFIG REQUIRED
  PATHS "${_occt_cmake_dir}"
  NO_DEFAULT_PATH)
find_package(Netgen CONFIG REQUIRED
  PATHS "${NETGEN_DIR}/cmake"
  NO_DEFAULT_PATH)

if(NOT NETGEN_VERSION STREQUAL EXPECTED_NETGEN_VERSION)
  message(FATAL_ERROR
    "Netgen SDK version ${NETGEN_VERSION} does not match ${EXPECTED_NETGEN_VERSION}")
endif()

foreach(_target TKernel TKBRep TKPrim TKTopAlgo TKMesh TKDESTL ngcore nglib)
  if(NOT TARGET ${_target})
    message(FATAL_ERROR "Required SDK target ${_target} is unavailable")
  endif()
endforeach()

add_executable(geomtool src/main.cpp)
target_compile_definitions(geomtool PRIVATE
  OCCGEOMETRY
  GEOMTOOL_MOCK_NETGEN_VERSION="${NETGEN_VERSION}")
target_include_directories(geomtool PRIVATE "${_occt_include_dir}")
target_link_libraries(geomtool PRIVATE
  nglib
  ngcore
  TKDESTL
  TKMesh
  TKPrim
  TKBRep
  TKTopAlgo
  TKernel)

if(BUILD_TESTING)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  add_test(
    NAME geomtool_mock_e2e
    COMMAND Python3::Interpreter
      "${PROJECT_SOURCE_DIR}/tests/e2e.py"
      --exe "$<TARGET_FILE:geomtool>"
      --occt-version "${EXPECTED_OCCT_VERSION}"
      --netgen-version "${EXPECTED_NETGEN_VERSION}"
      --work "${CMAKE_CURRENT_BINARY_DIR}/e2e")
endif()

include(GNUInstallDirs)
install(TARGETS geomtool RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
