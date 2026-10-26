# SolarBot – rooftop solar-panel cleaning droid

**Electricity Group 2** · Gazebo Harmonic + ROS 2 Jazzy · simulation-first

A student-budget (about USD 15–24) wheeled droid that cleans solar panels on the roofs of rural houses.
A technician places the droid on a panel and drives it with a gamepad; the front brush sweeps the panel.
This repository holds the simulation: a realistic Zimbabwean village with **modern houses** (corrugated-iron
gable roofs) and **thatched rondavels**, each carrying solar panels, plus the droid and its controls.

```
        N (+y)  panels face north (southern hemisphere)
        ^
        |   modern_1 + ladder + technician with gamepad
        +--> E (+x)       7 houses, 26 rooftop panels, trees, water tank, dirt road
```

## Team and roles (Electricity Group 2)
# Electricity Group 2 – roles and GitHub accounts

| Role | Member | Student number | GitHub username | Main folders / duties |
|---|---|---|---|---|
| Project Manager | Tyrese Mapamgisana | N02534462L | @Tyrese | Issues board, milestones, PR approvals, supervisor reports, README/docs |
| Software Engineer | Hope M Chibare | N02532738H | @Hope178 | launch/, config/bridge.yaml, package structure, code review |
| Systems Engineer | Tawananyasha Tarugarira | N02532657D | @TawanaTarue | models/, tools/generate_models.py, docs/physical_droid.md, hardware build |
| Network Engineer | Precious R Magaya | N02529749P | @Precious | LoRa/WiFi link simulation, message format, POTRAZ rules |
| Programmer 1 | Tafadzwa Chinhoyi | N02529632Q | @tafadzwa012 | Navigation/docking helpers for the later autonomy phase |
| Programmer 2 | Tinevimbo Chikaka | N02534499J | @tine-20 | scripts/brush_control.py, scripts/cleaning_monitor.py |
| Test Programmer | Patience Mafira | N02529263K | @patien025 | tools/check_repo.py, test/, bug reports |
| Database Administrator | Ashton Ndlovu | N02532750L | @Ashera-dev | SQLite reports/logs schema, panel inventory |
| AI/ML Engineer | Bernard J Kadenhe | N02531833Y | @n02531833y-afk | Dust/crack inspection model: training and evaluation |
| AI/ML Engineer (shared) | Dumisile N Ndlovu | N02418654Y | @TBC | Dust/crack dataset: collecting, labelling, organising images |
| Chief Security Officer | Zvinaishe Marume | N02530132V | @nicoDee20 | Authenticated commands, keys out of source, privacy |
| Lecturer / Supervisor | Lecturer | N/A | @kchilumani | Project supervision and assessment |

>
## Repository layout

```
models/                   <- EVERY model except the sun and the ground
  solarbot_droid/         the low-cost droid (2 geared motors, caster, front brush, Arduino Nano, L298N, battery)
  solar_panel/            100 W panel (1.00 x 0.67 m) with a dust film
  house_modern/           6 x 4.5 m house, 10 degree corrugated-iron roof, 6 panels on the north slope
  house_thatched/         round rondavel, stepped thatch, timber rack with 2 panels
  ladder/  technician/  water_tank/  acacia_large/  acacia_small/  dirt_path/
worlds/village.sdf        sun + ground + the placement of everything in models/
config/                   bridge.yaml, gamepad.yaml, panels.yaml (world pose of every panel)
launch/                   sim.launch.py (everything), teleop.launch.py (gamepad only)
scripts/                  brush_control.py, cleaning_monitor.py, place_droid.py, run_world_only.sh
tools/                    generate_models.py (rebuilds models/world/panels), check_repo.py
docs/                     TEAM_ROLES.md, physical_droid.md
```

## Setup (Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic already installed)

```bash
sudo apt install ros-jazzy-ros-gz ros-jazzy-joy ros-jazzy-teleop-twist-joy \
                 ros-jazzy-teleop-twist-keyboard python3-yaml

mkdir -p ~/solarbot_ws/src && cd ~/solarbot_ws/src
git clone https://github.com/<your-org>/solarbot-electricity-group2.git solarbot_sim
cd ~/solarbot_ws && colcon build --packages-select solarbot_sim
source install/setup.bash
```

## Run

```bash
ros2 launch solarbot_sim sim.launch.py               # world + bridge + gamepad + cleaning monitor
ros2 launch solarbot_sim sim.launch.py gamepad:=false  # no gamepad plugged in
scripts/run_world_only.sh                             # just look at the village, no ROS
```

The droid starts on the first panel of `modern_1` (the house with the ladder and the technician).

**Gamepad (Xbox layout):** hold **LB** to drive · left stick = forward/back + turn · **RB** = turbo ·
**A** = brush on/off · **B** = stop.

**No gamepad?**
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard          # drive
ros2 run solarbot_sim brush_control.py &                      # (if not already running)
ros2 topic pub --once /brush_toggle std_msgs/msg/Bool "{data: true}"   # brush on
```

**Put the droid on another roof** (the technician "places" it):
```bash
ros2 run solarbot_sim place_droid.py --list
ros2 run solarbot_sim place_droid.py thatched_2_panel_r1_c0
```
You can also drag it with Gazebo's *Transform Control* tool.

**Watch the cleaning:** `ros2 topic echo /solarbot/cleaning_status` – the monitor logs
`<panel>: cleaning complete (≥95 %)` when a panel is swept (SRS PERF-2).

## Editing the models

Everything in `models/`, `worlds/village.sdf` and `config/panels.yaml` is produced by one script, so houses and
panels always agree:

```bash
python3 tools/generate_models.py      # then rebuild with colcon
python3 tools/check_repo.py           # XML, model:// links and panel table sanity check
```

## Publishing to GitHub

```bash
cd solarbot_sim            # this folder
git init -b main
git add .
git commit -m "Initial SolarBot village simulation (Electricity Group 2)"
git remote add origin https://github.com/<your-org>/solarbot-electricity-group2.git
git push -u origin main
```
Then on GitHub: **Settings → Collaborators** (or an Organisation team) → add all members, and record each person's
username and role in `docs/TEAM_ROLES.md`. Suggested: protect `main` (pull request + 1 review), one branch per
feature (`feature/<role>-<topic>`), one GitHub Issue per task assigned to the role owner.

## Simplifications to know about

- **Teleoperated only** in this release. The low-budget build has no LiDAR or camera, so Nav2/SLAM and AI
  inspection from the SRS are deferred to a later phase or a hardware upgrade.
- **Thatched roofs are steep in real life.** Here the thatch has a flat crown carrying a timber rack with two
  panels tilted 10°, so a droid can sit on them.
- **Dust is bookkeeping, not graphics:** the dust film is a static translucent layer; `cleaning_monitor.py` tracks coverage.
- Brush has no collision, so it spins freely without catching the panel.
- Written and checked without Gazebo on the build machine: the SDF/XML, links and geometry are validated, but
  expect small tuning (friction, speeds) the first time you run it. Report what you see as an Issue.

## Licence

MIT – see `LICENSE`.
