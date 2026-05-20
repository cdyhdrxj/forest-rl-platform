FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_GL_VERSION_OVERRIDE=4.5
ENV MESA_GLSL_VERSION_OVERRIDE=450

RUN apt-get update && apt-get install -y \
    xvfb \
    libglu1-mesa \
    libgl1-mesa-dri \
    mesa-vulkan-drivers \
    libxcursor1 libxinerama1 libxi6 libxrandr2 \
    libglib2.0-0 libgtk-3-0 \
    libasound2 \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем уже собранный Unity билд (Linux Server Build)
COPY linux_build /linux_build/
RUN chmod +x /linux_build/simulator.x86_64

# Стартовый скрипт
COPY entrypoint.unity.sh /entrypoint.unity.sh
RUN chmod +x /entrypoint.unity.sh

EXPOSE 80 443

CMD ["/entrypoint.unity.sh"]