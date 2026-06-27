# Architecture Write-Up

## How Prompt → LLM → JSON → Executor → Sim Fits Together

### The One Design Rule

**The LLM proposes, the validator polices, the executor is deterministic and never imports the LLM.**

The executor can run from a validated JSON file with the LLM process completely killed. This is not a "mode" — it is the only way the system works. The LLM is an optional input transducer; the executor is the actual flight controller.

### Five Contracts (Strict Boundaries)

Every stage communicates through a typed contract, making each stage independently observable, testable, and replaceable:

1. **CLI → LLM**: `str` — plain natural language prompt. The operator types "Patrol the perimeter loop twice at 15 metres" and it arrives as a string.
2. **LLM → Validator**: `str` (raw JSON) — the LLM outputs text that *hopefully* parses into the mission schema. The LLM is allowed to be wrong; that's what the validator is for.
3. **Validator → Executor**: `MissionPlan` (validated Pydantic model) — this only publishes if the JSON passed all 3 layers of validation. Nothing reaches the executor without being checked.
4. **Validator → Operator**: `str` (rejection message) — if validation fails, the operator sees what went wrong.
5. **Executor → Operator**: `dict` (telemetry) — position, flight mode, battery, mission progress.

### Three Validation Layers

**Layer 1 — Structural (parse)**:
- Valid JSON syntax
- Root is a JSON object
- `actions` field exists and is a non-empty array
- Catches garbage output, markdown-wrapped JSON, missing fields

**Layer 2 — Semantic/Safety (the guardrail)**:
- Altitude in [1, 50] meters
- Speed in [0.5, 15] m/s
- Mission must start with TAKEOFF
- Mission must end with LAND or RETURN_TO_LAUNCH
- Waypoint jump distance ≤ 500 meters
- Geofence compliance (if geofence is defined)
- Max 50 actions per mission
- GOTO actions must have waypoints
- TAKEOFF actions must have altitude

**Layer 3 — Re-prompt-on-failure (self-correction)**:
- If validation fails, errors are returned to the LLM with the original prompt
- LLM generates a corrected version
- Up to 3 retries before hard-failing to the operator
- Every attempt is logged for audit

### Deterministic Executor State Machine

```
IDLE → ARMING → TAKEOFF → EXECUTING(action_i) → ... → LANDING → DONE
                              |
                              ↓
                           FAILSAFE
```

- **No randomness**: same JSON input → identical command sequence every time
- **Audit trail**: every command logged with ISO 8601 timestamp
- **File-based operation**: `--mission validated.json` argument, no LLM dependency
- **Failsafe**: any MAVSDK error triggers RTL/land fallback

### How Decoupling Makes It Safe

| Property | How It's Enforced |
|----------|-------------------|
| LLM out of control loop | Executor reads JSON files. Kill LLM → executor still flies. |
| Deterministic | Same JSON → diff audit logs → identical. File-based, no clock branching. |
| Auditable | Every command logged with timestamp. Full replay from log. |
| Fail-safe | State machine has FAILSAFE branch on every action. |

### Data Flow Example

**User types**: "Patrol the perimeter loop twice at 15 metres"

```
1. CLI publishes string to /operator/prompt
2. LLM node generates JSON with TAKEOFF(15m) → 8 GOTO waypoints (2 loops) → LAND
3. Validator Layer 1: JSON parses successfully
4. Validator Layer 2: altitude ≤ 50m ✓, starts TAKEOFF ✓, ends LAND ✓, speeds ≤ 15 ✓
5. Validator publishes MissionPlan to /mission/validated
6. Executor reads mission, connects via MAVSDK, walks state machine:
   ARM → TAKEOFF(15m) → GOTO(50,0,-15) → GOTO(50,50,-15) → ... → LAND → DONE
7. Every command logged with timestamp
```

## Vision AI (Challenge 3) Architecture

```
              ┌─ Webcam ─┐
              │ Video file│
              │ SimCamera │──→ VisionNode.detect() ─→ PID Controller ─→ Executor.set_velocity_body()
              └───────────┘         ↓
                              Image saved (1st detection)
                              Operator: "Target acquired"
```

### Two Detection Modes

1. **YOLOv8 mode** (default): Loads ultralytics YOLO model, runs inference on every frame.
   Filters results by target class ID and confidence threshold.
2. **Mock detection mode** (`--sim` or when ultralytics unavailable): HSV color thresholding
   + contour detection. Falls back to mock when YOLO finds nothing (graceful degradation).

### Simulated Camera (`src/vision/sim_camera.py`)

Generates synthetic 640×480 frames with a bouncing colored circle:
- Circle position follows velocity-vector physics, bouncing off frame edges
- Replaces need for physical camera or Gazebo camera feed in headless demos
- Used with `--sim` flag; `--executor` flag pipes PID output to executor

### PID Visual Servoing

- **Pixel error**: `(cx - frame_center_x, cy - frame_center_y)` where cx,cy is bounding box center
- **Proportional control**: `vx = -Kp_x * error_x`, `vy = -Kp_y * error_y`
- **Depth control**: `vz = Kp_z * (area_target - area_fraction) * 100` (closer when target small)
- **Yaw rate**: `yaw_rate = -Kp_yaw * error_x` (turn toward target horizontally)
- **Clipping**: All velocities clamped to `[-max_speed, +max_speed]`

### Executor Integration

```
PID velocity dict ─→ Executor.set_velocity_body(vx, vy, vz, yaw_rate)
                         ↓
                    [CMD] SET_VELOCITY_BODY logged with timestamp
                         ↓
                    MAVSDK offboard.set_velocity_body() [real mode]
                    Simulation mode fallback [no drone connected]
```

- `Executor.set_velocity_body()` added for offboard velocity control
- In real mode: sends MAVSDK `OffboardVelocityBodyYawspeed` commands to PX4
- In simulation mode: logs every command to audit trail (deterministic)
- Target-lost: sends zero velocity + yaw search rotation (5 deg/s)

### Headless Verification

```bash
python3 -m src.vision.vision_node person --sim --executor --frames 30 --headless
```
Produces 33 audit entries: ARM → TAKEOFF → 30× SET_VELOCITY_BODY → LAND

## Multi-Agent Formations (Challenge 1) Architecture

```
LLM: squad-level intent ("sweep in wedge")
  → Validator checks formation action types
    → Coordinator computes per-drone setpoints
      → Per-drone executors stream offboard velocity
```

- **4 formation types**: LINE, WEDGE, DIAMOND, COLUMN
- **Leader-follower**: leader follows path, followers maintain computed offsets
- **Body-frame transform**: follower offsets rotated by leader yaw

## SLAM/Navigation (Challenge 2) Architecture

```
LiDAR → SLAM Toolbox → /map + /odom → Nav2 → Goal Pose → Velocity Commands
```

- SLAM Toolbox builds occupancy grid online
- Nav2 plans obstacle-free path to goal
- Executor sends NAVIGATE_TO action → Nav2 action server

## Scaling to Real-World Systems

The architecture was designed with production deployment in mind:

1. **SITL → Real hardware**: Executor uses MAVSDK — swap the UDP connection string for a serial radio link (`/dev/ttyUSB0:57600`). The executor code does not change.

2. **LLM off the critical path**: In production, mission planning happens pre-flight or via ground station. The LLM is never needed at flight time.

3. **Geofence → Regulatory boundary**: The validator's geofence becomes a hard airspace boundary with regulatory altitude limits.

4. **Failsafe → Real failsafes**: The FAILSAFE state maps to real PX4 failsafes (RC loss, GPS loss, low battery, geofence breach).

5. **Multi-agent → Fleet orchestration**: The coordinator scales by adding namespaced executors per drone. A fleet manager could handle dynamic join/leave and airspace deconfliction.

6. **What SITL hides**: Real systems need to handle GPS dropout, wind disturbance, comms latency, battery voltage sag, and sensor noise. The deterministic executor + auditable logging makes these failures diagnosable.

7. **YOLO licensing note**: Ultralytics YOLO uses AGPL-3.0. For commercial deployment, either use a permissively-licensed model (e.g., YOLOX Apache-2.0) or obtain a commercial license from Ultralytics.
