cmake_minimum_required(VERSION 3.16)
project(gz_pose_writer LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(gz-transport13 REQUIRED)
find_package(gz-msgs10 REQUIRED)
add_executable(gz_pose_writer gz_pose_writer.cpp)
target_link_libraries(gz_pose_writer PRIVATE
  gz-transport13::gz-transport13 gz-msgs10::gz-msgs10)
