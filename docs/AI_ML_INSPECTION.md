# SolarBot: Rooftop Solar-Panel Dust and Crack Inspection System

**Author:** Bernard J Kadenhe  
**Student ID:** `N02531833Y`  
**Role:** AI/ML Engineer  
**GitHub:** `@n02531833y-afk`  
**Group:** Electricity Group 2 · National University of Science and Technology (NUST)  
**Project:** SolarBot Rooftop Solar-Panel Cleaning Droid (`patien025/solarbot-electricity-group2`)  

---

## 1. Executive Summary and Problem Statement

Rooftop photovoltaic (PV) installations in rural and semi-arid Zimbabwean environments (e.g. Matabeleland and Midlands provinces) suffer severe performance degradation from two primary glass surface failure modes:

1. **Dust and Sand Soiling (Irradiance Loss):** Airborne silica sand, arid red loam dust, and organic droppings form an opaque veil over the tempered glass. Studies in Southern Africa establish typical power output losses of **15% to 30%** within weeks of dry spells.
2. **Surface Micro-Cracks and Fractures:** Thermal cycling (daily roof swings from 12°C at night to >55°C midday) and mechanical impacts cause micro-cracks across silicon wafer cells. Unattended cracks form localized high-resistance hot spots, trigger bypass diode burnout, and risk module degradation or electrical arcing.

### The 3-Wheeled Droid Operational Context

SolarBot is a student-budget rooftop cleaning robot designed with a **3-wheeled chassis**:
- **Two driven wheels** powered by geared DC motors (radius $r_w = 0.035\text{ m}$, track width $L = 0.125\text{ m}$).
- **One rear passive caster wheel** providing high maneuverability and low weight.
- **One front rotating cylindrical brush** ($r_b = 0.025\text{ m}$, span $0.20\text{ m}$) rotating at $\omega_b \approx 25\text{ rad/s}$.
- **Chassis envelope:** $20 \times 15 \times 10\text{ cm}$, total mass $\approx 0.45\text{ kg}$.
- **Downward-facing optical inspection module:** Mounted at height $h = 0.08\text{ m}$ above the panel surface, looking down at the panel glass swath directly in front of the cleaning brush.

```
       [ Front Cylindrical Rotating Brush ]
           |                           |
       [==== Downward Inspection Camera ====]
           |                           |
       (Left Drive Wheel)      (Right Drive Wheel)
           \                           /
            \       [Chassis]         /
             \                       /
              --- (Rear Caster) ----
```

### Safety and Operational Imperative

Running a rotating mechanical brush over an already cracked solar panel poses severe risks:
- The bristle friction and mechanical downward pressure can propagate micro-fissures into catastrophic shattered glass.
- Grit trapped in bristles against cracked silicon can sever delicate 10-micron contact fingers and metallic busbars.
- **Rule:** The robot must **detect cracks immediately**, **halt the spinning brush**, issue **Safety Warning W-04**, and log the panel GPS/roof coordinates for manual technician replacement. Conversely, when heavy dust is detected without cracks, the droid **autonomously activates the brush** to clear the panel.

---

## 2. System Architecture

The AI/ML inspection architecture is organized into four decoupled components designed for low-power edge execution:

```mermaid
flowchart TD
    CAM[Inspection Camera / ROS 2 Frame] --> FE[Edge Invariant Feature Extractor<br/>20 Radiometric & Gradient Descriptors]
    FE --> MLP[Multi-Task Neural Inspector<br/>MLP Classifier + Dust & Crack Regressors]
    MLP --> CLS[4-Class Classification<br/>Clean | Dusty | Cracked | Both]
    MLP --> REG[Continuous Severities<br/>Dust Density 0-100% | Crack Severity 0-1.0]
    MLP --> HEAT[Saliency Heatmap Overlay]
    
    CLS --> ARB[Robot Action Policy Arbitrator]
    REG --> ARB
    
    ARB -->|Clean| ACT1[Continue Pass / Brush OFF]
    ARB -->|Dusty > 25%| ACT2[Activate Brush / Cleaning ON]
    ARB -->|Crack Detected| ACT3[HALT BRUSH / Safety Alert W-04]
    ARB -->|Dust & Crack| ACT4[Priority Maintenance Flag]
```

### 2.1 Feature Engineering (Edge Invariant Descriptors)

Rather than running heavy, resource-intensive deep convolutional networks that cannot execute on embedded edge CPUs (such as an onboard Raspberry Pi or operator laptop) at 30+ FPS, we developed **20 physics-grounded, rotation-invariant radiometric and directional gradient descriptors**:

1. **Directional Fracture Descriptors:**
   - Standard monocrystalline solar cells possess strictly **orthogonal rectilinear patterns**: horizontal silver paste grid fingers ($0^\circ$) and vertical copper busbars ($90^\circ$).
   - Structural micro-cracks form irregular, jagged fracture lines propagating at diagonal angles ($22.5^\circ$ to $67.5^\circ$).
   - Using optimized Sobel edge decomposition, we isolate non-grid diagonal fracture magnitude without expensive trigonometric functions:
     $$\text{Diagonal Condition: } 0.414 \cdot |G_x| < |G_y| < 2.414 \cdot |G_x|$$
   - Features: `diagonal_pixel_ratio`, `diagonal_fracture_index`, `grid_index`.

2. **Spectral & Finger Attenuation:**
   - Periodic grid fingers produce sharp local high-frequency variance.
   - Dust deposition acts as a low-pass optical filter, scattering light and attenuating the high-frequency finger amplitude.
   - Features: `finger_variance`, `finger_peak_to_peak`, `laplacian_var`.

3. **Radiometric Soiling & Colorimetric Shift:**
   - Pristine silicon wafers exhibit high blue reflectance ($B > R$).
   - Zimbabwean dust/sand shifts the chromaticity strongly towards red-yellow ($R/B \text{ ratio} \gg 1.0$).
   - Features: `dust_color_index`, `rb_ratio`, `rg_ratio`, `mean_s`, `std_v`.

4. **Morphological Defect Profiling:**
   - Local contrast deviations against a uniform background filter detect localized bird droppings and spot anomalies.
   - Features: `anomaly_density`, `anomaly_energy`, `diff_var`.

### 2.2 Neural Architecture

The classifier and regressors utilize calibrated Multi-Layer Perceptrons (MLP) with batch scaling:
- **Classifier:** Dense $(20 \to 64 \to 32 \to 4)$, ReLU activations, Adam optimizer, $L_2$ regularization $\alpha = 0.001$.
- **Dust Regressor:** Dense $(20 \to 32 \to 16 \to 1)$, outputs continuous dust density $\hat{d} \in [0.0, 1.0]$.
- **Crack Regressor:** Dense $(20 \to 32 \to 16 \to 1)$, outputs continuous crack severity $\hat{c} \in [0.0, 1.0]$.

---

## 3. Training Protocol and Implementation

The model was trained using the pipeline in `ai_inspection/train.py`:
- **Dataset:** 600 procedural solar cell surface samples (150 per class) with procedural monocrystalline/polycrystalline wafer textures, silver busbars, grid fingers, procedural dust deposition, and stochastic micro-crack branching.
- **Partition:** Stratified 80% training (480 samples) and 20% validation (120 samples).
- **Training Time:** 77.8 seconds total on standard host CPU.
- **Convergence:** Validation classification accuracy achieved **99.17%** with Dust MAE of $0.0724$.
- **Model Checkpoint:** Saved to `ai_inspection/weights/inspection_model.joblib`.

---

## 4. Evaluation Results and Performance Metrics

The model was evaluated on a held-out test distribution of **400 unseen samples** (100 per class) using `ai_inspection/evaluate.py`.

### 4.1 Summary Metrics

| Metric | Score | Target Requirement | Status |
|---|---|---|---|
| **Overall Classification Accuracy** | **99.00%** | $\ge 90.0\%$ | **EXCEEDED** |
| **Balanced Accuracy** | **99.00%** | $\ge 90.0\%$ | **EXCEEDED** |
| **Macro F1-Score** | **99.00%** | $\ge 90.0\%$ | **EXCEEDED** |
| **Weighted F1-Score** | **99.00%** | $\ge 90.0\%$ | **EXCEEDED** |
| **Robot Action Arbitration Accuracy** | **98.75%** | $\ge 95.0\%$ | **EXCEEDED** |
| **Dust Density Regression MAE** | **0.0671** ($R^2 = 0.892$) | $\le 0.100$ | **EXCEEDED** |
| **Crack Severity Regression MAE** | **0.1033** ($R^2 = 0.806$) | $\le 0.150$ | **EXCEEDED** |
| **Mean Edge Latency (CPU)** | **29.51 ms** | $\le 50.0\text{ ms}$ | **EXCEEDED** |
| **95th Percentile Latency** | **36.80 ms** | $\le 60.0\text{ ms}$ | **EXCEEDED** |
| **Throughput** | **33.9 FPS** | $\ge 15.0\text{ FPS}$ | **EXCEEDED** |

### 4.2 Per-Class Breakdown

| Class | True Condition | Precision | Recall | F1-Score |
|---|---|---|---|---|
| **0: Clean** | Pristine PV glass, no soiling | 98.04% | 100.00% | **99.01%** |
| **1: Dusty / Soiled** | Sand / loam veil (>25% density) | 98.99% | 98.00% | **98.49%** |
| **2: Surface Crack** | Wafer micro-cracks / fractures | 99.00% | 99.00% | **99.00%** |
| **3: Dusty & Cracked** | Combined soiling + structural crack | 100.00% | 99.00% | **99.50%** |

### 4.3 Confusion Matrix

```
                      Predicted Clean   Predicted Dust   Predicted Crack   Predicted Both
True Clean                  100                0                0                0
True Dusty / Soiled           2               98                0                0
True Surface Crack            0                1               99                0
True Dusty & Cracked          0                0                1               99
```

### 4.4 Diagnostic Evaluation Figures

The evaluation suite automatically renders high-resolution diagnostic plots stored in `docs/images/inspection/`:

1. **Confusion Matrix:** `docs/images/inspection/confusion_matrix.png`
2. **Multi-Class ROC Curves:** `docs/images/inspection/roc_curves.png` (AUC > 0.99 for all classes)
3. **Inference Latency Distribution:** `docs/images/inspection/latency_distribution.png` (Mean 29.5 ms)
4. **Sample Predictions with Defect Saliency Heatmaps:** `docs/images/inspection/sample_predictions.png`

---

## 5. Robot Action Arbitration Policy

The AI/ML inspection engine maps classifications and continuous regression scores to discrete robot commands for the 3-wheeled SolarBot droid:

| Detected State | Severity Threshold | Robot Action | Hardware Command |
|---|---|---|---|
| **Clean** | Dust $< 15\%$, Crack $= 0$ | `CONTINUE_PASS` | Drive forward; brush remains **OFF** (conserves battery) |
| **Dusty / Soiled** | Dust $\ge 25\%$, Crack $= 0$ | `ACTIVATE_BRUSH` | Publish `/brush_toggle` **True** ($\omega_b = 25\text{ rad/s}$) |
| **Surface Crack** | Crack Severity $> 0.25$ | `HALT_CRACK_ALERT` | Publish `/brush_toggle` **False**; raise **Warning W-04**; log coordinates |
| **Dusty & Cracked** | Dust $> 30\%$, Crack $> 0.30$ | `PRIORITY_MAINTENANCE` | Halt cleaning; flag module for urgent technician physical replacement |

---

## 6. ROS 2 Jazzy Integration

A dedicated ROS 2 Jazzy node is provided in [`scripts/inspection_node.py`](../scripts/inspection_node.py):

### Subscriptions
- `/brush_state` (`std_msgs/msg/Bool`): Current brush motor status.
- `/solarbot/world_pose` (`tf2_msgs/msg/TFMessage`): Droid world position to correlate defect locations with rooftop panel IDs in `config/panels.yaml`.

### Publications
- `/solarbot/inspection_report` (`std_msgs/msg/String`): Real-time JSON telemetry report.
- `/solarbot/crack_alert` (`std_msgs/msg/Bool`, latched): Triggered upon crack detection.
- `/brush_toggle` (`std_msgs/msg/Bool`): Autonomous command to toggle the rotating brush.

### Telemetry Message Schema
```json
{
  "timestamp": 1763550204.12,
  "panel_id": "thatched_2_panel_r1_c0",
  "condition": "Dusty / Soiled",
  "confidence": 0.985,
  "dust_density_percent": 64.2,
  "crack_detected": false,
  "crack_severity": 0.041,
  "recommended_action": "Activate Brush (Cleaning ON)",
  "latency_ms": 28.7
}
```

---

## 7. CLI Usage and Verification

The command-line interface provides full control over the inspection subsystem:

```bash
# 1. Run unit tests (9 tests covering specs, generation, features, model, safety, latency)
python3 -m pytest test/test_ai_inspection.py -v

# 2. Train model from scratch
python3 -m ai_inspection.cli train --samples 150

# 3. Evaluate model on held-out test distribution and generate plots
python3 -m ai_inspection.cli evaluate --samples 100 --out docs/images/inspection

# 4. Inspect a single panel image and save saliency overlay
python3 -m ai_inspection.cli inspect sample_panel.png --save-overlay overlay.png

# 5. Output inspection report as JSON
python3 -m ai_inspection.cli inspect sample_panel.png --json
```

---

## 8. Verification and Quality Assurance

- **Repository Checker:** Verified passing with `python3 tools/check_repo.py`.
- **Unit Test Suite:** 100% pass rate (9/9 tests passed in `test/test_ai_inspection.py`).
- **Edge Efficiency:** Measured at **29.51 ms per frame (33.9 FPS)**, enabling smooth 2–5 Hz closed-loop visual inspection while the 3-wheeled droid drives at $0.15\text{ m/s}$.
