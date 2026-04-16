#!/bin/bash
set -e

echo "======================================"
echo "   Unity Forest Simulator (Virtual)"
echo "======================================"
echo "Date: $(date)"
echo "Working directory: $(pwd)"
echo "User: $(whoami)"
echo "======================================"

# ---------------- GPU DETECT ----------------
USE_GPU=0

if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi > /dev/null 2>&1; then
        echo "✅ NVIDIA GPU detected"
        USE_GPU=1
    fi
fi

if [ "$USE_GPU" = "1" ]; then
    echo "→ GPU mode enabled"
    export LIBGL_ALWAYS_SOFTWARE=0
    export __NV_PRIME_RENDER_OFFLOAD=1
    export __GLX_VENDOR_LIBRARY_NAME=nvidia
else
    echo "→ CPU mode (software rendering)"
    export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
    export LIBGL_ALWAYS_SOFTWARE=1
fi

# ---------------- VIRTUAL DISPLAY (Xvfb) ----------------
echo ""
echo "Starting virtual display Xvfb on :99..."

# Убить старые процессы
pkill Xvfb 2>/dev/null || true
rm -f /tmp/.X99-lock

# Запуск Xvfb с GLX поддержкой
Xvfb :99 -screen 0 1920x1080x24 +extension GLX +render -ac &
XVFB_PID=$!
export DISPLAY=:99

# Ожидание готовности Xvfb
MAX_WAIT=10
for i in $(seq 1 $MAX_WAIT); do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "✅ Xvfb ready on :99"
        break
    fi
    echo "Waiting for Xvfb... ($i/$MAX_WAIT)"
    sleep 1
done

if ! xdpyinfo -display :99 >/dev/null 2>&1; then
    echo "❌ Xvfb failed to start"
    exit 1
fi

# ---------------- CHECK EXECUTABLE ----------------
cd /linux_build

echo ""
echo "Contents of /linux_build:"
ls -la

if [ ! -f "./simulator.x86_64" ]; then
    echo "❌ simulator.x86_64 not found!"
    exit 1
fi

chmod +x ./simulator.x86_64

# ---------------- UNITY SETTINGS ----------------
# Отключение лишних проверок
export GPU_MAX_HEAP_SIZE=100
export GPU_MAX_ALLOC_PERCENT=100

# ---------------- RUN UNITY ----------------
echo ""
echo "======================================"
echo "Starting Unity simulator..."
echo "Command: ./simulator.x86_64 -screen-fullscreen 0 -batchmode -nographics"
echo "======================================"

# Запуск с минимальными требованиями
./simulator.x86_64 \
    -screen-fullscreen 0 \
    -screen-width 1280 \
    -screen-height 720 \
    -logFile /tmp/unity.log \
    -force-opengl

EXIT_CODE=$?

echo ""
echo "======================================"
echo "Unity exited with code: $EXIT_CODE"
echo "======================================"

if [ $EXIT_CODE -ne 0 ]; then
    echo "Last 50 lines of log:"
    tail -50 /tmp/unity.log 2>/dev/null || echo "No log file found"
fi

exit $EXIT_CODE