"""SolarBot Rooftop Solar-Panel Inspection System.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y, @n02531833y-afk)
Electricity Group 2 · NUST · Low-cost, phone-controlled, simulation-first
"""

from .config import (
    InspectionConfig,
    DefectClass,
    RobotAction,
    CLASS_NAMES,
    ACTION_NAMES,
)
from .features import extract_features, extract_feature_vector
from .model import SolarBotInspector
from .dataset_generator import SolarPanelDatasetGenerator

__all__ = [
    "InspectionConfig",
    "DefectClass",
    "RobotAction",
    "CLASS_NAMES",
    "ACTION_NAMES",
    "extract_features",
    "extract_feature_vector",
    "SolarBotInspector",
    "SolarPanelDatasetGenerator",
]

__version__ = "1.0.0"
__author__ = "Bernard J Kadenhe"
