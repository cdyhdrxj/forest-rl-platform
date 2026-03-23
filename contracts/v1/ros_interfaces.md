# Интерфейсы ROS 2

Здесь фиксируются топики, сервисы и форматы сообщений, используемые в проекте.

## 1. Общие принципы

- Пространство имён запуска: `/env`
- Время: ROS time
- Все ключевые события среды публикуются как сообщения

## 2. Topics

### 2.1 Observations (Environment -> Agent)

#### `/env/scan`
**Тип:** `sensor_msgs/LaserScan`  
**Описание:** Данные лидара.

#### `/env/odom`
**Тип:** `nav_msgs/Odometry`  
**Описание:** Положение и скорость агента.

#### `/env/grid_state`
**Тип:** `nav_msgs/OccupancyGrid`  
**Описание:** Сеточное представление среды.

Используется в режимах:
- `fast`
- `patrol`

### 2.2 Actions (Agent -> Environment)

#### `/cmd_vel`
**Тип:** `geometry_msgs/Twist`  
**Описание:** Команда движения робота.

#### `/cmd_action`
**Тип:** `std_msgs/Int32`  
**Описание:** Дискретное действие.  
Кодировка:
- `0` = up
- `1` = down
- `2` = left
- `3` = right
- `4` = stay

Используется в режимах:
- `fast`
- `patrol`

### 2.3 Rewards

#### `/env/reward`
**Тип:** `std_msgs/Float32`  
**Описание:** Награда за текущий шаг.  
Используется обучающими модулями для записи журнала эпизода.

---

### 2.4 Events

#### `/env/events`
**Тип:** `custom_msgs/EpisodeEvent`  
**Описание:** События среды:
- `collision`
- `goal_reached`
- `intruder_spawn`
- `intruder_detected`
- `intruder_intercepted`
- `fire_started`
- `fire_finished`
- `damage`

## 3. Services

#### `/env/reset`
**Тип:** `std_srvs/Empty`  
**Описание:** Сброс эпизода.

#### `/env/step`
**Тип:** `custom_msgs/Step`  
**Описание:** Выполнение одного шага симуляции.

Используется в режимах:
- `fast`
- `patrol`

## 4. Custom messages

### `EpisodeEvent.msg`
```
builtin_interfaces/Time timestamp
string event_type
float32 value
geometry_msgs/Point position
int32 step_index
```

### `Step.srv`
```
int32 action
---
bool done
float32 reward
```
