cmake_minimum_required(VERSION 3.21)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL" CACHE STRING
    "MSVC runtime library used by native geomtool targets" FORCE)
project(geomtool LANGUAGES CXX)

option(USE_MESH "Build geomtool with Netgen mesh generation" OFF)
option(USE_INSTANTMESH2D "Build geomtool with the InstantMesh2D 2D mesh backend" OFF)
set(NETGEN_DIR "" CACHE PATH "Installed Netgen native SDK root")
set(OCCT_ROOT "" CACHE PATH "Selected OCCT SDK root")
set(OCC_INC_DIR "" CACHE PATH "Directory containing OCCT headers")
set(OCC_LIB_DIR "" CACHE PATH "Directory containing OCCT import/static libraries")
set(OpenCASCADE_DIR "" CACHE PATH "Directory containing OpenCASCADEConfig.cmake")
set(BUILDNO "" CACHE STRING "Unquoted geomtool build identifier preprocessing token")

if(WIN32)
  if(NOT OCCT_ROOT)
    message(FATAL_ERROR "OCCT_ROOT must select the qualified managed OCCT SDK")
  endif()
  if(NOT OCC_INC_DIR)
    set(OCC_INC_DIR "${OCCT_ROOT}/inc" CACHE PATH "Directory containing OCCT headers" FORCE)
  endif()
  if(NOT OCC_LIB_DIR)
    set(OCC_LIB_DIR "${OCCT_ROOT}/win64/vc14/lib" CACHE PATH
        "Directory containing OCCT import/static libraries" FORCE)
  endif()
  if(NOT OpenCASCADE_DIR)
    set(OpenCASCADE_DIR "${OCCT_ROOT}/cmake" CACHE PATH
        "Directory containing OpenCASCADEConfig.cmake" FORCE)
  endif()
else()
  if(OCCT_ROOT)
    if(NOT OCC_INC_DIR)
      set(OCC_INC_DIR "${OCCT_ROOT}/include/opencascade" CACHE PATH
          "Directory containing OCCT headers" FORCE)
    endif()
    if(NOT OCC_LIB_DIR)
      set(OCC_LIB_DIR "${OCCT_ROOT}/lib" CACHE PATH
          "Directory containing OCCT import/static libraries" FORCE)
    endif()
    if(NOT OpenCASCADE_DIR)
      set(OpenCASCADE_DIR "${OCCT_ROOT}/lib/cmake/opencascade" CACHE PATH
          "Directory containing OpenCASCADEConfig.cmake" FORCE)
    endif()
  endif()
  if(NOT OCC_INC_DIR)
    set(OCC_INC_DIR "/usr/local/include/opencascade" CACHE PATH
        "Directory containing OCCT headers" FORCE)
  endif()
  if(NOT OCC_LIB_DIR)
    set(OCC_LIB_DIR "/usr/local/lib/opencascade" CACHE PATH
        "Directory containing OCCT import/static libraries" FORCE)
  endif()
  if(STATIC)
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".a")
    set(BUILD_SHARED_LIBS OFF)
  endif()
endif()

if(NOT EXISTS "${OCC_INC_DIR}/Standard.hxx")
  message(FATAL_ERROR
    "OCC_INC_DIR must contain Standard.hxx (received: ${OCC_INC_DIR})")
endif()
if(NOT IS_DIRECTORY "${OCC_LIB_DIR}")
  message(FATAL_ERROR
    "OCC_LIB_DIR must be an OCCT library directory (received: ${OCC_LIB_DIR})")
endif()
if(OpenCASCADE_DIR AND NOT EXISTS "${OpenCASCADE_DIR}/OpenCASCADEConfig.cmake")
  message(FATAL_ERROR
    "OpenCASCADE_DIR must contain OpenCASCADEConfig.cmake (received: ${OpenCASCADE_DIR})")
endif()
if(NOT BUILDNO)
  if(WIN32)
    message(FATAL_ERROR "BUILDNO must be supplied by the product build entry point")
  else()
    set(BUILDNO "2021.05.00")
  endif()
endif()

function(assert_in_occt_root label path_value)
  if(NOT OCCT_ROOT)
    return()
  endif()
  set(_root "${OCCT_ROOT}")
  set(_path "${path_value}")
  cmake_path(NORMAL_PATH _root)
  cmake_path(NORMAL_PATH _path)
  if(WIN32)
    string(TOLOWER "${_root}" _root)
    string(TOLOWER "${_path}" _path)
  endif()
  cmake_path(IS_PREFIX _root "${_path}" NORMALIZE _inside)
  if(NOT _inside)
    message(FATAL_ERROR "${label} resolved outside OCCT_ROOT '${OCCT_ROOT}': '${path_value}'")
  endif()
endfunction()

function(assert_in_netgen_root label path_value)
  set(_root "${NETGEN_DIR}")
  set(_path "${path_value}")
  cmake_path(NORMAL_PATH _root)
  cmake_path(NORMAL_PATH _path)
  if(WIN32)
    string(TOLOWER "${_root}" _root)
    string(TOLOWER "${_path}" _path)
  endif()
  cmake_path(IS_PREFIX _root "${_path}" NORMALIZE _inside)
  if(NOT _inside)
    message(FATAL_ERROR
      "${label} resolved outside NETGEN_DIR '${NETGEN_DIR}': '${path_value}'")
  endif()
endfunction()

if(OCCT_ROOT)
  assert_in_occt_root("OCC_INC_DIR" "${OCC_INC_DIR}")
  assert_in_occt_root("OCC_LIB_DIR" "${OCC_LIB_DIR}")
  if(OpenCASCADE_DIR)
    assert_in_occt_root("OpenCASCADE_DIR" "${OpenCASCADE_DIR}")
  endif()
endif()

set(SRCDIR "${PROJECT_SOURCE_DIR}/src")
set(INSTANTMESH2D_DIR "${PROJECT_SOURCE_DIR}/third_party/instantmesh2d")
set(OCC_LIBS
  TKDESTEP
  TKDEIGES
  TKDESTL
  TKDE
  TKXCAF
  TKVCAF
  TKV3d
  TKService
  TKLCAF
  TKHLR
  TKCDF
  TKCAF
  TKXSBase
  TKMesh
  TKOffset
  TKFillet
  TKBool
  TKBO
  TKShHealing
  TKPrim
  TKTopAlgo
  TKGeomAlgo
  TKBRep
  TKGeomBase
  TKG3d
  TKG2d
  TKMath
  TKernel
  )

set(OCC_LIBRARIES)
set(OCC_SYSTEM_LIBRARIES)
if(STATIC AND WIN32)
  find_package(OpenCASCADE CONFIG REQUIRED
    PATHS "${OpenCASCADE_DIR}"
    NO_DEFAULT_PATH)
  set(OCC_LIBRARIES ${OpenCASCADE_LIBRARIES})
  set(OCC_SYSTEM_LIBRARIES
    advapi32 gdi32 user32 wsock32 psapi windowscodecs winmm)
elseif(STATIC)
  find_package(OpenCASCADE CONFIG REQUIRED
    PATHS "${OpenCASCADE_DIR}"
    NO_DEFAULT_PATH)
  foreach(libname IN LISTS OCC_LIBS)
    if(NOT TARGET ${libname})
      message(FATAL_ERROR "OpenCASCADE package did not define required target ${libname}")
    endif()
    list(APPEND OCC_LIBRARIES ${libname})
  endforeach()
else()
  foreach(libname IN LISTS OCC_LIBS)
    find_library(OCC_LIBRARY_${libname} NAMES ${libname}
      PATHS "${OCC_LIB_DIR}" NO_DEFAULT_PATH REQUIRED)
    assert_in_occt_root("OCCT library ${libname}" "${OCC_LIBRARY_${libname}}")
    list(APPEND OCC_LIBRARIES "${OCC_LIBRARY_${libname}}")
  endforeach()
endif()

if(USE_MESH)
  if(NOT NETGEN_DIR)
    message(FATAL_ERROR "NETGEN_DIR must select the qualified Netgen native SDK")
  endif()
  if(NOT EXISTS "${NETGEN_DIR}/cmake/NetgenConfig.cmake")
    message(FATAL_ERROR
      "NETGEN_DIR must contain cmake/NetgenConfig.cmake (received: ${NETGEN_DIR})")
  endif()

  find_package(Netgen CONFIG REQUIRED
    PATHS "${NETGEN_DIR}/cmake"
    NO_DEFAULT_PATH)

  foreach(_target ngcore nglib)
    if(NOT TARGET ${_target})
      message(FATAL_ERROR "Netgen package did not define required target ${_target}")
    endif()
    set(_required_artifact_properties IMPORTED_LOCATION_RELEASE)
    if(WIN32 AND NOT STATIC)
      list(APPEND _required_artifact_properties IMPORTED_IMPLIB_RELEASE)
    endif()
    foreach(_property IN LISTS _required_artifact_properties)
      get_target_property(_artifact ${_target} ${_property})
      if(NOT _artifact OR NOT EXISTS "${_artifact}")
        message(FATAL_ERROR "${_target} has no usable ${_property}: ${_artifact}")
      endif()
      assert_in_netgen_root("${_target} ${_property}" "${_artifact}")
      if(STATIC AND _target STREQUAL "nglib" AND
         _property STREQUAL "IMPORTED_LOCATION_RELEASE")
        set(NETGEN_NGLIB_LIBRARY "${_artifact}")
      endif()
    endforeach()
  endforeach()
endif()

include("${SRCDIR}/sources.cmake")
set(SOURCES ${GEOMTOOL_BASE_SOURCES})

if(USE_MESH OR USE_INSTANTMESH2D)
  list(APPEND SOURCES ${GEOMTOOL_MESH_SOURCES})
endif()

if(USE_MESH)
  list(APPEND SOURCES ${GEOMTOOL_NETGEN_SOURCES})
  set_source_files_properties(${GEOMTOOL_NETGEN_SOURCES} PROPERTIES
    COMPILE_DEFINITIONS OCCGEOMETRY)
endif()

if(USE_INSTANTMESH2D)
  include("${INSTANTMESH2D_DIR}/sources.cmake")
  add_library(instantmesh2d_core STATIC
    ${GEOMTOOL_INSTANTMESH2D_CORE_SOURCES})
  target_include_directories(instantmesh2d_core PUBLIC ${INSTANTMESH2D_DIR})
  set_target_properties(instantmesh2d_core PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF)
  list(APPEND SOURCES ${GEOMTOOL_INSTANTMESH2D_SOURCES})
endif()

add_executable(geomtool ${SOURCES})
set_target_properties(geomtool PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF)
target_include_directories(geomtool PRIVATE ${SRCDIR} ${OCC_INC_DIR})
target_compile_definitions(geomtool PRIVATE
  BUILDNO=${BUILDNO}
  $<$<CONFIG:Release>:PROD>)
if(USE_MESH OR USE_INSTANTMESH2D)
  target_compile_definitions(geomtool PRIVATE MESH)
endif()
if(USE_MESH)
  target_compile_definitions(geomtool PRIVATE
    MESH_NETGEN
    GEOMTOOL_MOCK_NETGEN_VERSION="${NETGEN_VERSION}")
endif()
if(USE_INSTANTMESH2D)
  target_compile_definitions(geomtool PRIVATE MESH_INSTANTMESH2D)
endif()
if(MSVC)
  target_compile_definitions(geomtool PRIVATE _USE_MATH_DEFINES)
endif()
if(STATIC)
  target_compile_definitions(geomtool PRIVATE STATIC)
  if(WIN32)
    target_compile_definitions(geomtool PRIVATE OCCT_STATIC_BUILD OCCT_NO_PLUGINS)
    target_link_directories(geomtool PRIVATE "${OpenCASCADE_LIBRARY_DIR}")
  endif()
  if(NOT WIN32)
    set(THREADS_PREFER_PTHREAD_FLAG ON)
    find_package(Threads REQUIRED)
    target_link_libraries(geomtool PRIVATE Threads::Threads)
  endif()
endif()
if(UNIX AND NOT APPLE)
  target_link_options(geomtool PRIVATE -s)
endif()
target_link_libraries(geomtool PRIVATE ${OCC_LIBRARIES} ${OCC_SYSTEM_LIBRARIES})
if(USE_MESH)
  if(STATIC)
    if(NOT NETGEN_NGLIB_LIBRARY)
      message(FATAL_ERROR "Static Netgen nglib archive was not resolved")
    endif()
    if(MSVC)
      target_link_options(geomtool PRIVATE "/WHOLEARCHIVE:${NETGEN_NGLIB_LIBRARY}")
    elseif(APPLE)
      target_link_options(geomtool PRIVATE "-Wl,-force_load,${NETGEN_NGLIB_LIBRARY}")
    else()
      target_link_libraries(geomtool PRIVATE
        "-Wl,--whole-archive" "${NETGEN_NGLIB_LIBRARY}" "-Wl,--no-whole-archive")
    endif()
  endif()
  target_link_libraries(geomtool PRIVATE nglib)
endif()
if(USE_INSTANTMESH2D)
  target_link_libraries(geomtool PRIVATE instantmesh2d_core)
endif()

include(GNUInstallDirs)
install(TARGETS geomtool RUNTIME DESTINATION bin)

include(CTest)
if(BUILD_TESTING)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  set(_e2e_args
    --exe "$<TARGET_FILE:geomtool>"
    --work "${CMAKE_CURRENT_BINARY_DIR}/e2e")
  if(USE_MESH)
    list(APPEND _e2e_args --mesh)
  endif()
  add_test(
    NAME geomtool_mock_e2e
    COMMAND Python3::Interpreter "${PROJECT_SOURCE_DIR}/tests/e2e.py" ${_e2e_args})
endif()
