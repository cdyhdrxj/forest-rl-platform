"""Настройка Torch и MSVC окружения для обучения.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

_VCVARSALL_DEFAULT = (
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
    r"\VC\Auxiliary\Build\vcvarsall.bat"
)
_TORCHINDUCTOR_CACHE_DIR_DEFAULT = "C:/torchinductor_cache"
_TRITON_CACHE_DIR_DEFAULT = "C:/triton_cache"


def setup_msvc_env(vcvarsall: str = _VCVARSALL_DEFAULT) -> bool:
    if sys.platform != "win32":
        return True
    if not os.path.isfile(vcvarsall):
        print(
            f"[torch_setup] vcvarsall.bat не найден: {vcvarsall}\n"
            "torch.compile с backend='inductor' может не работать на Windows."
        )
        return False
    result = subprocess.run(
        f'"{vcvarsall}" amd64 && set',
        shell=True, capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            os.environ[k] = v
    return True


def check_cl_available() -> bool:
    """Вернуть True если cl.exe доступен в PATH (только Windows)."""
    if sys.platform != "win32":
        return True
    try:
        subprocess.check_output(["cl", "/help"], stderr=subprocess.STDOUT)
        return True
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def _setup_torchinductor_cache(
    inductor_cache: str,
    triton_cache: str,
) -> None:
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = inductor_cache
    os.environ["TRITON_CACHE_DIR"] = triton_cache


def _setup_compile_threads(n: int) -> None:
    import torch._inductor.config as _ind_cfg
    _ind_cfg.compile_threads = n


def configure_torch(
    cpu_cores_num: Optional[int] = None,
    use_torch_compile: bool = False,
    setup_msvc: bool = True,
    inductor_cache: str = _TORCHINDUCTOR_CACHE_DIR_DEFAULT,
    triton_cache: str = _TRITON_CACHE_DIR_DEFAULT,
    compile_threads: int = 1,
) -> None:
    """Единая точка настройки Torch перед началом обучения.

    Вызывается из run_training() до создания среды и модели.

    Args:
        cpu_cores_num:     Если задано — torch.set_num_threads(n).
        use_torch_compile: Настраивает кэши и MSVC если True.
        setup_msvc:        Пытаться ли инъектировать MSVC env на Windows.
        inductor_cache:    Путь для TORCHINDUCTOR_CACHE_DIR.
        triton_cache:      Путь для TRITON_CACHE_DIR.
        compile_threads:   torch._inductor.config.compile_threads.
    """
    import torch

    if cpu_cores_num is not None:
        torch.set_num_threads(cpu_cores_num)

    if use_torch_compile:
        _setup_torchinductor_cache(inductor_cache, triton_cache)
        _setup_compile_threads(compile_threads)
        if setup_msvc and sys.platform == "win32":
            setup_msvc_env()
