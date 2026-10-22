"""Gamepad control: joy -> teleop_twist_joy -> /cmd_vel, plus brush toggle."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory("solarbot_sim")
    return LaunchDescription([
        DeclareLaunchArgument("joy_device", default_value="0"),
        Node(package="joy", executable="joy_node", name="joy_node",
             parameters=[{"device_id": LaunchConfiguration("joy_device"), "deadzone": 0.1}]),
        Node(package="teleop_twist_joy", executable="teleop_node", name="teleop_twist_joy_node",
             parameters=[os.path.join(pkg, "config", "gamepad.yaml")]),
        Node(package="solarbot_sim", executable="brush_control.py", name="brush_control",
             output="screen"),
    ])
