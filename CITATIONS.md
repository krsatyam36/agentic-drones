# Citations & Sources

This project builds on several open-source works. Each entry lists what was taken and the license.

---

## Core Dependencies

| Source | License | What we used |
|--------|---------|-------------|
| [PX4/PX4-Autopilot](https://github.com/PX4/PX4-Autopilot) | BSD-3-Clause | Flight stack + SITL simulation. Pinned to v1.15.4. |
| [mavlink/MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python) | BSD-3-Clause | Python API for drone communication (arm, takeoff, goto, land). |
| [ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) | AGPL-3.0 | YOLOv8 object detection model used in vision challenge. |
| [pydantic/pydantic](https://github.com/pydantic/pydantic) | MIT | Schema validation (MissionPlan, Action models). |
| [openai/openai-python](https://github.com/openai/openai-python) | MIT | LLM backend for prompt-to-JSON generation. |
| [ollama/ollama](https://github.com/ollama/ollama) | MIT | Local LLM serving (default backend). |

## ROS 2 Ecosystem

| Source | License | What we used |
|--------|---------|-------------|
| [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2) | Apache-2.0 | Nav2 stack reference for SLAM/navigation challenge. |
| [SteveMacenski/slam_toolbox](https://github.com/SteveMacenski/slam_toolbox) | LGPL-2.1 | 2D SLAM reference for mapping + localization. |

## Architecture & Design References

| Source | License | What we used |
|--------|---------|-------------|
| [SathanBERNARD/PX4-ROS2-Gazebo-Drone-Simulation-Template](https://github.com/SathanBERNARD/PX4-ROS2-Gazebo-Drone-Simulation-Template) | MIT | Reference for PX4 + ROS 2 Humble + Gazebo Harmonic integration pattern. |
| [monemati/PX4-ROS2-Gazebo-YOLOv8](https://github.com/monemati/PX4-ROS2-Gazebo-YOLOv8) | MIT | Reference for vision + drone integration architecture. |
| [artastier/PX4_Swarm_Controller](https://github.com/artastier/PX4_Swarm_Controller) | MIT | Reference for leader-follower formation control on PX4. |
| [Gaurang-1402/ChatDrones](https://github.com/Gaurang-1402/ChatDrones) | MIT | Reference for NL-to-drone ROS 2 pipeline architecture. |

## Our Own Code

The following files were written from scratch for this submission:
- `src/schema/mission.py` — Pydantic schema with semantic validators
- `src/validator/validator.py` — 3-layer validation pipeline
- `src/executor/executor.py` — Deterministic state-machine executor
- `src/llm/llm_node.py` — Dual-backend LLM interface
- `src/cli/cli.py` — Operator CLI
- `src/vision/vision_node.py` — YOLO detection + visual servoing
- `src/swarm/coordinator.py` — Multi-agent formation coordinator
- `src/slam/slam_navigator.py` — SLAM/Nav2 integration layer
- `docker/Dockerfile`, `docker-compose.yml` — Reproducible environment
- `scripts/verify.sh` — Headless verification
- `config/*.json` — Example missions
