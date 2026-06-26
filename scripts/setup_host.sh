#!/bin/bash
set -e

echo "================================================"
echo "  Omokai Robotics — Host Setup Script"
echo "  Ubuntu 22.04 / 24.04"
echo "================================================"

PYTHON_DEPS=(
    "mavsdk==3.0.0"
    "pydantic==2.10.0"
    "openai==1.55.0"
    "opencv-python-headless==4.10.0.84"
    "numpy==1.26.4"
    "requests==2.32.0"
    "fastapi==0.115.0"
    "uvicorn==0.32.0"
    "pymavlink==2.4.43"
    "ultralytics==8.3.0"
)

echo "[STEP] Installing Python dependencies..."
pip3 install --upgrade pip
for dep in "${PYTHON_DEPS[@]}"; do
    echo "  Installing $dep ..."
    pip3 install "$dep" 2>/dev/null || echo "  (continuing without $dep)"
done

echo "[STEP] Installing Ollama (local LLM)..."
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/install.sh | bash
else
    echo "  Ollama already installed"
fi

echo ""
echo "================================================"
echo "  Setup complete!"
echo ""
echo "  Run the pipeline:"
echo "    python3 -m src.cli.cli"
echo ""
echo "  Run verification:"
echo "    bash scripts/verify.sh"
echo "================================================"
