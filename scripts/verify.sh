#!/bin/bash
set -e

echo "================================================"
echo "  Omokai Robotics — Headless Verification Script"
echo "================================================"
echo ""

PASS=0
FAIL=0

check() {
    local name="$1"
    shift
    echo -n "  [TEST] $name ... "
    if "$@" > /tmp/verify_$$.log 2>&1; then
        echo "PASS"
        PASS=$((PASS + 1))
    else
        echo "FAIL"
        cat /tmp/verify_$$.log
        FAIL=$((FAIL + 1))
    fi
}

echo "--- Validator Tests ---"
check "Valid mission accepted" python3 scripts/test_validator.py -v test_good_mission 2>/dev/null
check "Unsafe mission rejected" python3 scripts/test_validator.py -v test_bad_mission 2>/dev/null
check "Malformed JSON rejected" python3 scripts/test_validator.py -v test_malformed_json 2>/dev/null
check "No TAKEOFF rejected" python3 scripts/test_validator.py -v test_no_takeoff 2>/dev/null
check "No LAND rejected" python3 scripts/test_validator.py -v test_no_land 2>/dev/null

echo ""
echo "--- Executor Tests ---"
check "Executor determinism" python3 scripts/test_executor_determinism.py 2>/dev/null

echo ""
echo "--- Challenge Modules ---"
check "Swarm coordinator" python3 -c "
from src.swarm.coordinator import SwarmCoordinator, FormationType
c = SwarmCoordinator()
c.add_drone('d1',14540); c.add_drone('d2',14541); c.add_drone('d3',14542)
c.set_formation(FormationType.WEDGE, 'd1')
sp = c.compute_follower_setpoints({'x':10,'y':10,'z':-10,'yaw':0})
assert len(sp) == 3, 'Expected 3 setpoints'
print(f'Swarm: {len(sp)} setpoints computed')
" 2>/dev/null

check "SLAM navigator" python3 -c "
from src.slam.slam_navigator import SLAMNavigator, PathPlanner
n = SLAMNavigator(); n.start_slam_toolbox(); n.start_nav2()
p = PathPlanner(); path = p.plan_route((0,0),(10,10))
assert len(path) >= 3, 'Path too short'
print(f'SLAM: path with {len(path)} waypoints')
" 2>/dev/null

check "Validator with file" python3 -c "
import sys; sys.path.insert(0,'.')
result = __import__('src.validator.validator', fromlist=['validate_mission']).validate_mission
with open('config/perimeter_loop.json') as f: raw = f.read()
r = result(raw)
assert r.valid, f'Perimeter loop rejected: {r.errors}'
print('Validator: perimeter loop accepted')
" 2>/dev/null

check "Bad mission rejected" python3 -c "
import sys; sys.path.insert(0,'.')
result = __import__('src.validator.validator', fromlist=['validate_mission']).validate_mission
with open('config/bad_mission.json') as f: raw = f.read()
r = result(raw)
assert not r.valid, 'Bad mission should have been rejected'
print('Validator: bad mission rejected')
" 2>/dev/null

echo ""
echo "================================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "================================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
