# Agentic Drones — Omokai Robotics Take-Home Task

Prompt → LLM → Validated JSON → Deterministic Executor → Simulator

## Quick Start

```bash
# 1. Clone and build
git clone <repo-url> agentic-drones
cd agentic-drones
docker compose build

# 2. Start the container (with X11 for GUI)
xhost +local:docker
docker compose up -d
docker compose exec omokai bash

# 3. Run headless verification (no GUI needed)
bash scripts/verify.sh

# 4. Run the interactive CLI
python -m src.cli.cli
```

## Pipeline Architecture

```
Prompt (NL) ──▶ LLM Node ──▶ Validator ──▶ Executor ──▶ Simulator
                    │              │
                    └── errors ────┘
```

Five strict contract boundaries:
1. **Operator → LLM**: Plain string prompt on `/operator/prompt`
2. **LLM → Validator**: Raw JSON on `/llm/raw_mission` (LLM may be wrong)
3. **Validator → Executor**: Validated `MissionPlan` on `/mission/validated` (only if all checks pass)
4. **Validator → Operator**: Human-readable rejection on `/mission/rejected`
5. **Executor → Operator**: Telemetry on `/drone/status`

## Key Design Decisions

### LLM is OUT of the control loop
The executor runs from a validated JSON file. You can kill the LLM process entirely and the executor still flies any valid mission. `python -m src.executor.executor --mission config/perimeter_loop.json`

### 3-Layer Validation
- **Layer 1 (Structural)**: JSON parse, required fields
- **Layer 2 (Semantic/Safety)**: Altitude ≤50m, speed ≤15m/s, geofence, must-start-TAKEOFF/must-end-LAND
- **Layer 3 (Re-prompt)**: Self-correction loop feeding errors back to LLM (up to 3 retries)

### Deterministic Executor
State machine: `IDLE → ARMING → TAKEOFF → EXECUTING → LANDING → DONE + FAILSAFE`
Same JSON → identical audit log every time. Every command timestamped.

## Challenges Implemented

### Core Pipeline (Mandatory) ✅
Prompt-to-flight: natural language → LLM → validated JSON → executor → motion.

### Challenge 3: Vision AI Target Detection + Follow ✅
- YOLOv8 object detection with configurable target class (person, car, dog, etc.)
- On first detection: saves annotated image + notifies operator with file path
- PID-based visual servoing: pixel error → body velocity → executor offboard control
- Target-lost fallback: hover (zero velocity) + yaw search (5 deg/s)
- Works with camera, video file, or simulated feed
- New: `--sim` flag for synthetic camera (bouncing target, no hardware needed)
- New: `--executor` flag to pipe PID velocity commands to MAVSDK offboard control
- New: `--headless` + `--frames N` for automated batch testing

### Challenge 2: SLAM / Autonomous Navigation ✅ (Partial + Write-up)
- SLAM Toolbox integration for online mapping
- Nav2 path planning with obstacle avoidance
- PathPlanner for route computation
- Full design documented in `src/slam/slam_navigator.py`

### Challenge 1: Multi-Agent Formations ✅ (Partial + Write-up)
- SwarmCoordinator with 4 formation types: LINE, WEDGE, DIAMOND, COLUMN
- Leader-follower model with body-frame offset computation
- Per-drone MAVLink port allocation (14540+)
- Full design documented in `src/swarm/coordinator.py`

## Example Commands

```
# Patrol the perimeter loop twice at 15 metres
# Fly the inspection route and return to start
# Sweep this area in a wedge formation
# Follow any person you see
# Navigate to the target position avoiding obstacles
```

## Running with LLM

### Local (Ollama) — Default
```bash
# Ollama runs inside the container automatically
python -m src.cli.cli
```

### OpenAI
```bash
export LLM_BACKEND=openai
export LLM_MODEL=gpt-4o-mini
export OPENAI_API_KEY=sk-...
python -m src.cli.cli
```

## Running Without LLM (Kill-the-LLM Demo)

```bash
python -m src.executor.executor --mission config/perimeter_loop.json
```

## Determinism Demo

```bash
python -m src.executor.executor --mission config/perimeter_loop.json --log run1.json
python -m src.executor.executor --mission config/perimeter_loop.json --log run2.json
diff run1.json run2.json  # identical = deterministic
```

## Running the Challenges

```bash
# ─── Vision AI ───

# Webcam: detect and follow a person (with display window)
python -m src.vision.vision_node person

# Simulated camera: synthetic moving target (no camera needed)
python -m src.vision.vision_node person --sim

# Simulated camera + pipe velocity commands to executor
python -m src.vision.vision_node person --sim --executor

# Headless mode (no display, for automated testing)
python -m src.vision.vision_node person --sim --executor --frames 30 --headless

# Video file: process a pre-recorded video
python -m src.vision.vision_node person path/to/video.mp4

# ─── SLAM Navigation ───

# Run the SLAM navigator demo (simulated)
python -m src.slam.slam_navigator

# Run with a specific mission file
python -m src.slam.slam_navigator config/inspection_route.json

# ─── Swarm Formation ───

# Run the formation demo (3 drones, WEDGE formation)
python -m src.swarm.coordinator

# Dispatch a mission across all drones
python -m src.swarm.coordinator config/perimeter_loop.json
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| OS | Ubuntu 22.04 |
| ROS 2 | Humble Hawksbill (LTS) |
| Simulator | Gazebo Harmonic |
| Flight Stack | PX4 v1.15.4 SITL |
| Drone API | MAVSDK-Python |
| LLM | Ollama (local, default) / OpenAI |
| Validation | Pydantic v2 |
| Vision | Ultralytics YOLOv8 |
| Container | Docker + Docker Compose |

## Reproducibility

- **Docker**: Exact pinned versions for all dependencies
- **Headless**: `scripts/verify.sh` proves core works without GUI/GPU
- **GUI opt-in**: X11 forwarding for Gazebo; headless runs without it
- **GPU opt-in**: YOLO falls back to CPU if no NVIDIA runtime

## Project Structure

```
agentic-drones/
├── docker-compose.yml          # Container orchestration
├── docker/
│   ├── Dockerfile              # Pinned environment
│   └── entrypoint.sh           # ROS 2 source
├── src/
│   ├── schema/mission.py       # Pydantic guardrail models
│   ├── validator/validator.py  # 3-layer validation
│   ├── executor/executor.py    # Deterministic state machine
│   ├── llm/llm_node.py         # LLM interface (Ollama/OpenAI)
│   ├── cli/cli.py              # Operator prompt loop
│   ├── vision/vision_node.py   # YOLO + visual servoing
│   ├── vision/sim_camera.py    # Synthetic camera feed
│   ├── swarm/coordinator.py    # Multi-agent formations
│   └── slam/slam_navigator.py  # SLAM + Nav2 integration
├── config/
│   ├── perimeter_loop.json     # 50m square patrol
│   ├── inspection_route.json   # Inspection with loiter
│   └── bad_mission.json        # Unsafe (for demo)
├── scripts/
│   ├── verify.sh               # Headless verification
│   ├── test_validator.py       # Validator test suite
│   └── test_executor_determinism.py
├── narration.txt               # Build log
├── CITATIONS.md                # Open-source credits
└── README.md
```

## Scaling to Real World

The decoupling that makes the demo clean is what makes it safe in production:
- **Same executor code** flies real hardware via MAVSDK (swap UDP for serial)
- **LLM offline** for mission planning, not real-time control
- **Validator geofence** becomes regulatory airspace boundary
- **Failsafe state** handles GPS loss, comms dropout, low battery
- **Multi-agent** coordinator scales with namespaced executors
