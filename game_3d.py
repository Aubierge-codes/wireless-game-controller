import math
import random
from ursina import *
from ursina.shaders import basic_lighting_shader, unlit_shader
from ursina.lights import DirectionalLight, AmbientLight


# =============================================================
# PolyDrive - a small low-poly time-trial racer, PolyTrack-style
# WASD / arrows = drive, SPACE = handbrake/drift, R = reset
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
sky.shader = unlit_shader  # sky must not be lit, otherwise it renders as a white screen



# -----------------------------
# Ground
# -----------------------------

ground = Entity(
    model="plane",
    scale=(120, 1, 120),
    color=color.rgb32(78, 128, 62),
    texture="grass",
    texture_scale=(40, 40),
    collider="box",
)
ground.shader = basic_lighting_shader

# Scattered low-poly trees/rocks around the track, kept clear of the track area.
def make_tree(x, z):
    trunk_color = color.rgb32(random.randint(70, 95), random.randint(48, 60), random.randint(30, 38))
    leaf_color = color.rgb32(random.randint(40, 60), random.randint(85, 115), random.randint(35, 50))
    Entity(model="cube", color=trunk_color, scale=(0.4, 1.6, 0.4), position=(x, 0.8, z), shader=basic_lighting_shader)
    Entity(model="cube", color=leaf_color, scale=(1.6, 1.8, 1.6), position=(x, 2.1, z), shader=basic_lighting_shader)

random.seed(1)
for _ in range(40):
    tx = random.uniform(-55, 55)
    tz = random.uniform(-55, 55)
    if abs(tx) < 28 and abs(tz) < 20:  # keep clear of the track loop
        continue
    make_tree(tx, tz)


# -----------------------------
# Track generation (a stadium loop with one jump gap)
# -----------------------------

TRACK_WIDTH = 8
STRAIGHT_LENGTH = 30
TURN_RADIUS = 10
JUMP_HEIGHT = 3


def build_track_points():
    points = []

    # Bottom straight (with a ramp -> gap -> landing ramp), z = -TURN_RADIUS
    z = -TURN_RADIUS
    bottom = [
        (-STRAIGHT_LENGTH / 2, 0),
        (-6, 0),
        (-3, JUMP_HEIGHT * 0.5),
        (0, JUMP_HEIGHT),      # ramp launch point
        (9, JUMP_HEIGHT),      # landing ramp top (gap is between these two)
        (12, JUMP_HEIGHT * 0.33),
        (STRAIGHT_LENGTH / 2, 0),
    ]
    for i, (x, y) in enumerate(bottom):
        gap_after = (x == 0)  # the launch point has no tile connecting to the next point
        points.append({"pos": Vec3(x, y, z), "gap_after": gap_after})

    # Right-hand turn (semicircle), center (STRAIGHT_LENGTH/2, 0, 0)
    cx = STRAIGHT_LENGTH / 2
    steps = 10
    for i in range(1, steps):
        angle = math.radians(-90 + (180 * i / steps))
        x = cx + TURN_RADIUS * math.cos(angle)
        zz = TURN_RADIUS * math.sin(angle)
        points.append({"pos": Vec3(x, 0, zz), "gap_after": False})

    # Top straight, z = +TURN_RADIUS, going back the other way
    for x in (STRAIGHT_LENGTH / 2, 0, -STRAIGHT_LENGTH / 2):
        points.append({"pos": Vec3(x, 0, TURN_RADIUS), "gap_after": False})

    # Left-hand turn (semicircle), center (-STRAIGHT_LENGTH/2, 0, 0)
    cx = -STRAIGHT_LENGTH / 2
    for i in range(1, steps):
        angle = math.radians(90 + (180 * i / steps))
        x = cx + TURN_RADIUS * math.cos(angle)
        zz = TURN_RADIUS * math.sin(angle)
        points.append({"pos": Vec3(x, 0, zz), "gap_after": False})

    return points


track_points = build_track_points()
num_points = len(track_points)

track_tiles = []
for i in range(num_points):
    p0 = track_points[i]
    p1 = track_points[(i + 1) % num_points]

    if p0["gap_after"]:
        continue  # this is the jump gap - deliberately leave no road here

    mid = (p0["pos"] + p1["pos"]) / 2
    length = distance(p0["pos"], p1["pos"])

    is_start_line = (i == 0)
    tile = Entity(
        model="cube",
        color=color.rgb32(230, 230, 235) if is_start_line else color.rgb32(58, 58, 64),
        scale=(TRACK_WIDTH, 0.3, max(length, 0.5)),
        position=mid,
        collider="box",
    )
    tile.look_at(p1["pos"])
    tile.shader = basic_lighting_shader
    track_tiles.append(tile)

# Thin ramp guard rails at the jump edges so the gap reads clearly.
for x, label_color in ((0, color.orange), (9, color.orange)):
    Entity(
        model="cube",
        color=label_color,
        scale=(TRACK_WIDTH + 0.4, 0.6, 0.3),
        position=(x, JUMP_HEIGHT + 0.3, -TURN_RADIUS),
    )


# -----------------------------
# Checkpoints (in driving order, looping back to the start/finish)
# -----------------------------

checkpoint_indices = [num_points // 3, (2 * num_points) // 3, 0]
checkpoint_positions = [track_points[i]["pos"] for i in checkpoint_indices]

for i, pos in enumerate(checkpoint_positions):
    pole_color = color.lime if i < len(checkpoint_positions) - 1 else color.red
    Entity(
        model="cube",
        color=pole_color,
        scale=(0.3, 3, 0.3),
        position=(pos.x - TRACK_WIDTH / 2 - 0.5, 1.5, pos.z),
    )
    Entity(
        model="cube",
        color=pole_color,
        scale=(0.3, 3, 0.3),
        position=(pos.x + TRACK_WIDTH / 2 + 0.5, 1.5, pos.z),
    )


# -----------------------------
# Car (low-poly, built from primitives)
# -----------------------------

start_pos = track_points[0]["pos"] + Vec3(0, 0.5, 0)

car = Entity(position=start_pos, rotation_y=0)

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

speed = 0.0
vertical_velocity = 0.0
grounded = True

current_checkpoint = 0
last_checkpoint_pos = start_pos
lap_start_time = time.time()
best_lap_time = None


def get_ground_y(position):
    hit = raycast(position + Vec3(0, 6, 0), direction=Vec3(0, -1, 0), distance=25, ignore=(car,))
    if hit.hit:
        return hit.point.y
    return None


def respawn_car():
    global speed, vertical_velocity
    car.position = last_checkpoint_pos + Vec3(0, 1, 0)
    speed = 0.0
    vertical_velocity = 0.0


def reset_race():
    global current_checkpoint, last_checkpoint_pos, lap_start_time
    car.position = start_pos
    car.rotation_y = 0
    current_checkpoint = 0
    last_checkpoint_pos = start_pos
    lap_start_time = time.time()
    reset_speed()


def reset_speed():
    global speed, vertical_velocity
    speed = 0.0
    vertical_velocity = 0.0


# -----------------------------
# UI
# -----------------------------

speed_text = Text(text="Speed: 0", position=(-0.85, 0.45), scale=1.3)
lap_text = Text(text="Lap: 0.0s", position=(-0.85, 0.40), scale=1.3)
best_text = Text(text="Best: --", position=(-0.85, 0.35), scale=1.3)
checkpoint_text = Text(text=f"Checkpoint 1/{len(checkpoint_positions)}", position=(-0.85, 0.30), scale=1.1)
instructions = Text(text="WASD/Arrows = Drive   SPACE = Drift   R = Reset", position=(-0.85, -0.46), scale=0.9)


# -----------------------------
# Camera
# -----------------------------

camera_smoothness = 7


# -----------------------------
# Input
# -----------------------------

def input(key):
    if key == "r":
        reset_race()


# -----------------------------
# Main update loop
# -----------------------------

def update():
    global speed, vertical_velocity, grounded
    global current_checkpoint, last_checkpoint_pos, lap_start_time, best_lap_time

    dt = time.dt

    # -------------------------
    # Throttle / brake
    # -------------------------
    throttle = held_keys["w"] or held_keys["up arrow"]
    brake = held_keys["s"] or held_keys["down arrow"]
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
    # Steering (scales with speed, drifting loosens the turn rate)
    # -------------------------
    steer = held_keys["d"] - held_keys["a"]
    steer += held_keys["right arrow"] - held_keys["left arrow"]

    if abs(speed) > 0.3:
        speed_factor = speed / MAX_SPEED
        turn_multiplier = 1.5 if drifting else 1.0
        car.rotation_y += steer * TURN_SPEED * turn_multiplier * speed_factor * dt

    # -------------------------
    # Move forward along facing direction
    # -------------------------
    car.position += car.forward * speed * dt

    # -------------------------
    # Vertical physics (ramps + the jump gap)
    # -------------------------
    ground_y = get_ground_y(car.position)

    if ground_y is not None and (car.y - CAR_HEIGHT_OFFSET - ground_y) <= GROUND_SNAP_THRESHOLD and vertical_velocity <= 0.1:
        car.y = ground_y + CAR_HEIGHT_OFFSET
        vertical_velocity = 0
        grounded = True
    else:
        grounded = False
        vertical_velocity -= GRAVITY * dt
        car.y += vertical_velocity * dt
        if ground_y is not None and (car.y - CAR_HEIGHT_OFFSET) <= ground_y:
            car.y = ground_y + CAR_HEIGHT_OFFSET
            vertical_velocity = 0
            grounded = True

    if car.y < -20:
        respawn_car()

    # -------------------------
    # Checkpoint / lap logic
    # -------------------------
    target = checkpoint_positions[current_checkpoint]
    if distance(car.position, target) < 6:
        last_checkpoint_pos = target
        if current_checkpoint == len(checkpoint_positions) - 1:
            # crossed the finish line - lap complete
            lap_time = time.time() - lap_start_time
            if best_lap_time is None or lap_time < best_lap_time:
                best_lap_time = lap_time
                best_text.text = f"Best: {best_lap_time:.2f}s"
            lap_start_time = time.time()
            current_checkpoint = 0
        else:
            current_checkpoint += 1
        checkpoint_text.text = f"Checkpoint {current_checkpoint + 1}/{len(checkpoint_positions)}"

    # -------------------------
    # Camera - smoothed chase cam behind the car
    # -------------------------
    desired_camera_position = car.position + car.back * 9 + Vec3(0, 4.5, 0)
    camera.position = lerp(camera.position, desired_camera_position, dt * camera_smoothness)
    camera.look_at(car.position + Vec3(0, 1, 0))

    # -------------------------
    # UI updates
    # -------------------------
    speed_text.text = f"Speed: {abs(speed):.0f}"
    lap_text.text = f"Lap: {time.time() - lap_start_time:.1f}s"


camera.position = start_pos + Vec3(0, 5, -9)

app.run()