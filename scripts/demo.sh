#!/bin/bash
# Agentic Drones — Demo Script (runs inside xterm)
set -e

DEMO_DIR="/workspace/output/demo"
mkdir -p "$DEMO_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Agentic Drones — Omokai Robotics Demo                   ║"
echo "║     Prompt → LLM → Validated JSON → Executor → Simulator    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

sleep 2

# ─── 1. Headless Verification ───
echo ""
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo "▓  STEP 1: Headless Verification (10 tests)                ▓"
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo ""
sleep 1

cd /workspace
bash scripts/verify.sh
echo ""
sleep 2

# ─── 2. CLI Pipeline ───
echo ""
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo "▓  STEP 2: Prompt → LLM → Validator → Saved Mission        ▓"
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo ""
sleep 1

echo ">>> Enter command: Patrol the perimeter loop twice at 15 metres"
echo ""
python3 -c "
from src.llm.llm_node import LLMNode
from src.validator.validator import validate_mission
import json

prompt = 'Patrol the perimeter loop twice at 15 metres'
node = LLMNode(backend='ollama', model='llama3.2')
raw = node.generate(prompt)
print('[LLM RAW] Mission JSON generated')
print(raw[:200] + '...')
print()

def llm_callback(p, raw, errors):
    return node.generate(p, errors)

result = validate_mission(raw, prompt, llm_callback=llm_callback)
if result.valid:
    mission = result.mission.model_dump()
    path = 'output/demo/mission.json'
    with open(path, 'w') as f:
        json.dump(mission, f, indent=2)
    print(f'[VALIDATOR] ✅ PASS (layer {result.layer})')
    print(f'[SAVED] Mission written to {path}')
    print(f'  Actions: {len(mission[\"actions\"])} waypoints')
else:
    print(f'[VALIDATOR] ❌ FAIL: {result.errors}')
"
echo ""
sleep 3

# ─── 3. Kill-the-LLM Executor ───
echo ""
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo "▓  STEP 3: Deterministic Executor (Kill-the-LLM Demo)       ▓"
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo ""
sleep 1

echo "Running executor with perimeter_loop.json (no LLM needed)..."
echo ""
python3 -m src.executor.executor --mission config/perimeter_loop.json --log output/demo/executor_audit.json
echo ""
echo "Audit log preview:"
python3 -c "
import json
with open('output/demo/executor_audit.json') as f:
    log = json.load(f)
for entry in log:
    ts = entry['timestamp'][-13:-4]
    print(f'  {ts}  [{entry[\"action\"]:20s}]  {entry[\"detail\"]}')
"
echo ""
sleep 3

# ─── 4. Vision AI ───
echo ""
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo "▓  STEP 4: Vision AI — Detection + Follow (Sim Camera)     ▓"
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo ""
sleep 1

echo "Running vision node with simulated camera..."
echo "Target: person | Mode: sim + executor | Frames: 15 | Headless"
echo ""
python3 -m src.vision.vision_node person --sim --executor --frames 15 --headless 2>&1
echo ""
echo "Detection image saved:"
ls -la output/detections/ 2>/dev/null | tail -1
echo ""
sleep 2

# ─── 5. Swarm Coordinator Demo ───
echo ""
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo "▓  STEP 5: Swarm Formation (3-drone WEDGE)                  ▓"
echo "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
echo ""
sleep 1

python3 -c "
from src.swarm.coordinator import SwarmCoordinator, FormationType
c = SwarmCoordinator()
c.add_drone('drone1',14540); c.add_drone('drone2',14541); c.add_drone('drone3',14542)
c.set_formation(FormationType.WEDGE, leader_id='drone1')
print('WEDGE Formation Setpoints:')
for wp_idx, (x,y,z) in enumerate([(0,0,-10),(20,0,-10),(20,20,-10)]):
    sp = c.compute_follower_setpoints({'x':x,'y':y,'z':z,'yaw':0})
    print(f'  Waypoint {wp_idx}: leader=({x},{y},{z})')
    for did, pt in sp.items():
        print(f'    {did}: ({pt[\"x\"]:.1f}, {pt[\"y\"]:.1f}, {pt[\"z\"]:.1f})')
"
echo ""
sleep 2

# ─── Done ───
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  DEMO COMPLETE ✅                                         ║"
echo "║  All pipeline stages verified successfully                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
sleep 2
