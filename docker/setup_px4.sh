#!/bin/bash
set -e

PX4_VERSION="${PX4_VERSION:-v1.15.4}"
WORKSPACE="${WORKSPACE:-/workspace}"
PX4_DIR="${WORKSPACE}/src/PX4-Autopilot"

echo "================================================"
echo "  PX4 SITL Setup Script"
echo "================================================"

if [ -d "$PX4_DIR" ] && [ -f "${PX4_DIR}/build/px4_sitl_default/bin/px4" ]; then
    echo "[OK] PX4 SITL already built at ${PX4_DIR}"
    exit 0
fi

if [ ! -d "$PX4_DIR" ]; then
    echo "[STEP] Cloning PX4-Autopilot ${PX4_VERSION} ..."
    git clone --depth 1 --branch ${PX4_VERSION} https://github.com/PX4/PX4-Autopilot.git ${PX4_DIR}
    cd ${PX4_DIR}
    git submodule update --init --recursive --depth 1
    echo "[OK] PX4 source cloned"
else
    cd ${PX4_DIR}
fi

echo "[STEP] Building PX4 SITL (Gazebo Classic)..."
echo "  This takes 20-40 min on first build."
echo "  Subsequent starts use ccache and are faster."

cd ${PX4_DIR}
make px4_sitl gazebo-classic 2>&1 | tail -20

if [ -f "${PX4_DIR}/build/px4_sitl_default/bin/px4" ]; then
    echo "[OK] PX4 SITL build complete"
    echo "export PATH=\${PATH}:${PX4_DIR}/build/px4_sitl_default/bin" >> ~/.bashrc
else
    echo "[ERROR] PX4 build failed"
    exit 1
fi

echo ""
echo "PX4 SITL ready. Start with:"
echo "  cd ${PX4_DIR} && make px4_sitl gazebo-classic"
