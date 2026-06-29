#!/bin/bash
# Start jMAVSim in TCP mode and wait
set +e

cd /workspace/src/PX4-Autopilot/Tools/simulation/jmavsim/jMAVSim || exit 1
DISPLAY=:1 LIBGL_ALWAYS_SOFTWARE=1 java -jar out/production/jmavsim_run.jar -tcp 127.0.0.1:4560 > /tmp/jmavsim_tcp3.txt 2>&1
echo "Exit code: $?"
