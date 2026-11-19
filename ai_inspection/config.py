"""Configuration and constants for the SolarBot AI/ML inspection system.

Author: Bernard J Kadenhe (AI/ML Engineer, Student ID: N02531833Y)
GitHub: @n02531833y-afk
Electricity Group 2 · NUST · SolarBot Project
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Tuple


class DefectClass(IntEnum):
    """Solar panel surface inspection condition."""
    CLEAN = 0
    DUSTY = 1
    CRACKED = 2
    DUSTY_CRACKED = 3


CLASS_NAMES = {
    DefectClass.CLEAN: "Clean",
    DefectClass.DUSTY: "Dusty / Soiled",
    DefectClass.CRACKED: "Surface Crack",
    DefectClass.DUSTY_CRACKED: "Dusty & Cracked",
}


class RobotAction(IntEnum):
    """Prescribed action for the 3-wheeled solar cleaning droid."""
    CONTINUE_PASS = 0          # Panel clean; drive without brushing (save battery)
    ACTIVATE_BRUSH = 1         # Dust detected; start front rotating brush
    HALT_CRACK_ALERT = 2       # Crack detected; stop brush immediately to prevent glass shattering
    PRIORITY_MAINTENANCE = 3   # Compound damage; flag panel for technician manual replacement


ACTION_NAMES = {
    RobotAction.CONTINUE_PASS: "Continue Driving (Brush OFF)",
    RobotAction.ACTIVATE_BRUSH: "Activate Brush (Cleaning ON)",
    RobotAction.HALT_CRACK_ALERT: "HALT BRUSH: Crack Safety Alert",
    RobotAction.PRIORITY_MAINTENANCE: "FLAG FOR REPLACEMENT: Severe Damage",
}


@dataclass
class DroidSpecs:
    """Physical and kinematic parameters of the 3-wheeled cleaning droid."""
    # Wheel configuration: 2 geared drive wheels + 1 rear caster
    wheel_count: int = 3
    driven_wheels: int = 2
    caster_wheels: int = 1
    wheel_radius_m: float = 0.035
    wheel_separation_m: float = 0.125
    chassis_length_m: float = 0.200
    chassis_width_m: float = 0.150
    chassis_height_m: float = 0.100
    total_mass_kg: float = 0.450
    
    # Cleaning apparatus
    brush_radius_m: float = 0.025
    brush_length_m: float = 0.200
    brush_nominal_speed_rad_s: float = 25.0
    
    # Inspection camera geometry
    camera_height_above_glass_m: float = 0.080
    camera_forward_offset_m: float = 0.050
    camera_fov_horizontal_deg: float = 78.0
    camera_fov_vertical_deg: float = 60.0
    swath_width_m: float = 0.200
    nominal_drive_speed_m_s: float = 0.150


@dataclass
class InspectionConfig:
    """Inspection model parameters, thresholds, and operational rules."""
    # Image processing dimensions
    image_width: int = 224
    image_height: int = 224
    num_channels: int = 3
    
    # Decision thresholds
    dust_density_clean_threshold: float = 0.15   # Below 15% is considered clean
    dust_density_brush_threshold: float = 0.25   # Above 25% triggers brush activation
    dust_density_heavy_threshold: float = 0.60   # Above 60% indicates heavy sand/soiling
    crack_confidence_threshold: float = 0.45     # Confidence to declare a crack
    
    # Hardware profile
    droid: DroidSpecs = field(default_factory=DroidSpecs)
    
    # Random seed for reproducibility
    random_seed: int = 42
    
    # Model storage paths
    weights_path: str = "ai_inspection/weights/inspection_model.joblib"
    reports_dir: str = "docs/images/inspection"
    dataset_cache_dir: str = "ai_inspection/data"
