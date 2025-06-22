# client.py
import pygame
import socket
import json
import sys
import logging
import threading
import time
from collections import deque # Untuk menyimpan posisi puck sebelumnya
from settings import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.score_font = pygame.font.Font("assets/myfont.ttf", 74)
        self.info_font = pygame.font.Font("assets/myfont.ttf", 50)
        self.menu_font = pygame.font.Font("assets/myfont.ttf", 60)
        self.countdown_font = pygame.font.Font("assets/myfont.ttf", 150)
        self.puck_trail = deque(maxlen=10) # Simpan 10 posisi puck terakhir

    def draw_menu(self, message):
        self.screen.fill(BLACK)
        title_text = self.menu_font.render("Dark Air Hockey", True, WHITE)
        start_text = self.menu_font.render("Start Game", True, WHITE)
        restart_text = self.menu_font.render("Restart Game", True, WHITE)
        quit_text = self.menu_font.render("Quit", True, WHITE)

        title_rect = title_text.get_rect(center=(WIDTH / 2, HEIGHT / 4))
        start_rect = start_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50))
        restart_rect = restart_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 50))
        quit_rect = quit_text.get_rect(center=(WIDTH / 2, HEIGHT * 3 / 4))

        self.screen.blit(title_text, title_rect)
        self.screen.blit(start_text, start_rect)
        if message == "game_over":
            self.screen.blit(restart_text, restart_rect)
        self.screen.blit(quit_text, quit_rect)

        pygame.display.flip()

        return start_rect, restart_rect, quit_rect

    def draw(self, state, player_id):
        self.screen.fill(BLACK) # Papan tetap hitam
        self.draw_border() # Gambar pembatas lapangan
        self.draw_board()
        self.draw_goals()

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
                self.draw_message("YOU WIN!", f"Final Score: {state['scores'].get('1', 0)} - {state['scores'].get('2', 0)}")
            else:
                self.draw_message("YOU LOSE", f"Final Score: {state['scores'].get('1', 0)} - {state['scores'].get('2', 0)}")

        # Gambar elemen game hanya jika status bukan waiting
        if state['status'] == 'active':
            self.draw_game_elements(state, player_id)

        # Tampilkan countdown jika ada
        if state.get('countdown', 0) > 0:
            self.draw_countdown(state['countdown'])

        pygame.display.flip()

    def draw_board(self):
        pygame.draw.line(self.screen, GLOW_COLOR, (WIDTH / 2, 0), (WIDTH / 2, HEIGHT), 5)
        pygame.draw.circle(self.screen, GLOW_COLOR, (WIDTH / 2, HEIGHT / 2), 75, 5)

    def draw_border(self):
        # Gambar garis pembatas di tepi lapangan dengan warna glow
        # Garis atas
        pygame.draw.line(self.screen, GLOW_COLOR, (0, 0), (WIDTH, 0), 5)
        # Garis bawah
        pygame.draw.line(self.screen, GLOW_COLOR, (0, HEIGHT), (WIDTH, HEIGHT), 5)
        # Garis kiri (kecuali area gawang)
        pygame.draw.line(self.screen, GLOW_COLOR, (0, 0), (0, GOAL_Y_START), 5)
        pygame.draw.line(self.screen, GLOW_COLOR, (0, GOAL_Y_START + GOAL_HEIGHT), (0, HEIGHT), 5)
        # Garis kanan (kecuali area gawang)
        pygame.draw.line(self.screen, GLOW_COLOR, (WIDTH, 0), (WIDTH, GOAL_Y_START), 5)
        pygame.draw.line(self.screen, GLOW_COLOR, (WIDTH, GOAL_Y_START + GOAL_HEIGHT), (WIDTH, HEIGHT), 5)


    def draw_goals(self):
        # Gawang kiri (Player 2 scores here)
        pygame.draw.rect(self.screen, WHITE, (0, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5) # Gawang putih
        # Gawang kanan (Player 1 scores here)
        pygame.draw.rect(self.screen, WHITE, (WIDTH - GOAL_WIDTH, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5) # Gawang putih

    def draw_game_elements(self, state, player_id):
         # Gambar paddle dengan warna lebih terang
        for pid_str, p_data in state['paddles'].items():
            pid = int(pid_str)
            color = LIGHT_BLUE if pid == 1 else LIGHT_RED
            pos = (int(p_data['x']), int(p_data['y']))
            pygame.draw.circle(self.screen, color, pos, PADDLE_RADIUS)
            # Beri sorotan pada paddle pemain
            if pid == player_id:
                pygame.draw.circle(self.screen, WHITE, pos, PADDLE_RADIUS, 3) # Sorotan tetap putih

        # Gambar shadow puck
        puck_data = state['puck']
        current_puck_pos = (int(puck_data['x']), int(puck_data['y']))
        self.puck_trail.appendleft(current_puck_pos) # Tambahkan posisi terbaru ke depan

        for i, pos in enumerate(self.puck_trail):
            # Hitung opasitas dan ukuran berdasarkan posisi dalam trail
            # Semakin jauh ke belakang (i lebih besar), semakin pudar dan kecil
            alpha = max(0, 255 - i * (255 // len(self.puck_trail)))
            radius = max(1, PUCK_RADIUS - i * (PUCK_RADIUS // len(self.puck_trail)))

            # Buat permukaan sementara dengan alpha channel
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (50, 50, 50, alpha), (radius, radius), radius) # Warna shadow abu-abu gelap
            self.screen.blit(s, (pos.x - radius, pos.y - radius) if hasattr(pos, 'x') else (pos_tuple_x - radius, pos_tuple_y - radius))

        # Gambar puck utama (warna putih)
        pygame.draw.circle(self.screen, WHITE, current_puck_pos, PUCK_RADIUS)
        pygame.draw.circle(self.screen, BLACK, current_puck_pos, PUCK_RADIUS, 2) # Tambahkan outline hitam tipis untuk visibilitas

        # Gambar skor
        scores = state['scores']
        # Pastikan key '1' dan '2' ada, berikan default 0 jika tidak
        p1_score_text = str(scores.get('1', 0)) # Ambil skor Player 1
        p2_score_text = str(scores.get('2', 0)) # Ambil skor Player 2

        p1_score = self.score_font.render(p1_score_text, True, LIGHT_BLUE)
        p2_score = self.score_font.render(p2_score_text, True, LIGHT_RED)
        self.screen.blit(p1_score, (WIDTH / 4, 10))
        self.screen.blit(p2_score, (WIDTH * 3 / 4 - p2_score.get_width(), 10))

    def draw_message(self, line1, line2=None):
        text1 = self.info_font.render(line1, True, WHITE) # Warna teks pesan disesuaikan untuk latar hitam
        rect1 = text1.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 20))
        self.screen.blit(text1, rect1)
        if line2:
            text2 = self.info_font.render(line2, True, WHITE) # Warna teks pesan disesuaikan
            rect2 = text2.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30))
            self.screen.blit(text2, rect2)

    def draw_countdown(self, number):
        text = self.countdown_font.render(str(number), True, GLOW_COLOR)
        rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
        self.screen.blit(text, rect)

class NetworkClient:
    def __init__(self, server_ip, port):
        self.server_address = (server_ip, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_id = None
        self.latest_state = None
        self.running = True
        self.connected = False
        self.game_started = False
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
                    self.connected = True
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
        while self.running and self.connected:
            message_str = self._receive_message()
            if message_str is None:
                logging.error("Disconnected from server.")
                self.connected = False
                self.game_started = False
                break
            try:
                state = json.loads(message_str)
                with self.lock:
                    self.latest_state = state
                    if state['status'] == 'game_over':
                        self.game_started = False # Go back to menu after game over
            except json.JSONDecodeError:
                logging.warning(f"Received invalid JSON: {message_str}")

    def send_paddle_update(self, pos):
        if self.connected and self.game_started:
            try:
                command = {'type': 'update_paddle', 'pos': pos}
                self.socket.sendall((json.dumps(command) + '\n').encode('utf-8'))
            except socket.error:
                self.connected = False
                self.game_started = False

    def get_state(self):
        with self.lock:
            return self.latest_state

    def start_listening(self):
        threading.Thread(target=self.listen, daemon=True).start()

    def close(self):
        self.running = False
        if self.socket:
            self.socket.close()

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Dark Air Hockey")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)

    server_ip = input(f"Masukkan IP server (default: {INPUT_SERVER_IP}): ") or INPUT_SERVER_IP
    client = NetworkClient(server_ip, SERVER_PORT)

    menu_state = "main" # "main", "game"
    start_button_rect = None
    restart_button_rect = None
    quit_button_rect = None

    client.running = True
    while client.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.running = False
            if menu_state == "main" or (menu_state == "game" and client.get_state() and client.get_state()['status'] == 'game_over'):
                start_rect, restart_rect, quit_rect = renderer.draw_menu(message="game_over" if client.get_state() and client.get_state()['status'] == 'game_over' else "main")
                start_button_rect = start_rect
                restart_button_rect = restart_rect
                quit_button_rect = quit_rect
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if start_button_rect and start_button_rect.collidepoint(event.pos):
                        if not client.connected:
                            if client.connect():
                                client.start_listening()
                        client.game_started = True
                        menu_state = "game"
                    elif restart_button_rect and restart_button_rect.collidepoint(event.pos) and client.get_state() and client.get_state()['status'] == 'game_over':
                        client.game_started = True
                        menu_state = "game"
                        # Optionally send a reset signal to the server if needed for more complex game resets
                    elif quit_button_rect and quit_button_rect.collidepoint(event.pos):
                        client.running = False
            elif menu_state == "game" and client.connected and client.game_started:
                if event.type == pygame.MOUSEMOTION:
                    client.send_paddle_update(event.pos)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    client.send_paddle_update(event.pos) # Send on click as well

                game_state = client.get_state()
                renderer.draw(game_state, client.player_id)
                if game_state and game_state['status'] == 'game_over':
                    menu_state = "main" # Go back to menu after game over
            else:
                # Initial connection screen or error message
                renderer.draw_menu("main") # Show menu even if not connected yet

        clock.tick(FPS)

    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()