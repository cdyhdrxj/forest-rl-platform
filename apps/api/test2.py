import sys
import time
import math
import roslibpy

# Подключение к ROS
client = roslibpy.Ros(host='localhost', port=9090)
client.run()

print("🔄 Подключение к ROS...")
time.sleep(1)

if not client.is_connected:
    print("❌ Не удалось подключиться к ROS")
    exit()

print("✅ Подключено к ROS")

# Создаём издатель команд
cmd_vel = roslibpy.Topic(client, '/robot_1/cmd_vel', 'geometry_msgs/msg/Twist')

# Переменные для состояния
collision = False
last_collision_time = 0
turn_duration = 1.5  # время поворота на 90 градусов (сек)
drive_duration = 2.0  # время движения вперёд (сек)
current_state = "FORWARD"  # FORWARD или TURNING
turn_start_time = 0
drive_start_time = 0

# Функция отправки команды
def send_command(linear, angular):
    msg = {
        'linear': {'x': linear, 'y': 0.0, 'z': 0.0},
        'angular': {'x': 0.0, 'y': 0.0, 'z': angular}
    }
    cmd_vel.publish(roslibpy.Message(msg))

# Функция остановки
def stop():
    send_command(0.0, 0.0)

# Подписка на столкновения
def on_collision(msg):
    global collision, last_collision_time, current_state, turn_start_time
    event_type = msg.get('type', 0)
    # 2 = COLLISION_PASSABLE, 3 = COLLISION_IMPASSABLE
    if event_type in [2, 3]:
        current_time = time.time()
        if current_time - last_collision_time > 1.0:  # не спамить
            collision = True
            last_collision_time = current_time
            print(f"💥 СТОЛКНОВЕНИЕ! Тип: {event_type}")
            
            # Переключаемся в режим поворота
            current_state = "TURNING"
            turn_start_time = current_time
            print("🔄 Поворот налево...")

collision_sub = roslibpy.Topic(client, '/env/events', 'forest_msgs/Event')
collision_sub.subscribe(on_collision)

print("="*60)
print("🚗 РОБОТ НАЧАЛ ДВИЖЕНИЕ")
print("   - Едет вперёд")
print("   - При столкновении поворачивает налево на 90°")
print("   - Потом снова едет вперёд")
print("   - Ctrl+C для остановки")
print("="*60)

try:
    while True:
        current_time = time.time()
        
        if current_state == "FORWARD":
            # Движение вперёд
            send_command(0.3, 0.0)
            
            # Если произошло столкновение, переключаемся на поворот
            if collision:
                collision = False
                current_state = "TURNING"
                turn_start_time = current_time
                print("🔄 Обнаружено столкновение! Поворот налево...")
        
        elif current_state == "TURNING":
            # Поворот налево (угловая скорость положительная)
            send_command(0.0, 0.5)  # 0.5 рад/с ≈ 30°/с
            
            # Проверяем, прошло ли достаточно времени для поворота на 90°
            if current_time - turn_start_time >= turn_duration:
                current_state = "FORWARD"
                drive_start_time = current_time
                print("✅ Поворот завершён! Движение вперёд...")
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n\n🛑 ОСТАНОВКА РОБОТА")
    stop()
    print("✅ Робот остановлен")

finally:
    stop()
    time.sleep(0.5)
    cmd_vel.unadvertise()
    client.terminate()
    print("👋 Завершение работы")