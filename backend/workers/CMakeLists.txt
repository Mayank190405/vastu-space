cmake_minimum_required(VERSION 3.10)
project(VastuSpatialWorkers VERSION 1.0)

# Specify C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Find OpenCV
find_package(OpenCV REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

# Find OpenMP
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${OpenMP_EXE_LINKER_FLAGS}")
endif()

# Build Camera Tracker
add_executable(camera_tracker tracking/camera_tracker.cpp)
target_link_libraries(camera_tracker ${OpenCV_LIBS})

# Build Video Preprocessor
add_executable(video_preprocessor preprocessing/video_preprocessor.cpp)
target_link_libraries(video_preprocessor ${OpenCV_LIBS})

# Build Dense Point Cloud Fuser
add_executable(dense_pointcloud_fuser pointcloud/dense_pointcloud_fuser.cpp)
# Note: open3d is handled via Python in the pipeline, but the native fuser uses standard C++ + OpenMP
if(OpenMP_CXX_FOUND)
    target_link_libraries(dense_pointcloud_fuser OpenMP::OpenMP_CXX)
endif()
