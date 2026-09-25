import math
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
# Road layout (long, fixed course running along +Z with bends and hills)
# -----------------------------

ROAD_WIDTH = 10
ROAD_LENGTH = 1600
FINISH_Z = ROAD_LENGTH - 30   # crossing this line wins the race
START_Z = 5
SEGMENT_LENGTH = 6


def course_blend(z):
    """0 on the flat straight at the start and finish, 1 in the middle of the course."""
    return clamp(z / 120, 0, 1) * clamp((FINISH_Z - 60 - z) / 120, 0, 1)


def road_x(z):
    """Sideways position of the road centre - gentle bends left and right."""
    return course_blend(z) * (20 * math.sin(z / 95) + 9 * math.sin(z / 41))


def road_y(z):
    """Height of the road - mountains it climbs and then drops down from."""
    return course_blend(z) * (5 * (1 - math.cos(z / 60)) + 3 * (1 - math.cos(z / 25)))


def road_point(z):
    return Vec3(road_x(z), road_y(z), z)


def make_frame(z):
    """An empty entity sitting on the road at z, facing along the road."""
    frame = Entity(position=road_point(z))
    frame.look_at(road_point(z + 1))
    return frame


# -----------------------------
# Ground
# -----------------------------

ground = Entity(
    model="cube",   # a slab whose top face sits exactly at y = 0
    scale=(400, 1, ROAD_LENGTH + 200),
    position=(0, -0.5, ROAD_LENGTH / 2),
    color=color.rgb32(78, 128, 62),
    texture="grass",
    texture_scale=(130, 500),
    collider="box",
    shader=basic_lighting_shader,
)


def make_tree(x, z):
    trunk_color = color.rgb32(random.randint(70, 95), random.randint(48, 60), random.randint(30, 38))
    leaf_color = color.rgb32(random.randint(40, 60), random.randint(85, 115), random.randint(35, 50))
    Entity(model="cube", color=trunk_color, scale=(0.4, 1.6, 0.4), position=(x, 0.8, z), shader=basic_lighting_shader)
    Entity(model="cube", color=leaf_color, scale=(1.6, 1.8, 1.6), position=(x, 2.1, z), shader=basic_lighting_shader)


random.seed(1)
for _ in range(300):
    tz = random.uniform(-20, ROAD_LENGTH + 40)
    tx = random.uniform(-70, 70) + road_x(tz)
    if abs(tx - road_x(tz)) < ROAD_WIDTH + 6:  # keep the road and its surroundings clear
        continue
    make_tree(tx, tz)

# Big low-poly mountains in the distance on both sides of the course
for _ in range(24):
    mz = random.uniform(0, ROAD_LENGTH)
    side = random.choice((-1, 1))
    mx = road_x(mz) + side * random.uniform(60, 110)
    height = random.uniform(30, 70)
    Entity(
        model="diamond",
        color=color.rgb32(random.randint(95, 125), random.randint(95, 120), random.randint(95, 115)),
        scale=(random.uniform(40, 70), height, random.uniform(40, 70)),
        position=(mx, height / 2 - 2, mz),
        shader=basic_lighting_shader,
    )


# -----------------------------
# Road, barriers, support columns
# -----------------------------

for z0 in range(0, ROAD_LENGTH + 20, SEGMENT_LENGTH):
    p0, p1 = road_point(z0), road_point(z0 + SEGMENT_LENGTH)
    length = distance(p0, p1)

    seg = Entity(position=(p0 + p1) / 2)
    seg.look_at(p1)

    # The drivable slab is a top-level entity (not a child) so its collider is solid.
    tile = Entity(
        model="cube", color=color.rgb32(58, 58, 64),
        scale=(ROAD_WIDTH, 0.3, length + 0.6), position=seg.position,
        collider="box", shader=basic_lighting_shader,
    )
    tile.look_at(p1)
    for side in (-1, 1):
        Entity(
            parent=seg, model="cube", color=color.rgb32(200, 60, 60),
            scale=(0.5, 0.8, length + 0.6), position=(side * (ROAD_WIDTH / 2 + 0.25), 0.4, 0),
            shader=basic_lighting_shader,
        )
    if (z0 // SEGMENT_LENGTH) % 2 == 0:   # dashed centre line
        Entity(
            parent=seg, model="cube", color=color.rgb32(235, 235, 235),
            scale=(0.3, 0.02, length * 0.6), position=(0, 0.17, 0),
            shader=basic_lighting_shader,
        )

    # Rock column under raised parts of the road so the hills look solid
    mid_y = (p0.y + p1.y) / 2
    if mid_y > 0.6:
        Entity(
            model="cube", color=color.rgb32(105, 95, 85),
            scale=(ROAD_WIDTH + 6, mid_y, SEGMENT_LENGTH + 0.5),
            position=((p0.x + p1.x) / 2, mid_y / 2 - 0.2, (p0.z + p1.z) / 2),
            shader=basic_lighting_shader,
        )


# -----------------------------
# Start line and finish line
# -----------------------------

start_frame = make_frame(START_Z - 2)
Entity(
    parent=start_frame, model="cube", color=color.rgb32(235, 235, 235),
    scale=(ROAD_WIDTH, 0.02, 0.6), position=(0, 0.17, 0),
    shader=basic_lighting_shader,
)

# Finish line: black/white checkered strip + a gate over the road
finish_frame = make_frame(FINISH_Z)
CHECKS = 10
check_w = ROAD_WIDTH / CHECKS
for row in range(2):
    for i in range(CHECKS):
        Entity(
            parent=finish_frame, model="cube",
            color=color.black if (i + row) % 2 else color.white,
            scale=(check_w, 0.02, 1),
            position=(-ROAD_WIDTH / 2 + check_w * (i + 0.5), 0.17, row),
            shader=basic_lighting_shader,
        )
for side in (-1, 1):
    Entity(
        parent=finish_frame, model="cube", color=color.rgb32(240, 200, 30),
        scale=(0.6, 7, 0.6), position=(side * (ROAD_WIDTH / 2 + 0.5), 3.5, 0),
        shader=basic_lighting_shader,
    )
Entity(
    parent=finish_frame, model="cube", color=color.rgb32(240, 200, 30),
    scale=(ROAD_WIDTH + 1.6, 1.2, 0.6), position=(0, 7, 0),
    shader=basic_lighting_shader,
)


# -----------------------------
# Car (low-poly, built from primitives)
# -----------------------------

start_pos = road_point(START_Z) + Vec3(0, 0.5, 0)

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
TURN_SPEED = 110        # max turn rate (deg/s) at full steering lock
STEER_RESPONSE = 4.0    # how fast the wheel turns toward the pressed direction
STEER_RETURN = 6.0      # how fast the wheel re-centres when keys are released
PEDAL_PRESS = 1.4       # pedal travel per second while a key is held (about 0.7s to full)
PEDAL_RELEASE = 3.0     # pedal travel per second once the key is let go
HILL_PULL = 12          # how strongly slopes speed you up / slow you down
HIGH_SPEED_STEER = 0.55 # steering lock left at top speed (1 = no reduction)
BODY_LEAN = 6           # degrees the body leans in a turn
GRAVITY = 28
CAR_HEIGHT_OFFSET = 0.5
GROUND_SNAP_THRESHOLD = 0.3
CAR_HALF_WIDTH = 0.9

speed = 0.0
vertical_velocity = 0.0
steer_amount = 0.0      # smoothed steering, -1 (left) .. 1 (right)
throttle_amount = 0.0   # how far the accelerator is pressed, 0..1
brake_amount = 0.0      # how far the brake is pressed, 0..1
race_start_time = time.time()
finish_time = None      # set when the race is won
best_time = None


def approach(value, target, step):
    if value < target:
        return min(target, value + step)
    return max(target, value - step)


def get_ground_y(position):
    hit = raycast(position + Vec3(0, 6, 0), direction=Vec3(0, -1, 0), distance=25, ignore=(car,))
    if hit.hit:
        return hit.world_point.y  # world coords, not local to the hit entity
    return None


def reset_race():
    global speed, vertical_velocity, race_start_time, finish_time, steer_amount, throttle_amount, brake_amount
    car.position = start_pos
    car.rotation_y = 0
    car.rotation_x = 0
    speed = 0.0
    vertical_velocity = 0.0
    steer_amount = 0.0
    throttle_amount = 0.0
    brake_amount = 0.0
    car_body.rotation_z = 0
    car_cabin.rotation_z = 0
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
camera.fov = 80
CAMERA_BACK = 12      # distance behind the car
CAMERA_HEIGHT = 6.5   # height above the car
CAMERA_LOOK_AHEAD = 8   # aim slightly ahead so the car stays in view with the road


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
    global speed, vertical_velocity, finish_time, best_time, steer_amount, throttle_amount, brake_amount

    dt = time.dt
    won = finish_time is not None

    # -------------------------
    # Throttle / brake (after winning the car just coasts to a stop)
    # -------------------------
    throttle_key = (held_keys["w"] or held_keys["up arrow"]) and not won
    brake_key = (held_keys["s"] or held_keys["down arrow"]) and not won
    drifting = held_keys["space"]

    # Keys are on/off, so ramp each pedal: the longer you hold it, the harder it pushes.
    throttle_amount = approach(throttle_amount, 1 if throttle_key else 0, (PEDAL_PRESS if throttle_key else PEDAL_RELEASE) * dt)
    brake_amount = approach(brake_amount, 1 if brake_key else 0, (PEDAL_PRESS if brake_key else PEDAL_RELEASE) * dt)

    if throttle_amount > 0:
        speed += ACCEL * throttle_amount * dt
    if brake_amount > 0:
        speed -= BRAKE_DECEL * brake_amount * dt
    if throttle_amount == 0 and brake_amount == 0:
        if speed > 0:
            speed = max(0, speed - FRICTION * dt)
        elif speed < 0:
            speed = min(0, speed + FRICTION * dt)

    # Top speed depends on how far the pedal is down, so a light press cruises slower.
    if speed > 0 and throttle_amount > 0:
        speed = min(speed, MAX_SPEED * (0.25 + 0.75 * throttle_amount))

    speed = clamp(speed, REVERSE_SPEED, MAX_SPEED)

    # -------------------------
    # Steering
    # -------------------------
    steer_input = 0
    if not won:
        steer_input = held_keys["d"] - held_keys["a"]
        steer_input += held_keys["right arrow"] - held_keys["left arrow"]
        steer_input = clamp(steer_input, -1, 1)

    # Ease the wheel toward the target instead of snapping, and re-centre gently.
    rate = STEER_RESPONSE if steer_input != 0 else STEER_RETURN
    steer_amount = lerp(steer_amount, steer_input, min(1, rate * dt))
    if abs(steer_amount) < 0.01 and steer_input == 0:
        steer_amount = 0

    if abs(speed) > 0.3:
        speed_ratio = abs(speed) / MAX_SPEED
        # Slow cars pivot a little less; fast cars have reduced lock, like real steering.
        grip = min(1, abs(speed) / 6) * (1 - (1 - HIGH_SPEED_STEER) * speed_ratio)
        turn_multiplier = 1.4 if drifting else 1.0
        direction = 1 if speed > 0 else -1   # steering reverses when backing up
        car.rotation_y += steer_amount * TURN_SPEED * turn_multiplier * grip * direction * dt
        car.rotation_y = clamp(car.rotation_y, -80, 80)   # can't turn around on the road

    # Body leans outward in a turn (visual only)
    target_lean = -steer_amount * BODY_LEAN * min(1, abs(speed) / MAX_SPEED * 1.5)
    car_body.rotation_z = lerp(car_body.rotation_z, target_lean, min(1, 8 * dt))
    car_cabin.rotation_z = car_body.rotation_z

    # -------------------------
    # Move, and keep the car on the road between the barriers
    # -------------------------
    car.position += car.forward * speed * dt
    limit = ROAD_WIDTH / 2 - CAR_HALF_WIDTH
    centre = road_x(car.z)
    car.x = clamp(car.x, centre - limit, centre + limit)
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

    # Tilt the car to match the slope and let hills help / slow it
    slope = (road_y(car.z + 1) - road_y(car.z - 1)) / 2
    if vertical_velocity == 0:
        speed = clamp(speed - slope * HILL_PULL * dt, REVERSE_SPEED, MAX_SPEED)
        target_pitch = -math.degrees(math.atan(slope))
    else:
        target_pitch = 0
    car.rotation_x = lerp(car.rotation_x, target_pitch, min(1, 8 * dt))

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
    camera.look_at(car.position + car.forward * CAMERA_LOOK_AHEAD + Vec3(0, 1, 0), up=Vec3(0, 1, 0))  # world up, so the camera never rolls

    # -------------------------
    # UI updates
    # -------------------------
    elapsed = finish_time if finish_time is not None else time.time() - race_start_time
    speed_text.text = f"Speed: {abs(speed):.0f}"
    time_text.text = f"Time: {elapsed:.1f}s"
    progress_text.text = f"Distance: {clamp((car.z - START_Z) / (FINISH_Z - START_Z), 0, 1) * 100:.0f}%"


camera.position = start_pos + Vec3(0, CAMERA_HEIGHT, -CAMERA_BACK)

app.run()
