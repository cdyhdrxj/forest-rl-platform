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

# Запускаем Unity БЕЗ логов!
echo "Starting Unity simulator (logging disabled)..."
echo "Command: ./simulator.x86_64 -screen-fullscreen 0"

./simulator.x86_64 -screen-fullscreen 0

echo "Unity simulator stopped unexpectedly"
exit 1