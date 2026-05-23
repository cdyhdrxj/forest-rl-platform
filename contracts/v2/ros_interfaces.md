# Интерфейсы ROS 2

Версия: v2

## 1. Общие принципы

1. Интерфейсы совместимы с 3 видами среды:
    - 3D среда
    - 2D непрерывная среда
    - Клеточная среда
2. Каждый агент работает в своем пространстве имен `/robot_{id}/`.
    - Для режима с одним агентом используется `robot_0`.
    - Для режима с `n` агентами используются `robot_0`, `robot_1`, ..., `robot_{n-1}`.
3. Для событий среды используется пространство имен `/env/`.
4. Ключевые происшествия публикуются через топик `/env/events`.
5. `v2` обратно несовместим с `v1` по набору кодов событий `forest_msgs/Event`.
6. Канонический RL runtime для 3D работает синхронно через `/env/step`: вызывающая сторона отправляет action, симулятор возвращает observation/reward/done/info.

## 2. Топики: Наблюдения (Среда -> Агент)

### `/robot_{id}/base_scan`
* **Тип:** `sensor_msgs/LaserScan`
* **Описание:** Данные лидара робота.
    * **Клеточная среда:** эмуляция лидара.

### `/robot_{id}/pose`
* **Тип:** `geometry_msgs/PoseStamped`
* **Описание:** Текущие координаты и ориентация.
    * **Клеточная среда:** координаты текущей ячейки `(x, y)`, ориентация игнорируется.

### `/env/events`
* **Тип:** `forest_msgs/Event`
* **Описание:** Регистрация всех runtime-событий среды.
* **Типы событий:**
    - `GOAL = 0` - достижение цели
    - `FLIP = 1` - переворот робота
    - `COLLISION_PASSABLE = 2` - столкновение c преодолимым препятствием
    - `COLLISION_IMPASSABLE = 3` - столкновение c непреодолимым препятствием
    - `INTRUDER_APPEARED = 4` - появился нарушитель
    - `INTRUDER_DETECTED = 5` - обнаружен нарушитель
    - `INTRUDER_CAUGHT = 6` - пойман нарушитель

### `/robot_{id}/events`
* **Тип:** `forest_msgs/Event`
* **Описание:** Регистрация всех runtime-событий, произошедших с роботом {id}.
* **Типы событий:**
    - `GOAL = 0` - достижение цели
    - `FLIP = 1` - переворот робота
    - `COLLISION_PASSABLE = 2` - столкновение c преодолимым препятствием
    - `COLLISION_IMPASSABLE = 3` - столкновение c непреодолимым препятствием
    - `INTRUDER_DETECTED = 5` - обнаружен нарушитель
    - `INTRUDER_CAUGHT = 6` - пойман нарушитель

## 3. Топики: Управление (Агент -> Среда)

### `/robot_{id}/cmd_vel`
* **Тип:** `geometry_msgs/Twist`
* **Описание:**
    * Линейная скорость (м/с) и угловая скорость (рад/с).
    * Только **3D/2D непрерывная среда**

### `/robot_{id}/cmd_step`
* **Тип:** `forest_msgs/StepCmd`
* **Описание:**
    * Дискретное действие, переход в соседнюю по стороне клетку
    * Только **клеточная среда**
* **Виды действий**:
    * `UP = 0` - наверх
    * `DOWN = 1` - вниз
    * `LEFT = 2` - влево
    * `RIGHT = 3` - вправо
    * `STAY = 4` - остаться в клетке

## 4. Сервисы

### `/env/reset`
* **Тип:** `std_srvs/Trigger`
* **Описание:**
    * Полная очистка сцены, возврат всех агентов в начальные точки.
    * Возвращает статус успешности операции.

### `/env/step`
* **Тип:** `forest_msgs/srv/Step`
* **Описание:**
    * Синхронный шаг среды в стиле Gymnasium.
    * Запрос содержит действия агентов и длительность такта `dt`.
    * Ответ содержит `observation_json`, `reward`, `terminated`, `truncated`, `info_json` и события, случившиеся на шаге.
    * Топики `/robot_{id}/pose`, `/robot_{id}/base_scan`, `/env/events` остаются live-каналом для мониторинга, но не являются каноническим RL handshake.

### `/env/generate`
* **Тип:** `forest_msgs/srv/SetTerrainParams`
* **Описание:**
    * Генерация terrain-а среды с заданными параметрами шума и отображения.
* **Параметры:**
    * uniform_scale       - равномерный масштаб сцены
    * mesh_height_multiplayer - множитель высоты меша
    * noise_scale         - масштаб шума
    * seed                - зерно генерации
    * octaves             - количество октав шума
    * persistance         - персистентность шума
    * lacunarity          - лакунарность шума
    * offset_x            - смещение по X
    * offset_y            - смещение по Y
    * density             - плотность объектов
    * max_view_dst        - максимальная дальность видимости
    * noise_normalize_mode - режим нормализации шума

### `/env/set_robots`
* **Тип:** `forest_msgs/srv/SetRobots`
* **Описание:**
    * Задание начальных позиций и типов роботов перед ресетом среды.
* **Параметры:**
    * positions_x  - список координат X для каждого робота
    * positions_y  - список координат Y для каждого робота
    * positions_z  - список координат Z для каждого робота
    * rotations_y  - список углов поворота по оси Y для каждого робота
    * type         - список типов роботов (0 = стандартный)
 
### `/env/set_goal`
* **Тип:** `forest_msgs/srv/SetGoal`
* **Описание:**
    * Установка целевой точки для роботов.
* **Параметры:**
    * position_x - координата X цели
    * position_y - координата Y цели
    * position_z - координата Z цели
    * radius     - радиус зоны достижения цели

## 5. Типовой порядок инициализации среды
 
Для корректного запуска среды рекомендуется следующий порядок вызовов:
 
  1. `/env/generate`   - сгенерировать terrain
  2. `/env/set_robots` - задать позиции роботов
  3. `/env/set_goal`   - установить цель
  4. `/env/reset`      - сброс среды (выполнить спавн роботов по заданным точкам)

## 6. Форматы данных

### 6.1 Сообщение `forest_msgs/Event.msg`

```text
# Заголовок со временем события
std_msgs/Header header

# ID робота
int32 robot_id

# Координаты события
geometry_msgs/Point position

uint8 GOAL=0
uint8 FLIP=1
uint8 COLLISION_PASSABLE=2
uint8 COLLISION_IMPASSABLE=3
uint8 INTRUDER_APPEARED=4
uint8 INTRUDER_DETECTED=5
uint8 INTRUDER_CAUGHT=6

# Тип
uint8 event_type

# Для event_type=INTRUDER_*: ID нарушителя, иначе -1
int32 intruder_id
```

### 6.2 Сообщение `forest_msgs/StepCmd.msg`

```text
uint8 UP=0
uint8 DOWN=1
uint8 LEFT=2
uint8 RIGHT=3
uint8 STAY=4

int32 robot_id

# Действие
uint8 action
```

### 6.3 Сообщение `forest_msgs/EnvAction.msg`

```text
uint8 TWIST=0
uint8 GRID_STEP=1

int32 robot_id
uint8 action_type

geometry_msgs/Twist twist
uint8 step_action
```

### 6.4 Сервис `forest_msgs/srv/Step.srv`

```text
forest_msgs/EnvAction[] actions
float32 dt
---
bool success
string message
string observation_json
float32 reward
bool terminated
bool truncated
string info_json
forest_msgs/Event[] events
```
