"""Start the rural-village world, bridge, cleaning monitor and (optionally) gamepad control.

  ros2 launch solarbot_sim sim.launch.py            # gamepad nodes on
  ros2 launch solarbot_sim sim.launch.py gamepad:=false
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("solarbot_sim")
    gz_share = get_package_share_directory("ros_gz_sim")
    models = os.path.join(pkg, "models")
    world = os.path.join(pkg, "worlds", "village.sdf")

    return LaunchDescription([
        DeclareLaunchArgument("gamepad", default_value="true"),
        SetEnvironmentVariable(
            "GZ_SIM_RESOURCE_PATH",
            models + os.pathsep + os.environ.get("GZ_SIM_RESOURCE_PATH", "")),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gz_share, "launch", "gz_sim.launch.py")),
            launch_arguments={"gz_args": f"-r {world}"}.items()),
        Node(package="ros_gz_bridge", executable="parameter_bridge", output="screen",
             parameters=[{"config_file": os.path.join(pkg, "config", "bridge.yaml")}]),
        Node(package="solarbot_sim", executable="cleaning_monitor.py", name="cleaning_monitor",
             output="screen",
             parameters=[{"panels_file": os.path.join(pkg, "config", "panels.yaml")}]),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg, "launch", "teleop.launch.py")),
            condition=IfCondition(LaunchConfiguration("gamepad"))),
    ])
