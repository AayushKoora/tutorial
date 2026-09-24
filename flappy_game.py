import random

import pygame

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 720
FPS = 60

GRAVITY = 0.5
JUMP_VELOCITY = -9

PIPE_SPEED = 3
PIPE_SPACING = 260
GAP_SIZE_MIN = 130
GAP_SIZE_MAX = 170
PIPE_WIDTH = 70
# How far a pipe's gap center may drift from the previous pipe's, so a run of
# jumps/falls that clears one gap can realistically reach the next one.
MAX_GAP_SHIFT = 200

BIRD_RADIUS = 15
BIRD_X = 120
GAP_SIZE_FLOOR = BIRD_RADIUS * 2 * 3

GROUND_HEIGHT = 80

PLAYING = "PLAYING"
GAME_OVER = "GAME_OVER"

SKY_COLOR = (135, 206, 235)
GROUND_FILL = (150, 111, 51)
GROUND_BORDER = (92, 64, 25)
PIPE_FILL = (34, 177, 76)
PIPE_BORDER = (18, 97, 41)
BIRD_FILL = (255, 221, 0)
BIRD_BORDER = (204, 112, 0)
TEXT_COLOR = (30, 30, 30)


class Bird:
    def __init__(self):
        self.x = BIRD_X
        self.y = SCREEN_HEIGHT / 2
        self.velocity = 0.0

    def rect(self):
        return pygame.Rect(
            self.x - BIRD_RADIUS,
            self.y - BIRD_RADIUS,
            BIRD_RADIUS * 2,
            BIRD_RADIUS * 2,
        )


class Pipe:
    def __init__(self, x, previous_gap_y=None):
        self.x = x
        gap_size = random.uniform(GAP_SIZE_MIN, GAP_SIZE_MAX)
        self.gap_size = max(gap_size, GAP_SIZE_FLOOR)
        min_center = self.gap_size / 2
        max_center = SCREEN_HEIGHT - GROUND_HEIGHT - self.gap_size / 2

        if previous_gap_y is None:
            self.gap_y = random.uniform(min_center, max_center)
        else:
            anchor = min(max(previous_gap_y, min_center), max_center)
            low = max(min_center, anchor - MAX_GAP_SHIFT)
            high = min(max_center, anchor + MAX_GAP_SHIFT)
            self.gap_y = random.uniform(low, high)

        self.scored = False

    def top_rect(self):
        top_height = self.gap_y - self.gap_size / 2
        return pygame.Rect(self.x, 0, PIPE_WIDTH, top_height)

    def bottom_rect(self):
        bottom_y = self.gap_y + self.gap_size / 2
        bottom_height = SCREEN_HEIGHT - GROUND_HEIGHT - bottom_y
        return pygame.Rect(self.x, bottom_y, PIPE_WIDTH, bottom_height)


def apply_gravity(bird):
    bird.velocity += GRAVITY
    bird.y += bird.velocity


def spawn_pipes(pipes):
    if not pipes or pipes[-1].x <= SCREEN_WIDTH - PIPE_SPACING:
        previous_gap_y = pipes[-1].gap_y if pipes else None
        pipes.append(Pipe(SCREEN_WIDTH, previous_gap_y))


def update_pipes(pipes):
    for pipe in pipes:
        pipe.x -= PIPE_SPEED
    pipes[:] = [pipe for pipe in pipes if pipe.x + PIPE_WIDTH > 0]


def update_scoring(bird, pipes):
    scored_this_frame = 0
    for pipe in pipes:
        if not pipe.scored and bird.x > pipe.x + PIPE_WIDTH:
            pipe.scored = True
            scored_this_frame += 1
    return scored_this_frame


def check_collision(bird, pipes):
    bird_rect = bird.rect()
    if bird_rect.top <= 0 or bird_rect.bottom >= SCREEN_HEIGHT - GROUND_HEIGHT:
        return True
    for pipe in pipes:
        if bird_rect.colliderect(pipe.top_rect()) or bird_rect.colliderect(
            pipe.bottom_rect()
        ):
            return True
    return False


def draw_filled_and_bordered_rect(surface, rect, fill, border, border_width=3):
    pygame.draw.rect(surface, fill, rect, width=0)
    pygame.draw.rect(surface, border, rect, width=border_width)


def draw_sky(surface):
    surface.fill(SKY_COLOR)


def draw_ground(surface):
    rect = pygame.Rect(0, SCREEN_HEIGHT - GROUND_HEIGHT, SCREEN_WIDTH, GROUND_HEIGHT)
    draw_filled_and_bordered_rect(surface, rect, GROUND_FILL, GROUND_BORDER)


def draw_pipes(surface, pipes):
    for pipe in pipes:
        draw_filled_and_bordered_rect(surface, pipe.top_rect(), PIPE_FILL, PIPE_BORDER)
        draw_filled_and_bordered_rect(
            surface, pipe.bottom_rect(), PIPE_FILL, PIPE_BORDER
        )


def draw_bird(surface, bird):
    center = (int(bird.x), int(bird.y))
    pygame.draw.circle(surface, BIRD_FILL, center, BIRD_RADIUS, width=0)
    pygame.draw.circle(surface, BIRD_BORDER, center, BIRD_RADIUS, width=3)


def draw_score(surface, font, score):
    text_surface = font.render(str(score), True, TEXT_COLOR)
    surface.blit(text_surface, (SCREEN_WIDTH / 2 - text_surface.get_width() / 2, 40))


def draw_game_over_overlay(surface, font):
    lines = ["Game Over", "Press SPACE to restart"]
    y = SCREEN_HEIGHT / 2 - 40
    for line in lines:
        text_surface = font.render(line, True, TEXT_COLOR)
        surface.blit(
            text_surface, (SCREEN_WIDTH / 2 - text_surface.get_width() / 2, y)
        )
        y += text_surface.get_height() + 10


def run_game() -> int:
    pygame.init()
    try:
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SCALED, vsync=1
        )
    except pygame.error:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Flappy Bird")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)

    bird = Bird()
    pipes = []
    live_score = 0
    session_best = 0
    state = PLAYING

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return session_best
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if state == PLAYING:
                    bird.velocity = JUMP_VELOCITY
                elif state == GAME_OVER:
                    bird = Bird()
                    pipes = []
                    live_score = 0
                    state = PLAYING

        if state == PLAYING:
            apply_gravity(bird)
            spawn_pipes(pipes)
            update_pipes(pipes)
            live_score += update_scoring(bird, pipes)

            if check_collision(bird, pipes):
                session_best = max(session_best, live_score)
                state = GAME_OVER

        draw_sky(screen)
        draw_pipes(screen, pipes)
        draw_ground(screen)
        draw_bird(screen, bird)
        draw_score(screen, font, live_score)
        if state == GAME_OVER:
            draw_game_over_overlay(screen, font)

        pygame.display.flip()
        clock.tick(FPS)
