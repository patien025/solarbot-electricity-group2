#!/usr/bin/env python3
"""Put the droid on a chosen rooftop panel (the 'technician places the droid' step).

  ros2 run solarbot_sim place_droid.py modern_2_panel_r1_c0
  ros2 run solarbot_sim place_droid.py --list
Works without ROS too:  python3 scripts/place_droid.py thatched_1_panel_r0_c0
You can also drag the droid by hand with Gazebo's Transform Control tool.
"""
import os
import subprocess
import sys
import yaml


def find_panels_file():
    here = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(here, "..", "config", "panels.yaml")
    if os.path.exists(local):
        return local
    try:
        from ament_index_python.packages import get_package_share_directory
        return os.path.join(get_package_share_directory("solarbot_sim"), "config", "panels.yaml")
    except Exception:
        sys.exit("panels.yaml not found")


def rot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def main():
    panels = {d["id"]: d for d in yaml.safe_load(open(find_panels_file()))["panels"]}
    if len(sys.argv) < 2 or sys.argv[1] in ("--list", "-l"):
        print("\n".join(panels))
        return
    d = panels.get(sys.argv[1])
    if d is None:
        sys.exit(f"unknown panel '{sys.argv[1]}' (use --list)")
    q = tuple(d["quat"])
    off = rot(q, (0.0, 0.0, 0.015 + 0.004))          # panel surface + small lift
    c = [d["center"][i] + off[i] for i in range(3)]
    req = (f'name: "solarbot", position: {{x: {c[0]:.4f}, y: {c[1]:.4f}, z: {c[2]:.4f}}}, '
           f'orientation: {{x: {q[0]:.6f}, y: {q[1]:.6f}, z: {q[2]:.6f}, w: {q[3]:.6f}}}')
    cmd = ["gz", "service", "-s", "/world/village/set_pose", "--reqtype", "gz.msgs.Pose",
           "--reptype", "gz.msgs.Boolean", "--timeout", "2000", "--req", req]
    print("Placing droid on", d["id"])
    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
