import math
import random
import re
import struct
import threading
import time as pytime
import wave
from pathlib import Path
from ursina import *
from ursina.shaders import basic_lighting_shader, unlit_shader
from ursina.lights import DirectionalLight, AmbientLight

try:
    import serial
    from serial.tools import list_ports
except ImportError:      # pyserial not installed: keyboard only
    serial = None


# =============================================================
# PolyDrive - race along a flat road with bends and U-turns
# WASD / arrows = drive, SPACE = drift
# R / ENTER = back to last checkpoint, T / BACKSPACE = start over
# Optional: Arduino joystick over USB serial (see arduino/joystick_controller)
# =============================================================

# Production settings: no dev overlay, no auto-reload on file save, normal window frame.
app = Ursina(title="PolyDrive", borderless=False, development_mode=False, editor_ui_enabled=False)

# Ursina searches the asset folder recursively for every model/texture/sound it loads.
# Point it at the small sounds/ folder (built-in models and textures are found anyway),
# so it never scans the whole project including .venv.
BASE_DIR = Path(__file__).resolve().parent
SOUND_DIR = BASE_DIR / "sounds"
try:
    SOUND_DIR.mkdir(exist_ok=True)
except OSError as error:
    print(f"[sound] cannot create {SOUND_DIR} ({error})")
application.asset_folder = SOUND_DIR

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
# Course layout: a flat road built from straights and arcs
# ("S", length) = straight,  ("A", degrees, radius) = arc (+ = right, - = left)
# -----------------------------

ROAD_WIDTH = 16
SAMPLE_SPACING = 2        # distance between points along the road centre-line
ROAD_SURFACE_Y = 0.15     # top of the road slab

COURSE = [
    ("S", 220),
    ("A", 70, 120),       # long right bend
    ("S", 180),
    ("A", -70, 120),      # long left bend back to the original heading
    ("S", 120),
    ("A", 180, 50),       # U-turn to the right
    ("S", 260),
    ("A", -45, 130),      # S-bend
    ("A", 45, 130),
    ("S", 140),
    ("A", -180, 50),      # U-turn to the left
    ("S", 260),
    ("A", 90, 80),        # sharp right corner
    ("S", 200),
]


def build_course():
    """Return (samples, pieces). samples: (x, z, heading_deg) every SAMPLE_SPACING units.
    pieces: (kind, first_sample, last_sample) for building the road tiles."""
    x = z = heading = 0.0
    samples = [(x, z, heading)]
    pieces = []
    for piece in COURSE:
        first = len(samples) - 1
        if piece[0] == "S":
            for _ in range(int(piece[1] / SAMPLE_SPACING)):
                x += SAMPLE_SPACING * math.sin(math.radians(heading))
                z += SAMPLE_SPACING * math.cos(math.radians(heading))
                samples.append((x, z, heading))
        else:
            angle, radius = piece[1], piece[2]
            steps = max(1, int(abs(math.radians(angle)) * radius / SAMPLE_SPACING))
            delta = angle / steps
            for _ in range(steps):
                mid = heading + delta / 2
                x += SAMPLE_SPACING * math.sin(math.radians(mid))
                z += SAMPLE_SPACING * math.cos(math.radians(mid))
                heading += delta
                samples.append((x, z, heading))
        pieces.append((piece[0], first, len(samples) - 1))
    return samples, pieces


samples, pieces = build_course()
START_INDEX = 4
FINISH_INDEX = len(samples) - 12   # reaching this point wins the race
# Checkpoints along the course (the last one is the finish line)
CHECKPOINT_INDICES = [FINISH_INDEX // 3, (2 * FINISH_INDEX) // 3, FINISH_INDEX]
xs = [s[0] for s in samples]
zs = [s[1] for s in samples]


def distance_to_road(x, z, step=4):
    return min(math.hypot(x - sx, z - sz) for sx, sz, _ in samples[::step])


# -----------------------------
# Ground
# -----------------------------

GROUND_MARGIN = 350
ground_w = max(xs) - min(xs) + GROUND_MARGIN * 2
ground_l = max(zs) - min(zs) + GROUND_MARGIN * 2
ground = Entity(
    model="cube",   # a slab whose top face sits exactly at y = 0
    scale=(ground_w, 1, ground_l),
    position=((max(xs) + min(xs)) / 2, -0.5, (max(zs) + min(zs)) / 2),
    color=color.rgb32(78, 128, 62),
    texture="grass",
    texture_scale=(ground_w / 8, ground_l / 8),
    collider="box",
    shader=basic_lighting_shader,
)


def make_tree(x, z):
    trunk_color = color.rgb32(random.randint(70, 95), random.randint(48, 60), random.randint(30, 38))
    leaf_color = color.rgb32(random.randint(40, 60), random.randint(85, 115), random.randint(35, 50))
    Entity(model="cube", color=trunk_color, scale=(0.4, 1.6, 0.4), position=(x, 0.8, z), shader=basic_lighting_shader)
    Entity(model="cube", color=leaf_color, scale=(1.6, 1.8, 1.6), position=(x, 2.1, z), shader=basic_lighting_shader)


random.seed(1)
trees = 0
while trees < 350:
    tx = random.uniform(min(xs) - 120, max(xs) + 120)
    tz = random.uniform(min(zs) - 120, max(zs) + 120)
    if distance_to_road(tx, tz) < ROAD_WIDTH + 6:  # keep the road and its surroundings clear
        continue
    make_tree(tx, tz)
    trees += 1

# Big low-poly mountains in the distance, well away from the road
mountains = 0
while mountains < 24:
    mx = random.uniform(min(xs) - 250, max(xs) + 250)
    mz = random.uniform(min(zs) - 250, max(zs) + 250)
    if distance_to_road(mx, mz) < 110:
        continue
    height = random.uniform(30, 70)
    Entity(
        model="diamond",
        color=color.rgb32(random.randint(95, 125), random.randint(95, 120), random.randint(95, 115)),
        scale=(random.uniform(40, 70), height, random.uniform(40, 70)),
        position=(mx, height / 2 - 2, mz),
        shader=basic_lighting_shader,
    )
    mountains += 1


# -----------------------------
# Road tiles and barriers
# -----------------------------

def add_tile(i0, i1):
    """One solid road slab (plus barriers) spanning samples i0..i1."""
    x0, z0, _ = samples[i0]
    x1, z1, _ = samples[i1]
    heading = math.degrees(math.atan2(x1 - x0, z1 - z0))
    length = math.hypot(x1 - x0, z1 - z0) + 0.8   # small overlap so tiles leave no gaps
    mid = Vec3((x0 + x1) / 2, 0, (z0 + z1) / 2)

    # Thick slab, top surface at ROAD_SURFACE_Y, so the car can never sink through it.
    Entity(
        model="cube", color=color.rgb32(58, 58, 64),
        scale=(ROAD_WIDTH, 2, length), position=(mid.x, ROAD_SURFACE_Y - 1, mid.z),
        rotation_y=heading, collider="box", shader=basic_lighting_shader,
    )
    frame = Entity(position=mid, rotation_y=heading)
    for side in (-1, 1):
        Entity(
            parent=frame, model="cube", color=color.rgb32(200, 60, 60),
            scale=(0.5, 0.8, length), position=(side * (ROAD_WIDTH / 2 + 0.25), 0.4, 0),
            shader=basic_lighting_shader,
        )


for kind, first, last in pieces:
    chunk = 25 if kind == "S" else 2    # long tiles on straights, short ones on curves
    for i0 in range(first, last, chunk):
        add_tile(i0, min(i0 + chunk, last))

# Dashed centre line
for i in range(0, len(samples), 4):
    sx, sz, sh = samples[i]
    Entity(
        model="cube", color=color.rgb32(235, 235, 235),
        scale=(0.3, 0.02, 3), position=(sx, ROAD_SURFACE_Y + 0.01, sz), rotation_y=sh,
        shader=basic_lighting_shader,
    )


def make_frame(index):
    """An empty entity on the road at a sample, facing along the road."""
    sx, sz, sh = samples[index]
    return Entity(position=(sx, 0, sz), rotation_y=sh)


# -----------------------------
# Start line and finish line
# -----------------------------

start_frame = make_frame(START_INDEX - 1)
Entity(
    parent=start_frame, model="cube", color=color.rgb32(235, 235, 235),
    scale=(ROAD_WIDTH, 0.02, 0.6), position=(0, ROAD_SURFACE_Y + 0.02, 0),
    shader=basic_lighting_shader,
)

# Finish line: black/white checkered strip + a gate over the road
finish_frame = make_frame(FINISH_INDEX)
CHECKS = 16
check_w = ROAD_WIDTH / CHECKS
for row in range(2):
    for i in range(CHECKS):
        Entity(
            parent=finish_frame, model="cube",
            color=color.black if (i + row) % 2 else color.white,
            scale=(check_w, 0.02, 1),
            position=(-ROAD_WIDTH / 2 + check_w * (i + 0.5), ROAD_SURFACE_Y + 0.02, row),
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


# Checkpoint gates (blue posts); the third checkpoint is the finish gate built above
for cp_index in CHECKPOINT_INDICES[:-1]:
    cp_frame = make_frame(cp_index)
    for side in (-1, 1):
        Entity(
            parent=cp_frame, model="cube", color=color.rgb32(60, 130, 255),
            scale=(0.5, 5, 0.5), position=(side * (ROAD_WIDTH / 2 + 0.5), 2.5, 0),
            shader=basic_lighting_shader,
        )
    Entity(
        parent=cp_frame, model="cube", color=color.rgb32(60, 130, 255),
        scale=(ROAD_WIDTH + 1.5, 0.5, 0.5), position=(0, 5, 0),
        shader=basic_lighting_shader,
    )


# -----------------------------
# Coins: grab one for a speed boost
# -----------------------------

COIN_SPACING = 30            # samples between coins (60 units)
COIN_PICKUP_RADIUS = 2.6
BOOST_SECONDS = 2.5          # boost time added per coin
BOOST_MAX_SECONDS = 6
BOOST_TOP_FACTOR = 1.35      # top speed multiplier while boosting
BOOST_ACCEL = 30             # extra acceleration while boosting
COIN_KICK = 5                # instant speed added when a coin is grabbed

coins = []
for n, idx in enumerate(range(START_INDEX + 40, FINISH_INDEX - 20, COIN_SPACING)):
    cx, cz, ch = samples[idx]
    offset = (-4, 0, 4)[n % 3]                       # weave across the road
    rx, rz = math.cos(math.radians(ch)), -math.sin(math.radians(ch))
    coin = Entity(
        model="sphere", color=color.rgb32(255, 200, 30),
        scale=(1.6, 1.6, 0.35), position=(cx + rx * offset, 1.3, cz + rz * offset),
        rotation_y=ch, shader=basic_lighting_shader,
    )
    coins.append(coin)

coins_collected = 0
boost_timer = 0.0


# -----------------------------
# Car (low-poly, built from primitives)
# -----------------------------

start_pos = Vec3(samples[START_INDEX][0], 0.5, samples[START_INDEX][1])
start_heading = samples[START_INDEX][2]

car = Entity(position=start_pos, rotation_y=start_heading)

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

MAX_SPEED = 60
TOP_SPEED_DISPLAY = 196   # top speed shown on the HUD
REVERSE_SPEED = -15
ACCEL = 30
BRAKE_DECEL = 50
FRICTION = 10
TURN_SPEED = 110        # max turn rate (deg/s) at full steering lock
STEER_RESPONSE = 4.0    # how fast the wheel turns toward the pressed direction
STEER_RETURN = 6.0      # how fast the wheel re-centres when keys are released
PEDAL_PRESS = 1.4       # pedal travel per second while a key is held (about 0.7s to full)
PEDAL_RELEASE = 3.0     # pedal travel per second once the key is let go
HIGH_SPEED_STEER = 0.6  # steering lock left at top speed (1 = no reduction)
BODY_LEAN = 6           # degrees the body leans in a turn
BARRIER_SCRAPE = 2.5    # how quickly speed is lost while rubbing a barrier
GRAVITY = 28
CAR_HEIGHT_OFFSET = 0.5
GROUND_SNAP_THRESHOLD = 0.3
CAR_HALF_WIDTH = 0.9

speed = 0.0
vertical_velocity = 0.0
steer_amount = 0.0      # smoothed steering, -1 (left) .. 1 (right)
throttle_amount = 0.0   # how far the accelerator is pressed, 0..1
brake_amount = 0.0      # how far the brake is pressed, 0..1
track_index = START_INDEX   # nearest point on the road centre-line
race_start_time = None      # set when the car first moves
finish_time = None      # set when the race is won
checkpoints_passed = 0
last_checkpoint_index = START_INDEX
run_time = 0.0
best_time = None


# -----------------------------
# Sound (generated on first run, no audio files needed)
# -----------------------------

SAMPLE_RATE = 22050


def write_wav(name, values):
    path = SOUND_DIR / name
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(b"".join(struct.pack("<h", int(clamp(v, -1, 1) * 30000)) for v in values))


def make_sounds():
    rng = random.Random(7)
    n = SAMPLE_RATE  # one second, so every pitch below loops without a click

    if not (SOUND_DIR / "engine.wav").exists():
        vals = []
        for i in range(n):
            t = i / SAMPLE_RATE
            v = (0.6 * math.sin(2 * math.pi * 55 * t) + 0.35 * math.sin(2 * math.pi * 110 * t)
                 + 0.25 * math.sin(2 * math.pi * 165 * t) + 0.15 * math.sin(2 * math.pi * 220 * t))
            v *= 1 + 0.15 * math.sin(2 * math.pi * 11 * t)
            vals.append(math.tanh(1.8 * v) * 0.7)
        write_wav("engine.wav", vals)

    if not (SOUND_DIR / "skid.wav").exists():   # tyre squeal for braking / hard cornering
        vals, y = [], 0.0
        for i in range(n):
            t = i / SAMPLE_RATE
            y = y * 0.4 + rng.uniform(-1, 1) * 0.6
            vals.append(0.35 * y + 0.25 * math.sin(2 * math.pi * 1800 * t) + 0.18 * math.sin(2 * math.pi * 2350 * t))
        write_wav("skid.wav", vals)

    if not (SOUND_DIR / "scrape.wav").exists():   # rubbing along a barrier
        vals, y = [], 0.0
        for _ in range(n):
            y = y * 0.85 + rng.uniform(-1, 1) * 0.15
            vals.append(y * 2.2)
        write_wav("scrape.wav", vals)

    if not (SOUND_DIR / "thump.wav").exists():   # hitting a barrier
        vals = []
        for i in range(int(SAMPLE_RATE * 0.35)):
            t = i / SAMPLE_RATE
            vals.append((rng.uniform(-1, 1) * 0.6 * math.exp(-t * 12) + math.sin(2 * math.pi * 60 * t) * math.exp(-t * 9)) * 0.9)
        write_wav("thump.wav", vals)

    def beeps(name, freqs, length):
        vals = []
        for f_hz in freqs:
            for i in range(int(SAMPLE_RATE * length)):
                t = i / SAMPLE_RATE
                vals.append(0.5 * math.sin(2 * math.pi * f_hz * t) * math.exp(-t * 6))
        write_wav(name, vals)

    if not (SOUND_DIR / "checkpoint.wav").exists():
        beeps("checkpoint.wav", (880, 1320), 0.12)
    if not (SOUND_DIR / "win.wav").exists():
        beeps("win.wav", (523, 659, 784, 1047), 0.18)
    if not (SOUND_DIR / "coin.wav").exists():
        beeps("coin.wav", (988, 1319, 1976), 0.07)
    if not (SOUND_DIR / "music.wav").exists():
        write_wav("music.wav", render_music(rng))


def render_music(rng):
    """A looping 8-bar track: kick, snare, hats, bass and an arpeggio, with a drum break
    in the last bar. Chords: Am - F - C - G."""
    sr = SAMPLE_RATE
    bpm = 124
    spb = int(sr * 60 / bpm)            # samples per beat
    bars = 8
    total = spb * 4 * bars
    buf = [0.0] * total

    def add(start, data, gain=1.0):
        for i, v in enumerate(data):
            j = start + i
            if j >= total:
                break
            buf[j] += v * gain

    kick, phase = [], 0.0
    for i in range(int(sr * 0.22)):
        t = i / sr
        phase += 2 * math.pi * (45 + 90 * math.exp(-t * 30)) / sr
        kick.append(math.sin(phase) * math.exp(-t * 9))
    snare = [(rng.uniform(-1, 1) * 0.7 + math.sin(2 * math.pi * 190 * i / sr) * 0.3) * math.exp(-i / sr * 22)
             for i in range(int(sr * 0.16))]
    hat, prev = [], 0.0
    for i in range(int(sr * 0.05)):
        n = rng.uniform(-1, 1)
        hat.append((n - prev) * 0.5 * math.exp(-i / sr * 70))
        prev = n

    def bass(freq, length):
        return [math.tanh(3 * math.sin(2 * math.pi * freq * i / sr)) * math.exp(-i / sr * 4)
                for i in range(length)]

    def lead(freq, length):
        return [(math.sin(2 * math.pi * freq * i / sr) + 0.4 * math.sin(4 * math.pi * freq * i / sr))
                * math.exp(-i / sr * 7) for i in range(length)]

    roots = [55.0, 43.65, 65.41, 49.0]
    tones = [
        [440.0, 523.25, 659.25, 523.25],
        [349.23, 440.0, 523.25, 440.0],
        [392.0, 523.25, 659.25, 523.25],
        [392.0, 493.88, 587.33, 493.88],
    ]
    for bar in range(bars):
        chord = bar % 4
        is_break = bar == bars - 1
        for beat in range(4):
            t0 = (bar * 4 + beat) * spb
            if is_break:
                for k in range(4):           # rising snare roll
                    add(t0 + k * spb // 4, snare, 0.35 + 0.1 * beat)
                continue
            add(t0, kick, 0.9)
            if beat in (1, 3):
                add(t0, snare, 0.6)
            add(t0 + spb // 2, hat, 0.5)
            add(t0, bass(roots[chord], spb // 2), 0.45)
            add(t0 + spb // 2, bass(roots[chord] * 2, spb // 2), 0.35)
            if bar >= 2:
                for k in range(4):
                    add(t0 + k * spb // 4, lead(tones[chord][k], spb // 4), 0.13 if k % 2 == 0 else 0.09)
    peak = max(abs(v) for v in buf) or 1
    return [v / peak * 0.85 for v in buf]


class SilentSound:
    """Stand-in used when a sound cannot be created, so the game still runs without audio."""
    volume = 0
    pitch = 1

    def play(self):
        pass


def load_sound(name, **options):
    try:
        sound = Audio(name, **options)
        if getattr(sound, "_clip", None) is None:
            raise RuntimeError(f"clip {name} not found")
        return sound
    except Exception as error:
        print(f"[sound] {name} unavailable ({error}); continuing without it")
        return SilentSound()


try:
    make_sounds()
except OSError as error:
    print(f"[sound] could not create sound files ({error}); continuing without audio")

MUSIC_VOLUME = 0.35
engine_sound = load_sound("engine", loop=True, autoplay=True, volume=0.3)
skid_sound = load_sound("skid", loop=True, autoplay=True, volume=0)
scrape_sound = load_sound("scrape", loop=True, autoplay=True, volume=0)
thump_sound = load_sound("thump", loop=False, autoplay=False)
checkpoint_sound = load_sound("checkpoint", loop=False, autoplay=False)
win_sound = load_sound("win", loop=False, autoplay=False)
coin_sound = load_sound("coin", loop=False, autoplay=False)
music = load_sound("music", loop=True, autoplay=True, volume=MUSIC_VOLUME)
thump_cooldown = 0.0



def approach(value, target, step):
    if value < target:
        return min(target, value + step)
    return max(target, value - step)


def get_ground_y(position):
    hit = raycast(position + Vec3(0, 6, 0), direction=Vec3(0, -1, 0), distance=25, ignore=(car,))
    if hit.hit:
        return hit.world_point.y  # world coords, not local to the hit entity
    return None


def find_track_index(x, z, near):
    """Nearest centre-line sample, searched around the previous one (cheap every frame)."""
    lo = max(0, near - 40)
    hi = min(len(samples) - 1, near + 80)
    best, best_d = near, float("inf")
    for i in range(lo, hi + 1):
        d = (samples[i][0] - x) ** 2 + (samples[i][1] - z) ** 2
        if d < best_d:
            best, best_d = i, d
    return best


def place_car(index):
    """Put the car on the road at a centre-line sample, stopped and facing along the road."""
    global speed, vertical_velocity, steer_amount, throttle_amount, brake_amount, track_index
    cx, cz, ch = samples[index]
    car.position = Vec3(cx, 0.5, cz)
    car.rotation_y = ch
    speed = 0.0
    vertical_velocity = 0.0
    steer_amount = 0.0
    throttle_amount = 0.0
    brake_amount = 0.0
    track_index = index
    car_body.rotation_z = 0
    car_cabin.rotation_z = 0
    camera.position = car.position + car.back * CAMERA_BACK + Vec3(0, CAMERA_HEIGHT, 0)


def reset_race():
    """Start over from the beginning."""
    global race_start_time, finish_time, checkpoints_passed, last_checkpoint_index, run_time
    global coins_collected, boost_timer
    place_car(START_INDEX)
    race_start_time = None
    run_time = 0.0
    finish_time = None
    checkpoints_passed = 0
    last_checkpoint_index = START_INDEX
    coins_collected = 0
    boost_timer = 0.0
    for coin in coins:
        coin.enabled = True
    win_text.enabled = False
    win_panel.enabled = False


def return_to_checkpoint():
    """Back to the last checkpoint (the timer keeps running)."""
    if finish_time is not None:
        reset_race()
    else:
        place_car(last_checkpoint_index)


# -----------------------------
# UI (dark blue panels)
# -----------------------------

PANEL = color.rgba32(28, 40, 105, 215)
LABEL = color.rgb32(220, 228, 255)


def panel(x, y, w, h):
    return Entity(parent=camera.ui, model="quad", color=PANEL, position=(x, y), scale=(w, h))


def ui_text(text, x, y, scale=1.0, origin=(0, 0), text_color=color.white):
    return Text(parent=camera.ui, text=text, position=(x, y), origin=origin, scale=scale, color=text_color)


def format_time(seconds):
    minutes, secs = divmod(abs(seconds), 60)
    return f"{int(minutes):02d}:{int(secs):02d}.{int((secs % 1) * 1000):03d}"


# top-left: track name
panel(-0.74, 0.445, 0.30, 0.10)
ui_text("PolyDrive 1", -0.87, 0.468, 1.4, origin=(-0.5, 0))
progress_text = ui_text("0%", -0.87, 0.428, 1.0, origin=(-0.5, 0), text_color=LABEL)

# top-centre: hint shown while the car is stopped
hint_panel = panel(0, 0.415, 0.72, 0.11)
hint_line1 = ui_text("Press R / Enter to return to the last checkpoint.", 0, 0.435, 1.15)
hint_line2 = ui_text("Press T / Backspace to start over.", 0, 0.395, 0.9)

# bottom-centre: record / current / difference
panel(-0.235, -0.462, 0.25, 0.06)
ui_text("Record", -0.235, -0.415, 0.9, text_color=LABEL)
best_text = ui_text("--:--.---", -0.235, -0.462, 1.5)

panel(0, -0.455, 0.29, 0.075)
ui_text("Current", 0, -0.407, 1.0, text_color=LABEL)
time_text = ui_text("00:00.000", 0, -0.455, 2.2)

panel(0.235, -0.462, 0.25, 0.06)
ui_text("Difference", 0.235, -0.415, 0.9, text_color=LABEL)
diff_text = ui_text("--", 0.235, -0.462, 1.5)

# bottom-left: checkpoints passed
panel(-0.79, -0.462, 0.17, 0.07)
Entity(parent=camera.ui, model="quad", color=color.rgb32(250, 210, 40), position=(-0.842, -0.462), scale=(0.018, 0.034))
checkpoint_text = ui_text(f"0/{len(CHECKPOINT_INDICES)}", -0.795, -0.462, 1.9)

# coins collected, and the boost timer above the speed panel
panel(-0.60, -0.462, 0.17, 0.07)
Entity(parent=camera.ui, model="circle", color=color.rgb32(255, 200, 30), position=(-0.652, -0.462), scale=0.035)
coin_text = ui_text("0", -0.60, -0.462, 1.9)
boost_text = ui_text("", 0.775, -0.405, 1.4, text_color=color.rgb32(255, 200, 30))

# bottom-right: speed
panel(0.775, -0.462, 0.22, 0.07)
speed_text = ui_text("0", 0.77, -0.462, 2.0, origin=(0.5, 0))
ui_text("km/h", 0.783, -0.470, 0.8, origin=(-0.5, 0), text_color=LABEL)

# finish message
win_panel = panel(0, 0.08, 0.6, 0.26)
win_panel.enabled = False
win_text = ui_text("", 0, 0.08, 2.0, text_color=color.yellow)
win_text.enabled = False

joystick_text = ui_text("", 0.87, 0.485, 0.8, origin=(0.5, 0), text_color=LABEL)
instructions = ui_text("WASD / Arrows = drive    SPACE = drift    M = music    Esc = quit    Grab coins for a speed boost", 0, -0.375, 0.8, text_color=LABEL)


# -----------------------------
# Camera
# -----------------------------

camera_smoothness = 7
camera.fov = 80
CAMERA_BACK = 12      # distance behind the car
CAMERA_HEIGHT = 6.5   # height above the car
CAMERA_LOOK_AHEAD = 8   # aim slightly ahead so the car stays in view with the road


# -----------------------------
# Arduino joystick (USB serial). Any text line containing the numbers x, y and
# (optionally) a button works: "512,498,0", "X:512 Y:498 SW:1", "-40 75", ...
# The value range is detected automatically. Keyboard keeps working too.
# -----------------------------

SERIAL_PORT = None       # e.g. "COM3"; None = auto-detect the Arduino
SERIAL_BAUD = 115200      # your board sends at 115200
                          # (the board sends x,y,button,x,y,button: both sticks are used)
JOY_RANGE = 400           # how far the raw value moves from the centre at full push
JOY_BUTTON_ACTIVE_LOW = True    # your button reads 1 at rest and 0 when pressed
JOY_INVERT_X = False     # flip if pushing right steers left
JOY_INVERT_Y = True      # flip if pushing the stick up brakes instead of accelerating
JOY_DEADZONE = 0.12      # ignore tiny movements around the centre


class Joystick:
    """Reads up to two sticks (x,y,button each). Both work the same: the stick pushed
    furthest wins for steering and for accelerate/brake, and either button drifts."""

    def __init__(self):
        self.x = 0.0          # -1 (left) .. 1 (right)
        self.y = 0.0          # -1 (down/brake) .. 1 (up/accelerate)
        self.button = False
        self.status = "Joystick: keyboard only"
        self._centers = None
        self._half = [[JOY_RANGE, JOY_RANGE], [JOY_RANGE, JOY_RANGE]]
        self._calibration = []
        if serial is None:
            self.status = "Joystick: install pyserial to use it"
            return
        threading.Thread(target=self._run, daemon=True).start()

    def _find_port(self):
        if SERIAL_PORT:
            return SERIAL_PORT
        ports = list(list_ports.comports())
        for port in ports:
            text = f"{port.description} {port.manufacturer}".lower()
            if any(word in text for word in ("arduino", "ch340", "usb serial", "usb-serial", "wch")):
                return port.device
        return ports[0].device if ports else None

    def _axis(self, raw, center, half_range, invert):
        value = clamp((raw - center) / half_range, -1, 1)
        if abs(value) < JOY_DEADZONE:
            return 0.0
        value = (abs(value) - JOY_DEADZONE) / (1 - JOY_DEADZONE) * (1 if value > 0 else -1)
        return -value if invert else value

    def _handle(self, sticks):
        if self._centers is None:            # stick(s) at rest: remember the centres
            self._calibration.append(sticks)
            if len(self._calibration) >= 30:
                count = min(len(c) for c in self._calibration)
                self._centers = [
                    (sum(c[k][0] for c in self._calibration) / len(self._calibration),
                     sum(c[k][1] for c in self._calibration) / len(self._calibration))
                    for k in range(count)
                ]
            return
        best_x = best_y = 0.0
        pressed = False
        for k, (raw_x, raw_y, button) in enumerate(sticks[:len(self._centers)]):
            cx, cy = self._centers[k]
            self._half[k][0] = max(self._half[k][0], abs(raw_x - cx))
            self._half[k][1] = max(self._half[k][1], abs(raw_y - cy))
            sx = self._axis(raw_x, cx, self._half[k][0], JOY_INVERT_X)
            sy = self._axis(raw_y, cy, self._half[k][1], JOY_INVERT_Y)
            if abs(sx) > abs(best_x):
                best_x = sx
            if abs(sy) > abs(best_y):
                best_y = sy
            pressed = pressed or (button != JOY_BUTTON_ACTIVE_LOW)
        self.x, self.y, self.button = best_x, best_y, pressed

    def _run(self):
        while True:
            port = self._find_port()
            if port is None:
                self.status = "Joystick: no Arduino found (keyboard only)"
                pytime.sleep(2)
                continue
            try:
                with serial.Serial(port, SERIAL_BAUD, timeout=1) as connection:
                    self.status = f"Joystick: connected on {port}"
                    self._centers = None
                    self._calibration = []
                    while True:
                        line = connection.readline().decode(errors="ignore").strip()
                        numbers = re.findall(r"-?\d+(?:\.\d+)?", line)
                        sticks = []
                        for k in (0, 3):     # first stick, then the second stick if present
                            if len(numbers) >= k + 2:
                                button = float(numbers[k + 2]) != 0 if len(numbers) > k + 2 else False
                                sticks.append((float(numbers[k]), float(numbers[k + 1]), button))
                        if sticks:
                            self._handle(sticks)
            except (serial.SerialException, OSError):
                self.x = self.y = 0.0
                self.button = False
                self.status = f"Joystick: lost {port}, reconnecting..."
                pytime.sleep(2)


joystick = Joystick()


# -----------------------------
# Input
# -----------------------------

def input(key):
    if key in ("r", "enter", "return"):
        return_to_checkpoint()
    elif key in ("t", "backspace"):
        reset_race()
    elif key == "m":
        music.volume = 0 if music.volume > 0 else MUSIC_VOLUME
    elif key == "escape":
        application.quit()


# -----------------------------
# Main update loop
# -----------------------------

def update():
    global speed, vertical_velocity, finish_time, best_time, track_index
    global steer_amount, throttle_amount, brake_amount
    global race_start_time, checkpoints_passed, last_checkpoint_index, run_time, thump_cooldown
    global coins_collected, boost_timer

    dt = time.dt
    won = finish_time is not None
    thump_cooldown = max(0, thump_cooldown - dt)

    # -------------------------
    # Throttle / brake (after winning the car just coasts to a stop)
    # -------------------------
    throttle_key = (held_keys["w"] or held_keys["up arrow"]) and not won
    brake_key = (held_keys["s"] or held_keys["down arrow"]) and not won
    drifting = held_keys["space"] or joystick.button

    # Stick up / down gives an analog pedal (how far you push = how hard).
    joy_throttle = max(0, joystick.y) if not won else 0
    joy_brake = max(0, -joystick.y) if not won else 0

    # Keys are on/off, so ramp each pedal: the longer you hold it, the harder it pushes.
    throttle_target = 1 if throttle_key else joy_throttle
    brake_target = 1 if brake_key else joy_brake
    throttle_rate = PEDAL_PRESS if throttle_key else (8 if throttle_target > throttle_amount else PEDAL_RELEASE)
    brake_rate = PEDAL_PRESS if brake_key else (8 if brake_target > brake_amount else PEDAL_RELEASE)
    throttle_amount = approach(throttle_amount, throttle_target, throttle_rate * dt)
    brake_amount = approach(brake_amount, brake_target, brake_rate * dt)

    speed_before = speed
    if throttle_amount > 0:
        speed += ACCEL * throttle_amount * dt
    if brake_amount > 0:
        speed -= BRAKE_DECEL * brake_amount * dt
    if throttle_amount == 0 and brake_amount == 0:
        if speed > 0:
            speed = max(0, speed - FRICTION * dt)
        elif speed < 0:
            speed = min(0, speed + FRICTION * dt)

    # Coin boost: extra push and a higher top speed while the timer runs.
    boosting = boost_timer > 0 and not won
    if boosting:
        boost_timer = max(0, boost_timer - dt)
        if brake_amount == 0:
            speed += BOOST_ACCEL * dt
    top_speed = MAX_SPEED * (BOOST_TOP_FACTOR if boosting else 1)

    # Top speed depends on how far the pedal is down, so a light press cruises slower.
    # Anything above the limit (e.g. when a boost ends) eases off instead of snapping.
    limit = top_speed * (0.25 + 0.75 * throttle_amount) if throttle_amount > 0 else top_speed
    if speed > limit:
        # hard cap, unless we were already above it (boost just ended): then ease down
        speed = max(limit, speed_before - 40 * dt) if speed_before > limit else limit
    speed = max(speed, REVERSE_SPEED)

    # -------------------------
    # Steering
    # -------------------------
    steer_input = 0
    if not won:
        steer_input = held_keys["d"] - held_keys["a"]
        steer_input += held_keys["right arrow"] - held_keys["left arrow"]
        steer_input = clamp(steer_input + joystick.x, -1, 1)

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

    # Body leans outward in a turn (visual only)
    target_lean = -steer_amount * BODY_LEAN * min(1, abs(speed) / MAX_SPEED * 1.5)
    car_body.rotation_z = lerp(car_body.rotation_z, target_lean, min(1, 8 * dt))
    car_cabin.rotation_z = car_body.rotation_z

    # -------------------------
    # Move, and keep the car on the road between the barriers
    # -------------------------
    car.position += car.forward * speed * dt

    track_index = find_track_index(car.x, car.z, track_index)
    cx, cz, ch = samples[track_index]
    right_x, right_z = math.cos(math.radians(ch)), -math.sin(math.radians(ch))
    sideways = (car.x - cx) * right_x + (car.z - cz) * right_z
    scraping = False
    limit = ROAD_WIDTH / 2 - CAR_HALF_WIDTH
    excess = sideways - clamp(sideways, -limit, limit)
    if excess:
        # Pushed back onto the road; rubbing the barrier costs speed.
        car.x -= right_x * excess
        car.z -= right_z * excess
        if abs(speed) > 8 and thump_cooldown == 0:
            thump_sound.play()
            thump_cooldown = 0.5
        speed -= speed * min(1, BARRIER_SCRAPE * dt)
    scraping = bool(excess) and abs(speed) > 2

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

    if car.y < -20:           # fell off the world: back to the last checkpoint
        return_to_checkpoint()

    # -------------------------
    # Timer, checkpoints and win check
    # -------------------------
    if race_start_time is None and not won and abs(speed) > 0.5:
        race_start_time = time.time()      # the clock starts when the car first moves
    if race_start_time is not None and not won:
        run_time = time.time() - race_start_time

    if not won and checkpoints_passed < len(CHECKPOINT_INDICES) and track_index >= CHECKPOINT_INDICES[checkpoints_passed]:
        last_checkpoint_index = CHECKPOINT_INDICES[checkpoints_passed]
        checkpoints_passed += 1
        if checkpoints_passed < len(CHECKPOINT_INDICES):
            checkpoint_sound.play()
        else:
            finish_time = run_time
            if best_time is None or finish_time < best_time:
                best_time = finish_time
            win_text.text = f"YOU WIN!\n{format_time(finish_time)}\nR / Enter to race again"
            win_text.enabled = True
            win_panel.enabled = True
            win_sound.play()

    # -------------------------
    # Coins
    # -------------------------
    for coin in coins:
        if not coin.enabled:
            continue
        coin.rotation_y += 180 * dt
        if (coin.x - car.x) ** 2 + (coin.z - car.z) ** 2 < COIN_PICKUP_RADIUS ** 2:
            coin.enabled = False
            coins_collected += 1
            boost_timer = min(BOOST_MAX_SECONDS, boost_timer + BOOST_SECONDS)
            speed = min(speed + COIN_KICK, MAX_SPEED * BOOST_TOP_FACTOR)
            coin_sound.play()

    # -------------------------
    # Camera - smoothed chase cam behind the car
    # -------------------------
    desired_camera_position = car.position + car.back * CAMERA_BACK + Vec3(0, CAMERA_HEIGHT, 0)
    camera.position = lerp(camera.position, desired_camera_position, dt * camera_smoothness)
    camera.look_at(car.position + car.forward * CAMERA_LOOK_AHEAD + Vec3(0, 1, 0), up=Vec3(0, 1, 0))  # world up, so the camera never rolls

    # -------------------------
    # Sound
    # -------------------------
    speed_ratio = abs(speed) / MAX_SPEED
    engine_sound.pitch = 0.7 + 2.3 * speed_ratio
    engine_sound.volume = 0.25 + 0.5 * throttle_amount + 0.15 * speed_ratio
    braking_hard = brake_amount * min(1, abs(speed) / 15) if speed > 0 else 0
    cornering_hard = max(0, abs(steer_amount) * speed_ratio - 0.35) * 1.5
    skid_sound.volume = clamp(max(braking_hard * 0.9, cornering_hard), 0, 1)
    skid_sound.pitch = 0.9 + 0.3 * speed_ratio
    scrape_sound.volume = 0.8 if scraping else 0

    # -------------------------
    # UI updates
    # -------------------------
    speed_text.text = f"{abs(speed) / MAX_SPEED * TOP_SPEED_DISPLAY:.0f}"
    time_text.text = format_time(run_time if finish_time is None else finish_time)
    if best_time is not None:
        best_text.text = format_time(best_time)
        diff = (finish_time if finish_time is not None else run_time) - best_time
        diff_text.text = ("+" if diff >= 0 else "-") + format_time(diff)
        diff_text.color = color.rgb32(255, 90, 90) if diff >= 0 else color.rgb32(90, 235, 130)
    joystick_text.text = joystick.status
    coin_text.text = str(coins_collected)
    boost_text.text = f"BOOST {boost_timer:.1f}s" if boost_timer > 0 else ""
    checkpoint_text.text = f"{checkpoints_passed}/{len(CHECKPOINT_INDICES)}"
    progress = (track_index - START_INDEX) / (FINISH_INDEX - START_INDEX)
    progress_text.text = f"{clamp(progress, 0, 1) * 100:.0f}%"
    hint_visible = abs(speed) < 1 and not won
    hint_panel.enabled = hint_line1.enabled = hint_line2.enabled = hint_visible


camera.position = start_pos + Vec3(0, CAMERA_HEIGHT, -CAMERA_BACK)

app.run()
