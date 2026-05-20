#!/bin/bash

pkill Xvfb 2>/dev/null || true
rm -f /tmp/.X99-lock

# Запускаем виртуальный дисплей
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp &
XVFB_PID=$!

# Ждём пока Xvfb поднимется
sleep 2

# Экспортируем переменные окружения
export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_GL_VERSION_OVERRIDE=4.5

# Запускаем Unity билд
exec env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 \
    /linux_build/simulator.x86_64 \
    -logFile /dev/stdout \
    -screen-width 1280 \
    -screen-height 720