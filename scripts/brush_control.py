#!/usr/bin/env python3
"""Brush on/off + emergency stop from the gamepad (or from a Bool topic).

  /joy           button A (0) toggles the brush, button B (1) = brush off + stop droid
  /brush_toggle  std_msgs/Bool   True = on, False = off   (keyboard / terminal use)
  /brush_cmd     std_msgs/Float64  brush speed in rad/s -> Gazebo joint controller
  /brush_state   std_msgs/Bool     current state (latched)
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool, Float64


class BrushControl(Node):
    def __init__(self):
        super().__init__("brush_control")
        self.speed = self.declare_parameter("brush_speed", 25.0).value
        self.btn_toggle = self.declare_parameter("toggle_button", 0).value
        self.btn_stop = self.declare_parameter("stop_button", 1).value
        self.on = False
        self.prev = {}
        self.cmd_pub = self.create_publisher(Float64, "/brush_cmd", 10)
        self.vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.state_pub = self.create_publisher(Bool, "/brush_state", latched)
        self.create_subscription(Joy, "/joy", self.on_joy, 10)
        self.create_subscription(Bool, "/brush_toggle", lambda m: self.set(m.data), 10)
        self.set(False)

    def set(self, on):
        self.on = bool(on)
        self.cmd_pub.publish(Float64(data=self.speed if self.on else 0.0))
        self.state_pub.publish(Bool(data=self.on))
        self.get_logger().info(f"Brush {'ON' if self.on else 'OFF'}")

    def pressed(self, msg, idx):
        now = len(msg.buttons) > idx and msg.buttons[idx] == 1
        was = self.prev.get(idx, False)
        self.prev[idx] = now
        return now and not was

    def on_joy(self, msg):
        if self.pressed(msg, self.btn_toggle):
            self.set(not self.on)
        if self.pressed(msg, self.btn_stop):
            self.set(False)
            self.vel_pub.publish(Twist())
            self.get_logger().warn("STOP pressed: brush off, droid halted")


def main():
    rclpy.init()
    node = BrushControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
