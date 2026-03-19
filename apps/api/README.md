# 1. Запуск

## Запуск через окружение (Conda)

Сервер использует [Miniconda](https://docs.conda.io/en/latest/miniconda.html).

Создать и активировать окружение:

```powershell
conda create -n api python=3.10
conda activate api
```

Установить зависимости внутри conda окружения из корня репозитория:

```powershell
pip install -r packages/common/requirements.txt
```

> Текущий `requirements.txt` содержит зависимости для примера среды — CAMAR (непрерывная 2-мерная). При подключении других сред следует установить их зависимости отдельно.

---

### Локальный запуск

Из корня:

```
conda activate api
python apps/api/main.py
```

---

## Запуск через Docker

Первый запуск или при изменении зависимостей:

```bash
docker-compose up --build server
```

Обычный запуск:

```bash
docker-compose up server
```

# 2. Подключение к вебсокету

## Структура

```
apps/api/
├── main.py                  # точка входа
├── app.py                   # FastAPI приложение, WebSocket роуты
├── websocket_manager.py     # общий WebSocket handler
└── sb3/
    ├── sb3_trainer.py       # базовый класс для SB3-сред
    └── model_params.py      # дефолтные параметры PPO/SAC/A2C
```

#### Модуль для CAMAR:

```
services/
└── trail_camar/
    ├── service.py           #  принимает команды от websocket_manager и возвращает состояние
    ├── wrapper.py           # адаптер JAX-среды CAMAR под gymnasium
    └── callback.py          # запись состояния среды в training_state
```

## Среды

| Эндпоинт             | Среда                              |
| -------------------- | ---------------------------------- |
| `/continuous/trail`  | CAMAR (непрерывная 2-мерная среда) |
| `/continuous/patrol` |                                    |
| `/discrete/trail`    | Клеточная 2-мерная среда           |
| `/discrete/patrol`   |                                    |
| `/threed/trail`      | 3-мерная среда                     |
| `/threed/patrol`     |                                    |

## Подключение среды к серверу

1. Реализовать сервис в `/services/<name>`, в котором будут:
    - start(params) — запуск обучения с параметрами от фронта
    - stop() — остановка обучения
    - reset() — сброс среды и модели
    - get_state() — возврат текущего состояния обучения (dict)
2. Передавать параметры в get_state():

    ```python
        {
            # счётчики эпизода
            "episode": int,          # номер текущего эпизода
            "step": int,             # счетчик шагов внутри эпизода (сбрасывается каждый эпизод)
            "total_reward": float,   # накопленная награда за текущий эпизод
            "goal_count": int,       # сколько раз агент достиг цели за эпизод
            "collision_count": int,  # сколько столкновений за эпизод

            # состояние среды (позиции)
            # float для непрерывных, int для дискретных
            "agent_pos": [[x, y]],          # позиция агента
            "goal_pos": [[x, y]],           # позиция цели
            "landmark_pos": [[x, y], ...],  # позиции препятствий, [] если нет

            #  визуальные слои
            "trajectory": [[x, y], ...],  # путь агента, накапливается за эпизод
            "terrain_map": [[float, ...], ...],  # float 0..1 значение для каждой клетки, размер grid_size×grid_size, null если нет рельефа
        }
    ```

    > Счетчики эпизода нужны для отображения в интерфейсе во время обучения:![alt text](/apps/api/docs/image.png)

    > Для режима trail (планирование пути) есть: agent_pos, goal_pos, landmark_pos - без них canvas не отрисует позиции объектов.![alt text](/apps/api/docs/image-1.png)

3. Подключить сервис в `app.py` по примеру:

    ```python
    _camar_trail = CamarService()

    @app.websocket("/continuous/trail")
    async def ws_continuous(websocket: WebSocket):
        await handle_ws(websocket, _camar_trail)
    ```
