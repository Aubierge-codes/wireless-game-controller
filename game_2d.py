import pygame


# -----------------------------
# Game configuration
# -----------------------------

WIDTH = 900
HEIGHT = 600

FPS = 60

PLAYER_SIZE = 34
PLAYER_SPEED = 260

COIN_RADIUS = 12

BACKGROUND_COLOR = (25, 25, 35)
PLAYER_COLOR = (70, 150, 255)
COIN_COLOR = (255, 210, 60)
TEXT_COLOR = (255, 255, 255)


# -----------------------------
# Starting positions
# -----------------------------

START_PLAYER_POSITION = pygame.Vector2(WIDTH // 2, HEIGHT // 2)

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
pygame.display.set_caption("Wireless Game Controller - Stage 1")

clock = pygame.time.Clock()

font = pygame.font.Font(None, 48)


# -----------------------------
# Game state
# -----------------------------

player_position = START_PLAYER_POSITION.copy()
coins = [coin.copy() for coin in START_COINS]

running = True


# -----------------------------
# Reset function
# -----------------------------

def reset_game():
    global player_position, coins

    player_position = START_PLAYER_POSITION.copy()
    coins = [coin.copy() for coin in START_COINS]


# -----------------------------
# Main game loop
# -----------------------------

while running:

    # Calculate time since previous frame
    dt = min(clock.tick(FPS) / 1000, 0.05)

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

    # Prevent diagonal movement from being faster
    if movement.length_squared() > 1:
        movement = movement.normalize()

    # Move player
    player_position += movement * PLAYER_SPEED * dt

    # -------------------------
    # Keep player inside window
    # -------------------------

    half_player = PLAYER_SIZE / 2

    player_position.x = max(
        half_player,
        min(WIDTH - half_player, player_position.x)
    )

    player_position.y = max(
        half_player,
        min(HEIGHT - half_player, player_position.y)
    )

    # -------------------------
    # Coin collision
    # -------------------------

    remaining_coins = []

    for coin in coins:

        distance = player_position.distance_to(coin)

        if distance <= half_player + COIN_RADIUS:
            continue

        remaining_coins.append(coin)

    coins = remaining_coins

    # -------------------------
    # Draw everything
    # -------------------------

    screen.fill(BACKGROUND_COLOR)

    # Draw player
    player_rect = pygame.Rect(
        int(player_position.x - half_player),
        int(player_position.y - half_player),
        PLAYER_SIZE,
        PLAYER_SIZE,
    )

    pygame.draw.rect(
        screen,
        PLAYER_COLOR,
        player_rect,
        border_radius=6,
    )

    # Draw coins
    for coin in coins:
        pygame.draw.circle(
            screen,
            COIN_COLOR,
            (int(coin.x), int(coin.y)),
            COIN_RADIUS,
        )

    # Score
    score = len(START_COINS) - len(coins)

    score_text = font.render(
        f"Coins: {score}/{len(START_COINS)}",
        True,
        TEXT_COLOR,
    )

    screen.blit(score_text, (20, 20))

    # Win message
    if len(coins) == 0:

        win_text = font.render(
            "YOU WIN! Press SPACE to restart",
            True,
            TEXT_COLOR,
        )

        text_rect = win_text.get_rect(
            center=(WIDTH // 2, HEIGHT // 2)
        )

        screen.blit(win_text, text_rect)

    pygame.display.flip()


# -----------------------------
# Quit Pygame
# -----------------------------

pygame.quit()