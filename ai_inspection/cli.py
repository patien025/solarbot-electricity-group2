"""Command Line Interface for SolarBot AI/ML Inspection.

Author: Bernard J Kadenhe (AI/ML Engineer, N02531833Y)
Electricity Group 2 · NUST · SolarBot Project
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

from .config import InspectionConfig
from .dataset_generator import SolarPanelDatasetGenerator
from .evaluate import ModelEvaluator
from .model import SolarBotInspector
from .train import train_inspection_model


def main():
    parser = argparse.ArgumentParser(
        prog="solarbot-inspect",
        description="SolarBot AI/ML PV Inspection CLI (Bernard J Kadenhe, N02531833Y)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Train command
    train_parser = subparsers.add_parser("train", help="Train inspection model")
    train_parser.add_argument("--samples", type=int, default=200, help="Samples per class")
    train_parser.add_argument("--out", type=str, default="ai_inspection/weights/inspection_model.joblib")

    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate model on unseen test set")
    eval_parser.add_argument("--weights", type=str, default="ai_inspection/weights/inspection_model.joblib")
    eval_parser.add_argument("--samples", type=int, default=100, help="Samples per class")
    eval_parser.add_argument("--out", type=str, default="docs/images/inspection")

    # Inspect single image command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a solar panel image")
    inspect_parser.add_argument("image_path", type=str, help="Path to input image (PNG/JPEG)")
    inspect_parser.add_argument("--weights", type=str, default="ai_inspection/weights/inspection_model.joblib")
    inspect_parser.add_argument("--save-overlay", type=str, default=None, help="Path to save heatmap overlay")
    inspect_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # Generate dataset command
    gen_parser = subparsers.add_parser("generate", help="Generate procedural PV image dataset")
    gen_parser.add_argument("--out-dir", type=str, default="ai_inspection/data/synthetic", help="Output directory")
    gen_parser.add_argument("--samples", type=int, default=50, help="Samples per class")

    args = parser.parse_args()

    if args.command == "train":
        train_inspection_model(samples_per_class=args.samples, weights_path=args.out)

    elif args.command == "evaluate":
        if not os.path.exists(args.weights):
            print(f"Weights file not found at {args.weights}. Running training first...")
            train_inspection_model(samples_per_class=180, weights_path=args.weights)
        inspector = SolarBotInspector.load(args.weights)
        evaluator = ModelEvaluator(inspector)
        evaluator.evaluate_test_set(samples_per_class=args.samples, output_dir=args.out)

    elif args.command == "inspect":
        if not os.path.exists(args.weights):
            print(f"Weights file not found at {args.weights}. Please run train first.", file=sys.stderr)
            sys.exit(1)
        inspector = SolarBotInspector.load(args.weights)
        raw_img = Image.open(args.image_path).convert("RGB")
        img_np = np.array(raw_img)
        res = inspector.predict_image(img_np, include_heatmap=bool(args.save_overlay))

        if args.save_overlay:
            overlay = (0.65 * img_np + 0.35 * res["defect_heatmap"]).astype(np.uint8)
            Image.fromarray(overlay).save(args.save_overlay)
            print(f"Overlay saved to {args.save_overlay}")

        if args.json:
            clean_res = {k: v for k, v in res.items() if k != "defect_heatmap"}
            print(json.dumps(clean_res, indent=2))
        else:
            print("\nSolarBot Surface Inspection Report:")
            print(f"  Condition:       {res['class_name']} (Confidence: {res['confidence']*100:.1f}%)")
            print(f"  Dust Density:    {res['dust_density_percent']}%")
            print(f"  Crack Detected:  {'YES' if res['crack_detected'] else 'NO'} (Severity: {res['crack_severity']*100:.1f}%)")
            print(f"  Action Policy:   {res['action_name']}\n")

    elif args.command == "generate":
        print(f"Generating dataset into {args.out_dir}...")
        gen = SolarPanelDatasetGenerator()
        gen.generate_dataset(samples_per_class=args.samples, output_dir=args.out_dir)
        print("Dataset generation complete!")


if __name__ == "__main__":
    main()
