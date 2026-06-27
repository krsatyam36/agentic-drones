#!/bin/bash
set -e

if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
fi

if [ -f /workspace/install/setup.bash ]; then
    source /workspace/install/setup.bash
fi

if ! python3 -c "import ultralytics" 2>/dev/null; then
    echo "[SETUP] Installing ultralytics + torch (first run only)..."
    pip install --no-cache-dir --ignore-installed sympy ultralytics==8.3.0
    echo "[SETUP] ultralytics ready"
fi
python3 -c "import ultralytics; print(f'[READY] ultralytics {ultralytics.__version__}')"

exec "$@"
