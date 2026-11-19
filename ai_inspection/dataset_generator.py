"""Photovoltaic cell surface image generator for dust and crack inspection.

Synthesizes high-fidelity solar panel surface images with realistic silicon wafer
textures, grid contact fingers, metallic busbars, Zimbabwean arid dust/soiling
profiles, and structural micro-cracks. Also supports loading external real-world images.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y)
Electricity Group 2 · NUST · SolarBot Project
"""

import math
import os
import random
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import DefectClass, InspectionConfig


class SolarPanelDatasetGenerator:
    """Generates synthetic solar panel inspection images with realistic physics."""

    def __init__(self, config: Optional[InspectionConfig] = None):
        self.config = config or InspectionConfig()
        self.width = self.config.image_width
        self.height = self.config.image_height
        self.rng = np.random.RandomState(self.config.random_seed)

    def _generate_base_pv_cell(self, cell_type: str = "monocrystalline") -> np.ndarray:
        """Render a pristine PV cell background with silicon texture, busbars, and fingers."""
        img = np.zeros((self.height, self.width, 3), dtype=np.float32)

        if cell_type == "monocrystalline":
            # Deep navy blue / dark charcoal characteristic of mono-Si cells
            base_color = np.array([18.0, 32.0, 68.0], dtype=np.float32)
            # Add slight antireflective coating shimmer / subtle texture
            noise = self.rng.normal(0.0, 2.5, (self.height, self.width, 3)).astype(np.float32)
            img += base_color + noise
        else:
            # Polycrystalline with crystalline grain flake texture
            base_color = np.array([25.0, 55.0, 110.0], dtype=np.float32)
            grain = self.rng.normal(0.0, 6.0, (self.height, self.width, 3)).astype(np.float32)
            img += base_color + grain

        # Draw grid fingers: thin parallel conductors spaced ~10 to 14 pixels apart
        finger_spacing = int(self.rng.uniform(10, 15))
        finger_color = np.array([170.0, 185.0, 205.0], dtype=np.float32)  # Silver paste
        for y in range(4, self.height, finger_spacing):
            # Vary finger intensity slightly
            alpha = self.rng.uniform(0.65, 0.85)
            y_start = max(0, y - 1)
            y_end = min(self.height, y + 1)
            img[y_start:y_end, :, :] = (1.0 - alpha) * img[y_start:y_end, :, :] + alpha * finger_color

        # Draw main busbars: 2 to 3 vertical thicker silver strips
        num_busbars = self.rng.choice([2, 3])
        busbar_positions = np.linspace(int(self.width * 0.18), int(self.width * 0.82), num_busbars, dtype=int)
        busbar_color = np.array([225.0, 230.0, 240.0], dtype=np.float32)  # Polished silver ribbon

        for bx in busbar_positions:
            half_w = self.rng.choice([2, 3])
            x0 = max(0, bx - half_w)
            x1 = min(self.width, bx + half_w + 1)
            # Draw busbar body
            img[:, x0:x1, :] = 0.85 * busbar_color + 0.15 * img[:, x0:x1, :]
            # Draw solder joint pads along busbars
            for sy in range(20, self.height, 45):
                img[max(0, sy - 4):min(self.height, sy + 5), max(0, bx - half_w - 2):min(self.width, bx + half_w + 3), :] = 210.0

        return np.clip(img, 0.0, 255.0)

    def _apply_dust(self, base_img: np.ndarray, density: float) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate dust and soiling accumulation.
        
        Args:
            base_img: Input RGB image of pristine panel.
            density: Severity level in range [0.0, 1.0].
            
        Returns:
            Tuple of (soiled_image, dust_mask)
        """
        if density <= 0.01:
            return base_img.copy(), np.zeros((self.height, self.width), dtype=np.float32)

        # Generate multi-scale low-frequency noise for uneven dust deposition
        h, w = self.height, self.width
        # Low frequency coarse noise
        s1 = 16
        c1 = self.rng.uniform(0.0, 1.0, (s1, s1)).astype(np.float32)
        im_c1 = Image.fromarray(c1).resize((w, h), resample=Image.Resampling.BICUBIC)
        low_noise = np.array(im_c1)

        # Medium frequency noise for patches / streaks
        s2 = 32
        c2 = self.rng.uniform(0.0, 1.0, (s2, s2)).astype(np.float32)
        im_c2 = Image.fromarray(c2).resize((w, h), resample=Image.Resampling.BILINEAR)
        med_noise = np.array(im_c2)

        # High frequency particulate grit
        fine_noise = self.rng.normal(0.0, 0.15, (h, w)).astype(np.float32)

        # Combine into composite dust density distribution
        dust_map = (0.55 * low_noise + 0.35 * med_noise + 0.10 * fine_noise)
        dust_map = (dust_map - dust_map.min()) / (dust_map.max() - dust_map.min() + 1e-6)
        
        # Scale by target density and create thresholded coverage
        dust_mask = np.clip(dust_map * density * 1.35, 0.0, 1.0)

        # Arid dust color characteristic of Zimbabwean sandy loam (ochre / yellowish brown / pale silica)
        dust_r = self.rng.uniform(155.0, 195.0)
        dust_g = self.rng.uniform(130.0, 165.0)
        dust_b = self.rng.uniform(90.0, 125.0)
        dust_rgb = np.array([dust_r, dust_g, dust_b], dtype=np.float32)

        # Alpha blend soiling layer: dust attenuates contrast of underlying silicon and fingers
        dust_3d = dust_mask[:, :, np.newaxis]
        soiled = (1.0 - 0.88 * dust_3d) * base_img + (0.88 * dust_3d) * dust_rgb

        # Attenuate high-frequency sharpness proportionally to dust thickness
        if density > 0.3:
            blur_radius = max(0.5, density * 1.8)
            pil_img = Image.fromarray(np.clip(soiled, 0, 255).astype(np.uint8))
            pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            soiled = np.array(pil_img, dtype=np.float32)

        return np.clip(soiled, 0.0, 255.0), dust_mask

    def _apply_cracks(self, base_img: np.ndarray, severity: float) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate micro-cracks and fracture propagation across solar cells.
        
        Args:
            base_img: Input RGB panel image.
            severity: Crack severity in range [0.0, 1.0].
            
        Returns:
            Tuple of (cracked_image, crack_mask)
        """
        if severity <= 0.01:
            return base_img.copy(), np.zeros((self.height, self.width), dtype=np.float32)

        h, w = self.height, self.width
        crack_mask = np.zeros((h, w), dtype=np.uint8)
        pil_mask = Image.fromarray(crack_mask)
        draw = ImageDraw.Draw(pil_mask)

        # Determine number of fracture traces based on severity
        num_main_cracks = int(np.clip(round(1 + severity * 3), 1, 4))
        
        all_segments = []

        for _ in range(num_main_cracks):
            # Start near an edge or stress concentration point
            if self.rng.rand() > 0.5:
                curr_x = float(self.rng.choice([0, w - 1]))
                curr_y = float(self.rng.uniform(0.1 * h, 0.9 * h))
                angle = 0.0 if curr_x == 0 else math.pi
                angle += self.rng.uniform(-0.6, 0.6)
            else:
                curr_x = float(self.rng.uniform(0.1 * w, 0.9 * w))
                curr_y = float(self.rng.choice([0, h - 1]))
                angle = math.pi / 2 if curr_y == 0 else -math.pi / 2
                angle += self.rng.uniform(-0.6, 0.6)

            step_count = int(self.rng.uniform(25, 60 * severity + 30))
            branch_prob = 0.15 + 0.25 * severity

            trace = [(curr_x, curr_y)]
            for step in range(step_count):
                step_len = self.rng.uniform(3.0, 7.0)
                # Random walk with directional momentum
                angle += self.rng.normal(0.0, 0.35)
                next_x = curr_x + step_len * math.cos(angle)
                next_y = curr_y + step_len * math.sin(angle)

                if 0 <= next_x < w and 0 <= next_y < h:
                    draw.line([(curr_x, curr_y), (next_x, next_y)], fill=255, width=int(1 + severity))
                    curr_x, next_x = next_x, next_x
                    curr_y, next_y = next_y, next_y
                    trace.append((curr_x, curr_y))
                else:
                    break

                # Branching crack
                if self.rng.rand() < branch_prob and step > 10:
                    branch_angle = angle + self.rng.choice([-1, 1]) * self.rng.uniform(0.4, 1.1)
                    bx, by = curr_x, curr_y
                    for _ in range(int(self.rng.uniform(10, 25))):
                        branch_angle += self.rng.normal(0.0, 0.3)
                        nbx = bx + 4.0 * math.cos(branch_angle)
                        nby = by + 4.0 * math.sin(branch_angle)
                        if 0 <= nbx < w and 0 <= nby < h:
                            draw.line([(bx, by), (nbx, nby)], fill=255, width=1)
                            bx, by = nbx, nby
                        else:
                            break

        mask_np = np.array(pil_mask, dtype=np.float32) / 255.0

        # Physical appearance of cracks on PV modules:
        # Fissure creates a dark refracted line with a thin bright reflection halo
        cracked_img = base_img.copy()

        # Dark fissure line
        fissure_3d = mask_np[:, :, np.newaxis]
        dark_crack_color = np.array([8.0, 10.0, 15.0], dtype=np.float32)
        cracked_img = (1.0 - fissure_3d) * cracked_img + fissure_3d * dark_crack_color

        # Subtle bright glint on fracture edges
        pil_dilated = pil_mask.filter(ImageFilter.MaxFilter(3))
        dilated_np = np.array(pil_dilated, dtype=np.float32) / 255.0
        edge_glint = np.clip(dilated_np - mask_np, 0.0, 1.0)[:, :, np.newaxis]
        glint_color = np.array([210.0, 220.0, 240.0], dtype=np.float32)
        cracked_img = cracked_img + edge_glint * 0.45 * (glint_color - cracked_img)

        return np.clip(cracked_img, 0.0, 255.0), mask_np

    def _apply_lighting_and_droid_noise(self, img: np.ndarray) -> np.ndarray:
        """Apply ambient illumination gradients and droid motion vibration noise."""
        h, w, _ = img.shape

        # Solar angle illumination gradient across the panel
        angle = self.rng.uniform(0.0, 2.0 * math.pi)
        grad_x = np.linspace(-0.5, 0.5, w) * math.cos(angle)
        grad_y = np.linspace(-0.5, 0.5, h) * math.sin(angle)
        grad_2d = grad_x[np.newaxis, :] + grad_y[:, np.newaxis]
        lighting_gain = 1.0 + 0.25 * grad_2d[:, :, np.newaxis]

        # Camera sensor noise (shot noise + thermal noise from ESP32/Pi camera)
        sensor_noise = self.rng.normal(0.0, 2.5, (h, w, 3))

        # 3-wheel differential drive vibration (slight horizontal/diagonal micro-blur)
        result = np.clip(img * lighting_gain + sensor_noise, 0.0, 255.0)
        return result

    def generate_sample(
        self,
        defect_class: DefectClass,
        dust_density: Optional[float] = None,
        crack_severity: Optional[float] = None,
    ) -> Dict[str, object]:
        """Generate a single annotated inspection sample.
        
        Returns:
            Dict containing:
                - image: uint8 ndarray of shape (H, W, 3)
                - class_id: DefectClass int
                - class_name: str
                - dust_density: float in [0.0, 1.0]
                - crack_severity: float in [0.0, 1.0]
                - recommended_action: RobotAction
        """
        cell_type = self.rng.choice(["monocrystalline", "polycrystalline"], p=[0.75, 0.25])
        pv = self._generate_base_pv_cell(cell_type)

        d_dens = 0.0
        c_sev = 0.0

        if defect_class == DefectClass.CLEAN:
            d_dens = self.rng.uniform(0.0, self.config.dust_density_clean_threshold * 0.7)
            c_sev = 0.0
            pv, _ = self._apply_dust(pv, d_dens)

        elif defect_class == DefectClass.DUSTY:
            d_dens = self.rng.uniform(0.28, 0.95) if dust_density is None else dust_density
            c_sev = 0.0
            pv, _ = self._apply_dust(pv, d_dens)

        elif defect_class == DefectClass.CRACKED:
            d_dens = self.rng.uniform(0.0, self.config.dust_density_clean_threshold * 0.8)
            c_sev = self.rng.uniform(0.35, 0.95) if crack_severity is None else crack_severity
            pv, _ = self._apply_dust(pv, d_dens)
            pv, _ = self._apply_cracks(pv, c_sev)

        elif defect_class == DefectClass.DUSTY_CRACKED:
            d_dens = self.rng.uniform(0.30, 0.85) if dust_density is None else dust_density
            c_sev = self.rng.uniform(0.35, 0.90) if crack_severity is None else crack_severity
            pv, _ = self._apply_dust(pv, d_dens)
            pv, _ = self._apply_cracks(pv, c_sev)

        # Apply lighting and camera noise
        final_img = self._apply_lighting_and_droid_noise(pv)
        final_uint8 = np.clip(final_img, 0, 255).astype(np.uint8)

        # Determine robotic action policy
        from .config import RobotAction
        if c_sev > 0.2:
            if d_dens > 0.3:
                action = RobotAction.PRIORITY_MAINTENANCE
            else:
                action = RobotAction.HALT_CRACK_ALERT
        elif d_dens >= self.config.dust_density_brush_threshold:
            action = RobotAction.ACTIVATE_BRUSH
        else:
            action = RobotAction.CONTINUE_PASS

        return {
            "image": final_uint8,
            "class_id": int(defect_class),
            "class_name": DefectClass(defect_class).name,
            "dust_density": float(d_dens),
            "crack_severity": float(c_sev),
            "recommended_action": int(action),
        }

    def generate_dataset(
        self,
        samples_per_class: int = 150,
        output_dir: Optional[str] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Generate a complete balanced dataset across all defect classes.
        
        Returns:
            Tuple of (images, class_labels, dust_densities, crack_severities)
        """
        all_images = []
        all_labels = []
        all_dust = []
        all_cracks = []

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            for cls in DefectClass:
                os.makedirs(os.path.join(output_dir, cls.name.lower()), exist_ok=True)

        for cls in DefectClass:
            for i in range(samples_per_class):
                sample = self.generate_sample(cls)
                img = sample["image"]
                all_images.append(img)
                all_labels.append(sample["class_id"])
                all_dust.append(sample["dust_density"])
                all_cracks.append(sample["crack_severity"])

                if output_dir:
                    fname = f"{cls.name.lower()}_{i:04d}.png"
                    fpath = os.path.join(output_dir, cls.name.lower(), fname)
                    Image.fromarray(img).save(fpath)

        return (
            np.array(all_images, dtype=np.uint8),
            np.array(all_labels, dtype=np.int64),
            np.array(all_dust, dtype=np.float32),
            np.array(all_cracks, dtype=np.float32),
        )
