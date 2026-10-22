#!/usr/bin/env python3
"""Sanity checks anyone can run (no ROS/Gazebo needed):  python3 tools/check_repo.py
 - every model has model.config + model.sdf and parses as XML
 - every model:// URI in models/ and the world points at an existing model
 - every panel in config/panels.yaml sits on a house in the world
"""
import glob, os, re, sys
import xml.etree.ElementTree as ET
import yaml

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
models = sorted(os.listdir(os.path.join(root, "models")))
bad = 0
for m in models:
    for f in ("model.config", "model.sdf"):
        p = os.path.join(root, "models", m, f)
        try:
            ET.parse(p)
        except Exception as e:
            print("FAIL", p, e); bad += 1
files = glob.glob(os.path.join(root, "models", "*", "model.sdf")) + [os.path.join(root, "worlds", "village.sdf")]
for f in files:
    for uri in re.findall(r"model://([A-Za-z0-9_]+)", open(f).read()):
        if uri not in models:
            print("FAIL missing model", uri, "in", f); bad += 1
world = open(os.path.join(root, "worlds", "village.sdf")).read()
for p in yaml.safe_load(open(os.path.join(root, "config", "panels.yaml")))["panels"]:
    if f'<name>{p["house"]}</name>' not in world:
        print("FAIL panel without house", p["id"]); bad += 1
print("models:", ", ".join(models))
print("OK" if not bad else f"{bad} problem(s)")
sys.exit(1 if bad else 0)
