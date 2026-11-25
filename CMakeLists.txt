cmake_minimum_required(VERSION 3.24)
project(VOLTA_ROOT VERSION 0.1.0 LANGUAGES CXX)

# 顶层只做一件事：把 src/ 作为子工程
add_subdirectory(src)
