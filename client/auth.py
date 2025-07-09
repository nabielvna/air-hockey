import pygame
import requests
import sys
from client.graphics import get_font, draw_text, show_message, TEXT_COLOR, BLACK, P1_PADDLE_COLOR

HTTP_SERVER_URL = 'http://127.0.0.1:8000'

def get_user_input(screen, prompt, is_password=False):
    user_text = ""
    WIDTH, HEIGHT = screen.get_size()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: 
                    return user_text
                elif event.key == pygame.K_BACKSPACE: 
                    user_text = user_text[:-1]
                else: 
                    user_text += event.unicode
        
        screen.fill(BLACK)
        draw_text(screen, prompt, get_font(), WIDTH / 2, HEIGHT / 2 - 50, color=TEXT_COLOR)
        display_text = "*" * len(user_text) if is_password else user_text
        draw_text(screen, display_text, get_font(), WIDTH / 2, HEIGHT / 2, color=TEXT_COLOR)
        pygame.display.flip()

def auth_flow(screen):
    WIDTH, HEIGHT = screen.get_size()
    
    while True:
        screen.fill(BLACK)
        draw_text(screen, "1. Login", get_font(), WIDTH / 2, HEIGHT / 2 - 20)
        draw_text(screen, "2. Register", get_font(), WIDTH / 2, HEIGHT / 2 + 20)
        draw_text(screen, "Pilih opsi (1 atau 2)", get_font(), WIDTH / 2, HEIGHT / 2 + 80)
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                return None, None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP_1):
                    username = get_user_input(screen, "Username:")
                    password = get_user_input(screen, "Password:", is_password=True)
                    try:
                        res = requests.post(f"{HTTP_SERVER_URL}/login", json={'name': username, 'password': password})
                        if res.status_code == 200:
                            show_message(screen, "Login successful!")
                            return username, res.json()['token']
                        else: 
                            show_message(screen, res.json().get('error', 'Login failed'), color=P1_PADDLE_COLOR)
                    except requests.RequestException: 
                        show_message(screen, "Server connection error.", color=P1_PADDLE_COLOR)
                        
                if event.key in (pygame.K_2, pygame.K_KP_2):
                    username = get_user_input(screen, "Choose Username:")
                    password = get_user_input(screen, "Choose Password:", is_password=True)
                    try:
                        res = requests.post(f"{HTTP_SERVER_URL}/register", json={'name': username, 'password': password})
                        if res.status_code == 201: 
                            show_message(screen, "Registration successful! Please login.")
                        else: 
                            show_message(screen, res.json().get('error', 'Registration failed'), color=P1_PADDLE_COLOR)
                    except requests.RequestException: 
                        show_message(screen, "Server connection error.", color=P1_PADDLE_COLOR)