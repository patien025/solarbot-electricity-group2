"""Multi-task inspection model for solar panel dust and crack detection.

Combines high-efficiency neural architectures (MLP) and calibrated regressors
to deliver real-time defect classification, continuous severity estimation,
and robot action arbitration for the 3-wheeled SolarBot droid.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y)
Electricity Group 2 · NUST · SolarBot Project
"""

import os
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler

from .config import (
    ACTION_NAMES,
    CLASS_NAMES,
    DefectClass,
    InspectionConfig,
    RobotAction,
)
from .features import FEATURE_NAMES, extract_feature_vector, rgb_to_gray


class SolarBotInspector:
    """End-to-end solar panel dust and crack inspection neural model."""

    def __init__(self, config: Optional[InspectionConfig] = None):
        self.config = config or InspectionConfig()
        self.scaler = StandardScaler()
        # Edge-optimized multi-layer perceptron for 4-way classification
        self.classifier = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            alpha=0.001,
            max_iter=350,
            random_state=self.config.random_seed,
        )
        # Dedicated neural regressor for continuous dust soiling density [0.0, 1.0]
        self.dust_regressor = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation="relu",
            solver="adam",
            alpha=0.001,
            max_iter=300,
            random_state=self.config.random_seed,
        )
        # Dedicated neural regressor for continuous crack severity [0.0, 1.0]
        self.crack_regressor = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            activation="relu",
            solver="adam",
            alpha=0.001,
            max_iter=300,
            random_state=self.config.random_seed,
        )
        self.is_trained = False

    def fit(
        self,
        X_train: np.ndarray,
        y_class: np.ndarray,
        y_dust: np.ndarray,
        y_crack: np.ndarray,
    ) -> "SolarBotInspector":
        """Train the multi-task model on extracted features.
        
        Args:
            X_train: Feature matrix of shape (N, num_features).
            y_class: Categorical defect labels (N,).
            y_dust: Continuous dust densities in [0, 1] (N,).
            y_crack: Continuous crack severities in [0, 1] (N,).
        """
        X_scaled = self.scaler.fit_transform(X_train)
        self.classifier.fit(X_scaled, y_class)
        self.dust_regressor.fit(X_scaled, y_dust)
        self.crack_regressor.fit(X_scaled, y_crack)
        self.is_trained = True
        return self

    def predict_features(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        """Run batch prediction on pre-extracted feature vectors."""
        if not self.is_trained:
            raise RuntimeError("Model has not been trained yet. Call fit() or load().")
        X_scaled = self.scaler.transform(X)
        probs = self.classifier.predict_proba(X_scaled)
        preds = np.argmax(probs, axis=1)
        dust_preds = np.clip(self.dust_regressor.predict(X_scaled), 0.0, 1.0)
        crack_preds = np.clip(self.crack_regressor.predict(X_scaled), 0.0, 1.0)

        actions = []
        for p, d, c in zip(preds, dust_preds, crack_preds):
            action = self._determine_action(p, d, c)
            actions.append(int(action))

        return {
            "class_id": preds,
            "probabilities": probs,
            "dust_density": dust_preds,
            "crack_severity": crack_preds,
            "recommended_action": np.array(actions, dtype=np.int64),
        }

    def predict_image(self, img: np.ndarray, include_heatmap: bool = False) -> Dict[str, Any]:
        """Inspect a single RGB solar panel image.
        
        Returns structured inspection report with classification, severities,
        robot action policy, and optional defect localization heatmap.
        """
        feat_vec = extract_feature_vector(img).reshape(1, -1)
        batch_res = self.predict_features(feat_vec)

        cls_id = int(batch_res["class_id"][0])
        probs = batch_res["probabilities"][0]
        dust_dens = float(batch_res["dust_density"][0])
        crack_sev = float(batch_res["crack_severity"][0])
        action = RobotAction(batch_res["recommended_action"][0])

        defect_mask = (
            self.generate_defect_heatmap(img, cls_id, crack_sev, dust_dens)
            if include_heatmap
            else None
        )

        res = {
            "class_id": cls_id,
            "class_name": CLASS_NAMES[DefectClass(cls_id)],
            "confidence": float(probs[cls_id]),
            "probabilities": {CLASS_NAMES[DefectClass(i)]: float(probs[i]) for i in range(4)},
            "dust_density": dust_dens,
            "dust_density_percent": round(dust_dens * 100.0, 1),
            "crack_severity": crack_sev,
            "crack_detected": bool(cls_id in (DefectClass.CRACKED, DefectClass.DUSTY_CRACKED) or crack_sev > 0.25),
            "recommended_action": int(action),
            "action_name": ACTION_NAMES[action],
        }
        if include_heatmap:
            res["defect_heatmap"] = defect_mask
        return res

    def _determine_action(self, class_id: int, dust_density: float, crack_severity: float) -> RobotAction:
        """Arbitrate robot action based on safety and operational priorities."""
        # Safety priority 1: Any crack requires protecting the panel glass from rotating brush damage
        if class_id in (DefectClass.CRACKED, DefectClass.DUSTY_CRACKED) or crack_severity > 0.30:
            if class_id == DefectClass.DUSTY_CRACKED or (dust_density > 0.40 and crack_severity > 0.30):
                return RobotAction.PRIORITY_MAINTENANCE
            return RobotAction.HALT_CRACK_ALERT

        # Operational priority 2: Dust accumulation exceeds cleaning threshold
        if dust_density >= self.config.dust_density_brush_threshold or class_id == DefectClass.DUSTY:
            return RobotAction.ACTIVATE_BRUSH

        # Normal condition: Clean panel
        return RobotAction.CONTINUE_PASS

    def generate_defect_heatmap(
        self,
        img: np.ndarray,
        class_id: int,
        crack_sev: float,
        dust_dens: float,
    ) -> np.ndarray:
        """Generate spatial saliency overlay pinpointing cracks and localized dust."""
        h, w = img.shape[:2]
        heatmap = np.zeros((h, w, 3), dtype=np.uint8)
        gray = rgb_to_gray(img)

        # Highlight diagonal crack lines in vivid red
        if class_id in (DefectClass.CRACKED, DefectClass.DUSTY_CRACKED) or crack_sev > 0.2:
            from scipy import ndimage
            gx = ndimage.sobel(gray, axis=1)
            gy = ndimage.sobel(gray, axis=0)
            abs_gx = np.abs(gx)
            abs_gy = np.abs(gy)
            grad_mag = np.sqrt(gx**2 + gy**2)

            # Diagonal non-grid edges
            diag_mask = (abs_gy > 0.414 * abs_gx) & (abs_gy < 2.414 * abs_gx)
            diag_mask = diag_mask & (grad_mag > np.percentile(grad_mag, 88))
            diag_dilated = ndimage.binary_dilation(diag_mask, iterations=2)
            heatmap[diag_dilated, 0] = 255  # Red channel for cracks

        # Highlight dust soiling in amber/yellow
        if dust_dens > 0.2:
            from scipy import ndimage
            blurred = ndimage.uniform_filter(gray, size=11)
            diff = np.abs(gray - blurred)
            dust_mask = diff > np.percentile(diff, 80)
            heatmap[dust_mask & (heatmap[:, :, 0] == 0), 0] = 220  # Yellow-orange
            heatmap[dust_mask & (heatmap[:, :, 0] == 0), 1] = 180

        return heatmap

    def save(self, filepath: Optional[str] = None) -> str:
        """Persist model bundle to disk."""
        target_path = filepath or self.config.weights_path
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        bundle = {
            "scaler": self.scaler,
            "classifier": self.classifier,
            "dust_regressor": self.dust_regressor,
            "crack_regressor": self.crack_regressor,
            "config": self.config,
            "feature_names": FEATURE_NAMES,
            "is_trained": self.is_trained,
        }
        joblib.dump(bundle, target_path)
        return target_path

    @classmethod
    def load(cls, filepath: str) -> "SolarBotInspector":
        """Load trained model bundle from disk."""
        bundle = joblib.load(filepath)
        instance = cls(config=bundle.get("config"))
        instance.scaler = bundle["scaler"]
        instance.classifier = bundle["classifier"]
        instance.dust_regressor = bundle["dust_regressor"]
        instance.crack_regressor = bundle["crack_regressor"]
        instance.is_trained = bundle["is_trained"]
        return instance
