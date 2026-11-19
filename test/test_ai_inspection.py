"""Unit tests for SolarBot AI/ML Dust and Crack Inspection Pipeline.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y, @n02531833y-afk)
Electricity Group 2 · NUST · SolarBot Project
"""

import os
import sys
import tempfile
import time

import numpy as np
import pytest

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_inspection.config import (
    CLASS_NAMES,
    DefectClass,
    DroidSpecs,
    InspectionConfig,
    RobotAction,
)
from ai_inspection.dataset_generator import SolarPanelDatasetGenerator
from ai_inspection.features import FEATURE_NAMES, extract_feature_vector, extract_features
from ai_inspection.model import SolarBotInspector


class TestSolarBotInspection:
    """Test suite covering data generation, features, models, safety, and latency."""

    @pytest.fixture
    def config(self):
        return InspectionConfig(random_seed=42)

    @pytest.fixture
    def generator(self, config):
        return SolarPanelDatasetGenerator(config)

    def test_droid_specs(self):
        """Verify the physical specifications of the 3-wheeled cleaning droid."""
        specs = DroidSpecs()
        assert specs.wheel_count == 3, "Droid must have 3 wheels"
        assert specs.driven_wheels == 2, "Droid must have 2 driven wheels"
        assert specs.caster_wheels == 1, "Droid must have 1 rear caster wheel"
        assert specs.wheel_radius_m == 0.035
        assert specs.wheel_separation_m == 0.125
        assert specs.brush_radius_m == 0.025
        assert specs.total_mass_kg <= 1.5, "Student budget droid must be lightweight"

    def test_dataset_generation_all_classes(self, generator):
        """Verify procedural image generator produces valid samples across all classes."""
        for cls in DefectClass:
            sample = generator.generate_sample(cls)
            img = sample["image"]
            assert img.shape == (224, 224, 3), f"Incorrect image shape for {cls.name}"
            assert img.dtype == np.uint8, "Image must be uint8"
            assert sample["class_id"] == int(cls)
            assert 0.0 <= sample["dust_density"] <= 1.0
            assert 0.0 <= sample["crack_severity"] <= 1.0
            assert sample["recommended_action"] in [int(a) for a in RobotAction]

    def test_feature_extraction_integrity(self, generator):
        """Verify feature extraction extracts exactly 25 non-NaN, non-Inf descriptors."""
        sample = generator.generate_sample(DefectClass.CLEAN)
        vec = extract_feature_vector(sample["image"])
        assert len(vec) == len(FEATURE_NAMES), f"Expected {len(FEATURE_NAMES)} features, got {len(vec)}"
        assert not np.isnan(vec).any(), "Features must not contain NaNs"
        assert not np.isinf(vec).any(), "Features must not contain Infs"

    def test_feature_differentiation_dust(self, generator):
        """Verify dust accumulation creates measurable color and high-frequency shifts."""
        clean_sample = generator.generate_sample(DefectClass.CLEAN)
        dusty_sample = generator.generate_sample(DefectClass.DUSTY, dust_density=0.85)

        feat_clean = extract_features(clean_sample["image"])
        feat_dusty = extract_features(dusty_sample["image"])

        # Dust increases Red/Blue ratio (ochre/sand color shift)
        assert feat_dusty["rb_ratio"] > feat_clean["rb_ratio"], "Dust must increase red-to-blue ratio"

    def test_feature_differentiation_crack(self, generator):
        """Verify cracks produce elevated non-grid diagonal gradient energy."""
        clean_sample = generator.generate_sample(DefectClass.CLEAN)
        crack_sample = generator.generate_sample(DefectClass.CRACKED, crack_severity=0.85)

        feat_clean = extract_features(clean_sample["image"])
        feat_crack = extract_features(crack_sample["image"])

        # Cracks generate diagonal gradient energy and edge variance exceeding pristine panels
        assert feat_crack["diagonal_pixel_ratio"] > feat_clean["diagonal_pixel_ratio"], (
            "Crack must produce higher diagonal edge pixel density"
        )
        assert feat_crack["laplacian_var"] > feat_clean["laplacian_var"], (
            "Crack must produce higher Laplacian edge variance"
        )

    def test_model_training_and_inference(self, generator, config):
        """Verify end-to-end model training, prediction shape, and probability calibration."""
        images, labels, dusts, cracks = generator.generate_dataset(samples_per_class=20)
        X = np.array([extract_feature_vector(im) for im in images], dtype=np.float32)

        inspector = SolarBotInspector(config)
        inspector.fit(X, labels, dusts, cracks)
        assert inspector.is_trained, "Model must be marked trained"

        # Test single image prediction
        test_img = generator.generate_sample(DefectClass.DUSTY)["image"]
        report = inspector.predict_image(test_img, include_heatmap=True)

        assert report["class_id"] in [0, 1, 2, 3]
        assert 0.0 <= report["confidence"] <= 1.0
        assert 0.0 <= report["dust_density"] <= 1.0
        assert 0.0 <= report["crack_severity"] <= 1.0
        assert isinstance(report["crack_detected"], bool)
        assert report["recommended_action"] in [int(a) for a in RobotAction]
        assert report["defect_heatmap"].shape == (224, 224, 3)

        # Check probabilities sum to 1.0
        prob_sum = sum(report["probabilities"].values())
        assert pytest.approx(prob_sum, abs=1e-3) == 1.0

    def test_robot_action_safety_policies(self, config):
        """Verify robot action arbitration strictly halts brush on cracks."""
        inspector = SolarBotInspector(config)

        # 1. Clean panel: continue pass
        act1 = inspector._determine_action(DefectClass.CLEAN, dust_density=0.05, crack_severity=0.0)
        assert act1 == RobotAction.CONTINUE_PASS

        # 2. Dusty panel: activate brush
        act2 = inspector._determine_action(DefectClass.DUSTY, dust_density=0.45, crack_severity=0.0)
        assert act2 == RobotAction.ACTIVATE_BRUSH

        # 3. Cracked panel: HALT brush immediately to prevent mechanical destruction
        act3 = inspector._determine_action(DefectClass.CRACKED, dust_density=0.05, crack_severity=0.60)
        assert act3 == RobotAction.HALT_CRACK_ALERT

        # 4. Dusty & Cracked panel: Priority maintenance
        act4 = inspector._determine_action(DefectClass.DUSTY_CRACKED, dust_density=0.55, crack_severity=0.60)
        assert act4 == RobotAction.PRIORITY_MAINTENANCE

    def test_edge_cpu_inference_latency(self, generator, config):
        """Verify model latency is well under 50 ms for real-time edge processing."""
        # Train on small set
        images, labels, dusts, cracks = generator.generate_dataset(samples_per_class=15)
        X = np.array([extract_feature_vector(im) for im in images], dtype=np.float32)
        inspector = SolarBotInspector(config)
        inspector.fit(X, labels, dusts, cracks)

        sample_img = generator.generate_sample(DefectClass.DUSTY)["image"]

        # Warmup
        for _ in range(5):
            _ = inspector.predict_image(sample_img)

        # Benchmark 20 iterations
        times = []
        for _ in range(20):
            t0 = time.perf_counter()
            _ = inspector.predict_image(sample_img)
            times.append((time.perf_counter() - t0) * 1000.0)

        mean_ms = np.mean(times)
        assert mean_ms < 50.0, f"Inference latency too slow: {mean_ms:.2f} ms (must be < 50 ms)"

    def test_model_serialization(self, generator, config):
        """Verify model can be saved and reloaded with exact reproduction."""
        images, labels, dusts, cracks = generator.generate_dataset(samples_per_class=10)
        X = np.array([extract_feature_vector(im) for im in images], dtype=np.float32)
        inspector = SolarBotInspector(config)
        inspector.fit(X, labels, dusts, cracks)

        sample_img = generator.generate_sample(DefectClass.CRACKED)["image"]
        pred1 = inspector.predict_image(sample_img)

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            inspector.save(tmp_path)
            loaded = SolarBotInspector.load(tmp_path)
            pred2 = loaded.predict_image(sample_img)

            assert pred1["class_id"] == pred2["class_id"]
            assert pytest.approx(pred1["confidence"], abs=1e-4) == pred2["confidence"]
            assert pytest.approx(pred1["dust_density"], abs=1e-4) == pred2["dust_density"]
            assert pytest.approx(pred1["crack_severity"], abs=1e-4) == pred2["crack_severity"]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
