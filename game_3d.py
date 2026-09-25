import random
from ursina import *
from ursina.shaders import basic_lighting_shader, unlit_shader
from ursina.lights import DirectionalLight, AmbientLight


# =============================================================
# PolyDrive - drive down a straight road to the finish line
# WASD / arrows = drive, SPACE = drift, ENTER = reset
# =============================================================

app = Ursina()

window.title = "PolyDrive"
window.borderless = False
window.fullscreen = False
window.color = color.rgb32(120, 170, 220)


# -----------------------------
# Lighting & atmosphere
# -----------------------------

sun = DirectionalLight(shadows=False)
sun.look_at(Vec3(1, -2, -1))
sun.color = color.rgb32(255, 244, 214)

ambient = AmbientLight(color=color.rgba32(150, 165, 190, 102))

sky = Sky(color=color.rgb32(130, 180, 230))
sky.shader = unlit_shader


# -----------------------------
# Road layout (fixed, straight, along +Z)
# -----------------------------

ROAD_WIDTH = 10
ROAD_LENGTH = 400
FINISH_Z = ROAD_LENGTH - 20   # crossing this line wins the race
START_Z = 5


# -----------------------------
# Ground
# -----------------------------

ground = Entity(
    model="plane",
    scale=(300, 1, ROAD_LENGTH + 200),
    position=(0, 0, ROAD_LENGTH / 2),
    color=color.rgb32(78, 128, 62),
    texture="grass",
    texture_scale=(100, 150),
    collider="box",
    shader=basic_lighting_shader,
)


def make_tree(x, z):
    trunk_color = color.rgb32(random.randint(70, 95), random.randint(48, 60), random.randint(30, 38))
    leaf_color = color.rgb32(random.randint(40, 60), random.randint(85, 115), random.randint(35, 50))
    Entity(model="cube", color=trunk_color, scale=(0.4, 1.6, 0.4), position=(x, 0.8, z), shader=basic_lighting_shader)
    Entity(model="cube", color=leaf_color, scale=(1.6, 1.8, 1.6), position=(x, 2.1, z), shader=basic_lighting_shader)


random.seed(1)
for _ in range(120):
    tx = random.uniform(-60, 60)
    tz = random.uniform(-20, ROAD_LENGTH + 40)
    if abs(tx) < ROAD_WIDTH:  # keep the road and its barriers clear
        continue
    make_tree(tx, tz)


# -----------------------------
# Road, barriers and finish line
# -----------------------------

road = Entity(
    model="cube",
    color=color.rgb32(58, 58, 64),
    scale=(ROAD_WIDTH, 0.3, ROAD_LENGTH + 20),
    position=(0, 0, ROAD_LENGTH / 2),
    collider="box",
    shader=basic_lighting_shader,
)

# Dashed centre line
for z in range(0, ROAD_LENGTH, 8):
    Entity(
        model="cube", color=color.rgb32(235, 235, 235),
        scale=(0.3, 0.02, 3), position=(0, 0.17, z + 2),
        shader=basic_lighting_shader,
    )

# Side barriers (the car is kept between them)
for side in (-1, 1):
    Entity(
        model="cube", color=color.rgb32(200, 60, 60),
        scale=(0.5, 0.8, ROAD_LENGTH + 20),
        position=(side * (ROAD_WIDTH / 2 + 0.25), 0.4, ROAD_LENGTH / 2),
        shader=basic_lighting_shader,
    )

# Start line
Entity(
    model="cube", color=color.rgb32(235, 235, 235),
    scale=(ROAD_WIDTH, 0.02, 0.6), position=(0, 0.17, START_Z - 2),
    shader=basic_lighting_shader,
)

# Finish line: black/white checkered strip + a gate over the road
CHECKS = 10
check_w = ROAD_WIDTH / CHECKS
for row in range(2):
    for i in range(CHECKS):
        Entity(
            model="cube",
            color=color.black if (i + row) % 2 else color.white,
            scale=(check_w, 0.02, 1),
            position=(-ROAD_WIDTH / 2 + check_w * (i + 0.5), 0.17, FINISH_Z + row),
            shader=basic_lighting_shader,
        )
for side in (-1, 1):
    Entity(
        model="cube", color=color.rgb32(240, 200, 30),
        scale=(0.6, 7, 0.6), position=(side * (ROAD_WIDTH / 2 + 0.5), 3.5, FINISH_Z),
        shader=basic_lighting_shader,
    )
Entity(
    model="cube", color=color.rgb32(240, 200, 30),
    scale=(ROAD_WIDTH + 1.6, 1.2, 0.6), position=(0, 7, FINISH_Z),
    shader=basic_lighting_shader,
)


# -----------------------------
# Car (low-poly, built from primitives)
# -----------------------------

start_pos = Vec3(0, 0.5, START_Z)

car = Entity(position=start_pos, rotation_y=0)   # faces +Z, down the road

car_body = Entity(
    parent=car, model="cube", color=color.rgb32(210, 40, 40),
    scale=(1.6, 0.5, 3), position=(0, 0.35, 0),
)
car_cabin = Entity(
    parent=car, model="cube", color=color.rgb32(40, 40, 45),
    scale=(1.2, 0.5, 1.4), position=(0, 0.75, -0.2),
)
wheel_positions = [(-0.85, 0.25, 1.05), (0.85, 0.25, 1.05), (-0.85, 0.25, -1.05), (0.85, 0.25, -1.05)]
for wx, wy, wz in wheel_positions:
    Entity(
        parent=car, model="cube", color=color.rgb32(20, 20, 20),
        scale=(0.35, 0.35, 0.5), position=(wx, wy, wz),
    )

for e in (car_body, car_cabin):
    e.shader = basic_lighting_shader


# -----------------------------
# Car physics state
# -----------------------------

MAX_SPEED = 22
REVERSE_SPEED = -8
ACCEL = 16
BRAKE_DECEL = 24
FRICTION = 8
TURN_SPEED = 110
GRAVITY = 28
CAR_HEIGHT_OFFSET = 0.5
GROUND_SNAP_THRESHOLD = 0.3
CAR_HALF_WIDTH = 0.9

speed = 0.0
vertical_velocity = 0.0
race_start_time = time.time()
finish_time = None      # set when the race is won
best_time = None


def get_ground_y(position):
    hit = raycast(position + Vec3(0, 6, 0), direction=Vec3(0, -1, 0), distance=25, ignore=(car,))
    if hit.hit:
        return hit.point.y
    return None


def reset_race():
    global speed, vertical_velocity, race_start_time, finish_time
    car.position = start_pos
    car.rotation_y = 0
    speed = 0.0
    vertical_velocity = 0.0
    race_start_time = time.time()
    finish_time = None
    win_text.enabled = False
    camera.position = start_pos + car.back * 9 + Vec3(0, 4.5, 0)


# -----------------------------
# UI
# -----------------------------

speed_text = Text(text="Speed: 0", position=(-0.85, 0.45), scale=1.3)
time_text = Text(text="Time: 0.0s", position=(-0.85, 0.40), scale=1.3)
best_text = Text(text="Best: --", position=(-0.85, 0.35), scale=1.3)
progress_text = Text(text="Distance: 0%", position=(-0.85, 0.30), scale=1.1)
instructions = Text(text="WASD/Arrows = Drive   SPACE = Drift   ENTER = Reset", position=(-0.85, -0.46), scale=0.9)
win_text = Text(text="", origin=(0, 0), position=(0, 0.1), scale=2.5, color=color.yellow, enabled=False)


# -----------------------------
# Camera
# -----------------------------

camera_smoothness = 7
CAMERA_BACK = 10      # distance behind the car
CAMERA_HEIGHT = 5.5   # height above the car
CAMERA_LOOK_AHEAD = 22  # camera aims this far in front of the car


# -----------------------------
# Input
# -----------------------------

def input(key):
    if key in ("enter", "return"):
        reset_race()


# -----------------------------
# Main update loop
# -----------------------------

def update():
    global speed, vertical_velocity, finish_time, best_time

    dt = time.dt
    won = finish_time is not None

    # -------------------------
    # Throttle / brake (after winning the car just coasts to a stop)
    # -------------------------
    throttle = (held_keys["w"] or held_keys["up arrow"]) and not won
    brake = (held_keys["s"] or held_keys["down arrow"]) and not won
    drifting = held_keys["space"]

    if throttle:
        speed += ACCEL * dt
    elif brake:
        speed -= BRAKE_DECEL * dt
    else:
        if speed > 0:
            speed = max(0, speed - FRICTION * dt)
        elif speed < 0:
            speed = min(0, speed + FRICTION * dt)

    speed = clamp(speed, REVERSE_SPEED, MAX_SPEED)

    # -------------------------
    # Steering
    # -------------------------
    if not won:
        steer = held_keys["d"] - held_keys["a"]
        steer += held_keys["right arrow"] - held_keys["left arrow"]

        if abs(speed) > 0.3:
            speed_factor = speed / MAX_SPEED
            turn_multiplier = 1.5 if drifting else 1.0
            car.rotation_y += steer * TURN_SPEED * turn_multiplier * speed_factor * dt
            car.rotation_y = clamp(car.rotation_y, -80, 80)   # can't turn around on the road

    # -------------------------
    # Move, and keep the car on the road between the barriers
    # -------------------------
    car.position += car.forward * speed * dt
    limit = ROAD_WIDTH / 2 - CAR_HALF_WIDTH
    car.x = clamp(car.x, -limit, limit)
    car.z = max(car.z, -5)

    # -------------------------
    # Vertical physics
    # -------------------------
    ground_y = get_ground_y(car.position)

    if ground_y is not None and (car.y - CAR_HEIGHT_OFFSET - ground_y) <= GROUND_SNAP_THRESHOLD and vertical_velocity <= 0.1:
        car.y = ground_y + CAR_HEIGHT_OFFSET
        vertical_velocity = 0
    else:
        vertical_velocity -= GRAVITY * dt
        car.y += vertical_velocity * dt
        if ground_y is not None and (car.y - CAR_HEIGHT_OFFSET) <= ground_y:
            car.y = ground_y + CAR_HEIGHT_OFFSET
            vertical_velocity = 0

    if car.y < -20:
        reset_race()

    # -------------------------
    # Win check
    # -------------------------
    if not won and car.z >= FINISH_Z:
        finish_time = time.time() - race_start_time
        if best_time is None or finish_time < best_time:
            best_time = finish_time
            best_text.text = f"Best: {best_time:.2f}s"
        win_text.text = f"YOU WIN!\n{finish_time:.2f}s\nPress ENTER to race again"
        win_text.enabled = True

    # -------------------------
    # Camera - smoothed chase cam behind the car
    # -------------------------
    desired_camera_position = car.position + car.back * CAMERA_BACK + Vec3(0, CAMERA_HEIGHT, 0)
    camera.position = lerp(camera.position, desired_camera_position, dt * camera_smoothness)
    camera.look_at(car.position + car.forward * CAMERA_LOOK_AHEAD + Vec3(0, 1, 0))

    # -------------------------
    # UI updates
    # -------------------------
    elapsed = finish_time if finish_time is not None else time.time() - race_start_time
    speed_text.text = f"Speed: {abs(speed):.0f}"
    time_text.text = f"Time: {elapsed:.1f}s"
    progress_text.text = f"Distance: {clamp((car.z - START_Z) / (FINISH_Z - START_Z), 0, 1) * 100:.0f}%"


camera.position = start_pos + Vec3(0, CAMERA_HEIGHT, -CAMERA_BACK)

app.run()
