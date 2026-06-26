# CMakeLists.txt — Vyn C/C++ Runtime Library
# Builds: vyn_rt (static) + vyn_async (C++20 optional) + vyn_ffi
# Usage:
#   mkdir build && cd build
#   cmake .. -DCMAKE_BUILD_TYPE=Release
#   cmake --build .

cmake_minimum_required(VERSION 3.16)
project(VynRuntime VERSION 1.0.0 LANGUAGES C CXX)

# ─── C/C++ Standards ──────────────────────────────────────────────────────────
set(CMAKE_C_STANDARD   11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ─── Options ──────────────────────────────────────────────────────────────────
option(VYN_ENABLE_ASYNC      "Build async C++ runtime"          ON)
option(VYN_ENABLE_FFI        "Build FFI bridge"                  ON)
option(VYN_ENABLE_TESTS      "Build runtime tests"               OFF)
option(VYN_ENABLE_COROUTINES "Enable C++20 coroutines (clang/gcc)" OFF)
option(VYN_SANITIZE          "Enable AddressSanitizer"           OFF)
option(VYN_COVERAGE          "Enable code coverage"              OFF)

# ─── Compiler flags ───────────────────────────────────────────────────────────
if(MSVC)
    add_compile_options(/W4 /WX- /O2 /MP)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
else()
    add_compile_options(
        -Wall -Wextra -Wpedantic
        -Wno-unused-parameter
        -Wno-sign-compare
        -fvisibility=hidden
    )
    if(CMAKE_BUILD_TYPE STREQUAL "Release")
        add_compile_options(-O3 -march=native -fomit-frame-pointer)
    elseif(CMAKE_BUILD_TYPE STREQUAL "Debug")
        add_compile_options(-O0 -g3 -DDEBUG)
    endif()
    if(VYN_SANITIZE)
        add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
        add_link_options(-fsanitize=address,undefined)
    endif()
    if(VYN_COVERAGE)
        add_compile_options(--coverage -fprofile-arcs -ftest-coverage)
        add_link_options(--coverage)
    endif()
endif()

# ─── Platform detection ───────────────────────────────────────────────────────
if(WIN32)
    add_compile_definitions(VYN_PLATFORM_WINDOWS=1)
elseif(APPLE)
    add_compile_definitions(VYN_PLATFORM_MACOS=1)
else()
    add_compile_definitions(VYN_PLATFORM_LINUX=1)
endif()

# ─── Include directories ──────────────────────────────────────────────────────
include_directories(${CMAKE_CURRENT_SOURCE_DIR})

# ═══════════════════════════════════════════════════════════════════════════════
#  Core C runtime (vyn_rt)
# ═══════════════════════════════════════════════════════════════════════════════

set(VYN_RT_SOURCES
    vyn_rt.c
)

set(VYN_RT_HEADERS
    vyn_rt.h
)

add_library(vyn_rt STATIC ${VYN_RT_SOURCES} ${VYN_RT_HEADERS})

target_include_directories(vyn_rt PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include/vyn>
)

# Link math library (needed for sin, cos, sqrt, etc.)
target_link_libraries(vyn_rt PUBLIC m)

# pthreads on Unix
if(NOT WIN32)
    find_package(Threads REQUIRED)
    target_link_libraries(vyn_rt PUBLIC Threads::Threads ${CMAKE_DL_LIBS})
else()
    target_link_libraries(vyn_rt PUBLIC ws2_32)
endif()

# Compile-time feature flags
target_compile_definitions(vyn_rt PRIVATE
    VYN_VERSION_STR="${PROJECT_VERSION}"
    VYN_BUILD_STATIC=1
)

# ═══════════════════════════════════════════════════════════════════════════════
#  C++ Async runtime (vyn_async)
# ═══════════════════════════════════════════════════════════════════════════════

if(VYN_ENABLE_ASYNC)
    set(VYN_ASYNC_SOURCES
        vyn_async.cpp
    )

    add_library(vyn_async STATIC ${VYN_ASYNC_SOURCES})

    target_include_directories(vyn_async PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<INSTALL_INTERFACE:include/vyn>
    )

    target_link_libraries(vyn_async PUBLIC vyn_rt)

    # C++20 coroutines (optional)
    if(VYN_ENABLE_COROUTINES)
        if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
            target_compile_options(vyn_async PRIVATE -std=c++20 -fcoroutines)
            target_compile_definitions(vyn_async PRIVATE VYN_HAS_COROUTINES=1)
        elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
            target_compile_options(vyn_async PRIVATE -std=c++20 -fcoroutines)
            target_compile_definitions(vyn_async PRIVATE VYN_HAS_COROUTINES=1)
        elseif(MSVC)
            target_compile_options(vyn_async PRIVATE /std:c++20 /await:strict)
            target_compile_definitions(vyn_async PRIVATE VYN_HAS_COROUTINES=1)
        endif()
    else()
        # C++17 fallback: no coroutines
        target_compile_definitions(vyn_async PRIVATE VYN_HAS_COROUTINES=0)
    endif()

    set_target_properties(vyn_async PROPERTIES
        CXX_STANDARD 17
        CXX_STANDARD_REQUIRED ON
        POSITION_INDEPENDENT_CODE ON
    )
endif()

# ═══════════════════════════════════════════════════════════════════════════════
#  C++ FFI bridge (vyn_ffi)
# ═══════════════════════════════════════════════════════════════════════════════

if(VYN_ENABLE_FFI)
    set(VYN_FFI_SOURCES
        vyn_ffi.cpp
    )

    # Only build if vyn_ffi.cpp exists (it may be generated later)
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/vyn_ffi.cpp)
        add_library(vyn_ffi STATIC ${VYN_FFI_SOURCES})

        target_include_directories(vyn_ffi PUBLIC
            $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
            $<INSTALL_INTERFACE:include/vyn>
        )

        target_link_libraries(vyn_ffi PUBLIC vyn_rt)

        if(VYN_ENABLE_ASYNC)
            target_link_libraries(vyn_ffi PUBLIC vyn_async)
        endif()

        set_target_properties(vyn_ffi PROPERTIES
            CXX_STANDARD 17
            CXX_STANDARD_REQUIRED ON
            POSITION_INDEPENDENT_CODE ON
        )

        # Optional: libffi for advanced FFI
        find_library(LIBFFI_LIB ffi)
        if(LIBFFI_LIB)
            target_link_libraries(vyn_ffi PUBLIC ${LIBFFI_LIB})
            target_compile_definitions(vyn_ffi PRIVATE VYN_HAS_LIBFFI=1)
            message(STATUS "Found libffi: ${LIBFFI_LIB}")
        else()
            message(STATUS "libffi not found, using built-in call dispatcher")
        endif()
    else()
        message(STATUS "vyn_ffi.cpp not found, skipping vyn_ffi target")
    endif()
endif()

# ═══════════════════════════════════════════════════════════════════════════════
#  Combined convenience target (vyn_runtime — links all sub-libraries)
# ═══════════════════════════════════════════════════════════════════════════════

add_library(vyn_runtime INTERFACE)
target_link_libraries(vyn_runtime INTERFACE vyn_rt)

if(VYN_ENABLE_ASYNC)
    target_link_libraries(vyn_runtime INTERFACE vyn_async)
endif()

if(VYN_ENABLE_FFI AND TARGET vyn_ffi)
    target_link_libraries(vyn_runtime INTERFACE vyn_ffi)
endif()

# ═══════════════════════════════════════════════════════════════════════════════
#  Shared library variant  (vyn_rt.so / vyn_rt.dll)
# ═══════════════════════════════════════════════════════════════════════════════

option(VYN_BUILD_SHARED "Also build shared library" OFF)

if(VYN_BUILD_SHARED)
    add_library(vyn_rt_shared SHARED ${VYN_RT_SOURCES})
    set_target_properties(vyn_rt_shared PROPERTIES OUTPUT_NAME vyn_rt)
    target_include_directories(vyn_rt_shared PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<INSTALL_INTERFACE:include/vyn>
    )
    target_link_libraries(vyn_rt_shared PUBLIC m)
    if(NOT WIN32)
        target_link_libraries(vyn_rt_shared PUBLIC Threads::Threads ${CMAKE_DL_LIBS})
    endif()
    target_compile_definitions(vyn_rt_shared PRIVATE VYN_BUILD_SHARED=1)
endif()

# ═══════════════════════════════════════════════════════════════════════════════
#  Tests
# ═══════════════════════════════════════════════════════════════════════════════

if(VYN_ENABLE_TESTS)
    enable_testing()

    # Test: basic runtime
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_rt.c)
        add_executable(test_rt tests/test_rt.c)
        target_link_libraries(test_rt PRIVATE vyn_rt)
        add_test(NAME test_rt COMMAND test_rt)
    endif()

    # Test: strings
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_string.c)
        add_executable(test_string tests/test_string.c)
        target_link_libraries(test_string PRIVATE vyn_rt)
        add_test(NAME test_string COMMAND test_string)
    endif()

    # Test: hashmap
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_hashmap.c)
        add_executable(test_hashmap tests/test_hashmap.c)
        target_link_libraries(test_hashmap PRIVATE vyn_rt)
        add_test(NAME test_hashmap COMMAND test_hashmap)
    endif()

    # Test: vec
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_vec.c)
        add_executable(test_vec tests/test_vec.c)
        target_link_libraries(test_vec PRIVATE vyn_rt)
        add_test(NAME test_vec COMMAND test_vec)
    endif()

    # Test: GC
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_gc.c)
        add_executable(test_gc tests/test_gc.c)
        target_link_libraries(test_gc PRIVATE vyn_rt)
        add_test(NAME test_gc COMMAND test_gc)
    endif()

    # Test: async (C++)
    if(VYN_ENABLE_ASYNC AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_async.cpp)
        add_executable(test_async tests/test_async.cpp)
        target_link_libraries(test_async PRIVATE vyn_async vyn_rt)
        add_test(NAME test_async COMMAND test_async)
    endif()

    # Test: FFI
    if(VYN_ENABLE_FFI AND TARGET vyn_ffi AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_ffi.cpp)
        add_executable(test_ffi tests/test_ffi.cpp)
        target_link_libraries(test_ffi PRIVATE vyn_ffi vyn_async vyn_rt)
        add_test(NAME test_ffi COMMAND test_ffi)
    endif()

    message(STATUS "Tests enabled. Run: ctest --output-on-failure")
endif()

# ═══════════════════════════════════════════════════════════════════════════════
#  Install rules
# ═══════════════════════════════════════════════════════════════════════════════

include(GNUInstallDirs)

install(TARGETS vyn_rt
    EXPORT  VynRuntimeTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(FILES ${VYN_RT_HEADERS}
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/vyn
)

if(VYN_ENABLE_ASYNC AND TARGET vyn_async)
    install(TARGETS vyn_async
        EXPORT  VynRuntimeTargets
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    )
    install(FILES vyn_async.hpp
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/vyn
    )
endif()

if(VYN_ENABLE_FFI AND TARGET vyn_ffi)
    install(TARGETS vyn_ffi
        EXPORT  VynRuntimeTargets
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    )
    install(FILES vyn_ffi.hpp
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/vyn
    )
endif()

install(EXPORT VynRuntimeTargets
    FILE      VynRuntimeTargets.cmake
    NAMESPACE Vyn::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/VynRuntime
)

# ─── CMake package config ─────────────────────────────────────────────────────
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/VynRuntimeConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/VynRuntimeConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/VynRuntime
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/VynRuntimeConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY AnyNewerVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/VynRuntimeConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/VynRuntimeConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/VynRuntime
)

# ═══════════════════════════════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════════════════════════════

message(STATUS "")
message(STATUS "=== Vyn Runtime ${PROJECT_VERSION} ===")
message(STATUS "  Build type      : ${CMAKE_BUILD_TYPE}")
message(STATUS "  C compiler      : ${CMAKE_C_COMPILER_ID} ${CMAKE_C_COMPILER_VERSION}")
message(STATUS "  C++ compiler    : ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "  Async runtime   : ${VYN_ENABLE_ASYNC}")
message(STATUS "  FFI bridge      : ${VYN_ENABLE_FFI}")
message(STATUS "  C++20 coroutines: ${VYN_ENABLE_COROUTINES}")
message(STATUS "  Tests           : ${VYN_ENABLE_TESTS}")
message(STATUS "  Sanitizer       : ${VYN_SANITIZE}")
message(STATUS "  Shared lib      : ${VYN_BUILD_SHARED}")
message(STATUS "  Install prefix  : ${CMAKE_INSTALL_PREFIX}")
message(STATUS "")
message(STATUS "  Build commands:")
message(STATUS "    mkdir build && cd build")
message(STATUS "    cmake .. -DCMAKE_BUILD_TYPE=Release -DVYN_ENABLE_TESTS=ON")
message(STATUS "    cmake --build . --parallel")
message(STATUS "    ctest --output-on-failure")
message(STATUS "")
