from ursina import *


# -----------------------------
# Game configuration
# -----------------------------

app = Ursina()

window.title = "Wireless Game Controller - 3D"
window.borderless = False
window.fullscreen = False

PLAYER_SPEED = 5
COIN_COUNT = 5


# -----------------------------
# Environment
# -----------------------------

ground = Entity(
    model="plane",
    scale=(20, 1, 20),
    color=color.green,
    texture="white_cube",
    texture_scale=(20, 20),
    collider="box",
)

Sky()


# -----------------------------
# Player
# -----------------------------

player = Entity(
    model="cube",
    color=color.azure,
    scale=(1, 1, 1),
    position=(0, 0.5, 0),
    collider="box",
)


# -----------------------------
# Camera
# -----------------------------

camera.position = (0, 8, -12)
camera.look_at(player)


# -----------------------------
# Coins
# -----------------------------

coin_positions = [
    (-6, 0.5, 4),
    (6, 0.5, 4),
    (-6, 0.5, -4),
    (6, 0.5, -4),
    (0, 0.5, 6),
]

coins = []

for position in coin_positions:
    coin = Entity(
        model="cube",
        color=color.yellow,
        scale=(0.6, 0.6, 0.6),
        position=position,
        rotation=(45, 45, 45),
    )

    coins.append(coin)


# -----------------------------
# Score
# -----------------------------

score = 0

score_text = Text(
    text=f"Coins: {score}/{COIN_COUNT}",
    position=(-0.85, 0.45),
    scale=1.5,
)


# -----------------------------
# Instructions
# -----------------------------

instructions = Text(
    text="WASD = Move    R = Reset",
    position=(-0.85, 0.40),
    scale=1,
)


# -----------------------------
# Reset function
# -----------------------------

def reset_game():
    global score

    player.position = (0, 0.5, 0)

    score = 0

    score_text.text = f"Coins: {score}/{COIN_COUNT}"

    for coin, position in zip(coins, coin_positions):
        coin.position = position
        coin.enabled = True


# -----------------------------
# Input
# -----------------------------

def input(key):

    if key == "r":
        reset_game()


# -----------------------------
# Game update
# -----------------------------

def update():

    # -------------------------
    # Player movement
    # -------------------------

    movement = Vec3(
        held_keys["d"] - held_keys["a"],
        0,
        held_keys["w"] - held_keys["s"],
    )

    if movement.length() > 0:
        movement = movement.normalized()

    player.position += movement * PLAYER_SPEED * time.dt


    # -------------------------
    # Keep player inside arena
    # -------------------------

    player.x = clamp(player.x, -9, 9)
    player.z = clamp(player.z, -9, 9)


    # -------------------------
    # Coin collection
    # -------------------------

    global score

    for coin in coins:

        if coin.enabled and distance(player, coin) < 1.2:

            coin.enabled = False

            score += 1

            score_text.text = f"Coins: {score}/{COIN_COUNT}"


    # -------------------------
    # Rotate coins
    # -------------------------

    for coin in coins:

        if coin.enabled:
            coin.rotation_y += 100 * time.dt


    # -------------------------
    # Camera follows player
    # -------------------------

    camera.position = (
        player.x,
        8,
        player.z - 12,
    )

    camera.look_at(player)


# -----------------------------
# Start the game
# -----------------------------

app.run()