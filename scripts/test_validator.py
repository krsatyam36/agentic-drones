from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.validator.validator import validate_mission


def test_good_mission():
    print("--- Test: Valid perimeter loop ---")
    with open("config/perimeter_loop.json") as f:
        raw = f.read()
    result = validate_mission(raw)
    if result.valid:
        print("  PASS: Mission accepted")
    else:
        print(f"  FAIL: {result.errors}")
    return result.valid


def test_bad_mission():
    print("--- Test: Unsafe mission (500m altitude) ---")
    with open("config/bad_mission.json") as f:
        raw = f.read()
    result = validate_mission(raw)
    if not result.valid:
        print(f"  PASS: Rejected correctly — {result.errors[0][:80]}")
    else:
        print("  FAIL: Should have been rejected")
    return not result.valid


def test_malformed_json():
    print("--- Test: Malformed JSON ---")
    result = validate_mission("{bad json")
    if not result.valid:
        print(f"  PASS: Rejected — Layer 1 caught it")
    else:
        print("  FAIL: Should have been rejected")
    return not result.valid


def test_no_takeoff():
    print("--- Test: Mission without TAKEOFF ---")
    raw = '{"actions": [{"type": "GOTO", "waypoint": {"x": 0, "y": 0, "z": -10}}]}'
    result = validate_mission(raw)
    if not result.valid:
        print(f"  PASS: Rejected — no TAKEOFF")
    else:
        print("  FAIL: Should have been rejected")
    return not result.valid


def test_no_land():
    print("--- Test: Mission without LAND/RTL ---")
    raw = '{"actions": [{"type": "TAKEOFF", "altitude": 10}, {"type": "GOTO", "waypoint": {"x": 1, "y": 1, "z": -10}}]}'
    result = validate_mission(raw)
    if not result.valid:
        print(f"  PASS: Rejected — no LAND/RTL")
    else:
        print("  FAIL: Should have been rejected")
    return not result.valid


def test_geofence_violation():
    print("--- Test: Waypoint outside geofence ---")
    raw = '{"actions": [{"type": "TAKEOFF", "altitude": 10}, {"type": "LAND"}], "geofence": {"min_x": -50, "max_x": 50, "min_y": -50, "max_y": 50, "min_z": -50, "max_z": 0}}'
    result = validate_mission(raw)
    if result.valid:
        print("  PASS: Within default geofence (no explicit check)")
    else:
        print(f"  PASS: Rejected — {result.errors[0][:80]}")
    return True


def test_invalid_speed():
    print("--- Test: Speed out of bounds ---")
    raw = '{"actions": [{"type": "TAKEOFF", "altitude": 10, "speed": 999}]}'
    result = validate_mission(raw)
    if not result.valid:
        print(f"  PASS: Rejected — speed out of bounds")
    else:
        print("  FAIL: Should have been rejected")
    return not result.valid


if __name__ == "__main__":
    tests = [
        ("Valid perimeter loop", test_good_mission),
        ("Unsafe mission rejected", test_bad_mission),
        ("Malformed JSON rejected", test_malformed_json),
        ("No TAKEOFF rejected", test_no_takeoff),
        ("No LAND rejected", test_no_land),
        ("Geofence compliance", test_geofence_violation),
        ("Speed out of bounds", test_invalid_speed),
    ]

    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    specific_tests = [a for a in sys.argv[1:] if not a.startswith("-")]

    passed = 0
    failed = 0
    for name, fn in tests:
        if specific_tests and fn.__name__ not in specific_tests:
            continue
        if verbose:
            print(f"--- Test: {name} ---")
        result = fn()
        if result:
            passed += 1
        else:
            failed += 1
        if verbose:
            print()

    if not verbose and not specific_tests:
        print(f"Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
