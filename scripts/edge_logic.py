"""Pure-Python geometry for the roof edge guard (no ROS needed, so it can be unit tested).

The droid may only drive while its footprint stays over the panel array of the roof it is on.
A command is blocked when, one short step ahead, any footprint point would end up further outside
the array than it is now (so backing away from an edge is always possible).
"""
import math

# points of the droid footprint in the droid frame (x forward, y left), metres
FOOTPRINT = [(0.11, 0.07), (0.11, -0.07), (-0.09, 0.07), (-0.09, -0.07), (0.0, 0.075), (0.0, -0.075)]
STEP_S = 0.3          # look this far ahead (seconds of motion)
EDGE_MARGIN = 0.02    # bridges the 3 cm gaps between panels
ACTIVE_MARGIN = 0.15  # guard is active when the droid is on, or just beside, an array
Z_TOL = 0.08          # points must be within 8 cm of the panel plane


def rot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def conj(q):
    return (-q[0], -q[1], -q[2], q[3])


class Array:
    """All panels of the world; a point is 'on the array' if it is over any panel (plus margin)."""

    def __init__(self, panels):
        self.panels = [(tuple(p["center"]), tuple(p["quat"]), p["size"][0] / 2.0, p["size"][1] / 2.0)
                       for p in panels]

    def on(self, pt, margin=EDGE_MARGIN):
        for c, q, hx, hy in self.panels:
            if abs(pt[0] - c[0]) > 1.4 or abs(pt[1] - c[1]) > 1.4:
                continue
            l = rot(conj(q), (pt[0] - c[0], pt[1] - c[1], pt[2] - c[2]))
            if abs(l[0]) <= hx + margin and abs(l[1]) <= hy + margin and abs(l[2]) <= Z_TOL:
                return True
        return False


def _excess(self, pt, margin=EDGE_MARGIN):
    """How far (m) pt is outside the nearest panel; 0 = on the array, 9 = no panel nearby."""
    best = 9.0
    for c, q, hx, hy in self.panels:
        if abs(pt[0] - c[0]) > 1.4 or abs(pt[1] - c[1]) > 1.4:
            continue
        l = rot(conj(q), (pt[0] - c[0], pt[1] - c[1], pt[2] - c[2]))
        if abs(l[2]) > Z_TOL:
            continue
        e = max(abs(l[0]) - hx - margin, abs(l[1]) - hy - margin, 0.0)
        best = min(best, e)
    return best


Array.excess = _excess


def _world(pos, quat, local):
    o = rot(quat, (local[0], local[1], 0.0))
    return (pos[0] + o[0], pos[1] + o[1], pos[2] + o[2])


def _excesses(array, pos, quat, dx, dyaw):
    c, s = math.cos(dyaw), math.sin(dyaw)
    return [array.excess(_world(pos, quat, (dx + px * c - py * s, px * s + py * c)))
            for px, py in FOOTPRINT]


def _blocked(array, pos, quat, lin, ang):
    """True if the step would take any footprint point further outside the array than it is now."""
    now = _excesses(array, pos, quat, 0.0, 0.0)
    nxt = _excesses(array, pos, quat, lin * STEP_S, ang * STEP_S)
    return any(b > a + 1e-4 for a, b in zip(now, nxt))


def filter_cmd(array, pos, quat, lin, ang):
    """Returns (lin, ang, blocked_text or None). Not on a roof -> command passes unchanged."""
    if (lin == 0.0 and ang == 0.0) or not array.on(pos, ACTIVE_MARGIN):
        return lin, ang, None
    lin2 = 0.0 if lin != 0.0 and _blocked(array, pos, quat, lin, 0.0) else lin
    ang2 = 0.0 if ang != 0.0 and _blocked(array, pos, quat, 0.0, ang) else ang
    if (lin2 != 0.0 or ang2 != 0.0) and _blocked(array, pos, quat, lin2, ang2):
        lin2, ang2 = 0.0, 0.0
    if (lin2, ang2) == (lin, ang):
        return lin, ang, None
    what = "forward" if lin > 0 else "reverse" if lin < 0 else "turn"
    return lin2, ang2, f"{what} motion would leave the panel array"
