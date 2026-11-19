#!/usr/bin/env python3
"""SolarBot Real-Time PV Inspection ROS 2 Node.

Subscribes to panel poses and camera images, processes surface condition with
the AI/ML model, logs defect reports, publishes to /solarbot/inspection_report,
and coordinates autonomous brush activation / crack safety halts.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y, @n02531833y-afk)
Electricity Group 2 · NUST · SolarBot 3-Wheeled Cleaning Droid
"""

import json
import math
import os
import sys
import time

# Ensure ai_inspection module is on python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool, Float32, String
from tf2_msgs.msg import TFMessage

from ai_inspection.config import (
    ACTION_NAMES,
    CLASS_NAMES,
    DefectClass,
    InspectionConfig,
    RobotAction,
)
from ai_inspection.dataset_generator import SolarPanelDatasetGenerator
from ai_inspection.model import SolarBotInspector


class SolarBotInspectionNode(Node):
    """ROS 2 node that runs PV surface defect inspection during droid navigation."""

    def __init__(self):
        super().__init__("inspection_node")

        # Declare parameters
        self.weights_path = self.declare_parameter(
            "weights_path",
            os.path.join(PROJECT_ROOT, "ai_inspection/weights/inspection_model.joblib"),
        ).value
        self.auto_brush = self.declare_parameter("auto_brush_control", True).value
        self.droid_name = self.declare_parameter("droid_name", "solarbot").value
        self.inspection_hz = self.declare_parameter("inspection_rate_hz", 2.0).value

        # Load or initialize model
        self.config = InspectionConfig(weights_path=self.weights_path)
        if os.path.exists(self.weights_path):
            self.get_logger().info(f"Loading trained inspection weights: {self.weights_path}")
            self.inspector = SolarBotInspector.load(self.weights_path)
        else:
            self.get_logger().warn(
                f"Weights not found at {self.weights_path}! Training lightweight model..."
            )
            from ai_inspection.train import train_inspection_model
            self.inspector, _ = train_inspection_model(samples_per_class=120, weights_path=self.weights_path)

        self.dataset_gen = SolarPanelDatasetGenerator(self.config)

        # State tracking
        self.current_panel_id = "unknown"
        self.brush_active = False
        self.crack_alert_latched = False

        # Subscriptions
        latched_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Bool, "/brush_state", self._on_brush_state, latched_qos)
        self.create_subscription(TFMessage, "/solarbot/world_pose", self._on_pose, 10)

        # Publishers
        self.report_pub = self.create_publisher(String, "/solarbot/inspection_report", 10)
        self.crack_pub = self.create_publisher(Bool, "/solarbot/crack_alert", latched_qos)
        self.brush_pub = self.create_publisher(Bool, "/brush_toggle", 10)

        # Periodic inspection timer (runs at inspection_rate_hz)
        timer_period = 1.0 / max(0.1, float(self.inspection_hz))
        self.timer = self.create_timer(timer_period, self._run_inspection_cycle)

        self.get_logger().info(
            f"SolarBot Inspection Node initialized at {self.inspection_hz} Hz. Auto-brush: {self.auto_brush}"
        )

    def _on_brush_state(self, msg: Bool):
        self.brush_active = msg.data

    def _on_pose(self, msg: TFMessage):
        """Estimate current panel location from droid world pose."""
        for t in msg.transforms:
            child = t.child_frame_id.replace("::", "/").split("/")[-1]
            if child == self.droid_name:
                px = t.transform.translation.x
                py = t.transform.translation.y
                # Approximation of panel ID tag based on coordinates
                self.current_panel_id = f"panel_at_({px:.1f},{py:.1f})"

    def _run_inspection_cycle(self):
        """Simulate real-time camera ingestion and neural inspection."""
        # In hardware / full camera sim, incoming image comes from sensor_msgs/Image.
        # Here we sample an operational frame representing rooftop conditions:
        sim_sample = self.dataset_gen.generate_sample(
            defect_class=DefectClass.DUSTY if self.brush_active else DefectClass.CLEAN
        )
        img = sim_sample["image"]

        # Run inference
        t0 = time.perf_counter()
        res = self.inspector.predict_image(img)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        cls_name = res["class_name"]
        dust_pct = res["dust_density_percent"]
        crack_detected = res["crack_detected"]
        action = RobotAction(res["recommended_action"])

        # Construct structured telemetry report
        report_data = {
            "timestamp": time.time(),
            "panel_id": self.current_panel_id,
            "condition": cls_name,
            "confidence": round(res["confidence"], 3),
            "dust_density_percent": dust_pct,
            "crack_detected": crack_detected,
            "crack_severity": round(res["crack_severity"], 3),
            "recommended_action": ACTION_NAMES[action],
            "latency_ms": round(latency_ms, 2),
        }

        # Publish report
        msg = String()
        msg.data = json.dumps(report_data)
        self.report_pub.publish(msg)

        # Safety arbitration
        if crack_detected and not self.crack_alert_latched:
            self.crack_alert_latched = True
            self.get_logger().error(
                f"SAFETY CRITICAL [W-04]: Crack detected on {self.current_panel_id}! Stopping brush!"
            )
            self.crack_pub.publish(Bool(data=True))
            if self.auto_brush:
                self.brush_pub.publish(Bool(data=False))

        elif not crack_detected and self.auto_brush:
            if action == RobotAction.ACTIVATE_BRUSH and not self.brush_active:
                self.get_logger().info(f"Dust threshold exceeded ({dust_pct}%). Auto-triggering brush ON.")
                self.brush_pub.publish(Bool(data=True))


def main(args=None):
    rclpy.init(args=args)
    node = SolarBotInspectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
