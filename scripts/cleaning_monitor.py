#!/usr/bin/env python3
"""Tracks how much of each rooftop panel the spinning brush has swept.

Uses the droid's world pose (/solarbot/world_pose) and the panel table in
config/panels.yaml. Each panel is a 5 cm grid; a cell counts as cleaned when the
brush is ON and its footprint passes over it. Logs when a panel reaches 95 %
(SRS PERF-2) and publishes:
  /solarbot/cleaning_status   std_msgs/String   one line per panel that has been touched
  /solarbot/panel_coverage    std_msgs/Float32  coverage of the panel under the brush (0-1)
NOTE: the dust film you see in Gazebo is static; this node does the bookkeeping.
"""
import math
import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import Bool, Float32, String
from tf2_msgs.msg import TFMessage

CELL = 0.05
BRUSH_X = 0.085                                # brush axis ahead of the droid origin
BRUSH_Y = (-0.05, -0.025, 0.0, 0.025, 0.05)    # samples along the 10 cm brush
SURFACE_TOL = 0.06                             # brush must be within 6 cm of the panel surface


def rot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


def conj(q):
    return (-q[0], -q[1], -q[2], q[3])


class Panel:
    def __init__(self, d):
        self.id, self.c, self.q = d["id"], d["center"], tuple(d["quat"])
        self.sx, self.sy = d["size"]
        self.nx, self.ny = math.ceil(self.sx / CELL), math.ceil(self.sy / CELL)
        self.done = set()
        self.reported = False

    @property
    def coverage(self):
        return len(self.done) / float(self.nx * self.ny)


class CleaningMonitor(Node):
    def __init__(self):
        super().__init__("cleaning_monitor")
        path = self.declare_parameter("panels_file", "config/panels.yaml").value
        self.droid = self.declare_parameter("droid_name", "solarbot").value
        with open(path) as fh:
            self.panels = [Panel(d) for d in yaml.safe_load(fh)["panels"]]
        self.brush_on = False
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Bool, "/brush_state",
                                 lambda m: setattr(self, "brush_on", m.data), latched)
        self.create_subscription(TFMessage, "/solarbot/world_pose", self.on_pose, 10)
        self.status_pub = self.create_publisher(String, "/solarbot/cleaning_status", 10)
        self.cov_pub = self.create_publisher(Float32, "/solarbot/panel_coverage", 10)
        self.create_timer(1.0, self.publish_status)
        self.get_logger().info(f"Tracking {len(self.panels)} panels")

    def on_pose(self, msg):
        pose = None
        for t in msg.transforms:
            if t.child_frame_id.replace("::", "/").split("/")[-1] == self.droid:
                pose = t.transform
        if pose is None or not self.brush_on:
            return
        p = (pose.translation.x, pose.translation.y, pose.translation.z)
        q = (pose.rotation.x, pose.rotation.y, pose.rotation.z, pose.rotation.w)
        under = None
        for by in BRUSH_Y:
            off = rot(q, (BRUSH_X, by, 0.0))
            w = (p[0] + off[0], p[1] + off[1], p[2] + off[2])
            for pan in self.panels:
                if abs(w[0] - pan.c[0]) > 1.2 or abs(w[1] - pan.c[1]) > 1.2:
                    continue
                l = rot(conj(pan.q), (w[0] - pan.c[0], w[1] - pan.c[1], w[2] - pan.c[2]))
                if abs(l[0]) <= pan.sx / 2 and abs(l[1]) <= pan.sy / 2 and abs(l[2]) <= SURFACE_TOL:
                    cx = min(pan.nx - 1, int((l[0] + pan.sx / 2) / CELL))
                    cy = min(pan.ny - 1, int((l[1] + pan.sy / 2) / CELL))
                    pan.done.add((cx, cy))
                    under = pan
        if under is not None:
            self.cov_pub.publish(Float32(data=float(under.coverage)))
            if under.coverage >= 0.95 and not under.reported:
                under.reported = True
                self.get_logger().info(
                    f"{under.id}: cleaning complete ({under.coverage * 100:.0f}% coverage)")

    def publish_status(self):
        lines = [f"{p.id}: {p.coverage * 100:.0f}%" for p in self.panels if p.done]
        if lines:
            self.status_pub.publish(String(data="; ".join(lines)))


def main():
    rclpy.init()
    node = CleaningMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
