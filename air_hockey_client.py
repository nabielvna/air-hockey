# air_hockey_client.py
# Client yang langsung connect via load balancer
# User cukup input IP load balancer, sisanya otomatis

import pygame
import socket
import json
import sys
import logging
import threading
import time
from collections import deque
from settings import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.score_font = pygame.font.Font(None, 74)
        self.info_font = pygame.font.Font(None, 50)
        self.small_font = pygame.font.Font(None, 36)
        self.countdown_font = pygame.font.Font(None, 150)
        self.puck_trail = deque(maxlen=10)

    def draw(self, state, player_id, connection_info=None):
        self.screen.fill(BLACK)
        self.draw_border()
        self.draw_board()
        self.draw_goals()

        if not state:
            if connection_info:
                self.draw_connection_status(connection_info)
            else:
                self.draw_message("Connecting to server...")
            return

        if state['status'] == 'waiting':
            self.draw_message("Waiting for opponent...")
        elif state['status'] == 'game_over':
            winner = state.get('winner')
            if winner == 'opponent_disconnected':
                self.draw_message("Opponent Disconnected", "You win by default")
            elif winner == player_id:
                self.draw_message("YOU WIN!", f"Final Score: {state['scores']['1']} - {state['scores']['2']}")
            else:
                self.draw_message("YOU LOSE", f"Final Score: {state['scores']['1']} - {state['scores']['2']}")
        
        if state['status'] != 'waiting':
            self.draw_game_elements(state, player_id)
        
        if state.get('countdown', 0) > 0:
            self.draw_countdown(state['countdown'])

        if connection_info and 'server_info' in connection_info:
            self.draw_server_info(connection_info['server_info'])

        pygame.display.flip()

    def draw_connection_status(self, info):
        """Draw connection status"""
        status = info.get('status', 'Connecting...')
        detail = info.get('detail', '')
        
        self.draw_message(status, detail)

    def draw_server_info(self, info):
        """Draw server info at top right"""
        text = self.small_font.render(f"Via Load Balancer: {info}", True, WHITE)
        self.screen.blit(text, (WIDTH - text.get_width() - 10, 10))

    def draw_board(self):
        pygame.draw.line(self.screen, GRAY, (WIDTH / 2, 0), (WIDTH / 2, HEIGHT), 5)
        pygame.draw.circle(self.screen, GRAY, (WIDTH / 2, HEIGHT / 2), 75, 5)

    def draw_border(self):
        pygame.draw.line(self.screen, GRAY, (0, 0), (WIDTH, 0), 5)
        pygame.draw.line(self.screen, GRAY, (0, HEIGHT), (WIDTH, HEIGHT), 5)
        pygame.draw.line(self.screen, GRAY, (0, 0), (0, GOAL_Y_START), 5)
        pygame.draw.line(self.screen, GRAY, (0, GOAL_Y_START + GOAL_HEIGHT), (0, HEIGHT), 5)
        pygame.draw.line(self.screen, GRAY, (WIDTH, 0), (WIDTH, GOAL_Y_START), 5)
        pygame.draw.line(self.screen, GRAY, (WIDTH, GOAL_Y_START + GOAL_HEIGHT), (WIDTH, HEIGHT), 5)

    def draw_goals(self):
        pygame.draw.rect(self.screen, WHITE, (0, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)
        pygame.draw.rect(self.screen, WHITE, (WIDTH - GOAL_WIDTH, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)

    def draw_game_elements(self, state, player_id):
        # Gambar paddle
        for pid_str, p_data in state['paddles'].items():
            pid = int(pid_str)
            color = BLUE if pid == 1 else RED
            pos = (int(p_data['x']), int(p_data['y']))
            pygame.draw.circle(self.screen, color, pos, PADDLE_RADIUS)
            if pid == player_id:
                pygame.draw.circle(self.screen, WHITE, pos, PADDLE_RADIUS, 3)

        # Puck trail effect
        puck_data = state['puck']
        current_puck_pos = (int(puck_data['x']), int(puck_data['y']))
        self.puck_trail.appendleft(current_puck_pos)

        for i, pos in enumerate(self.puck_trail):
            alpha = max(0, 255 - i * (255 // len(self.puck_trail)))
            radius = max(1, PUCK_RADIUS - i * (PUCK_RADIUS // len(self.puck_trail)))
            
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (100, 100, 100, alpha), (radius, radius), radius)
            self.screen.blit(s, (pos[0] - radius, pos[1] - radius))

        # Main puck
        pygame.draw.circle(self.screen, WHITE, current_puck_pos, PUCK_RADIUS)
        pygame.draw.circle(self.screen, BLACK, current_puck_pos, PUCK_RADIUS, 2)

        # Scores
        scores = state['scores']
        p1_score_text = str(scores.get('1', 0))
        p2_score_text = str(scores.get('2', 0))

        p1_score = self.score_font.render(p1_score_text, True, BLUE)
        p2_score = self.score_font.render(p2_score_text, True, RED)
        self.screen.blit(p1_score, (WIDTH / 4, 10))
        self.screen.blit(p2_score, (WIDTH * 3 / 4 - p2_score.get_width(), 10))

    def draw_message(self, line1, line2=None):
        text1 = self.info_font.render(line1, True, WHITE)
        rect1 = text1.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 20))
        self.screen.blit(text1, rect1)
        if line2:
            text2 = self.info_font.render(line2, True, WHITE)
            rect2 = text2.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30))
            self.screen.blit(text2, rect2)

    def draw_countdown(self, number):
        text = self.countdown_font.render(str(number), True, GRAY)
        rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
        self.screen.blit(text, rect)

class LoadBalancerClient:
    def __init__(self, lb_ip, lb_port=LOAD_BALANCER_PORT):
        self.lb_address = (lb_ip, lb_port)
        self.socket = None
        self.player_id = None
        self.latest_state = None
        self.running = True
        self.connected = False
        self.lock = threading.Lock()
        self.buffer = ""
        self.connection_info = {}

    def connect(self):
        """Connect via load balancer"""
        try:
            self.connection_info = {
                'status': f'Connecting to {self.lb_address[0]}:{self.lb_address[1]}',
                'detail': 'Via Load Balancer...'
            }
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect(self.lb_address)
            
            logging.info(f"Connected to load balancer at {self.lb_address}")
            
            # Wait for server initialization
            self.connection_info = {
                'status': 'Connected to Load Balancer',
                'detail': 'Waiting for server assignment...'
            }
            
            init_data_str = self._receive_message()
            if init_data_str:
                data = json.loads(init_data_str)
                if data.get('type') == 'init':
                    self.player_id = data['player_id']
                    self.connected = True
                    self.connection_info = {
                        'server_info': f'{self.lb_address[0]}:{self.lb_address[1]}'
                    }
                    logging.info(f"Assigned Player ID: {self.player_id} via Load Balancer")
                    return True
                elif data.get('error'):
                    self.connection_info = {
                        'status': 'Connection Failed',
                        'detail': data['error']
                    }
                    logging.error(f"Load Balancer error: {data['error']}")
                    return False
            return False
            
        except socket.timeout:
            self.connection_info = {
                'status': 'Connection Timeout',
                'detail': 'Load Balancer not responding'
            }
            logging.error(f"Connection to load balancer timed out")
        except socket.error as e:
            self.connection_info = {
                'status': 'Connection Failed',
                'detail': f'Cannot reach {self.lb_address[0]}'
            }
            logging.error(f"Connection failed: {e}")
        except Exception as e:
            self.connection_info = {
                'status': 'Unexpected Error',
                'detail': str(e)
            }
            logging.error(f"Unexpected error: {e}")

        if self.socket:
            self.socket.close()
            self.socket = None
        return False

    def _receive_message(self):
        while '\n' not in self.buffer:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    return None
                self.buffer += data
            except (socket.error, ConnectionResetError):
                return None
        message, self.buffer = self.buffer.split('\n', 1)
        return message

    def listen(self):
        """Listen for messages from server via load balancer"""
        while self.running:
            if not self.connected:
                time.sleep(1)
                continue

            try:
                message_str = self._receive_message()
                if message_str is None:
                    logging.warning("Lost connection to server via load balancer")
                    self.handle_disconnection()
                    continue

                state = json.loads(message_str)
                with self.lock:
                    self.latest_state = state

            except json.JSONDecodeError:
                logging.warning(f"Received invalid JSON: {message_str}")
            except Exception as e:
                logging.error(f"Listen error: {e}")
                self.handle_disconnection()

    def handle_disconnection(self):
        """Handle disconnection"""
        self.connected = False
        if self.socket:
            self.socket.close()
            self.socket = None
        
        with self.lock:
            self.latest_state = None
        
        self.connection_info = {
            'status': 'Connection Lost',
            'detail': 'Trying to reconnect...'
        }
        
        logging.info("Attempting to reconnect via load balancer...")
        time.sleep(5)
        
        if self.running:
            if self.connect():
                logging.info("Reconnection successful!")

    def send_paddle_update(self, pos):
        if not self.connected or not self.socket:
            return

        try:
            command = {'type': 'update_paddle', 'pos': pos}
            self.socket.sendall((json.dumps(command) + '\n').encode('utf-8'))
        except socket.error:
            logging.warning("Failed to send paddle update")
            self.handle_disconnection()

    def get_state(self):
        with self.lock:
            return self.latest_state

    def get_connection_info(self):
        return self.connection_info

    def start(self):
        threading.Thread(target=self.listen, daemon=True).start()

    def close(self):
        self.running = False
        self.connected = False
        if self.socket:
            self.socket.close()

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Air Hockey - Load Balancer Client")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    
    print("=" * 60)
    print("    AIR HOCKEY - LOAD BALANCER CLIENT")
    print("=" * 60)
    print()
    print("This client connects via Load Balancer which automatically")
    print("routes you to an available game server.")
    print()
    
    # Get load balancer IP
    default_lb_ip = "127.0.0.1"  # Local default
    lb_ip = input(f"Enter Load Balancer IP (default: {default_lb_ip}): ").strip()
    if not lb_ip:
        lb_ip = default_lb_ip
    
    # Optional: Custom port
    lb_port_input = input(f"Enter Load Balancer Port (default: {LOAD_BALANCER_PORT}): ").strip()
    lb_port = int(lb_port_input) if lb_port_input else LOAD_BALANCER_PORT
    
    print()
    print(f"Connecting to Load Balancer at {lb_ip}:{lb_port}...")
    print("Load Balancer will automatically assign you to an available server.")
    print()

    client = LoadBalancerClient(lb_ip, lb_port)
    
    if not client.connect():
        print("Could not connect via Load Balancer.")
        print("Make sure:")
        print("1. Load Balancer is running on the specified IP:Port")
        print("2. At least one game server is available")
        print("3. Network connection is working")
        
        # Show error for a few seconds
        start_time = time.time()
        while time.time() - start_time < 5:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            
            renderer.draw(None, None, client.get_connection_info())
            clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

    client.start()
    last_update_time = 0

    print("Connected via Load Balancer! Waiting for game to start...")

    while client.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.running = False

        # Send paddle updates
        current_time = time.time()
        if current_time - last_update_time > (1 / 60):
            client.send_paddle_update(pygame.mouse.get_pos())
            last_update_time = current_time

        # Render game state
        game_state = client.get_state()
        connection_info = client.get_connection_info()
        renderer.draw(game_state, client.player_id, connection_info)
        
        clock.tick(FPS)
    
    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()