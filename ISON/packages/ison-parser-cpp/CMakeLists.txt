cmake_minimum_required(VERSION 3.14)
project(ison_parser
    VERSION 1.0.0
    DESCRIPTION "ISON v1.0 Parser - Interchange Simple Object Notation for C++"
    LANGUAGES CXX
)

# C++11 minimum (C++17 optional for std::optional)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(ISON_BUILD_TESTS "Build tests" ON)
option(ISON_BUILD_EXAMPLES "Build examples" ON)
option(ISON_INSTALL "Install headers" ON)

# Header-only library
add_library(ison_parser INTERFACE)
add_library(ison::parser ALIAS ison_parser)

target_include_directories(ison_parser
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(ison_parser INTERFACE cxx_std_11)

# Tests
if(ISON_BUILD_TESTS)
    enable_testing()
    add_executable(test_ison_parser tests/test_ison_parser.cpp)
    target_link_libraries(test_ison_parser PRIVATE ison_parser)

    # Add compiler warnings
    if(MSVC)
        target_compile_options(test_ison_parser PRIVATE /W4)
    else()
        target_compile_options(test_ison_parser PRIVATE -Wall -Wextra -Wpedantic)
    endif()

    add_test(NAME ison_parser_tests COMMAND test_ison_parser)
endif()

# Examples
if(ISON_BUILD_EXAMPLES)
    add_executable(ison_example examples/example.cpp)
    target_link_libraries(ison_example PRIVATE ison_parser)
endif()

# Installation
if(ISON_INSTALL)
    include(GNUInstallDirs)

    install(TARGETS ison_parser
        EXPORT ison_parserTargets
        INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    )

    install(FILES include/ison_parser.hpp
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    )

    install(EXPORT ison_parserTargets
        FILE ison_parserTargets.cmake
        NAMESPACE ison::
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ison_parser
    )

    # Package config
    include(CMakePackageConfigHelpers)

    configure_package_config_file(
        ${CMAKE_CURRENT_SOURCE_DIR}/cmake/ison_parserConfig.cmake.in
        ${CMAKE_CURRENT_BINARY_DIR}/ison_parserConfig.cmake
        INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ison_parser
    )

    write_basic_package_version_file(
        ${CMAKE_CURRENT_BINARY_DIR}/ison_parserConfigVersion.cmake
        VERSION ${PROJECT_VERSION}
        COMPATIBILITY SameMajorVersion
    )

    install(FILES
        ${CMAKE_CURRENT_BINARY_DIR}/ison_parserConfig.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/ison_parserConfigVersion.cmake
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ison_parser
    )
endif()
