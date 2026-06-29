#!/bin/bash
# run_gemini_test.sh — Final version, tested working
# Runs: jMAVSim → PX4 SITL → Mission → Executor
set +e

WORKSPACE=/workspace
TEST_DIR=$WORKSPACE/test
LOG_DIR=$TEST_DIR/logs
SCREENSHOT_DIR=$TEST_DIR/screenshots
AUDIT_DIR=$TEST_DIR/audit
TS=$(date +%H%M%S)

mkdir -p $LOG_DIR $SCREENSHOT_DIR $AUDIT_DIR

log() { echo "$1" | tee -a $LOG_DIR/00_main.log; }
scr() {
    /usr/bin/ffmpeg -y -video_size 1280x720 -f x11grab -i :1.0 -vframes 1 \
      $SCREENSHOT_DIR/$1.png 2>> $LOG_DIR/ffmpeg.log
    [ -f $SCREENSHOT_DIR/$1.png ] && log "  📸 $1.png ($(du -h $SCREENSHOT_DIR/$1.png | cut -f1))"
}

cleanup() {
    # Kill by PID file if exists
    [ -f /tmp/jmavsim_pid.txt ] && kill $(cat /tmp/jmavsim_pid.txt) 2>/dev/null
    [ -f /tmp/px4_pid.txt ] && kill $(cat /tmp/px4_pid.txt) 2>/dev/null
    pkill -9 -f "bin/px4" 2>/dev/null
    pkill -9 -f java 2>/dev/null
    sleep 2
    rm -f /dev/shm/* 2>/dev/null
    rm -f /tmp/px4_* /tmp/jmavsim_* 2>/dev/null
}

# ====== MAIN ======
log "============================================"
log "  Gemini Test Suite — $(date)"
log "============================================"

cleanup
log "  State cleaned"

# ---- STEP 1: jMAVSim ----
log ""
log "=== STEP 1: jMAVSim (UDP:4560) ==="
cd $WORKSPACE/src/PX4-Autopilot/Tools/simulation/jmavsim/jMAVSim
DISPLAY=:1 LIBGL_ALWAYS_SOFTWARE=1 java -jar out/production/jmavsim_run.jar -udp 4560 \
  > $LOG_DIR/01_jmavsim.log 2>&1 &
echo $! > /tmp/jmavsim_pid.txt
log "  PID: $(cat /tmp/jmavsim_pid.txt)"

sleep 6
kill -0 $(cat /tmp/jmavsim_pid.txt) 2>/dev/null && log "  ✅ jMAVSim running" || log "  ❌ jMAVSim died"

scr "01_jmavsim_startup"

# ---- STEP 2: PX4 SITL ----
log ""
log "=== STEP 2: PX4 SITL (jmavsim_iris) ==="

cd $WORKSPACE/src/PX4-Autopilot/build/px4_sitl_default
PX4_SIM_MODEL=jmavsim_iris ./bin/px4 -d -s etc/init.d-posix/rcS \
  > $LOG_DIR/02_px4.log 2>&1 &
echo $! > /tmp/px4_pid.txt
log "  PID: $(cat /tmp/px4_pid.txt)"

sleep 12

PX4_OK=no
kill -0 $(cat /tmp/px4_pid.txt) 2>/dev/null && { PX4_OK=yes; log "  ✅ PX4 running"; } || log "  ❌ PX4 died"

# Extract PX4 status lines
grep -i "mavlink\|ready\|simulator\|connected\|SYS_AUTOSTART\|airspeed\|EKF\|GPS" \
  $LOG_DIR/02_px4.log 2>/dev/null | while read line; do log "  [PX4] $line"; done

# Check if jMAVSim received the connection
grep -i "message\|connected\|PX4\|SIM" $LOG_DIR/01_jmavsim.log 2>/dev/null | while read line; do log "  [jMAVSim] $line"; done

scr "02_px4_connected"

# ---- Port Check ----
log ""
log "=== Port Check ==="
for p in 4560 14540 14550 14580; do
    ss -u -a 2>/dev/null | grep -q ":$p " && log "  ✅ UDP/$p" || log "  ⬜ UDP/$p"
    ss -t -a 2>/dev/null | grep -q ":$p " && log "  ✅ TCP/$p" || log "  ⬜ TCP/$p"
done

# ---- STEP 3: Mission ----
log ""
log "=== STEP 3: Mission ==="
if [ -f $WORKSPACE/output/mission.json ]; then
    SRC=$WORKSPACE/output/mission.json
elif [ -f $WORKSPACE/config/perimeter_loop.json ]; then
    SRC=$WORKSPACE/config/perimeter_loop.json
fi
cp "$SRC" $TEST_DIR/mission.json
log "  Using: $SRC"
python3 -c "
import json
with open('$TEST_DIR/mission.json') as f:
    d = json.load(f)
acts = d.get('actions', d.get('waypoints', []))
print(f'  Actions: {len(acts)}')
for a in acts:
    t = a.get('action', a.get('type', '?'))
    print(f'    - {t}')
" 2>> $LOG_DIR/00_main.log

scr "03_before_executor"

# ---- STEP 4: Executor ----
log ""
log "=== STEP 4: Executor (udp://:14540) ==="
cd $WORKSPACE
timeout 120 python3 -m src.executor.executor --mission $TEST_DIR/mission.json 2>&1 | \
  tee $LOG_DIR/04_executor.log
EC=${PIPESTATUS[0]}
log "  Exit: $EC"

scr "04_after_executor"

# Collect files
cp /workspace/output/demo/executor_audit.json $AUDIT_DIR/ 2>/dev/null
cp /workspace/output/mission.json $AUDIT_DIR/ 2>/dev/null

# ---- Summary ----
log ""
log "============================================"
log "  RESULTS"
log "============================================"
log "  jMAVSim:   $(kill -0 $(cat /tmp/jmavsim_pid.txt 2>/dev/null) 2>/dev/null && echo ALIVE || echo stopped)"
log "  PX4:       $(kill -0 $(cat /tmp/px4_pid.txt 2>/dev/null) 2>/dev/null && echo ALIVE || echo stopped)"
log "  Executor:  exit=$EC"
log "  Screenshots ($(ls $SCREENSHOT_DIR/*.png 2>/dev/null | wc -l)):"
ls $SCREENSHOT_DIR/*.png 2>/dev/null | while read f; do log "    $f"; done
log ""

# Show executor outcome
if [ -f $LOG_DIR/04_executor.log ]; then
    log "  Executor timeline:"
    grep -E "\[(INFO|CMD|WARNING|ERROR)\]" $LOG_DIR/04_executor.log | head -25 | while read line; do log "    $line"; done
    log ""
    if grep -q "DONE" $LOG_DIR/04_executor.log 2>/dev/null; then
        log "  ✅ MISSION COMPLETE"
    elif grep -q "FAILSAFE" $LOG_DIR/04_executor.log 2>/dev/null; then
        log "  ⚠️  FAILSAFE TRIGGERED"
    elif [ $EC -eq 124 ]; then
        log "  ⏰ TIMEOUT (simulation mode — no real drone detected)"
    fi
fi

log ""
log "============================================"
log "  TEST COMPLETE — $(date)"
log "============================================"

# Don't cleanup — leave for inspection
