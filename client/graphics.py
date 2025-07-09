import pygame
import math

# Colors
TABLE_BLUE = (1, 8, 38)
LINE_WHITE = (200, 200, 200)
PUCK_COLOR = (255, 230, 0)
P1_PADDLE_COLOR = (227, 20, 20)
P2_PADDLE_COLOR = (20, 125, 227)
GOAL_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
BLACK = (0,0,0)

# Trail untuk Puck
puck_trail = []
MAX_TRAIL_LENGTH = 15

def get_font(size=38):
    """Get font object (lazy initialization) - CENTRAL FONT PROVIDER"""
    return pygame.font.Font(None, size)

def draw_text(screen, text, font, x, y, color=TEXT_COLOR, center=True):
    """UNIVERSAL text drawing function - used by all modules"""
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(x, y)) if center else text_surface.get_rect(topleft=(x,y))
    screen.blit(text_surface, text_rect)

def show_message(screen, message, duration=2000, color=TEXT_COLOR):
    """UNIVERSAL message display - used by auth and game"""
    WIDTH, HEIGHT = screen.get_size()
    screen.fill(TABLE_BLUE)
    draw_text(screen, message, get_font(), WIDTH / 2, HEIGHT / 2, color)
    pygame.display.flip()
    pygame.time.wait(duration)

def draw_arena(screen):
    WIDTH, HEIGHT = screen.get_size()
    screen.fill(TABLE_BLUE)
    
    goal_width, goal_height = 10, 150
    pygame.draw.rect(screen, GOAL_COLOR, (0, HEIGHT/2 - goal_height/2, goal_width, goal_height))
    pygame.draw.rect(screen, GOAL_COLOR, (WIDTH - goal_width, HEIGHT/2 - goal_height/2, goal_width, goal_height))
    pygame.draw.line(screen, LINE_WHITE, (WIDTH/2, 0), (WIDTH/2, HEIGHT), 3)
    pygame.draw.circle(screen, LINE_WHITE, (WIDTH/2, HEIGHT/2), 70, 3)
    pygame.draw.arc(screen, LINE_WHITE, [-80, HEIGHT/2 - 80, 160, 160], -math.pi/2, math.pi/2, 3)
    pygame.draw.arc(screen, LINE_WHITE, [WIDTH - 80, HEIGHT/2 - 80, 160, 160], math.pi/2, 3*math.pi/2, 3)

def update_puck_trail(puck_pos):
    """Update trail puck"""
    global puck_trail
    puck_trail.append(tuple(puck_pos))
    if len(puck_trail) > MAX_TRAIL_LENGTH:
        puck_trail.pop(0)

def draw_puck_trail(screen):
    global puck_trail
    for i, pos in enumerate(puck_trail):
        if i < len(puck_trail) - 1: 
            alpha = int(255 * (i / len(puck_trail)) * 0.6)
            radius = int(15 * (i / len(puck_trail)) * 0.8)
            if radius > 2:
                trail_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                trail_color = (*PUCK_COLOR, alpha)
                pygame.draw.circle(trail_surface, trail_color, (radius, radius), radius)
                screen.blit(trail_surface, (pos[0] - radius, pos[1] - radius))

def draw_paddle(screen, pos, color, radius):
    """Draw paddle with border"""
    pygame.draw.circle(screen, color, pos, radius)
    pygame.draw.circle(screen, LINE_WHITE, pos, radius-3, 3)

def draw_puck(screen, pos, radius):
    """Draw puck with border"""
    pygame.draw.circle(screen, PUCK_COLOR, pos, radius)
    pygame.draw.circle(screen, BLACK, pos, radius, 2)

def draw_score_display(screen, p1_name, p2_name, score):
    """Draw player names and scores"""
    WIDTH = screen.get_width()
    
    draw_text(screen, p1_name, get_font(), WIDTH / 4, 30, color=P1_PADDLE_COLOR)
    draw_text(screen, f"{score[0]}", get_font(72), WIDTH / 4, 80, color=TEXT_COLOR)
    draw_text(screen, p2_name, get_font(), WIDTH * 3 / 4, 30, color=P2_PADDLE_COLOR)
    draw_text(screen, f"{score[1]}", get_font(72), WIDTH * 3 / 4, 80, color=TEXT_COLOR)