# air_hockey_client.py
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
        # Menggunakan font default Pygame (None)
        self.score_font = pygame.font.Font(None, 74)
        self.info_font = pygame.font.Font(None, 50)
        self.menu_font = pygame.font.Font(None, 60)
        self.small_font = pygame.font.Font(None, 36) # Untuk info server
        self.countdown_font = pygame.font.Font(None, 150)
        self.puck_trail = deque(maxlen=10)

    def draw_menu(self, message):
        self.screen.fill(BLACK)
        title_text = self.menu_font.render("Air Hockey", True, WHITE)
        start_text = self.menu_font.render("Start Game", True, WHITE)
        restart_text = self.menu_font.render("Restart Game", True, WHITE)
        quit_text = self.menu_font.render("Quit", True, WHITE)

        title_rect = title_text.get_rect(center=(WIDTH / 2, HEIGHT / 4))
        start_rect = start_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50))
        restart_rect = restart_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 50))
        quit_rect = quit_text.get_rect(center=(WIDTH / 2, HEIGHT * 3 / 4))

        self.screen.blit(title_text, title_rect)
        self.screen.blit(start_text, start_rect)
        if message == "game_over": # Hanya tampilkan tombol restart jika game over
            self.screen.blit(restart_text, restart_rect)
        self.screen.blit(quit_text, quit_rect)

        pygame.display.flip()

        return start_rect, restart_rect, quit_rect

    def draw(self, state, player_id, connection_info=None):
        self.screen.fill(BLACK) # Papan gelap
        self.draw_border() # Pembatas dengan glow
        self.draw_board() # Papan dengan glow
        self.draw_goals() # Gawang putih

        if not state:
            if connection_info:
                self.draw_connection_status(connection_info)
            else:
                self.draw_message("Connecting to server...")
            return

        # Menampilkan pesan status game
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
        
        # Gambar elemen game hanya jika status aktif
        if state['status'] == 'active':
            self.draw_game_elements(state, player_id)
        
        # Tampilkan countdown jika ada
        if state.get('countdown', 0) > 0:
            self.draw_countdown(state['countdown'])

        # Tampilkan info koneksi di pojok kanan atas
        if connection_info and 'server_info' in connection_info:
            self.draw_server_info(connection_info['server_info'])

        pygame.display.flip()

    def draw_connection_status(self, info):
        status = info.get('status', 'Connecting...')
        detail = info.get('detail', '')
        self.draw_message(status, detail)

    def draw_server_info(self, info):
        text = self.small_font.render(f"Connected: {info}", True, WHITE)
        self.screen.blit(text, (WIDTH - text.get_width() - 10, 10))

    def draw_board(self):
        pygame.draw.line(self.screen, GLOW_COLOR, (WIDTH / 2, 0), (WIDTH / 2, HEIGHT), 5)
        pygame.draw.circle(self.screen, GLOW_COLOR, (WIDTH / 2, HEIGHT / 2), 75, 5)

    def draw_border(self):
        pygame.draw.line(self.screen, GLOW_COLOR, (0, 0), (WIDTH, 0), 5)
        pygame.draw.line(self.screen, GLOW_COLOR, (0, HEIGHT), (WIDTH, HEIGHT), 5)
        pygame.draw.line(self.screen, GLOW_COLOR, (0, 0), (0, GOAL_Y_START), 5)
        pygame.draw.line(self.screen, GLOW_COLOR, (0, GOAL_Y_START + GOAL_HEIGHT), (0, HEIGHT), 5)
        pygame.draw.line(self.screen, GLOW_COLOR, (WIDTH, 0), (WIDTH, GOAL_Y_START), 5)
        pygame.draw.line(self.screen, GLOW_COLOR, (WIDTH, GOAL_Y_START + GOAL_HEIGHT), (WIDTH, HEIGHT), 5)

    def draw_goals(self):
        pygame.draw.rect(self.screen, WHITE, (0, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)
        pygame.draw.rect(self.screen, WHITE, (WIDTH - GOAL_WIDTH, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)

    def draw_game_elements(self, state, player_id):
        # Gambar paddle dengan warna lebih terang
        for pid_str, p_data in state['paddles'].items():
            pid = int(pid_str)
            color = LIGHT_BLUE if pid == 1 else LIGHT_RED
            pos = (int(p_data['x']), int(p_data['y']))
            pygame.draw.circle(self.screen, color, pos, PADDLE_RADIUS)
            if pid == player_id:
                pygame.draw.circle(self.screen, WHITE, pos, PADDLE_RADIUS, 3)

        # Shadow puck
        puck_data = state['puck']
        current_puck_pos = (int(puck_data['x']), int(puck_data['y']))
        self.puck_trail.appendleft(current_puck_pos)

        for i, pos_tuple in enumerate(self.puck_trail):
            alpha = max(0, 255 - i * (255 // len(self.puck_trail)))
            radius = max(1, PUCK_RADIUS - i * (PUCK_RADIUS // len(self.puck_trail)))
            
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            # Menggunakan SHADOW_COLOR dari settings.py
            pygame.draw.circle(s, (SHADOW_COLOR[0], SHADOW_COLOR[1], SHADOW_COLOR[2], alpha), (radius, radius), radius)
            self.screen.blit(s, (pos_tuple[0] - radius, pos_tuple[1] - radius))

        # Main puck (putih dengan outline hitam)
        pygame.draw.circle(self.screen, WHITE, current_puck_pos, PUCK_RADIUS)
        pygame.draw.circle(self.screen, BLACK, current_puck_pos, PUCK_RADIUS, 2)

        # Scores (menggunakan warna paddle yang lebih terang)
        scores = state['scores']
        p1_score_text = str(scores.get('1', 0))
        p2_score_text = str(scores.get('2', 0))

        p1_score = self.score_font.render(p1_score_text, True, LIGHT_BLUE)
        p2_score = self.score_font.render(p2_score_text, True, LIGHT_RED)
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
        text = self.countdown_font.render(str(number), True, GLOW_COLOR)
        rect = text.get_rect(center=(WIDTH/2, HEIGHT/2))
        self.screen.blit(text, rect)

class LoadBalancerClient:
    def __init__(self, lb_ip, lb_port=LOAD_BALANCER_PORT):
        self.lb_address = (lb_ip, lb_port)
        self.socket = None
        self.player_id = None
        self.latest_state = None
        self.running = True
        self.connected = False # Status koneksi ke game server via LB
        self.lock = threading.Lock()
        self.buffer = ""
        self.connection_info = {} # Untuk menampilkan status koneksi di UI

    def connect(self):
        if self.connected and self.socket: # Jika sudah terhubung dan socket masih ada
            logging.info("Already connected. Skipping new connection.")
            return True
        
        # Tutup socket lama jika ada
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        try:
            self.connection_info = {
                'status': f'Connecting to {self.lb_address[0]}:{self.lb_address[1]}',
                'detail': 'Via Load Balancer...'
            }
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10) # Timeout untuk koneksi awal ke LB
            self.socket.connect(self.lb_address)
            
            logging.info(f"Connected to load balancer at {self.lb_address}")
            
            # Tunggu pesan inisialisasi dari server (yang di-proxy oleh LB)
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
                        'server_info': f'{self.lb_address[0]}:{self.lb_address[1]}' # Menunjukkan koneksi via LB
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
            # Jika tidak ada init data atau data tidak valid
            self.connection_info = {
                'status': 'Connection Failed',
                'detail': 'Invalid server response'
            }
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
                'detail': f'Cannot reach {self.lb_address[0]}: {e}'
            }
            logging.error(f"Connection failed: {e}")
        except Exception as e:
            self.connection_info = {
                'status': 'Unexpected Error',
                'detail': str(e)
            }
            logging.error(f"Unexpected error during connection: {e}")
        finally:
            # Tutup socket jika koneksi gagal atau inisialisasi tidak berhasil
            if self.socket and not self.connected:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
        return False

    def _receive_message(self):
        try:
            while '\n' not in self.buffer:
                # Periksa apakah socket masih valid sebelum recv
                if not self.socket:
                    return None
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    logging.warning("Server closed connection during receive.")
                    return None
                self.buffer += data
            message, self.buffer = self.buffer.split('\n', 1)
            return message
        except (socket.error, ConnectionResetError, BrokenPipeError) as e:
            logging.error(f"Error receiving message: {e}")
            return None

    def listen(self):
        """Listen for messages from server via load balancer"""
        while self.running:
            if not self.connected:
                time.sleep(0.5) # Tunggu sebentar jika tidak terhubung
                continue

            message_str = self._receive_message()
            if message_str is None:
                logging.warning("Lost connection to server via load balancer")
                self.handle_disconnection()
                continue # Lanjutkan loop untuk mencoba reconnect

            try:
                state = json.loads(message_str)
                with self.lock:
                    self.latest_state = state

            except json.JSONDecodeError:
                logging.warning(f"Received invalid JSON: {message_str}")
            except Exception as e:
                logging.error(f"Unexpected error in listen thread: {e}")
                self.handle_disconnection()

    def handle_disconnection(self):
        """Handle disconnection from game server"""
        if not self.connected: # Sudah ditangani
            return
        
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        with self.lock:
            self.latest_state = None # Clear state saat terputus
        
        self.connection_info = {
            'status': 'Connection Lost!',
            'detail': 'Attempting reconnect...'
        }
        
        logging.info("Disconnected from game server. Attempting to reconnect via load balancer...")
        # Reconnect logic will be handled by the main loop by setting menu_state to "main"
        # and letting the user click "Start Game" again.
        # Or you can add an automatic reconnect attempt here for seamless experience.
        # For now, let's rely on the menu.

    def send_paddle_update(self, pos):
        if not self.connected or not self.socket:
            return

        try:
            command = {'type': 'update_paddle', 'pos': pos}
            self.socket.sendall((json.dumps(command) + '\n').encode('utf-8'))
        except (socket.error, BrokenPipeError):
            logging.warning("Failed to send paddle update. Connection might be lost.")
            self.handle_disconnection()

    def get_state(self):
        with self.lock:
            return self.latest_state

    def get_connection_info(self):
        return self.connection_info

    def start_listening_thread(self):
        # Pastikan hanya satu thread listen yang berjalan
        for t in threading.enumerate():
            if t.name == "ClientListenThread":
                logging.info("Listen thread already running.")
                return
        thread = threading.Thread(target=self.listen, daemon=True, name="ClientListenThread")
        thread.start()
        logging.info("Client listen thread started.")

    def close(self):
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
                logging.info("Socket closed.")
            except OSError as e:
                logging.warning(f"Error closing socket: {e}")
            self.socket = None

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
    
    default_lb_ip = "127.0.0.1"
    lb_ip = input(f"Enter Load Balancer IP (default: {default_lb_ip}): ").strip()
    if not lb_ip:
        lb_ip = default_lb_ip
    
    lb_port_input = input(f"Enter Load Balancer Port (default: {LOAD_BALANCER_PORT}): ").strip()
    lb_port = int(lb_port_input) if lb_port_input else LOAD_BALANCER_PORT
    
    print()
    print(f"Connecting to Load Balancer at {lb_ip}:{lb_port}...")
    print("Load Balancer will automatically assign you to an available server.")
    print()

    client = LoadBalancerClient(lb_ip, lb_port)
    
    menu_state = "main" # "main", "game"
    
    # Variabel untuk menyimpan rect tombol
    start_button_rect = None
    restart_button_rect = None
    quit_button_rect = None

    client.running = True
    while client.running:
        current_game_state = client.get_state()
        connection_info = client.get_connection_info() # Ambil info koneksi terbaru

        # Logika transisi menu
        # Jika game over (dari server) dan kita sedang di game, pindah ke menu
        if current_game_state and current_game_state['status'] == 'game_over' and client.game_started:
            logging.info("Client detected game_over status from server. Returning to menu.")
            client.game_started = False
            menu_state = "main"
        # Jika koneksi terputus saat di game, pindah ke menu
        if not client.connected and menu_state == "game":
            logging.warning("Connection lost during game. Returning to main menu.")
            menu_state = "main"
            client.game_started = False
            client.latest_state = None # Clear state for menu display

        if menu_state == "main":
            menu_message = "game_over" if current_game_state and current_game_state['status'] == 'game_over' else "main"
            start_rect, restart_rect, quit_rect = renderer.draw_menu(message=menu_message)
            start_button_rect = start_rect
            restart_button_rect = restart_rect
            quit_button_rect = quit_rect

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    client.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if start_button_rect and start_button_rect.collidepoint(event.pos):
                        logging.info("Start Game button clicked.")
                        if not client.connected: # Coba connect hanya jika belum terhubung
                            if client.connect(): # Mencoba koneksi baru ke LB
                                client.start_listening_thread() # Mulai thread listen setelah connect
                                client.game_started = True
                                menu_state = "game"
                                client.latest_state = None # Reset state agar tidak render state lama
                            else:
                                # Jika gagal koneksi, tampilkan pesan error singkat di menu
                                renderer.draw_connection_status(client.get_connection_info())
                                pygame.display.flip()
                                pygame.time.wait(1000)
                        else: # Sudah terhubung, langsung mulai game (mungkin dari game_over sebelumnya)
                            client.game_started = True
                            menu_state = "game"
                            client.latest_state = None
                            logging.info("Already connected, starting new game session.")
                    elif restart_button_rect and restart_button_rect.collidepoint(event.pos) and current_game_state and current_game_state['status'] == 'game_over':
                        logging.info("Restart Game button clicked.")
                        # Untuk restart, klien hanya perlu mengatur ulang statusnya sendiri dan server
                        # akan mengirim state game baru jika ada slot yang tersedia atau game dimulai ulang.
                        # Tidak perlu reconnect jika masih terhubung.
                        if client.connected:
                            client.game_started = True
                            menu_state = "game"
                            client.latest_state = None # Reset state agar tidak render state lama
                            logging.info("Attempting to restart game with existing connection.")
                        else: # Jika terputus, coba connect lagi seperti Start Game
                             if client.connect():
                                client.start_listening_thread()
                                client.game_started = True
                                menu_state = "game"
                                client.latest_state = None
                             else:
                                renderer.draw_connection_status(client.get_connection_info())
                                pygame.display.flip()
                                pygame.time.wait(1000)
                    elif quit_button_rect and quit_button_rect.collidepoint(event.pos):
                        logging.info("Quit button clicked.")
                        client.running = False
        
        elif menu_state == "game":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    client.running = False
                if event.type == pygame.MOUSEMOTION:
                    client.send_paddle_update(pygame.mouse.get_pos())
                if event.type == pygame.MOUSEBUTTONDOWN: # Juga kirim update posisi saat klik
                    client.send_paddle_update(pygame.mouse.get_pos())

            # Render game state hanya jika terhubung dan game_started
            if client.connected and client.game_started and current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info)
            else:
                # Jika tidak terhubung atau game_started false, tampilkan info koneksi
                renderer.draw_connection_status(connection_info)
                pygame.display.flip()

        clock.tick(FPS)
    
    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()