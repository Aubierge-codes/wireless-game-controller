import pygame
import math


# ============================================================
# INITIALIZATION
# ============================================================

pygame.init()

WIDTH = 1000
HEIGHT = 650
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stick Fighters - Wireless Game Controller")

clock = pygame.time.Clock()


# ============================================================
# COLORS
# ============================================================

BACKGROUND = (18, 20, 30)
GROUND_COLOR = (45, 48, 60)
GRID_COLOR = (65, 68, 82)

BLUE = (70, 160, 255)
BLUE_LIGHT = (130, 200, 255)

RED = (255, 80, 90)
RED_LIGHT = (255, 140, 145)

WHITE = (255, 255, 255)
BLACK = (10, 10, 15)

HEALTH_GREEN = (60, 220, 110)
HEALTH_RED = (220, 55, 65)

YELLOW = (255, 210, 60)
ORANGE = (255, 140, 40)


# ============================================================
# GAME SETTINGS
# ============================================================

GROUND_Y = 540

GRAVITY = 1200
MOVE_SPEED = 280
JUMP_SPEED = -550

MAX_HEALTH = 100

ATTACK_COOLDOWN = 0.35

PUNCH_DAMAGE = 8
KICK_DAMAGE = 12

PUNCH_RANGE = 65
KICK_RANGE = 85

KNOCKBACK_PUNCH = 120
KNOCKBACK_KICK = 220


# ============================================================
# FONTS
# ============================================================

font_large = pygame.font.Font(None, 64)
font_medium = pygame.font.Font(None, 38)
font_small = pygame.font.Font(None, 26)


# ============================================================
# PARTICLE
# ============================================================

class Particle:

    def __init__(self, x, y, color):

        self.position = pygame.Vector2(x, y)

        self.velocity = pygame.Vector2(
            pygame.uniform(-120, 120) if False else 0,
            0
        )

        self.life = 0.35
        self.color = color

        # Random-looking deterministic directions
        self.velocity.x = pygame.math.Vector2(
            1, 0
        ).rotate(
            pygame.time.get_ticks() % 360
        ).x * 180

        self.velocity.y = -100

        self.size = 5

    def update(self, dt):

        self.position += self.velocity * dt

        self.velocity.y += 600 * dt

        self.life -= dt

    def draw(self, surface):

        if self.life > 0:

            pygame.draw.circle(
                surface,
                self.color,
                (
                    int(self.position.x),
                    int(self.position.y)
                ),
                self.size
            )


# ============================================================
# FIGHTER CLASS
# ============================================================

class Fighter:

    def __init__(
        self,
        x,
        color,
        light_color,
        name,
        controls
    ):

        self.position = pygame.Vector2(
            x,
            GROUND_Y - 90
        )

        self.velocity = pygame.Vector2(0, 0)

        self.color = color
        self.light_color = light_color

        self.name = name

        self.controls = controls

        self.width = 45
        self.height = 90

        self.health = MAX_HEALTH

        self.facing = 1

        self.on_ground = True

        self.attack = None

        self.attack_timer = 0

        self.attack_duration = 0

        self.attack_hit = False

        self.hit_timer = 0

        self.stun_timer = 0

        self.animation_time = 0

        self.walking = False

    # --------------------------------------------------------
    # Reset
    # --------------------------------------------------------

    def reset(self, x):

        self.position = pygame.Vector2(
            x,
            GROUND_Y - 90
        )

        self.velocity = pygame.Vector2(0, 0)

        self.health = MAX_HEALTH

        self.facing = 1

        self.on_ground = True

        self.attack = None

        self.attack_timer = 0

        self.attack_duration = 0

        self.attack_hit = False

        self.hit_timer = 0

        self.stun_timer = 0

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------

    def handle_input(self, keys, opponent):

        if self.stun_timer > 0:
            return

        left = keys[self.controls["left"]]
        right = keys[self.controls["right"]]
        jump = keys[self.controls["jump"]]

        punch = keys[self.controls["punch"]]
        kick = keys[self.controls["kick"]]

        movement = 0

        if left:
            movement -= 1

        if right:
            movement += 1

        self.walking = movement != 0

        # Face opponent
        if opponent.position.x > self.position.x:
            self.facing = 1
        else:
            self.facing = -1

        # Movement
        if self.attack is None:

            self.velocity.x = movement * MOVE_SPEED

        else:

            self.velocity.x = 0

        # Jump
        if jump and self.on_ground and self.attack is None:

            self.velocity.y = JUMP_SPEED

            self.on_ground = False

        # Attack
        if self.attack is None:

            if punch:

                self.start_attack("punch")

            elif kick:

                self.start_attack("kick")

    # --------------------------------------------------------
    # Start attack
    # --------------------------------------------------------

    def start_attack(self, attack_type):

        self.attack = attack_type

        self.attack_timer = 0

        self.attack_hit = False

        if attack_type == "punch":

            self.attack_duration = 0.28

        else:

            self.attack_duration = 0.42

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def update(self, dt):

        self.animation_time += dt

        if self.hit_timer > 0:
            self.hit_timer -= dt

        if self.stun_timer > 0:
            self.stun_timer -= dt

        # Gravity
        self.velocity.y += GRAVITY * dt

        # Position
        self.position += self.velocity * dt

        # Ground collision
        ground_position = GROUND_Y - 90

        if self.position.y >= ground_position:

            self.position.y = ground_position

            self.velocity.y = 0

            self.on_ground = True

        else:

            self.on_ground = False

        # Attack timer
        if self.attack is not None:

            self.attack_timer += dt

            if self.attack_timer >= self.attack_duration:

                self.attack = None

                self.attack_timer = 0

                self.attack_hit = False

        # Friction
        if self.on_ground:

            self.velocity.x *= 0.8

    # --------------------------------------------------------
    # Attack progress
    # --------------------------------------------------------

    def attack_progress(self):

        if self.attack is None:
            return 0

        return self.attack_timer / self.attack_duration

    # --------------------------------------------------------
    # Attack active
    # --------------------------------------------------------

    def attack_is_active(self):

        if self.attack is None:
            return False

        progress = self.attack_progress()

        return 0.25 <= progress <= 0.70

    # --------------------------------------------------------
    # Attack range
    # --------------------------------------------------------

    def attack_range(self):

        if self.attack == "punch":
            return PUNCH_RANGE

        if self.attack == "kick":
            return KICK_RANGE

        return 0

    # --------------------------------------------------------
    # Attack damage
    # --------------------------------------------------------

    def attack_damage(self):

        if self.attack == "punch":
            return PUNCH_DAMAGE

        if self.attack == "kick":
            return KICK_DAMAGE

        return 0

    # --------------------------------------------------------
    # Receive hit
    # --------------------------------------------------------

    def receive_hit(self, attacker):

        damage = attacker.attack_damage()

        self.health -= damage

        self.health = max(
            0,
            self.health
        )

        self.hit_timer = 0.18

        self.stun_timer = 0.12

        knockback = (
            KNOCKBACK_PUNCH
            if attacker.attack == "punch"
            else KNOCKBACK_KICK
        )

        self.velocity.x = (
            attacker.facing * knockback
        )

        self.velocity.y = -180

        attacker.attack_hit = True

        return True

    # --------------------------------------------------------
    # Get body rectangle
    # --------------------------------------------------------

    def get_body_rect(self):

        return pygame.Rect(
            int(
                self.position.x
                - self.width / 2
            ),
            int(self.position.y),
            self.width,
            self.height
        )

    # --------------------------------------------------------
    # Draw fighter
    # --------------------------------------------------------

    def draw(self, surface):

        x = self.position.x
        y = self.position.y

        # Animation
        if self.walking and self.on_ground:

            leg_swing = math.sin(
                self.animation_time * 14
            ) * 14

            arm_swing = math.sin(
                self.animation_time * 14
            ) * 10

        else:

            leg_swing = 0
            arm_swing = 0

        # Hit flash
        draw_color = WHITE if self.hit_timer > 0 else self.color

        # ----------------------------------------------------
        # Head
        # ----------------------------------------------------

        head = pygame.Vector2(
            x,
            y - 58
        )

        pygame.draw.circle(
            surface,
            draw_color,
            (
                int(head.x),
                int(head.y)
            ),
            17
        )

        # ----------------------------------------------------
        # Body
        # ----------------------------------------------------

        neck = pygame.Vector2(
            x,
            y - 41
        )

        chest = pygame.Vector2(
            x,
            y - 5
        )

        pygame.draw.line(
            surface,
            draw_color,
            neck,
            chest,
            7
        )

        # ----------------------------------------------------
        # Arms
        # ----------------------------------------------------

        shoulder = pygame.Vector2(
            x,
            y - 32
        )

        if self.attack == "punch":

            # Punch arm
            punch_extension = 38

            punch_hand = pygame.Vector2(
                x + self.facing * punch_extension,
                y - 28
            )

            pygame.draw.line(
                surface,
                draw_color,
                shoulder,
                punch_hand,
                7
            )

            # Other arm
            other_hand = pygame.Vector2(
                x - self.facing * 22,
                y - 10
            )

            pygame.draw.line(
                surface,
                draw_color,
                shoulder,
                other_hand,
                6
            )

        else:

            left_hand = pygame.Vector2(
                x - 22,
                y - 8 + arm_swing
            )

            right_hand = pygame.Vector2(
                x + 22,
                y - 8 - arm_swing
            )

            pygame.draw.line(
                surface,
                draw_color,
                shoulder,
                left_hand,
                6
            )

            pygame.draw.line(
                surface,
                draw_color,
                shoulder,
                right_hand,
                6
            )

        # ----------------------------------------------------
        # Legs
        # ----------------------------------------------------

        hip = pygame.Vector2(
            x,
            y + 8
        )

        left_knee = pygame.Vector2(
            x - 11 - leg_swing,
            y + 38
        )

        right_knee = pygame.Vector2(
            x + 11 + leg_swing,
            y + 38
        )

        left_foot = pygame.Vector2(
            x - 18 - leg_swing,
            y + 70
        )

        right_foot = pygame.Vector2(
            x + 18 + leg_swing,
            y + 70
        )

        # Kick animation
        if self.attack == "kick":

            kick_foot = pygame.Vector2(
                x + self.facing * 55,
                y + 22
            )

            pygame.draw.line(
                surface,
                draw_color,
                hip,
                kick_foot,
                8
            )

            # Other leg
            pygame.draw.line(
                surface,
                draw_color,
                hip,
                left_knee,
                7
            )

            pygame.draw.line(
                surface,
                draw_color,
                left_knee,
                left_foot,
                7
            )

        else:

            pygame.draw.line(
                surface,
                draw_color,
                hip,
                left_knee,
                7
            )

            pygame.draw.line(
                surface,
                draw_color,
                left_knee,
                left_foot,
                7
            )

            pygame.draw.line(
                surface,
                draw_color,
                hip,
                right_knee,
                7
            )

            pygame.draw.line(
                surface,
                draw_color,
                right_knee,
                right_foot,
                7
            )

        # ----------------------------------------------------
        # Attack effect
        # ----------------------------------------------------

        if self.attack_is_active():

            attack_distance = self.attack_range()

            effect_x = (
                x
                + self.facing
                * attack_distance
            )

            pygame.draw.circle(
                surface,
                YELLOW,
                (
                    int(effect_x),
                    int(y - 20)
                ),
                7,
                2
            )


# ============================================================
# COLLISION / FIGHT LOGIC
# ============================================================

def check_attack(attacker, defender, particles):

    if attacker.attack is None:
        return

    if not attacker.attack_is_active():
        return

    if attacker.attack_hit:
        return

    distance = (
        defender.position.x
        - attacker.position.x
    )

    # Must be in front of attacker
    if distance * attacker.facing <= 0:
        return

    if abs(distance) <= attacker.attack_range():

        defender.receive_hit(attacker)

        # Impact particles
        for _ in range(8):

            particles.append(
                Particle(
                    defender.position.x,
                    defender.position.y + 35,
                    YELLOW
                )
            )


# ============================================================
# HEALTH BAR
# ============================================================

def draw_health_bar(
    x,
    y,
    width,
    health,
    name,
    color
):

    # Name
    name_text = font_small.render(
        name,
        True,
        WHITE
    )

    screen.blit(
        name_text,
        (x, y - 28)
    )

    # Background
    pygame.draw.rect(
        screen,
        (70, 70, 80),
        (x, y, width, 24),
        border_radius=5
    )

    # Health
    health_width = int(
        width * health / MAX_HEALTH
    )

    pygame.draw.rect(
        screen,
        color,
        (
            x,
            y,
            health_width,
            24
        ),
        border_radius=5
    )

    # Border
    pygame.draw.rect(
        screen,
        WHITE,
        (x, y, width, 24),
        2,
        border_radius=5
    )


# ============================================================
# CREATE FIGHTERS
# ============================================================

player1_controls = {
    "left": pygame.K_a,
    "right": pygame.K_d,
    "jump": pygame.K_w,
    "punch": pygame.K_f,
    "kick": pygame.K_g,
}

player2_controls = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "jump": pygame.K_UP,
    "punch": pygame.K_k,
    "kick": pygame.K_l,
}

player1 = Fighter(
    300,
    BLUE,
    BLUE_LIGHT,
    "PLAYER 1",
    player1_controls
)

player2 = Fighter(
    700,
    RED,
    RED_LIGHT,
    "PLAYER 2",
    player2_controls
)

particles = []


# ============================================================
# GAME STATE
# ============================================================

game_over = False
winner = ""

screen_shake = 0


# ============================================================
# RESET GAME
# ============================================================

def reset_game():

    global game_over
    global winner
    global particles

    player1.reset(300)
    player2.reset(700)

    particles = []

    game_over = False
    winner = ""


# ============================================================
# MAIN GAME LOOP
# ============================================================

running = True

while running:

    dt = min(
        clock.tick(FPS) / 1000,
        0.05
    )

    # --------------------------------------------------------
    # Events
    # --------------------------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                running = False

            if event.key == pygame.K_SPACE:

                reset_game()

    # --------------------------------------------------------
    # Keyboard state
    # --------------------------------------------------------

    keys = pygame.key.get_pressed()

    # --------------------------------------------------------
    # Game
    # --------------------------------------------------------

    if not game_over:

        player1.handle_input(
            keys,
            player2
        )

        player2.handle_input(
            keys,
            player1
        )

        player1.update(dt)
        player2.update(dt)

        # Keep fighters inside arena
        player1.position.x = max(
            60,
            min(
                WIDTH - 60,
                player1.position.x
            )
        )

        player2.position.x = max(
            60,
            min(
                WIDTH - 60,
                player2.position.x
            )
        )

        # Attacks
        check_attack(
            player1,
            player2,
            particles
        )

        check_attack(
            player2,
            player1,
            particles
        )

        # Check winner
        if player1.health <= 0:

            game_over = True
            winner = "PLAYER 2 WINS!"

        elif player2.health <= 0:

            game_over = True
            winner = "PLAYER 1 WINS!"

    # --------------------------------------------------------
    # Update particles
    # --------------------------------------------------------

    for particle in particles[:]:

        particle.update(dt)

        if particle.life <= 0:

            particles.remove(particle)

    # --------------------------------------------------------
    # Background
    # --------------------------------------------------------

    screen.fill(BACKGROUND)

    # --------------------------------------------------------
    # Arena
    # --------------------------------------------------------

    pygame.draw.rect(
        screen,
        GROUND_COLOR,
        (
            0,
            GROUND_Y,
            WIDTH,
            HEIGHT - GROUND_Y
        )
    )

    # Arena grid
    for x in range(0, WIDTH, 50):

        pygame.draw.line(
            screen,
            GRID_COLOR,
            (x, GROUND_Y),
            (x, HEIGHT)
        )

    # Ground line
    pygame.draw.line(
        screen,
        WHITE,
        (0, GROUND_Y),
        (WIDTH, GROUND_Y),
        3
    )

    # --------------------------------------------------------
    # Health bars
    # --------------------------------------------------------

    draw_health_bar(
        40,
        35,
        350,
        player1.health,
        "PLAYER 1",
        HEALTH_GREEN
    )

    draw_health_bar(
        610,
        35,
        350,
        player2.health,
        "PLAYER 2",
        HEALTH_RED
    )

    # --------------------------------------------------------
    # Draw fighters
    # --------------------------------------------------------

    player1.draw(screen)
    player2.draw(screen)

    # --------------------------------------------------------
    # Draw particles
    # --------------------------------------------------------

    for particle in particles:

        particle.draw(screen)

    # --------------------------------------------------------
    # Controls
    # --------------------------------------------------------

    controls_text = font_small.render(
        "P1: A/D Move   W Jump   F Punch   G Kick",
        True,
        BLUE_LIGHT
    )

    screen.blit(
        controls_text,
        (35, HEIGHT - 65)
    )

    controls_text2 = font_small.render(
        "P2: ←/→ Move   ↑ Jump   K Punch   L Kick",
        True,
        RED_LIGHT
    )

    screen.blit(
        controls_text2,
        (535, HEIGHT - 65)
    )

    # --------------------------------------------------------
    # Winner
    # --------------------------------------------------------

    if game_over:

        overlay = pygame.Surface(
            (WIDTH, HEIGHT),
            pygame.SRCALPHA
        )

        overlay.fill(
            (0, 0, 0, 150)
        )

        screen.blit(
            overlay,
            (0, 0)
        )

        winner_text = font_large.render(
            winner,
            True,
            WHITE
        )

        winner_rect = winner_text.get_rect(
            center=(
                WIDTH // 2,
                HEIGHT // 2 - 30
            )
        )

        screen.blit(
            winner_text,
            winner_rect
        )

        restart_text = font_medium.render(
            "Press SPACE to fight again",
            True,
            WHITE
        )

        restart_rect = restart_text.get_rect(
            center=(
                WIDTH // 2,
                HEIGHT // 2 + 40
            )
        )

        screen.blit(
            restart_text,
            restart_rect
        )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    pygame.display.flip()


# ============================================================
# QUIT
# ============================================================

pygame.quit()