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
    # Fetch tags for version header generation (full depth for tags — they're small)
    echo "[INFO] Fetching tags (full depth)..."
    git fetch --tags 2>/dev/null || true
    # NuttX submodule also needs tags for version header generation
    if [ -d "platforms/nuttx/NuttX/nuttx/.git" ]; then
        git -C platforms/nuttx/NuttX/nuttx fetch --tags --depth 100 2>/dev/null || true
    fi
    echo "[OK] PX4 source cloned"
else
    cd ${PX4_DIR}
    # Ensure tags are available (shallow clone issue)
    git fetch --tags 2>/dev/null || true
fi

echo "[STEP] Building PX4 SITL..."
echo "  This takes 20-40 min on first build."
echo "  Subsequent starts use ccache and are faster."

cd ${PX4_DIR}

# Clean stale build artifacts from previous failed attempts
if [ -f "build/px4_sitl_default/CMakeCache.txt" ]; then
    echo "[INFO] Cleaning stale build cache..."
    rm -rf build/px4_sitl_default
fi

# Try gazebo-classic first (PX4 ≤1.14), then new Gazebo (1.15+), fall back to headless
if make px4_sitl gazebo-classic 2>/dev/null; then
    echo "[OK] PX4 SITL built with gazebo-classic"
elif make px4_sitl gz_x500 2>/dev/null; then
    echo "[OK] PX4 SITL built with gz_x500 (new Gazebo)"
else
    echo "[WARN] Simulator targets unavailable, building headless px4_sitl..."
    make px4_sitl 2>&1 | tail -20
fi

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
