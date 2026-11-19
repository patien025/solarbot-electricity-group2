"""Edge-efficient feature extraction for PV dust and crack inspection.

Extracts radiometric, high-frequency spatial, directional edge, and morphological
texture features optimized for real-time edge processing on the SolarBot droid.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y)
Electricity Group 2 · NUST · SolarBot Project
"""

import math
from typing import Dict, List, Tuple

import numpy as np
from scipy import ndimage


def rgb_to_gray(img: np.ndarray) -> np.ndarray:
    """Convert RGB image (H, W, 3) to grayscale (H, W) in range [0, 1]."""
    if img.ndim == 2:
        return img.astype(np.float32) / 255.0 if img.max() > 1.0 else img.astype(np.float32)
    gray = 0.2989 * img[:, :, 0] + 0.5870 * img[:, :, 1] + 0.1140 * img[:, :, 2]
    return gray.astype(np.float32) / 255.0 if gray.max() > 1.0 else gray.astype(np.float32)


def compute_directional_gradients(gray: np.ndarray) -> Dict[str, float]:
    """Compute directional gradient energies to isolate non-grid crack fractures.
    
    Grid fingers are strictly horizontal; busbars are strictly vertical.
    Crack fissures propagate at diagonal angles.
    Optimized for CPU edge inference (< 10 ms).
    """
    gx = ndimage.sobel(gray, axis=1)  # Vertical edges (busbars)
    gy = ndimage.sobel(gray, axis=0)  # Horizontal edges (grid fingers)

    abs_gx = np.abs(gx)
    abs_gy = np.abs(gy)
    grad_mag = np.sqrt(gx**2 + gy**2 + 1e-8)

    # Threshold for strong edges
    thresh = float(np.percentile(grad_mag, 85))
    strong_edges = grad_mag > thresh

    # Diagonal edges satisfy: 0.414 < |gy| / |gx| < 2.414 (between 22.5 deg and 67.5 deg)
    diag_cond = (abs_gy > 0.414 * abs_gx) & (abs_gy < 2.414 * abs_gx)
    diagonal_mask = diag_cond & strong_edges

    grid_cond = (abs_gy <= 0.414 * abs_gx) | (abs_gy >= 2.414 * abs_gx)
    grid_mask = grid_cond & strong_edges

    total_mag_sum = float(np.sum(grad_mag)) + 1e-6
    diag_mag_sum = float(np.sum(grad_mag[diagonal_mask]))
    grid_mag_sum = float(np.sum(grad_mag[grid_mask]))

    diagonal_pixel_ratio = float(np.mean(diagonal_mask))
    diagonal_fracture_index = diag_mag_sum / total_mag_sum
    grid_index = grid_mag_sum / total_mag_sum

    grad_mean = float(np.mean(grad_mag))
    grad_std = float(np.std(grad_mag))
    grad_max = float(np.max(grad_mag))

    return {
        "grad_mean": grad_mean,
        "grad_std": grad_std,
        "grad_max": grad_max,
        "diagonal_pixel_ratio": diagonal_pixel_ratio,
        "diagonal_fracture_index": diagonal_fracture_index,
        "grid_index": grid_index,
    }


def compute_spectral_finger_attenuation(gray: np.ndarray) -> Dict[str, float]:
    """Measure attenuation of periodic grid finger patterns caused by dust deposition."""
    row_profile = np.mean(gray, axis=1)
    # Fast 1D box filter detrend
    row_baseline = ndimage.uniform_filter1d(row_profile, size=9)
    row_detrended = row_profile - row_baseline

    finger_variance = float(np.var(row_detrended))
    finger_peak_to_peak = float(np.ptp(row_detrended))

    laplacian = ndimage.laplace(gray)
    laplacian_var = float(np.var(laplacian))

    return {
        "finger_variance": finger_variance,
        "finger_peak_to_peak": finger_peak_to_peak,
        "laplacian_var": laplacian_var,
    }


def compute_radiometric_soiling(img: np.ndarray) -> Dict[str, float]:
    """Compute color shifts and contrast degradation characteristic of arid dust accumulation."""
    img_f = img.astype(np.float32) if img.max() > 1.0 else img.astype(np.float32) * 255.0
    r = img_f[:, :, 0]
    g = img_f[:, :, 1]
    b = img_f[:, :, 2]

    mean_r = float(np.mean(r))
    mean_g = float(np.mean(g))
    mean_b = float(np.mean(b))

    dust_color_index = (mean_r + mean_g) / (2.0 * mean_b + 1e-6)
    rb_ratio = mean_r / (mean_b + 1e-6)
    rg_ratio = mean_r / (mean_g + 1e-6)

    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    sat = (cmax - cmin) / (cmax + 1e-6)
    mean_s = float(np.mean(sat))
    std_v = float(np.std(cmax)) / 255.0

    return {
        "mean_r": mean_r,
        "mean_g": mean_g,
        "mean_b": mean_b,
        "dust_color_index": dust_color_index,
        "rb_ratio": rb_ratio,
        "rg_ratio": rg_ratio,
        "mean_s": mean_s,
        "std_v": std_v,
    }


def compute_morphological_defects(gray: np.ndarray) -> Dict[str, float]:
    """Detect localized defect clusters and high-contrast anomaly contours."""
    # Fast uniform filter difference instead of expensive 2D Gaussian + label
    blurred = ndimage.uniform_filter(gray, size=11)
    diff = np.abs(gray - blurred)

    anomaly_thresh = float(np.percentile(diff, 95))
    anomaly_mask = diff > anomaly_thresh

    anomaly_density = float(np.mean(anomaly_mask))
    anomaly_energy = float(np.mean(diff[anomaly_mask])) if np.any(anomaly_mask) else 0.0

    return {
        "anomaly_density": anomaly_density,
        "anomaly_energy": anomaly_energy,
        "diff_var": float(np.var(diff)),
    }


def extract_features(img: np.ndarray) -> Dict[str, float]:
    """Extract complete dictionary of calibrated PV inspection features."""
    gray = rgb_to_gray(img)

    feats = {}
    feats.update(compute_directional_gradients(gray))
    feats.update(compute_spectral_finger_attenuation(gray))
    feats.update(compute_radiometric_soiling(img))
    feats.update(compute_morphological_defects(gray))

    return feats


FEATURE_NAMES = [
    "grad_mean", "grad_std", "grad_max",
    "diagonal_pixel_ratio", "diagonal_fracture_index", "grid_index",
    "finger_variance", "finger_peak_to_peak", "laplacian_var",
    "mean_r", "mean_g", "mean_b", "dust_color_index", "rb_ratio", "rg_ratio",
    "mean_s", "std_v",
    "anomaly_density", "anomaly_energy", "diff_var",
]


def extract_feature_vector(img: np.ndarray) -> np.ndarray:
    """Extract ordered 1D feature array suitable for model inference."""
    fdict = extract_features(img)
    return np.array([fdict[k] for k in FEATURE_NAMES], dtype=np.float32)
