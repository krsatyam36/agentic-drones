from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.executor.executor import DeterministicExecutor


def test_determinism():
    print("--- Test: Determinism — same JSON → same audit log ---")

    mission = {
        "mission_id": "test_det_001",
        "target": "drone1",
        "actions": [
            {"type": "TAKEOFF", "altitude": 10, "speed": 5},
            {"type": "GOTO", "waypoint": {"x": 10, "y": 0, "z": -10}, "speed": 5},
            {"type": "GOTO", "waypoint": {"x": 10, "y": 10, "z": -10}, "speed": 5},
            {"type": "GOTO", "waypoint": {"x": 0, "y": 10, "z": -10}, "speed": 5},
            {"type": "GOTO", "waypoint": {"x": 0, "y": 0, "z": -10}, "speed": 5},
            {"type": "LAND"},
        ]
    }

    def run_and_capture(m):
        e = DeterministicExecutor()
        e.connect()
        e.execute_mission(m)
        return e.audit_log

    log1 = run_and_capture(mission)
    log2 = run_and_capture(mission)

    trimmed1 = [{k: v for k, v in entry.items() if k != "timestamp"} for entry in log1]
    trimmed2 = [{k: v for k, v in entry.items() if k != "timestamp"} for entry in log2]

    if trimmed1 == trimmed2:
        print(f"  PASS: Both runs produced identical audit logs ({len(log1)} entries)")
        return True
    else:
        print("  FAIL: Audit logs differ between runs")
        print(f"  Run 1: {json.dumps(trimmed1, indent=2)}")
        print(f"  Run 2: {json.dumps(trimmed2, indent=2)}")
        return False


def test_kill_llm():
    print("\n--- Test: Kill LLM — executor runs from file ---")

    mission_path = Path("config/perimeter_loop.json")
    if not mission_path.exists():
        print("  SKIP: perimeter_loop.json not found")
        return True

    raw = mission_path.read_text()
    mission = json.loads(raw)

    e = DeterministicExecutor()
    e.connect()
    success = e.execute_mission(mission)

    if success:
        print("  PASS: Executor completed mission from file (LLM not needed)")
        print(f"  Audit log: {len(e.audit_log)} commands")
        e.save_audit_log("/tmp/test_kill_llm_log.json")
    else:
        print("  FAIL: Executor did not complete")
    return success


if __name__ == "__main__":
    tests = [test_determinism, test_kill_llm]

    passed = 0
    failed = 0
    for t in tests:
        if t():
            passed += 1
        else:
            failed += 1
        print()

    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
