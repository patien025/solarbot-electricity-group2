#!/usr/bin/env python3
"""
generate_models.py  --  SolarBot / Electricity Group 2

Regenerates EVERYTHING in models/, worlds/village.sdf and config/panels.yaml.
Only SDF primitives (box, cylinder, sphere, ellipsoid) plus one tiny generated
.obj (the gable prism under the modern roof) are used, so nothing is downloaded.

    python3 tools/generate_models.py

Conventions (same as the world): +x = east, +y = north, +z = up.
Bulawayo is in the southern hemisphere, so every panel faces NORTH (+y).
"""
import math
import os
from xml.dom import minidom

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS = os.path.join(ROOT, "models")
WORLDS = os.path.join(ROOT, "worlds")
CONFIG = os.path.join(ROOT, "config")

THETA = math.radians(10.0)             # roof/panel tilt (= SRS NAV-5 slope limit)
PANEL_L, PANEL_W, PANEL_T = 1.00, 0.67, 0.03   # ~100 W module (x, slope, thickness)
PANEL_TOP = PANEL_T / 2                # collision surface above the panel origin
DROID_LIFT = 0.004                     # spawn the droid this far above the panel

# --------------------------------------------------------------------------- #
# small SDF helpers
# --------------------------------------------------------------------------- #
def n(v):
    return f"{v:.4f}"


def P(x=0.0, y=0.0, z=0.0, r=0.0, p=0.0, w=0.0):
    return " ".join(n(v) for v in (x, y, z, r, p, w))


def BOX(x, y, z):
    return f"<box><size>{n(x)} {n(y)} {n(z)}</size></box>"


def CYL(r, l):
    return f"<cylinder><radius>{n(r)}</radius><length>{n(l)}</length></cylinder>"


def SPH(r):
    return f"<sphere><radius>{n(r)}</radius></sphere>"


def ELL(a, b, c):
    return f"<ellipsoid><radii>{n(a)} {n(b)} {n(c)}</radii></ellipsoid>"


def MESH(uri):
    return f"<mesh><uri>{uri}</uri></mesh>"


def material(rgb):
    r, g, b = rgb
    return (f"<material><ambient>{n(r)} {n(g)} {n(b)} 1</ambient>"
            f"<diffuse>{n(r)} {n(g)} {n(b)} 1</diffuse>"
            f"<specular>0.1 0.1 0.1 1</specular></material>")


def V(name, geom, pose, rgb, transp=0.0):
    t = f"<transparency>{n(transp)}</transparency>" if transp else ""
    return (f'<visual name="{name}"><pose>{pose}</pose><geometry>{geom}</geometry>'
            f"{material(rgb)}{t}</visual>")


def C(name, geom, pose, mu=1.0):
    return (f'<collision name="{name}"><pose>{pose}</pose><geometry>{geom}</geometry>'
            f"<surface><friction><ode><mu>{mu}</mu><mu2>{mu}</mu2></ode></friction></surface>"
            f"</collision>")


def INERTIA(m, ixx, iyy, izz):
    return (f"<inertial><mass>{m}</mass><inertia><ixx>{ixx:.6g}</ixx><ixy>0</ixy><ixz>0</ixz>"
            f"<iyy>{iyy:.6g}</iyy><iyz>0</iyz><izz>{izz:.6g}</izz></inertia></inertial>")


def pretty(xml):
    txt = minidom.parseString(xml).toprettyxml(indent="  ")
    return "\n".join(l for l in txt.splitlines() if l.strip()) + "\n"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def write_model(name, body, description, static=True):
    st = "<static>true</static>" if static else ""
    sdf = (f'<?xml version="1.0"?><sdf version="1.9"><model name="{name}">{st}{body}'
           f"</model></sdf>")
    d = os.path.join(MODELS, name)
    write(os.path.join(d, "model.sdf"), pretty(sdf))
    cfg = (f'<?xml version="1.0"?><model><name>{name}</name><version>1.0</version>'
           f'<sdf version="1.9">model.sdf</sdf>'
           f"<author><name>Electricity Group 2</name></author>"
           f"<description>{description}</description></model>")
    write(os.path.join(d, "model.config"), pretty(cfg))


def link(name, *parts, pose=None):
    ps = f"<pose>{pose}</pose>" if pose else ""
    return f'<link name="{name}">{ps}{"".join(parts)}</link>'


# --------------------------------------------------------------------------- #
# rotation helpers (quaternions are x, y, z, w)
# --------------------------------------------------------------------------- #
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def q_yaw_roll(yaw, roll):
    """SDF rpy with pitch = 0:  R = Rz(yaw) * Rx(roll)."""
    qz = (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2))
    qx = (math.sin(roll / 2), 0.0, 0.0, math.cos(roll / 2))
    return qmul(qz, qx)


def rot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


# --------------------------------------------------------------------------- #
# MODEL: solar_panel
# --------------------------------------------------------------------------- #
def make_panel():
    v = [V("frame", BOX(PANEL_L, PANEL_W, PANEL_T), P(), (0.75, 0.77, 0.80)),
         V("cells", BOX(PANEL_L - 0.04, PANEL_W - 0.04, 0.004),
           P(0, 0, PANEL_TOP + 0.0005), (0.06, 0.12, 0.38))]
    for i, x in enumerate((-0.32, -0.16, 0.0, 0.16, 0.32)):
        v.append(V(f"busbar_v{i}", BOX(0.004, PANEL_W - 0.04, 0.0006),
                   P(x, 0, PANEL_TOP + 0.0028), (0.78, 0.80, 0.88)))
    for i, y in enumerate((-0.252, -0.126, 0.0, 0.126, 0.252)):
        v.append(V(f"busbar_h{i}", BOX(PANEL_L - 0.04, 0.004, 0.0006),
                   P(0, y, PANEL_TOP + 0.0028), (0.78, 0.80, 0.88)))
    # translucent dust film (what the droid is there to clean)
    v.append(V("dust", BOX(PANEL_L - 0.04, PANEL_W - 0.04, 0.0012),
               P(0, 0, PANEL_TOP + 0.0038), (0.78, 0.68, 0.50), transp=0.55))
    body = link("panel_link", C("surface", BOX(PANEL_L, PANEL_W, PANEL_T), P(), 1.5), *v)
    write_model("solar_panel", body,
                "100 W class PV module, 1.00 x 0.67 m, with a light dust film.")


# --------------------------------------------------------------------------- #
# MODEL: solarbot_droid   (the low-cost build from the project sheet)
# --------------------------------------------------------------------------- #
def make_droid():
    wr, wy, pz = 0.035, 0.0625, 0.05     # wheel radius, wheel y offset, plate height
    ROLL = -math.pi / 2                  # cylinder axis (z) -> +y

    # --- chassis -----------------------------------------------------------
    b = [INERTIA(0.45, 5.7e-4, 9.7e-4, 1.23e-3),
         C("plate_col", BOX(0.14, 0.10, 0.008), P(), 0.8),
         V("plate", BOX(0.14, 0.10, 0.008), P(), (0.80, 0.63, 0.40))]
    for s, nm in ((1, "left"), (-1, "right")):
        b.append(V(f"{nm}_gear_motor", BOX(0.065, 0.022, 0.018), P(0, s * 0.040, -0.015),
                   (0.95, 0.80, 0.10)))
    b.append(V("battery_pack", BOX(0.065, 0.035, 0.022), P(-0.036, 0, 0.015), (0.08, 0.08, 0.09)))
    b.append(V("battery_label", BOX(0.040, 0.020, 0.001), P(-0.036, 0, 0.0265), (0.85, 0.15, 0.10)))
    b.append(V("arduino_nano", BOX(0.045, 0.018, 0.003), P(0.0, -0.028, 0.0075), (0.10, 0.25, 0.65)))
    b.append(V("nano_chip", BOX(0.010, 0.010, 0.003), P(0.0, -0.028, 0.0105), (0.05, 0.05, 0.05)))
    b.append(V("nano_usb", BOX(0.008, 0.009, 0.004), P(-0.0225, -0.028, 0.0105), (0.75, 0.75, 0.78)))
    b.append(V("l298n_board", BOX(0.043, 0.043, 0.002), P(0.020, 0.022, 0.006), (0.80, 0.10, 0.10)))
    b.append(V("l298n_heatsink", BOX(0.020, 0.030, 0.020), P(0.020, 0.022, 0.017), (0.05, 0.05, 0.05)))
    for k in (-1, 1):
        b.append(V(f"l298n_terminal{k}", BOX(0.008, 0.012, 0.010), P(0.020 + k * 0.016, 0.022, 0.012),
                   (0.10, 0.30, 0.85)))
    # brush arms + brush motor (brush axis is at x=0.085, z=0.026 -> -0.024 below plate centre)
    for s in (1, -1):
        b.append(V(f"brush_arm{s}", BOX(0.025, 0.004, 0.035), P(0.0775, s * 0.052, -0.0125),
                   (0.45, 0.45, 0.48)))
    b.append(V("brush_motor", CYL(0.011, 0.024), P(0.085, 0.066, -0.024, ROLL, 0, 0), (0.62, 0.62, 0.65)))
    b.append(V("caster_mount", BOX(0.030, 0.030, 0.003), P(-0.060, 0, -0.0055), (0.45, 0.45, 0.48)))
    base = link("base_link", *b, pose=P(0, 0, pz))

    # --- wheels --------------------------------------------------------------
    def wheel(name, y):
        return link(name,
                    INERTIA(0.05, 1.7e-5, 1.7e-5, 3.06e-5),
                    C("tyre_col", CYL(wr, 0.020), P(), 1.5),
                    V("tyre", CYL(wr, 0.020), P(), (0.05, 0.05, 0.05)),
                    V("hub", CYL(0.024, 0.0215), P(), (0.95, 0.80, 0.10)),
                    pose=P(0, y, wr, ROLL, 0, 0))

    # --- caster ----------------------------------------------------------------
    caster = link("caster",
                  INERTIA(0.01, 1.2e-6, 1.2e-6, 1.2e-6),
                  C("ball_col", SPH(0.0175), P(), 0.0),
                  V("ball", SPH(0.0175), P(), (0.60, 0.60, 0.62)),
                  V("fork", CYL(0.006, 0.030), P(0, 0, 0.015), (0.45, 0.45, 0.48)),
                  pose=P(-0.060, 0, 0.0175))

    # --- rotating brush ---------------------------------------------------------
    bristles = [V(f"bristle{k}", BOX(0.050, 0.004, 0.096), P(0, 0, 0, 0, 0, k * math.pi / 6),
                  (0.10, 0.35, 0.95)) for k in range(6)]
    brush = link("brush",
                 INERTIA(0.03, 2.97e-5, 2.97e-5, 9.4e-6),
                 V("core", CYL(0.012, 0.100), P(), (0.08, 0.25, 0.80)),
                 V("shaft", CYL(0.004, 0.112), P(), (0.70, 0.70, 0.72)),
                 *bristles,
                 pose=P(0.085, 0, 0.026, ROLL, 0, 0))   # visual only: no collision

    def rev(name, parent, child):
        return (f'<joint name="{name}" type="revolute"><parent>{parent}</parent><child>{child}</child>'
                f"<axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit>"
                f"<dynamics><damping>0.0005</damping></dynamics></axis></joint>")

    joints = (rev("left_wheel_joint", "base_link", "left_wheel")
              + rev("right_wheel_joint", "base_link", "right_wheel")
              + rev("brush_joint", "base_link", "brush")
              + '<joint name="caster_joint" type="fixed"><parent>base_link</parent>'
                "<child>caster</child></joint>")

    plugins = """
<plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
  <left_joint>left_wheel_joint</left_joint>
  <right_joint>right_wheel_joint</right_joint>
  <wheel_separation>0.125</wheel_separation>
  <wheel_radius>0.035</wheel_radius>
  <odom_publish_frequency>30</odom_publish_frequency>
  <topic>/cmd_vel</topic>
  <odom_topic>/odom</odom_topic>
  <tf_topic>/tf</tf_topic>
  <frame_id>odom</frame_id>
  <child_frame_id>base_link</child_frame_id>
  <max_linear_velocity>0.4</max_linear_velocity>
  <max_angular_velocity>3.0</max_angular_velocity>
</plugin>
<plugin filename="gz-sim-joint-controller-system" name="gz::sim::systems::JointController">
  <joint_name>brush_joint</joint_name>
  <topic>/brush_cmd</topic>
</plugin>
<plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher"/>
<plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher">
  <publish_link_pose>false</publish_link_pose>
  <publish_model_pose>true</publish_model_pose>
  <publish_nested_model_pose>false</publish_nested_model_pose>
  <use_pose_vector_msg>true</use_pose_vector_msg>
  <update_frequency>20</update_frequency>
</plugin>"""
    body = base + wheel("left_wheel", wy) + wheel("right_wheel", -wy) + caster + brush + joints + plugins
    write_model("solarbot_droid", body,
                "Low-cost SolarBot droid: 2 geared DC motors, rear caster, front rotating brush, "
                "Arduino Nano, L298N, 7.4 V pack. About 20 x 15 x 10 cm. Teleoperated.",
                static=False)


# --------------------------------------------------------------------------- #
# MODEL: house_modern   (brick/plaster walls, corrugated-iron gable roof, 6 panels)
# --------------------------------------------------------------------------- #
def write_gable_obj(path, L, W, h):
    x, y = L / 2, W / 2
    verts = [(-x, -y, 0), (x, -y, 0), (x, y, 0), (-x, y, 0), (-x, 0, h), (x, 0, h)]
    faces = [(1, 3, 2), (1, 4, 3), (1, 2, 6), (1, 6, 5), (3, 4, 5), (3, 5, 6), (2, 3, 6), (1, 5, 4)]
    txt = "# gable prism generated by tools/generate_models.py\n"
    txt += "".join(f"v {a:.4f} {b:.4f} {c:.4f}\n" for a, b, c in verts)
    txt += "".join(f"f {a} {b} {c}\n" for a, b, c in faces)
    write(path, txt)


def make_house_modern():
    L, W, H = 6.0, 4.5, 2.6
    t = (W / 2) * math.tan(THETA)
    zr = H + t                                   # ridge height
    cream, roof, white = (0.93, 0.88, 0.76), (0.58, 0.22, 0.16), (0.95, 0.95, 0.95)
    p = [C("walls_col", BOX(L, W, H), P(0, 0, H / 2)),
         V("plinth", BOX(L + 0.3, W + 0.3, 0.15), P(0, 0, 0.075), (0.55, 0.55, 0.55)),
         V("walls", BOX(L, W, H), P(0, 0, H / 2), cream),
         V("gable_fill", MESH("model://house_modern/meshes/gable.obj"), P(0, 0, H), cream),
         V("ridge_cap", BOX(L + 0.5, 0.30, 0.04), P(0, 0, zr + 0.02), (0.30, 0.30, 0.32)),
         V("door", BOX(0.90, 0.06, 2.00), P(1.5, -W / 2 - 0.005, 1.0), (0.35, 0.20, 0.10)),
         V("door_frame", BOX(1.05, 0.05, 2.10), P(1.5, -W / 2 - 0.0, 1.05), white),
         V("step", BOX(1.3, 0.4, 0.12), P(1.5, -W / 2 - 0.2, 0.06), (0.6, 0.6, 0.6))]
    for i, (x, y) in enumerate(((-1.7, W / 2), (1.7, W / 2), (-1.5, -W / 2))):
        s = 1 if y > 0 else -1
        p.append(V(f"win_frame{i}", BOX(1.10, 0.04, 1.00), P(x, y + s * 0.005, 1.5), white))
        p.append(V(f"win_glass{i}", BOX(0.95, 0.04, 0.85), P(x, y + s * 0.02, 1.5), (0.40, 0.55, 0.70)))

    s0 = -0.10
    s1 = (W / 2 + 0.30) / math.cos(THETA)
    sc, ln = (s0 + s1) / 2, s1 - s0
    for sign in (1, -1):
        nrm = (0.0, sign * math.sin(THETA), math.cos(THETA))
        surf = (0.0, sign * sc * math.cos(THETA), zr - sc * math.sin(THETA))
        ctr = tuple(surf[i] - 0.025 * nrm[i] for i in range(3))
        pose = P(*ctr, -sign * THETA, 0, 0)
        p.append(C(f"roof_col{sign}", BOX(L + 0.5, ln, 0.05), pose, 1.0))
        p.append(V(f"roof{sign}", BOX(L + 0.5, ln, 0.05), pose, roof))

    panels, incl = [], []
    for r in range(2):
        for c in range(3):
            s = 0.55 + r * 0.70
            x = (c - 1) * 1.03
            nrm = (0.0, math.sin(THETA), math.cos(THETA))
            pos = (x, s * math.cos(THETA) + PANEL_T / 2 * nrm[1],
                   zr - s * math.sin(THETA) + PANEL_T / 2 * nrm[2])
            name = f"panel_r{r}_c{c}"
            panels.append((name, pos, -THETA))
            incl.append(f"<include><uri>model://solar_panel</uri><name>{name}</name>"
                        f"<static>true</static><pose>{P(*pos, -THETA, 0, 0)}</pose></include>")
    write_gable_obj(os.path.join(MODELS, "house_modern", "meshes", "gable.obj"), L, W, t)
    write_model("house_modern", link("house", *p) + "".join(incl),
                "Modern rural house 6 x 4.5 m, corrugated-iron gable roof (10 deg), "
                "six 100 W panels on the north slope.")
    return panels


# --------------------------------------------------------------------------- #
# MODEL: house_thatched   (round rondavel, stepped thatch, panel rack on top)
# --------------------------------------------------------------------------- #
def make_house_thatched():
    zb, Hw, Rw = 0.12, 2.0, 2.0
    p = [V("plinth", CYL(2.2, zb), P(0, 0, zb / 2), (0.55, 0.55, 0.55)),
         C("wall_col", CYL(Rw, Hw), P(0, 0, zb + Hw / 2)),
         V("wall", CYL(Rw, Hw), P(0, 0, zb + Hw / 2), (0.78, 0.55, 0.36)),
         V("wall_band", CYL(Rw + 0.01, 0.25), P(0, 0, zb + 0.125), (0.45, 0.30, 0.20))]
    z_top = zb + Hw
    for k in range(5):
        r, h = 2.8 - 0.45 * k, 0.4
        z = z_top + h / 2 + k * h
        col = (0.80, 0.67, 0.31) if k % 2 == 0 else (0.70, 0.57, 0.25)
        p.append(C(f"thatch_col{k}", CYL(r, h), P(0, 0, z), 1.0))
        p.append(V(f"thatch{k}", CYL(r, h), P(0, 0, z), col))
    z_top += 5 * 0.4                                   # flat thatch crown, radius 1.0
    # door + two windows
    p.append(V("door", BOX(0.85, 0.12, 1.70), P(0, -Rw, zb + 0.85), (0.30, 0.18, 0.10)))
    for i, phi in enumerate((math.radians(30), math.radians(150))):
        p.append(V(f"window{i}", BOX(0.50, 0.12, 0.50),
                   P(Rw * math.cos(phi), Rw * math.sin(phi), 1.5, 0, 0, phi - math.pi / 2),
                   (0.18, 0.13, 0.10)))
    # timber rack carrying two panels, tilted 10 deg to the north
    zc = z_top + 0.28
    nrm = (0.0, math.sin(THETA), math.cos(THETA))
    u = (0.0, math.cos(THETA), -math.sin(THETA))         # down-slope direction
    panels, incl = [], []
    for r, d in enumerate((-0.345, 0.345)):
        pos = (0.0, d * u[1] + PANEL_T / 2 * nrm[1], zc + d * u[2] + PANEL_T / 2 * nrm[2])
        name = f"panel_r{r}_c0"
        panels.append((name, pos, -THETA))
        incl.append(f"<include><uri>model://solar_panel</uri><name>{name}</name>"
                    f"<static>true</static><pose>{P(*pos, -THETA, 0, 0)}</pose></include>")
    for i, (px, py) in enumerate(((-0.4, -0.5), (0.4, -0.5), (-0.4, 0.5), (0.4, 0.5))):
        zt = zc - py * math.tan(THETA)
        length = zt - z_top
        p.append(V(f"rack_post{i}", CYL(0.025, length), P(px, py, z_top + length / 2), (0.40, 0.28, 0.15)))
    write_model("house_thatched", link("house", *p) + "".join(incl),
                "Round thatched rondavel (4 m diameter walls) with a flat thatch crown "
                "carrying a timber rack and two 100 W panels.")
    return panels


# --------------------------------------------------------------------------- #
# MODELS: ladder, technician, water_tank, trees, dirt_path
# --------------------------------------------------------------------------- #
def make_ladder():
    p = [V("rail_l", BOX(0.04, 0.04, 2.8), P(-0.22, 0, 1.4), (0.70, 0.70, 0.72)),
         V("rail_r", BOX(0.04, 0.04, 2.8), P(0.22, 0, 1.4), (0.70, 0.70, 0.72)),
         C("col", BOX(0.5, 0.06, 2.8), P(0, 0, 1.4), 1.0)]
    for i in range(9):
        p.append(V(f"rung{i}", BOX(0.44, 0.03, 0.03), P(0, 0, 0.3 + 0.3 * i), (0.70, 0.70, 0.72)))
    write_model("ladder", link("ladder", *p), "2.8 m aluminium ladder (modelled upright; tilt it in the world).")


def make_technician():
    skin, jeans, vest = (0.38, 0.24, 0.16), (0.15, 0.20, 0.38), (0.95, 0.50, 0.08)
    p = [V("leg_l", CYL(0.065, 0.85), P(0, 0.09, 0.425), jeans),
         V("leg_r", CYL(0.065, 0.85), P(0, -0.09, 0.425), jeans),
         V("torso", BOX(0.22, 0.38, 0.62), P(0, 0, 1.16), vest),
         V("head", SPH(0.11), P(0, 0, 1.60), skin),
         V("neck", CYL(0.04, 0.08), P(0, 0, 1.49), skin),
         V("upper_arm_l", CYL(0.045, 0.30), P(0, 0.235, 1.22), vest),
         V("upper_arm_r", CYL(0.045, 0.30), P(0, -0.235, 1.22), vest),
         V("fore_arm_l", CYL(0.04, 0.30), P(0.15, 0.20, 1.07, 0, math.pi / 2, 0), skin),
         V("fore_arm_r", CYL(0.04, 0.30), P(0.15, -0.20, 1.07, 0, math.pi / 2, 0), skin),
         V("controller", BOX(0.06, 0.17, 0.03), P(0.34, 0, 1.07), (0.07, 0.07, 0.08)),
         V("stick_l", CYL(0.012, 0.015), P(0.34, 0.04, 1.095), (0.5, 0.5, 0.5)),
         V("stick_r", CYL(0.012, 0.015), P(0.34, -0.04, 1.095), (0.5, 0.5, 0.5)),
         C("col", BOX(0.3, 0.45, 1.7), P(0, 0, 0.85), 1.0)]
    write_model("technician", link("body", *p),
                "Village technician holding the gamepad (faces +x).")


def make_water_tank():
    p = [V(f"post{i}", CYL(0.05, 1.8), P(x, y, 0.9), (0.45, 0.45, 0.48))
         for i, (x, y) in enumerate(((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)))]
    p += [V("platform", BOX(1.7, 1.7, 0.08), P(0, 0, 1.84), (0.40, 0.28, 0.15)),
          V("tank", CYL(0.80, 1.4), P(0, 0, 2.58), (0.08, 0.10, 0.12)),
          V("lid", CYL(0.30, 0.06), P(0, 0, 3.31), (0.10, 0.12, 0.15)),
          C("col", BOX(1.7, 1.7, 3.3), P(0, 0, 1.65), 1.0)]
    write_model("water_tank", link("tank", *p), "Village water tank on a timber stand.")


def make_tree(name, scale):
    s = scale
    p = [V("trunk", CYL(0.17 * s, 3.0 * s), P(0, 0, 1.5 * s), (0.35, 0.25, 0.16)),
         C("trunk_col", CYL(0.17 * s, 3.0 * s), P(0, 0, 1.5 * s), 1.0),
         V("canopy1", ELL(2.4 * s, 2.4 * s, 0.8 * s), P(0, 0, 3.6 * s), (0.26, 0.38, 0.16)),
         V("canopy2", ELL(1.6 * s, 1.6 * s, 0.6 * s), P(0.4 * s, 0.3 * s, 4.1 * s), (0.30, 0.43, 0.18))]
    write_model(name, link("tree", *p), "Flat-topped acacia / msasa style tree.")


def make_path():
    p = [V("path", BOX(60, 2.2, 0.01), P(0, 0, 0.005), (0.62, 0.50, 0.35))]
    write_model("dirt_path", link("path", *p), "Dirt road through the village (visual only).")


# --------------------------------------------------------------------------- #
# WORLD + panel table
# --------------------------------------------------------------------------- #
HOUSES = [  # name, model, x, y, yaw
    ("modern_1", "house_modern", 0.0, 0.0, 0.0),
    ("thatched_1", "house_thatched", 12.0, 4.0, 0.20),
    ("thatched_2", "house_thatched", -11.0, 3.0, -0.15),
    ("modern_2", "house_modern", -4.0, -15.0, 0.08),
    ("thatched_3", "house_thatched", 10.0, -12.0, 0.10),
    ("thatched_4", "house_thatched", 22.0, -4.0, 0.0),
    ("modern_3", "house_modern", -20.0, -8.0, 0.12),
]
TREES = [("tree_1", "acacia_large", 6, 9), ("tree_2", "acacia_small", -8, -4),
         ("tree_3", "acacia_large", 17, -8), ("tree_4", "acacia_large", -15, 12),
         ("tree_5", "acacia_small", 3, -10), ("tree_6", "acacia_large", 28, 5),
         ("tree_7", "acacia_small", -25, 0), ("tree_8", "acacia_large", -9, -20),
         ("tree_9", "acacia_small", 15, 14), ("tree_10", "acacia_large", 0, -25)]


def make_world(panel_defs):
    rows, table = [], []
    for hname, model, x, y, yaw in HOUSES:
        rows.append(f"<include><uri>model://{model}</uri><name>{hname}</name>"
                    f"<pose>{P(x, y, 0, 0, 0, yaw)}</pose></include>")
        qh = (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2))
        for pname, pos, roll in panel_defs[model]:
            wp = rot(qh, pos)
            wq = q_yaw_roll(yaw, roll)
            table.append(dict(id=f"{hname}_{pname}", house=hname,
                              center=(wp[0] + x, wp[1] + y, wp[2]), quat=wq))
    for name, model, x, y in TREES:
        rows.append(f"<include><uri>model://{model}</uri><name>{name}</name><pose>{P(x, y)}</pose></include>")
    rows.append(f"<include><uri>model://water_tank</uri><name>water_tank</name><pose>{P(6, -3.5)}</pose></include>")
    rows.append(f"<include><uri>model://dirt_path</uri><name>dirt_path</name><pose>{P(0, -6.5)}</pose></include>")
    # ladder on the north wall of modern_1 + technician beside it
    th = math.asin(0.883 / 2.8)
    rows.append(f"<include><uri>model://ladder</uri><name>ladder_1</name>"
                f"<pose>{P(0.6, 3.43, 0, th, 0, 0)}</pose></include>")
    rows.append(f"<include><uri>model://technician</uri><name>technician</name>"
                f"<pose>{P(-0.7, 4.3, 0, 0, 0, -math.pi / 2)}</pose></include>")

    # droid starts ON a panel (placed by the technician): modern_1, row 0, middle column
    start = next(t for t in table if t["id"] == "modern_1_panel_r0_c1")
    sp = rot(tuple(start["quat"]), (0.0, 0.0, PANEL_TOP + DROID_LIFT))
    spawn = tuple(start["center"][i] + sp[i] for i in range(3))
    rows.append(f"<include><uri>model://solarbot_droid</uri><name>solarbot</name>"
                f"<pose>{P(*spawn, -THETA, 0, 0.0)}</pose></include>")

    world = f"""<?xml version="1.0"?>
<sdf version="1.9">
<world name="village">
  <physics name="village_physics" type="ignored">
    <max_step_size>0.002</max_step_size><real_time_factor>1.0</real_time_factor>
  </physics>
  <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
  <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
  <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
  <scene><ambient>0.55 0.55 0.55 1</ambient><background>0.60 0.78 0.95 1</background><shadows>true</shadows></scene>
  <spherical_coordinates>
    <surface_model>EARTH_WGS84</surface_model><latitude_deg>-20.15</latitude_deg>
    <longitude_deg>28.58</longitude_deg><elevation>1350</elevation><heading_deg>0</heading_deg>
  </spherical_coordinates>

  <!-- SUN and GROUND live in the world file; every other model is in models/ -->
  <light type="directional" name="sun">
    <cast_shadows>true</cast_shadows><pose>0 0 60 0 0 0</pose>
    <diffuse>1 0.96 0.88 1</diffuse><specular>0.3 0.3 0.3 1</specular>
    <direction>-0.3 -0.5 -0.8</direction>
  </light>
  <model name="ground_plane"><static>true</static>
    <link name="link">
      <collision name="collision"><geometry><plane><normal>0 0 1</normal><size>400 400</size></plane></geometry>
        <surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision>
      <visual name="visual"><geometry><plane><normal>0 0 1</normal><size>400 400</size></plane></geometry>
        <material><ambient>0.74 0.62 0.42 1</ambient><diffuse>0.74 0.62 0.42 1</diffuse><specular>0.05 0.05 0.05 1</specular></material></visual>
    </link>
  </model>

  {"".join(rows)}
</world>
</sdf>"""
    write(os.path.join(WORLDS, "village.sdf"), pretty(world))

    y = ["# Generated by tools/generate_models.py -- world-frame pose of every panel surface.",
         "# center = panel origin, quat = (x, y, z, w), size = (along x, along slope) in metres",
         "panels:"]
    for t in table:
        c, q = t["center"], t["quat"]
        y += [f"  - id: {t['id']}", f"    house: {t['house']}",
              f"    center: [{c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}]",
              f"    quat: [{q[0]:.6f}, {q[1]:.6f}, {q[2]:.6f}, {q[3]:.6f}]",
              f"    size: [{PANEL_L}, {PANEL_W}]"]
    write(os.path.join(CONFIG, "panels.yaml"), "\n".join(y) + "\n")
    return table, spawn


def main():
    make_panel()
    make_droid()
    pd = {"house_modern": make_house_modern(), "house_thatched": make_house_thatched()}
    make_ladder()
    make_technician()
    make_water_tank()
    make_tree("acacia_large", 1.0)
    make_tree("acacia_small", 0.7)
    make_path()
    table, spawn = make_world(pd)
    print(f"{len(table)} panels on {len(HOUSES)} houses; droid spawn = "
          f"({spawn[0]:.3f}, {spawn[1]:.3f}, {spawn[2]:.3f})")


if __name__ == "__main__":
    main()
