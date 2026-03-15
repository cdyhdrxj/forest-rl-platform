#!/bin/bash
set -e

echo "======================================"
echo "   Unity Forest Simulator Startup"
echo "======================================"
echo "Date: $(date)"
echo "Working directory: $(pwd)"
echo "User: $(whoami)"
echo "DISPLAY=$DISPLAY"
echo "======================================"

# Проверяем подключение к X серверу
echo "🔍 Testing X11 connection..."
if ! xdpyinfo >/dev/null 2>&1; then
    echo "Cannot connect to X server at $DISPLAY"
    echo ""
    echo "ПРОВЕРЬТЕ:"
    echo "1. XLaunch запущен?"
    echo "2. В XLaunch включен 'Disable access control'?"
    echo "3. Попробуйте: export DISPLAY=$(ip route | grep default | awk '{print $3}'):0.0"
    exit 1
fi
echo "Connected to X server at $DISPLAY"

# Переходим в папку с билдом
cd /linux_build
echo "Contents of /linux_build:"
ls -la

# Проверяем наличие исполняемого файла
if [ ! -f "./simulator.x86_64" ]; then
    echo "simulator.x86_64 not found!"
    exit 1
fi

# Создаем папку для логов
echo "Creating logs directory with proper permissions..."
mkdir -p ./logs
echo "Logs directory ready at: $(pwd)/logs"

# Запускаем Unity
echo "Starting Unity simulator..."
echo "Command: ./simulator.x86_64 -logfile ./logs/unity_$(date +%Y%m%d_%H%M%S).log -screen-fullscreen 0"

./simulator.x86_64 \
    -logfile "./logs/unity_$(date +%Y%m%d_%H%M%S).log" \
    -screen-fullscreen 0

echo "Unity simulator stopped unexpectedly"
exit 1