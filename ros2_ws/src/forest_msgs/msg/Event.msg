std_msgs/Header header

int32 robot_id
geometry_msgs/Point position

uint8 GOAL=0
uint8 FLIP=1
uint8 COLLISION_PASSABLE=2
uint8 COLLISION_IMPASSABLE=3
uint8 INTRUDER_APPEARED=4
uint8 INTRUDER_DETECTED=5
uint8 INTRUDER_CAUGHT=6

uint8 event_type

# For INTRUDER_* events. Use -1 when not applicable.
int32 intruder_id
