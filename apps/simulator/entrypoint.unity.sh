#!/bin/bash
set -euo pipefail

pkill Xvfb 2>/dev/null || true
rm -f /tmp/.X99-lock

export DISPLAY="${DISPLAY:-:99}"
export MESA_GL_VERSION_OVERRIDE="${MESA_GL_VERSION_OVERRIDE:-4.5}"
export MESA_GLSL_VERSION_OVERRIDE="${MESA_GLSL_VERSION_OVERRIDE:-450}"

if [ "${UNITY_SOFTWARE_RENDERING:-0}" = "1" ]; then
    export LIBGL_ALWAYS_SOFTWARE=1
else
    unset LIBGL_ALWAYS_SOFTWARE
fi

if [ "${UNITY_REQUIRE_NVIDIA:-0}" = "1" ] && [ "${UNITY_SOFTWARE_RENDERING:-0}" != "1" ]; then
    if ! command -v nvidia-smi >/dev/null 2>&1 || ! nvidia-smi >/dev/null 2>&1; then
        echo "NVIDIA GPU is required for this compose profile, but nvidia-smi is not available." >&2
        echo "Use docker-compose.cpu.yml only for explicit CPU-only development runs." >&2
        exit 42
    fi
fi

link_nvidia_runtime_library() {
    local name="$1"
    local lib_dir="/usr/lib/x86_64-linux-gnu"

    if [ ! -e "${lib_dir}/${name}.so" ] && [ -e "${lib_dir}/${name}.so.1" ]; then
        ln -s "${name}.so.1" "${lib_dir}/${name}.so" 2>/dev/null || true
    fi
}

link_library_alias() {
    local lib_dir="$1"
    local alias="$2"
    local target="$3"

    if [ ! -e "${lib_dir}/${alias}" ] && [ -e "${lib_dir}/${target}" ]; then
        ln -s "${target}" "${lib_dir}/${alias}" 2>/dev/null || true
    fi
}

link_nvidia_runtime_library libnvidia-encode
link_library_alias /usr/lib/x86_64-linux-gnu libdl libdl.so.2
link_library_alias /usr/lib/x86_64-linux-gnu libdl.so libdl.so.2

Xvfb "${DISPLAY}" -screen 0 "${UNITY_SCREEN:-1280x720x24}" -nolisten tcp &
XVFB_PID=$!

cleanup() {
    kill "${XVFB_PID}" 2>/dev/null || true
}
trap cleanup EXIT

sleep "${XVFB_STARTUP_DELAY:-2}"

UNITY_ARGS=(
    -logFile /dev/stdout
    -screen-width "${UNITY_SCREEN_WIDTH:-1280}"
    -screen-height "${UNITY_SCREEN_HEIGHT:-720}"
)

case "${UNITY_GRAPHICS_API:-vulkan}" in
    vulkan)
        UNITY_ARGS=(-force-vulkan "${UNITY_ARGS[@]}")
        ;;
    glcore|opengl)
        UNITY_ARGS=(-force-glcore "${UNITY_ARGS[@]}")
        ;;
    auto|"")
        ;;
    *)
        echo "Unknown UNITY_GRAPHICS_API='${UNITY_GRAPHICS_API}'. Expected vulkan, glcore or auto." >&2
        exit 43
        ;;
esac

if [ "${UNITY_HEADLESS_NO_GRAPHICS:-0}" = "1" ]; then
    UNITY_ARGS=(-batchmode -nographics "${UNITY_ARGS[@]}")
fi

exec env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 \
    /linux_build/simulator.x86_64 "${UNITY_ARGS[@]}"
