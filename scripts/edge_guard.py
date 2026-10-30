#!/usr/bin/env python3
"""Roof edge guard: the droid cannot be driven off the panel array.

  teleop (/cmd_vel_raw) --> edge_guard --> /cmd_vel --> Gazebo droid

Uses the droid's world pose and config/panels.yaml. On a roof, any command that would push part of
the droid's footprint past the edge of the panel array is cancelled (backing away stays possible).
Off a roof (e.g. droid on the ground) commands pass straight through.
  /solarbot/edge_guard  std_msgs/Bool  True while a command is being blocked
Parameters: enabled (true), input_topic (/cmd_vel_raw), output_topic (/cmd_vel), panels_file
"""
import yaml
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
from tf2_msgs.msg import TFMessage
from edge_logic import Array, filter_cmd


class EdgeGuard(Node):
    def __init__(self):
        super().__init__("edge_guard")
        path = self.declare_parameter("panels_file", "config/panels.yaml").value
        self.enabled = self.declare_parameter("enabled", True).value
        self.droid = self.declare_parameter("droid_name", "solarbot").value
        src = self.declare_parameter("input_topic", "/cmd_vel_raw").value
        dst = self.declare_parameter("output_topic", "/cmd_vel").value
        with open(path) as fh:
            self.array = Array(yaml.safe_load(fh)["panels"])
        self.raw = Twist()
        self.pose = None
        self.sent_nonzero = False
        self.was_blocking = False
        self.out = self.create_publisher(Twist, dst, 10)
        self.flag = self.create_publisher(Bool, "/solarbot/edge_guard", 10)
        self.create_subscription(Twist, src, lambda m: setattr(self, "raw", m), 10)
        self.create_subscription(TFMessage, "/solarbot/world_pose", self.on_pose, 10)
        self.create_timer(0.05, self.tick)
        self.get_logger().info(f"Edge guard {'ON' if self.enabled else 'OFF'}: {src} -> {dst}")

    def on_pose(self, msg):
        for t in msg.transforms:
            if t.child_frame_id.replace("::", "/").split("/")[-1] == self.droid:
                tr, r = t.transform.translation, t.transform.rotation
                self.pose = ((tr.x, tr.y, tr.z), (r.x, r.y, r.z, r.w))

    def tick(self):
        lin, ang = self.raw.linear.x, self.raw.angular.z
        why = None
        if self.enabled and self.pose is not None:
            lin, ang, why = filter_cmd(self.array, self.pose[0], self.pose[1], lin, ang)
        if why:
            self.get_logger().warn(f"EDGE GUARD: {why}", throttle_duration_sec=2.0)
        if (why is not None) != self.was_blocking:
            self.was_blocking = why is not None
            self.flag.publish(Bool(data=self.was_blocking))
        nonzero = lin != 0.0 or ang != 0.0
        if nonzero or self.sent_nonzero:          # stay silent while idle
            msg = Twist()
            msg.linear.x, msg.angular.z = lin, ang
            self.out.publish(msg)
        self.sent_nonzero = nonzero


def main():
    rclpy.init()
    node = EdgeGuard()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
