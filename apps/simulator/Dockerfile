FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем только нужное (БЕЗ xvfb, fluxbox, x11vnc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Графические библиотеки для Unity
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    libxcursor1 \
    libxrandr2 \
    libxcomposite1 \
    libxi6 \
    libxinerama1 \
    libxext6 \
    libxfixes3 \
    libxrender1 \
    libxxf86vm1 \
    # X11 клиент
    libx11-6 \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя
RUN groupadd --gid 2000 unity && \
    useradd --gid 2000 --uid 2000 --create-home --shell /bin/bash unity

WORKDIR /linux_build

# Копируем скрипт запуска
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Копируем билд Unity
COPY linux_build /linux_build/

# Проверка
RUN ls -la /linux_build/ && \
    if [ ! -f /linux_build/simulator.x86_64 ]; then \
        echo "simulator.x86_64 not found!"; \
        exit 1; \
    fi

RUN chown -R unity:unity /linux_build /entrypoint.sh

USER unity

EXPOSE 10000

ENTRYPOINT ["/entrypoint.sh"]