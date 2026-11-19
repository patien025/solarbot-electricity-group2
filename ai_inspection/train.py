"""Training pipeline for the SolarBot solar panel dust and crack inspector.

Trains the feature-based multi-task classifier and regressors, performs
stratified validation, and saves the production weights.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y)
Electricity Group 2 · NUST · SolarBot Project
"""

import argparse
import os
import time
from typing import Dict, Tuple

import numpy as np
from sklearn.model_selection import train_test_split

from .config import InspectionConfig
from .dataset_generator import SolarPanelDatasetGenerator
from .features import extract_feature_vector
from .model import SolarBotInspector


def train_inspection_model(
    samples_per_class: int = 200,
    config: Optional[InspectionConfig] = None,
    save_weights: bool = True,
    weights_path: Optional[str] = None,
) -> Tuple[SolarBotInspector, Dict[str, float]]:
    """Train the inspection model end-to-end.
    
    Args:
        samples_per_class: Number of samples per defect class (total = 4 * N).
        config: Inspection configuration object.
        save_weights: Whether to save model weights to disk.
        weights_path: Custom output file path.
        
    Returns:
        Tuple of (trained_model, training_metrics_dict)
    """
    cfg = config or InspectionConfig()
    print("=" * 65)
    print("SolarBot PV Inspection Model Training Pipeline")
    print("Lead AI/ML Engineer: Bernard J Kadenhe (ID: N02531833Y)")
    print("Electricity Group 2 · SolarBot 3-Wheeled Cleaning Droid")
    print("=" * 65)

    start_time = time.time()

    # 1. Generate procedural PV inspection dataset
    print(f"\n[1/4] Generating synthetic PV inspection dataset ({samples_per_class} samples/class)...")
    generator = SolarPanelDatasetGenerator(cfg)
    images, labels, dust_severities, crack_severities = generator.generate_dataset(
        samples_per_class=samples_per_class
    )
    total_samples = len(images)
    print(f"      Dataset ready: {total_samples} samples across 4 classes.")

    # 2. Extract edge-invariant radiometric and directional texture features
    print(f"\n[2/4] Extracting invariant features (25 descriptors per frame)...")
    t_feat_start = time.time()
    feature_list = []
    for i, img in enumerate(images):
        vec = extract_feature_vector(img)
        feature_list.append(vec)
    X = np.array(feature_list, dtype=np.float32)
    feat_time = time.time() - t_feat_start
    print(f"      Features extracted in {feat_time:.2f}s ({1000.0 * feat_time / total_samples:.2f} ms/sample).")

    # 3. Stratified train/val split (80% train, 20% validation)
    print(f"\n[3/4] Partitioning data (80% train, 20% validation) with stratification...")
    (
        X_train, X_val,
        y_cls_train, y_cls_val,
        y_dust_train, y_dust_val,
        y_crack_train, y_crack_val,
    ) = train_test_split(
        X, labels, dust_severities, crack_severities,
        test_size=0.20,
        random_state=cfg.random_seed,
        stratify=labels,
    )
    print(f"      Train set: {len(X_train)} samples | Validation set: {len(X_val)} samples.")

    # 4. Train multi-task models
    print(f"\n[4/4] Fitting multi-task models (Classifier, Dust Regressor, Crack Regressor)...")
    t_fit_start = time.time()
    inspector = SolarBotInspector(cfg)
    inspector.fit(X_train, y_cls_train, y_dust_train, y_crack_train)
    fit_time = time.time() - t_fit_start
    print(f"      Model fitting complete in {fit_time:.2f}s.")

    # Evaluate validation accuracy
    val_preds = inspector.predict_features(X_val)
    val_acc = float(np.mean(val_preds["class_id"] == y_cls_val))
    dust_mae = float(np.mean(np.abs(val_preds["dust_density"] - y_dust_val)))
    crack_mae = float(np.mean(np.abs(val_preds["crack_severity"] - y_crack_val)))

    total_time = time.time() - start_time
    print("-" * 65)
    print("Validation Results:")
    print(f"  * Classification Accuracy: {val_acc * 100.0:.2f}%")
    print(f"  * Dust Density MAE:        {dust_mae:.4f}")
    print(f"  * Crack Severity MAE:      {crack_mae:.4f}")
    print(f"  * Total Training Duration: {total_time:.2f}s")
    print("-" * 65)

    metrics = {
        "val_accuracy": val_acc,
        "dust_mae": dust_mae,
        "crack_mae": crack_mae,
        "total_time_seconds": total_time,
        "total_samples": total_samples,
    }

    if save_weights:
        out_path = weights_path or cfg.weights_path
        inspector.save(out_path)
        print(f"Saved trained weights to: {out_path}\n")

    return inspector, metrics


def main():
    parser = argparse.ArgumentParser(description="Train SolarBot PV Inspection Model")
    parser.add_argument("--samples", type=int, default=200, help="Samples per class (default: 200)")
    parser.add_argument("--out", type=str, default=None, help="Output path for weights")
    args = parser.parse_args()

    train_inspection_model(samples_per_class=args.samples, weights_path=args.out)


if __name__ == "__main__":
    main()
