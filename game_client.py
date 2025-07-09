import pygame
import socket
import json
import sys
from client.auth import auth_flow
from client.graphics import (
    draw_arena, update_puck_trail, draw_puck_trail, 
    draw_paddle, draw_puck, draw_score_display, show_message,
    P1_PADDLE_COLOR, P2_PADDLE_COLOR
)

GAME_SERVER_HOST = '127.0.0.1'
GAME_PORT = 9999
WIDTH, HEIGHT = 1200, 800

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Air Hockey")

def game_loop(game_socket):
    try:
        json.loads(game_socket.recv(1024).decode())
    except (socket.error, json.JSONDecodeError):
        show_message(screen, "Failed to start game.", color=P1_PADDLE_COLOR)
        return

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False
        
        try:
            game_socket.sendall(json.dumps({'x': pygame.mouse.get_pos()[0], 'y': pygame.mouse.get_pos()[1]}).encode())
            data = game_socket.recv(2048).decode()
            if not data: 
                break
            state = json.loads(data)

            # Draw game
            draw_arena(screen)
            
            PADDLE_RADIUS, PUCK_RADIUS = 25, 15
            p1_pos = [int(c) for c in state['p1_pos']]
            p2_pos = [int(c) for c in state['p2_pos']]
            
            # Draw paddles
            draw_paddle(screen, p1_pos, P1_PADDLE_COLOR, PADDLE_RADIUS)
            draw_paddle(screen, p2_pos, P2_PADDLE_COLOR, PADDLE_RADIUS)

            # Draw puck with trail
            puck_pos_int = [int(c) for c in state['puck_pos']]
            update_puck_trail(puck_pos_int)
            draw_puck_trail(screen)
            draw_puck(screen, puck_pos_int, PUCK_RADIUS)
            
            # Draw scores
            p1_name, p2_name = state.get('p1_name', 'P1'), state.get('p2_name', 'P2')
            draw_score_display(screen, p1_name, p2_name, state['score'])

            pygame.display.flip()
            
            if state['game_over']:
                winner_name = p1_name if state['score'][0] > state['score'][1] else p2_name
                show_message(screen, f"Game Over! {winner_name} Wins!", duration=3000)
                running = False
                
        except (socket.error, json.JSONDecodeError):
            running = False
            
    game_socket.close()

def main():
    username, token = auth_flow(screen)
    if not (username and token):
        pygame.quit()
        sys.exit()

    show_message(screen, "Waiting for another player...")
    try:
        game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        game_socket.connect((GAME_SERVER_HOST, GAME_PORT))
        game_socket.sendall(json.dumps({'name': username, 'token': token}).encode())
        game_loop(game_socket)
    except socket.error:
        show_message(screen, "Could not connect to game server.", color=P1_PADDLE_COLOR)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()