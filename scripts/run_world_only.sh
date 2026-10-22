#!/usr/bin/env bash
# Open the world in Gazebo without ROS (quick look at the models).
cd "$(dirname "$0")/.." || exit 1
export GZ_SIM_RESOURCE_PATH="$PWD/models:$GZ_SIM_RESOURCE_PATH"
gz sim -r worlds/village.sdf
