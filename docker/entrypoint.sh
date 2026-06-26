#!/bin/bash
set -e

source /opt/ros/humble/setup.bash

source /workspace/install/setup.bash 2>/dev/null || true

exec "$@"
