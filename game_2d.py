import pygame
import math


# -----------------------------
# Game configuration
# -----------------------------

WIDTH = 900
HEIGHT = 600

FPS = 60

PLAYER_SPEED = 260

PLAYER_HEAD_RADIUS = 11
PLAYER_BODY_LENGTH = 28

COIN_RADIUS = 12

BACKGROUND_COLOR = (25, 25, 35)
PLAYER_COLOR = (70, 150, 255)
COIN_COLOR = (255, 210, 60)
TEXT_COLOR = (255, 255, 255)


# -----------------------------
# Starting positions
# -----------------------------

START_PLAYER_POSITION = pygame.Vector2(
    WIDTH // 2,
    HEIGHT // 2
)

START_COINS = [
    pygame.Vector2(100, 100),
    pygame.Vector2(800, 100),
    pygame.Vector2(100, 500),
    pygame.Vector2(800, 500),
    pygame.Vector2(450, 130),
]


# -----------------------------
# Initialize Pygame
# -----------------------------

pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption(
    "Wireless Game Controller - Stage 1"
)

clock = pygame.time.Clock()

font = pygame.font.Font(None, 48)


# -----------------------------
# Game state
# -----------------------------

player_position = START_PLAYER_POSITION.copy()

coins = [
    coin.copy()
    for coin in START_COINS
]

running = True

# Used for running animation
animation_time = 0


# -----------------------------
# Reset function
# -----------------------------

def reset_game():
    global player_position, coins

    player_position = START_PLAYER_POSITION.copy()

    coins = [
        coin.copy()
        for coin in START_COINS
    ]


# -----------------------------
# Draw stick man
# -----------------------------

def draw_stick_man(position, movement, animation_time):
    """
    Draws a simple animated running stick man.
    """

    x = position.x
    y = position.y

    # -------------------------
    # Determine if player moves
    # -------------------------

    is_moving = movement.length_squared() > 0

    # Running animation
    if is_moving:
        swing = math.sin(animation_time * 12) * 12
        leg_swing = math.sin(animation_time * 12) * 14
    else:
        swing = 0
        leg_swing = 0

    # -------------------------
    # Body positions
    # -------------------------

    head_center = pygame.Vector2(
        x,
        y - 32
    )

    neck = pygame.Vector2(
        x,
        y - 20
    )

    hip = pygame.Vector2(
        x,
        y + 12
    )

    # -------------------------
    # Arms
    # -------------------------

    left_shoulder = pygame.Vector2(
        x - 8,
        y - 17
    )

    right_shoulder = pygame.Vector2(
        x + 8,
        y - 17
    )

    left_elbow = pygame.Vector2(
        x - 18,
        y - 5 + swing
    )

    right_elbow = pygame.Vector2(
        x + 18,
        y - 5 - swing
    )

    left_hand = pygame.Vector2(
        x - 25,
        y + 7 + swing
    )

    right_hand = pygame.Vector2(
        x + 25,
        y + 7 - swing
    )

    # -------------------------
    # Legs
    # -------------------------

    left_knee = pygame.Vector2(
        x - 10 + leg_swing,
        y + 32
    )

    right_knee = pygame.Vector2(
        x + 10 - leg_swing,
        y + 32
    )

    left_foot = pygame.Vector2(
        x - 18 + leg_swing * 1.4,
        y + 55
    )

    right_foot = pygame.Vector2(
        x + 18 - leg_swing * 1.4,
        y + 55
    )

    # -------------------------
    # Draw head
    # -------------------------

    pygame.draw.circle(
        screen,
        PLAYER_COLOR,
        (int(head_center.x), int(head_center.y)),
        PLAYER_HEAD_RADIUS
    )

    # -------------------------
    # Draw body
    # -------------------------

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        neck,
        hip,
        5
    )

    # -------------------------
    # Draw left arm
    # -------------------------

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        left_shoulder,
        left_elbow,
        5
    )

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        left_elbow,
        left_hand,
        5
    )

    # -------------------------
    # Draw right arm
    # -------------------------

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        right_shoulder,
        right_elbow,
        5
    )

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        right_elbow,
        right_hand,
        5
    )

    # -------------------------
    # Draw left leg
    # -------------------------

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        hip,
        left_knee,
        6
    )

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        left_knee,
        left_foot,
        6
    )

    # -------------------------
    # Draw right leg
    # -------------------------

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        hip,
        right_knee,
        6
    )

    pygame.draw.line(
        screen,
        PLAYER_COLOR,
        right_knee,
        right_foot,
        6
    )


# -----------------------------
# Main game loop
# -----------------------------

while running:

    # Calculate time since previous frame
    dt = min(
        clock.tick(FPS) / 1000,
        0.05
    )

    # -------------------------
    # Handle events
    # -------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_SPACE:
                reset_game()

    # -------------------------
    # Read keyboard input
    # -------------------------

    keys = pygame.key.get_pressed()

    movement = pygame.Vector2(0, 0)

    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        movement.x -= 1

    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        movement.x += 1

    if keys[pygame.K_w] or keys[pygame.K_UP]:
        movement.y -= 1

    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        movement.y += 1

    # -------------------------
    # Prevent diagonal movement
    # from being faster
    # -------------------------

    if movement.length_squared() > 1:
        movement = movement.normalize()

    # -------------------------
    # Move player
    # -------------------------

    player_position += (
        movement
        * PLAYER_SPEED
        * dt
    )

    # -------------------------
    # Keep player inside window
    # -------------------------

    player_radius = 12

    player_position.x = max(
        player_radius,
        min(
            WIDTH - player_radius,
            player_position.x
        )
    )

    player_position.y = max(
        player_radius,
        min(
            HEIGHT - 55,
            player_position.y
        )
    )

    # -------------------------
    # Update running animation
    # -------------------------

    if movement.length_squared() > 0:
        animation_time += dt

    # -------------------------
    # Coin collision
    # -------------------------

    remaining_coins = []

    for coin in coins:

        distance = (
            player_position.distance_to(coin)
        )

        if distance <= 30:
            continue

        remaining_coins.append(coin)

    coins = remaining_coins

    # -------------------------
    # Draw background
    # -------------------------

    screen.fill(BACKGROUND_COLOR)

    # -------------------------
    # Draw coins
    # -------------------------

    for coin in coins:

        pygame.draw.circle(
            screen,
            COIN_COLOR,
            (
                int(coin.x),
                int(coin.y)
            ),
            COIN_RADIUS
        )

    # -------------------------
    # Draw player
    # -------------------------

    draw_stick_man(
        player_position,
        movement,
        animation_time
    )

    # -------------------------
    # Score
    # -------------------------

    score = (
        len(START_COINS)
        - len(coins)
    )

    score_text = font.render(
        f"Coins: {score}/{len(START_COINS)}",
        True,
        TEXT_COLOR
    )

    screen.blit(
        score_text,
        (20, 20)
    )

    # -------------------------
    # Instructions
    # -------------------------

    instruction_font = pygame.font.Font(
        None,
        26
    )

    instruction_text = instruction_font.render(
        "WASD / Arrow Keys = Move     SPACE = Reset",
        True,
        TEXT_COLOR
    )

    screen.blit(
        instruction_text,
        (20, 70)
    )

    # -------------------------
    # Win message
    # -------------------------

    if len(coins) == 0:

        win_text = font.render(
            "YOU WIN! Press SPACE to restart",
            True,
            TEXT_COLOR
        )

        text_rect = win_text.get_rect(
            center=(
                WIDTH // 2,
                HEIGHT // 2
            )
        )

        screen.blit(
            win_text,
            text_rect
        )

    # -------------------------
    # Update display
    # -------------------------

    pygame.display.flip()


# -----------------------------
# Quit Pygame
# -----------------------------

pygame.quit()