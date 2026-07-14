"""Пакетная валидация чекпоинтов AltDRQN.

Структура выходной директории
------------------------------
  output_dir/
    {полное_имя_папки_запуска}/
      {имя_чекпоинта_без_pt}/
        heatmap_visits.npy / .png
        heatmap_idleness_mean.npy / .png
        heatmap_idleness_max.npy / .png
        heatmap_intruders.npy / .png
        heatmap_damage.npy / .png
        action_histogram.npy / .png
        invalid_actions.png
        episodes.csv
        steps.csv

"""

import argparse
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

_DIR = os.path.abspath(os.path.dirname(__file__))

_DEFAULT_VAL_CONFIG = os.path.join(_DIR, "test_configs", "forest_16x16_val_v3.json")
_DEFAULT_EXCLUDE    = ["terrain"]
_DEFAULT_N_EPISODES = 20
_DEFAULT_SEED       = 2026
_DEFAULT_DEVICE     = "cuda"
_DEFAULT_RUNS_ROOT  = os.path.join(PROJECT_ROOT, "runs", "16x16_forest")

# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

def _gui_select() -> tuple[str, str, str] | None:
    """Показать диалог выбора источника и выходной папки.

    Возвращает (mode, source_path, output_dir) или None при отмене.
    """
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    result: list = []

    root = tk.Tk()
    root.title("Validate checkpoints")
    root.resizable(False, False)
    root.update_idletasks()
    w, h = 460, 200
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth()-w)//2}+{(root.winfo_screenheight()-h)//2}")

    tk.Label(root, text="Шаг 1 — выберите источник чекпоинтов:", font=("Segoe UI", 10, "bold")).pack(pady=(14, 6))

    btn_frame = tk.Frame(root)
    btn_frame.pack()

    output_var = tk.StringVar()

    def _pick_output():
        d = filedialog.askdirectory(title="Куда сохранять результаты", initialdir=PROJECT_ROOT)
        if d:
            output_var.set(d)

    def _proceed(mode: str, path: str):
        if not output_var.get():
            messagebox.showwarning("Нет выходной папки", "Сначала выберите папку для результатов.")
            return
        root.destroy()
        result.append((mode, path, output_var.get()))

    def _pick(mode: str):
        root.withdraw()
        if mode == "checkpoint":
            path = filedialog.askopenfilename(
                title="Выберите чекпоинт (.pt)",
                initialdir=_DEFAULT_RUNS_ROOT,
                filetypes=[("PyTorch checkpoint", "*.pt"), ("Все файлы", "*.*")],
            )
        else:
            titles = {
                "run_dir":   "Выберите папку одного запуска",
                "runs_root": "Выберите корневую папку (все запуски внутри)",
            }
            path = filedialog.askdirectory(title=titles[mode], initialdir=_DEFAULT_RUNS_ROOT)
        root.deiconify()
        if path:
            _proceed(mode, path)

    # ttk.Button(btn_frame, text="Один чекпоинт (.pt)", width=22, command=lambda: _pick("checkpoint")).grid(row=0, column=0, padx=5)
    ttk.Button(btn_frame, text="Один запуск",          width=22, command=lambda: _pick("run_dir")).grid(row=0, column=1, padx=5)
    # ttk.Button(btn_frame, text="Все запуски в папке",  width=22, command=lambda: _pick("runs_root")).grid(row=0, column=2, padx=5)

    sep = ttk.Separator(root, orient="horizontal")
    sep.pack(fill="x", padx=20, pady=10)

    tk.Label(root, text="Шаг 2 — выберите выходную папку:", font=("Segoe UI", 10, "bold")).pack()
    out_frame = tk.Frame(root)
    out_frame.pack(pady=4)
    tk.Entry(out_frame, textvariable=output_var, width=42, state="readonly").pack(side="left", padx=(0, 6))
    ttk.Button(out_frame, text="Обзор…", command=_pick_output).pack(side="left")

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()

    return result[0] if result else None


# ---------------------------------------------------------------------------
# Определение алгоритма и поиск чекпоинтов
# ---------------------------------------------------------------------------

def _detect_algorithm(run_dir: str) -> str:
    """Определить алгоритм по имени папки запуска."""
    name = os.path.basename(run_dir).lower()
    # Порядок важен: проверяем более специфичные варианты первыми
    if "alt_drqn" in name or ("drqn" in name and "dqn" not in name.replace("drqn", "")):
        return "alt_drqn"
    if "drqn" in name:
        return "alt_drqn"
    if "rppo" in name or "recurrent_ppo" in name:
        return "rppo"
    if "ppo" in name:
        return "ppo"
    if "dqn" in name:
        return "dqn"
    if "a2c" in name:
        return "a2c"
    if "sac" in name:
        return "sac"
    return "alt_drqn"  # дефолт для этого проекта


_SB3_ALGOS = {"ppo", "dqn", "rppo", "a2c", "sac"}
_ALGO_EXT  = {algo: ".zip" for algo in _SB3_ALGOS}
_ALGO_EXT["alt_drqn"] = ".pt"


def _find_checkpoints(run_dir: str) -> list[str]:
    """Вернуть все чекпоинты запуска: checkpoints/* + model/final (если есть).

    Расширение файла определяется по алгоритму (детект из имени папки):
      AltDRQN → .pt,  PPO/DQN/RPPO/A2C/SAC → .zip
    """
    algo = _detect_algorithm(run_dir)
    ext  = _ALGO_EXT[algo]

    ckpt_dir = os.path.join(run_dir, "checkpoints")
    search = ckpt_dir if os.path.isdir(ckpt_dir) else run_dir
    result = sorted(
        os.path.join(search, f) for f in os.listdir(search) if f.endswith(ext)
    )
    final = os.path.join(run_dir, "model", f"final{ext}")
    if os.path.isfile(final):
        result.append(final)
    return result


def _find_run_dirs(runs_root: str) -> list[str]:
    return sorted(
        os.path.join(runs_root, e)
        for e in os.listdir(runs_root)
        if os.path.isdir(os.path.join(runs_root, e))
        and _find_checkpoints(os.path.join(runs_root, e))
    )


def _resolve_run_dir(checkpoint_path: str) -> str | None:
    parent = os.path.dirname(checkpoint_path)
    return os.path.dirname(parent) if os.path.basename(parent) == "checkpoints" else None


# ---------------------------------------------------------------------------
# Среда
# ---------------------------------------------------------------------------

def _build_eval_env(config_path: str, exclude_layers: list[str]):
    import json
    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.service.models import GridWorldTrainState

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    config = GridForestConfig.model_validate(raw)
    config.obs_config.exclude_layers = exclude_layers
    env = GridForest.load(config)
    env.train_state = GridWorldTrainState()
    return env, config.grid_size


# ---------------------------------------------------------------------------
# Валидация одного чекпоинта
# ---------------------------------------------------------------------------

def _make_agent(algorithm: str, checkpoint_path: str, env, device: str):
    """Создать EvalAgent нужного типа."""
    from services.patrol_planning.learning.test.evaluation.agent import (
        AltDRQNEvalAgent, SB3EvalAgent, RecurrentSB3EvalAgent,
    )
    if algorithm == "alt_drqn":
        return AltDRQNEvalAgent(
            model_path=checkpoint_path,
            observation_space=env.observation_space,
            n_actions=env.action_space.n,
            device=device,
        )
    if algorithm == "rppo":
        return RecurrentSB3EvalAgent(checkpoint_path)
    # ppo / dqn / a2c / sac
    return SB3EvalAgent(checkpoint_path, algorithm)


def _parse_step(checkpoint_path: str, algorithm: str) -> int | None:
    """Извлечь номер шага из имени файла или из содержимого чекпоинта."""
    name = os.path.basename(checkpoint_path)
    # SB3 и AltDRQN: {prefix}_{step}_steps.{ext}
    try:
        return int(name.split("_steps")[0].rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        pass
    # Для final.pt AltDRQN — читаем из файла
    if algorithm == "alt_drqn":
        import torch
        data = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        return data.get("step")
    return None


def validate_one(
    checkpoint_path: str,
    save_dir: str,
    algorithm: str = "alt_drqn",
    val_config_path: str = _DEFAULT_VAL_CONFIG,
    exclude_layers: list[str] = _DEFAULT_EXCLUDE,
    n_episodes: int = _DEFAULT_N_EPISODES,
    seed: int = _DEFAULT_SEED,
    device: str = _DEFAULT_DEVICE,
):
    """Прогнать валидацию чекпоинта, сохранить данные и графики в save_dir."""
    from services.patrol_planning.learning.validation.training_validator import (
        TrainingValidator, ValidationConfig,
    )

    step = _parse_step(checkpoint_path, algorithm)
    env, grid_size = _build_eval_env(val_config_path, exclude_layers)
    agent = _make_agent(algorithm, checkpoint_path, env, device)

    val_cfg = ValidationConfig(
        config_path=val_config_path,
        exclude_layers=exclude_layers,
        freq=1,
        n_episodes=n_episodes,
        seed=seed,
        drqn_device=device,
        verbose=False,   # tqdm показывает прогресс — консольный спам не нужен
        log_images=False,
    )
    validator = TrainingValidator(val_cfg)
    validator._env = env
    validator._grid_size = grid_size

    df = validator.run_validation(agent, step=step, writer=None, save_dir=save_dir)
    return df, step


# ---------------------------------------------------------------------------
# Сборка задач
# ---------------------------------------------------------------------------

Task = tuple[str, str, str]   # (checkpoint_path, run_folder_name, algorithm)


def _collect_tasks(mode: str, path: str) -> list[Task]:
    if mode == "checkpoint":
        run_dir  = _resolve_run_dir(path)
        run_name = os.path.basename(run_dir) if run_dir else "unknown_run"
        algo     = _detect_algorithm(run_dir or path)
        return [(path, run_name, algo)]

    if mode == "run_dir":
        algo  = _detect_algorithm(path)
        ckpts = _find_checkpoints(path)
        if not ckpts:
            sys.exit(f"Чекпоинты не найдены в: {path}")
        return [(c, os.path.basename(path), algo) for c in ckpts]

    # runs_root
    run_dirs = _find_run_dirs(path)
    if not run_dirs:
        sys.exit(f"Запуски с чекпоинтами не найдены в: {path}")
    tasks: list[Task] = []
    print(f"\nНайдено запусков: {len(run_dirs)}")
    for rd in run_dirs:
        algo  = _detect_algorithm(rd)
        ckpts = _find_checkpoints(rd)
        print(f"  {os.path.basename(rd)}  [{algo}]  ({len(ckpts)} чекпоинтов)")
        tasks.extend((c, os.path.basename(rd), algo) for c in ckpts)
    return tasks


# ---------------------------------------------------------------------------
# Вывод сводной таблицы
# ---------------------------------------------------------------------------

def _print_combined(results: list[tuple[str, object, int | None]]) -> None:
    import pandas as pd

    print(f"\n{'='*70}")
    print("  СВОДНАЯ ТАБЛИЦА (mean по эпизодам)")
    print(f"{'='*70}")
    key_cols = ["total_reward", "metric_Z", "metric_M_idleness", "catch_rate"]
    rows = []
    for name, df, step in results:
        row = {"checkpoint": name, "step": step}
        for col in key_cols:
            if col in df.columns:
                row[col] = round(float(df[col].mean()), 4)
        rows.append(row)
    summary = pd.DataFrame(rows).set_index("checkpoint")
    with pd.option_context("display.float_format", "{:.4f}".format, "display.max_columns", 20):
        print(summary.to_string())


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Пакетная валидация чекпоинтов AltDRQN",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--checkpoint",  "-c", metavar="PATH")
    src.add_argument("--run-dir",     "-r", metavar="DIR")
    src.add_argument("--runs-root",   "-R", metavar="DIR")

    parser.add_argument("--output-dir", "-o", metavar="DIR",
                        help="Куда сохранять результаты (обязательно в CLI-режиме)")
    parser.add_argument("--config",         default=_DEFAULT_VAL_CONFIG)
    parser.add_argument("--exclude-layers", nargs="+", default=_DEFAULT_EXCLUDE)
    parser.add_argument("--n-episodes",     type=int, default=_DEFAULT_N_EPISODES)
    parser.add_argument("--seed",           type=int, default=_DEFAULT_SEED)
    parser.add_argument("--device",         default=_DEFAULT_DEVICE)

    args = parser.parse_args()

    # Определить режим и output_dir
    output_dir: str
    tasks: list[Task]

    no_source = not args.checkpoint and not args.run_dir and not args.runs_root

    if no_source:
        picked = _gui_select()
        if picked is None:
            print("Отменено.")
            sys.exit(0)
        mode, path, output_dir = picked
        tasks = _collect_tasks(mode, path)
    else:
        if not args.output_dir:
            sys.exit("Укажите --output-dir при использовании CLI-флагов.")
        output_dir = args.output_dir
        if args.checkpoint:
            tasks = _collect_tasks("checkpoint", args.checkpoint)
        elif args.run_dir:
            tasks = _collect_tasks("run_dir", args.run_dir)
        else:
            tasks = _collect_tasks("runs_root", args.runs_root)

    if not tasks:
        sys.exit("Нет чекпоинтов для обработки.")

    try:
        from tqdm import tqdm  # type: ignore[import-untyped]
        _tqdm = tqdm
    except ImportError:
        print("[warn] tqdm не установлен — прогресс-бар недоступен (pip install tqdm)")
        _tqdm = lambda x, **_: x  # noqa: E731

    import pandas as pd
    all_results: list[tuple[str, pd.DataFrame, int | None]] = []

    for ckpt_path, run_name, algo in _tqdm(tasks, desc="Валидация", unit="ckpt"):
        # Убираем расширение (.pt или .zip) из имени папки
        ckpt_stem = os.path.splitext(os.path.basename(ckpt_path))[0]
        save_dir  = os.path.join(output_dir, run_name, ckpt_stem)

        msg = f"\n  [{algo}] {run_name} / {ckpt_stem}"
        _tqdm.write(msg) if hasattr(_tqdm, "write") else print(msg)

        df, step = validate_one(
            checkpoint_path=ckpt_path,
            save_dir=save_dir,
            algorithm=algo,
            val_config_path=args.config,
            exclude_layers=args.exclude_layers,
            n_episodes=args.n_episodes,
            seed=args.seed,
            device=args.device,
        )

        # Краткий итог по чекпоинту
        if not df.empty:
            parts = []
            for col in ("total_reward", "metric_Z", "catch_rate"):
                if col in df.columns:
                    parts.append(f"{col}={df[col].mean():.3f}")
            msg = "  → " + "  ".join(parts)
            _tqdm.write(msg) if hasattr(_tqdm, "write") else print(msg)

        all_results.append((ckpt_stem, df, step))

    if len(all_results) > 1:
        _print_combined(all_results)

    print(f"\nГотово. Результаты: {output_dir}")


if __name__ == "__main__":
    main()
