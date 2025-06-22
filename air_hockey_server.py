# server.py
import socket
import threading
import json
import time
import random
import logging
from settings import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Puck:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT / 2
        self.vx = 0
        self.vy = 0

    def reset(self, direction):
        self.x = WIDTH / 2
        self.y = HEIGHT / 2
        # Puck diluncurkan ke arah pemain yang tidak mencetak gol
        self.vx = 5 * direction
        self.vy = random.uniform(-5, 5)

    def move(self):
        self.x += self.vx
        self.y += self.vy

class Paddle:
    def __init__(self, player_id):
        self.id = player_id
        self.x = 100 if player_id == 1 else WIDTH - 100
        self.y = HEIGHT / 2
        
    def update_pos(self, x, y):
        self.y = max(PADDLE_RADIUS, min(y, HEIGHT - PADDLE_RADIUS))
        if self.id == 1:
            self.x = max(PADDLE_RADIUS, min(x, WIDTH / 2 - PADDLE_RADIUS))
        else:
            self.x = max(WIDTH / 2 + PADDLE_RADIUS, min(x, WIDTH - PADDLE_RADIUS))

class Game:
    def __init__(self):
        self.puck = Puck()
        self.paddles = {1: Paddle(1), 2: Paddle(2)}
        self.scores = {1: 0, 2: 0}
        self.status = 'waiting'  # waiting, active, game_over
        self.winner = None
        self.last_goal_time = 0
        self.countdown = 0

    def update(self):
        if self.status != 'active':
            return
            
        # Countdown setelah gol
        if time.time() - self.last_goal_time < 2:
            self.countdown = 2 - int(time.time() - self.last_goal_time)
            return
        else:
            self.countdown = 0

        self.puck.move()
        self.check_collisions()

    def check_collisions(self):
        # Tumbukan dinding atas/bawah
        if self.puck.y - PUCK_RADIUS <= 0:
            self.puck.y = PUCK_RADIUS + 1 # Pindahkan sedikit ke dalam
            self.puck.vy *= -1
        elif self.puck.y + PUCK_RADIUS >= HEIGHT:
            self.puck.y = HEIGHT - PUCK_RADIUS - 1 # Pindahkan sedikit ke dalam
            self.puck.vy *= -1

        # Tumbukan paddle
        for paddle in self.paddles.values():
            dist_x = self.puck.x - paddle.x
            dist_y = self.puck.y - paddle.y
            distance = (dist_x**2 + dist_y**2)**0.5
            if distance < PADDLE_RADIUS + PUCK_RADIUS:
                # Fisika pantulan yang lebih baik
                norm_x, norm_y = dist_x / distance, dist_y / distance
                
                # Pindahkan puck keluar dari tabrakan untuk mencegah tersangkut
                overlap = (PADDLE_RADIUS + PUCK_RADIUS) - distance
                self.puck.x -= norm_x * overlap
                self.puck.y -= norm_y * overlap

                self.puck.vx = norm_x * 9
                self.puck.vy = norm_y * 9
                # Tambahkan sedikit "spin" acak untuk menghindari gerakan bolak-balik yang membosankan
                self.puck.vy += random.uniform(-0.5, 0.5)

        # Cek Gol
        # Cek Gol untuk Player 1 (gawang di kiri)
        if self.puck.x - PUCK_RADIUS <= GOAL_WIDTH and \
           self.puck.y > GOAL_Y_START and self.puck.y < GOAL_Y_START + GOAL_HEIGHT:
            self.score_goal(2) # Player 2 mencetak gol
        # Cek Gol untuk Player 2 (gawang di kanan)
        elif self.puck.x + PUCK_RADIUS >= WIDTH - GOAL_WIDTH and \
             self.puck.y > GOAL_Y_START and self.puck.y < GOAL_Y_START + GOAL_HEIGHT:
            self.score_goal(1) # Player 1 mencetak gol
        # Tumbukan dinding samping jika bukan di area gawang
        elif self.puck.x - PUCK_RADIUS <= 0:
            self.puck.x = PUCK_RADIUS + 1 # Pindahkan sedikit ke dalam
            self.puck.vx *= -1 # Pantulkan jika menabrak sisi kiri
        elif self.puck.x + PUCK_RADIUS >= WIDTH:
            self.puck.x = WIDTH - PUCK_RADIUS - 1 # Pindahkan sedikit ke dalam
            self.puck.vx *= -1 # Pantulkan jika menabrak sisi kanan

    def score_goal(self, player_id):
        self.scores[player_id] += 1
        logging.info(f"Goal for Player {player_id}! Score: {self.scores[1]}-{self.scores[2]}")
        
        if self.scores[player_id] >= WINNING_SCORE:
            self.status = 'game_over'
            self.winner = player_id
            logging.info(f"Player {player_id} wins the game!")
        else:
            # Reset puck ke arah pemain yang kebobolan
            direction = -1 if player_id == 1 else 1
            self.puck.reset(direction)
            self.last_goal_time = time.time()

    def reset(self):
        logging.info("Resetting game state.")
        self.__init__()

    def get_state(self):
        return {
            'status': self.status,
            'winner': self.winner,
            'countdown': self.countdown,
            'puck': {'x': self.puck.x, 'y': self.puck.y},
            'paddles': {pid: {'x': p.x, 'y': p.y} for pid, p in self.paddles.items()},
            'scores': self.scores
        }

class GameServer:
    def __init__(self, host, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.clients = {} # {player_id: conn}
        self.game = Game()
        self.lock = threading.Lock()

    def broadcast(self):
        while True:
            with self.lock:
                if not self.clients:
                    time.sleep(0.5)
                    continue
                
                state = self.game.get_state()
                message = json.dumps(state) + '\n'
                
                # Buat salinan untuk mencegah error saat iterasi jika ada diskoneksi
                disconnected_clients = []
                for pid, conn in list(self.clients.items()):
                    try:
                        conn.sendall(message.encode('utf-8'))
                    except (socket.error, BrokenPipeError):
                        disconnected_clients.append(pid)
            
            # Handle diskoneksi di luar lock utama
            for pid in disconnected_clients:
                self.handle_disconnection(pid)

            time.sleep(1 / FPS)
    
    def client_handler(self, conn, player_id):
        buffer = ""
        while True:
            try:
                data = conn.recv(1024).decode('utf-8')
                if not data:
                    break # Koneksi ditutup oleh klien
                
                buffer += data
                while '\n' in buffer:
                    command_str, buffer = buffer.split('\n', 1)
                    command = json.loads(command_str)
                    
                    if command['type'] == 'update_paddle':
                        with self.lock:
                            self.game.paddles[player_id].update_pos(command['pos'][0], command['pos'][1])

            except (socket.error, json.JSONDecodeError, ConnectionResetError):
                break
        
        self.handle_disconnection(player_id)

    def handle_disconnection(self, player_id):
        with self.lock:
            if player_id in self.clients:
                logging.info(f"Player {player_id} disconnected.")
                self.clients.pop(player_id, None)
                
                # Jika semua pemain keluar, reset total
                if not self.clients:
                    self.game.reset()
                else: # Jika masih ada pemain, set status ke 'waiting'
                    self.game.status = 'waiting'
                    self.game.winner = 'opponent_disconnected'

    def run(self):
        self.server_socket.listen()
        logging.info(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

        # Thread untuk menyiarkan state game
        threading.Thread(target=self.broadcast, daemon=True).start()
        # Thread untuk update fisika game
        threading.Thread(target=self.game_loop, daemon=True).start()

        while True:
            conn, addr = self.server_socket.accept()
            with self.lock:
                if len(self.clients) >= 2:
                    logging.warning(f"Connection refused from {addr}. Game is full.")
                    conn.sendall((json.dumps({'error': 'Game is full'}) + '\n').encode('utf-8'))
                    conn.close()
                    continue

                player_id = 1 if 1 not in self.clients else 2
                self.clients[player_id] = conn
                logging.info(f"Player {player_id} connected from {addr}")
                
                # Kirim ID ke client
                init_msg = json.dumps({'type': 'init', 'player_id': player_id}) + '\n'
                conn.sendall(init_msg.encode('utf-8'))
                
                if len(self.clients) == 2:
                    logging.info("Two players connected. Starting game.")
                    self.game.reset() # Reset game untuk sesi baru
                    self.game.status = 'active'
                
                threading.Thread(target=self.client_handler, args=(conn, player_id), daemon=True).start()

    def game_loop(self):
        while True:
            with self.lock:
                self.game.update()
            time.sleep(1/120) # Fisika berjalan lebih cepat dari broadcast

if __name__ == "__main__":
    server = GameServer(SERVER_HOST, SERVER_PORT)
    server.run()