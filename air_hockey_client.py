# client.py
import pygame
import socket
import json
import sys
import logging
import threading
import time
from settings import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.score_font = pygame.font.Font(None, 74)
        self.info_font = pygame.font.Font(None, 50)
        self.countdown_font = pygame.font.Font(None, 150)

    def draw(self, state, player_id):
        self.screen.fill(WHITE)
        self.draw_board()
        self.draw_goals() # Gambar gawang

        if not state:
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
        
        # Gambar elemen game hanya jika status bukan waiting
        if state['status'] != 'waiting':
            self.draw_game_elements(state, player_id)
        
        # Tampilkan countdown jika ada
        if state.get('countdown', 0) > 0:
            self.draw_countdown(state['countdown'])

        pygame.display.flip()

    def draw_board(self):
        pygame.draw.line(self.screen, GRAY, (WIDTH / 2, 0), (WIDTH / 2, HEIGHT), 5)
        pygame.draw.circle(self.screen, GRAY, (WIDTH / 2, HEIGHT / 2), 75, 5)

    def draw_goals(self):
        # Gawang kiri (Player 2 scores here)
        pygame.draw.rect(self.screen, BLACK, (0, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)
        # Gawang kanan (Player 1 scores here)
        pygame.draw.rect(self.screen, BLACK, (WIDTH - GOAL_WIDTH, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)

    def draw_game_elements(self, state, player_id):
         # Gambar paddle
        for pid_str, p_data in state['paddles'].items():
            pid = int(pid_str)
            color = BLUE if pid == 1 else RED
            pos = (int(p_data['x']), int(p_data['y']))
            pygame.draw.circle(self.screen, color, pos, PADDLE_RADIUS)
            # Beri sorotan pada paddle pemain
            if pid == player_id:
                pygame.draw.circle(self.screen, BLACK, pos, PADDLE_RADIUS, 3)

        # Gambar puck
        puck_data = state['puck']
        pygame.draw.circle(self.screen, BLACK, (int(puck_data['x']), int(puck_data['y'])), PUCK_RADIUS)
        
        # Gambar skor
        scores = state['scores']
        p1_score = self.score_font.render(str(scores.get(1, 0)), True, BLUE)
        p2_score = self.score_font.render(str(scores.get(2, 0)), True, RED)
        self.screen.blit(p1_score, (WIDTH / 4, 10))
        self.screen.blit(p2_score, (WIDTH * 3 / 4 - p2_score.get_width(), 10))

    def draw_message(self, line1, line2=None):
        text1 = self.info_font.render(line1, True, BLACK)
        rect1 = text1.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 20))
        self.screen.blit(text1, rect1)
        if line2:
            text2 = self.info_font.render(line2, True, BLACK)
            rect2 = text2.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30))
            self.screen.blit(text2, rect2)

    def draw_countdown(self, number):
        text = self.countdown_font.render(str(number), True, GRAY)
        rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
        self.screen.blit(text, rect)

class NetworkClient:
    def __init__(self, server_ip, port):
        self.server_address = (server_ip, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_id = None
        self.latest_state = None
        self.running = True
        self.lock = threading.Lock()
        self.buffer = ""

    def connect(self):
        try:
            self.socket.connect(self.server_address)
            logging.info(f"Connected to server at {self.server_address}")
            
            # Tunggu pesan inisialisasi dari server
            init_data_str = self._receive_message()
            if init_data_str:
                data = json.loads(init_data_str)
                if data.get('type') == 'init':
                    self.player_id = data['player_id']
                    logging.info(f"Assigned Player ID: {self.player_id}")
                    return True
                elif data.get('error'):
                    logging.error(f"Server error: {data['error']}")
                    return False
            return False
        except socket.error as e:
            logging.error(f"Connection failed: {e}")
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
        while self.running:
            message_str = self._receive_message()
            if message_str is None:
                logging.error("Disconnected from server.")
                self.running = False
                break
            try:
                state = json.loads(message_str)
                with self.lock:
                    self.latest_state = state
            except json.JSONDecodeError:
                logging.warning(f"Received invalid JSON: {message_str}")

    def send_paddle_update(self, pos):
        try:
            command = {'type': 'update_paddle', 'pos': pos}
            self.socket.sendall((json.dumps(command) + '\n').encode('utf-8'))
        except socket.error:
            self.running = False

    def get_state(self):
        with self.lock:
            return self.latest_state

    def start(self):
        threading.Thread(target=self.listen, daemon=True).start()

    def close(self):
        self.running = False
        self.socket.close()

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Real-Time Air Hockey")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    
    server_ip = input(f"Masukkan IP server (default: {INPUT_SERVER_IP}): ") or INPUT_SERVER_IP
    client = NetworkClient(server_ip, SERVER_PORT)

    if not client.connect():
        renderer.draw_message("Could not connect to server.")
        pygame.time.wait(2000)
        pygame.quit()
        sys.exit()

    client.start()
    last_update_time = 0

    while client.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.running = False

        # Kirim update posisi paddle dengan interval
        current_time = time.time()
        if current_time - last_update_time > (1 / 60): # Kirim 60x per detik
             client.send_paddle_update(pygame.mouse.get_pos())
             last_update_time = current_time

        # Gambar state terbaru
        game_state = client.get_state()
        renderer.draw(game_state, client.player_id)
        
        clock.tick(FPS)
    
    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()