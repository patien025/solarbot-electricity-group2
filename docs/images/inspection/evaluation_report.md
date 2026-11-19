# SolarBot PV Inspection Model - Evaluation Report

**AI/ML Engineer:** Bernard J Kadenhe (Student ID: `N02531833Y`, GitHub: `@n02531833y-afk`)
**Role:** AI/ML Engineer · Electricity Group 2 · NUST
**Target System:** 3-Wheeled Rooftop Solar Cleaning Droid

## 1. Executive Summary

- **Overall Classification Accuracy:** 99.00%
- **Macro F1-Score:** 99.00%
- **Weighted F1-Score:** 99.00%
- **Robot Action Arbitration Accuracy:** 98.75%
- **Dust Density Regression MAE:** 0.0671 ($R^2$ = 0.892)
- **Crack Severity Regression MAE:** 0.1033 ($R^2$ = 0.806)
- **Mean Edge Latency:** 29.51 ms (33.9 FPS on CPU)

## 2. Per-Class Performance Breakdown

| Defect Class | Precision | Recall | F1-Score |
|---|---|---|---|
| **Clean** | 98.04% | 100.00% | 99.01% |
| **Dusty / Soiled** | 98.99% | 98.00% | 98.49% |
| **Surface Crack** | 99.00% | 99.00% | 99.00% |
| **Dusty & Cracked** | 100.00% | 99.00% | 99.50% |

## 3. Confusion Matrix

```
                Predicted Clean  Predicted Dust  Predicted Crack  Predicted Both
True Clean        100              0               0                0             
True Dust         1                98              1                0             
True Crack        1                0               99               0             
True Both         0                1               0                99            
```

## 4. Latency and Hardware Compatibility

Tested on host CPU with batch size = 1 simulating the onboard/edge computer of the 3-wheeled SolarBot.
- **Mean Latency:** 29.51 ms
- **95th Percentile:** 36.80 ms
- **Real-time processing capability:** Confirmed (comfortably exceeds the 10-20 Hz requirement for a 0.15 m/s cleaning speed).

Generated automatically by `ai_inspection/evaluate.py`.
