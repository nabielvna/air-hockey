# air_hockey_client.py
import pygame
import socket
import json
import sys
import logging
import threading
import time
from collections import deque
from settings import * # Pastikan settings.py sudah diupdate dengan GLOW_COLOR, SHADOW_COLOR, dll.

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.score_font = pygame.font.Font(None, 74)
        self.info_font = pygame.font.Font(None, 50)
        self.menu_font = pygame.font.Font(None, 60)
        self.small_font = pygame.font.Font(None, 36)
        self.countdown_font = pygame.font.Font(None, 150)
        self.puck_trail = deque(maxlen=10)

    def draw_main_menu(self, message):
        # Ini adalah menu utama sebelum atau sesudah game
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
        if message == "game_over":
            self.screen.blit(restart_text, restart_rect)
        self.screen.blit(quit_text, quit_rect)

        pygame.display.flip()

        return start_rect, restart_rect, quit_rect

    def draw_ingame_menu(self):
        # Ini adalah menu saat game sedang berjalan (misal: setelah tombol Esc ditekan)
        # Tambahkan overlay semi-transparan
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) # Hitam dengan alpha 180 (semi-transparan)
        self.screen.blit(overlay, (0, 0))

        menu_title = self.menu_font.render("PAUSED", True, WHITE)
        restart_game_text = self.info_font.render("Restart Game", True, WHITE)
        quit_game_text = self.info_font.render("Quit Game", True, WHITE)
        resume_game_text = self.info_font.render("Resume (Esc)", True, WHITE)

        menu_title_rect = menu_title.get_rect(center=(WIDTH / 2, HEIGHT / 4))
        restart_game_rect = restart_game_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 60))
        quit_game_rect = quit_game_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30))
        resume_game_rect = resume_game_text.get_rect(center=(WIDTH / 2, HEIGHT * 3 / 4))

        self.screen.blit(menu_title, menu_title_rect)
        self.screen.blit(restart_game_text, restart_game_rect)
        self.screen.blit(quit_game_text, quit_game_rect)
        self.screen.blit(resume_game_text, resume_game_rect)

        pygame.display.flip()

        return restart_game_rect, quit_game_rect # Mengembalikan rects untuk deteksi klik

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
                self.draw_message("YOU WIN!", f"Final Score: {state['scores'].get('1', 0)} - {state['scores'].get('2', 0)}")
            else:
                self.draw_message("YOU LOSE", f"Final Score: {state['scores'].get('1', 0)} - {state['scores'].get('2', 0)}")
        
        if state['status'] == 'active':
            self.draw_game_elements(state, player_id)
        
        if state.get('countdown', 0) > 0:
            self.draw_countdown(state['countdown'])

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
        for pid_str, p_data in state['paddles'].items():
            pid = int(pid_str)
            color = LIGHT_BLUE if pid == 1 else LIGHT_RED
            pos = (int(p_data['x']), int(p_data['y']))
            pygame.draw.circle(self.screen, color, pos, PADDLE_RADIUS)
            if pid == player_id:
                pygame.draw.circle(self.screen, WHITE, pos, PADDLE_RADIUS, 3)

        puck_data = state['puck']
        current_puck_pos = (int(puck_data['x']), int(puck_data['y']))
        self.puck_trail.appendleft(current_puck_pos)

        for i, pos_tuple in enumerate(self.puck_trail):
            alpha = max(0, 255 - i * (255 // len(self.puck_trail)))
            radius = max(1, PUCK_RADIUS - i * (PUCK_RADIUS // len(self.puck_trail)))
            
            s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (SHADOW_COLOR[0], SHADOW_COLOR[1], SHADOW_COLOR[2], alpha), (radius, radius), radius)
            self.screen.blit(s, (pos_tuple[0] - radius, pos_tuple[1] - radius))

        pygame.draw.circle(self.screen, WHITE, current_puck_pos, PUCK_RADIUS)
        pygame.draw.circle(self.screen, BLACK, current_puck_pos, PUCK_RADIUS, 2)

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
        self.connected = False
        self.lock = threading.Lock()
        self.buffer = ""
        self.connection_info = {}

    def connect(self):
        if self.connected and self.socket:
            logging.info("Already connected. Skipping new connection.")
            return True
        
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
            self.socket.settimeout(10)
            self.socket.connect(self.lb_address)
            
            logging.info(f"Connected to load balancer at {self.lb_address}")
            
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
        while self.running:
            if not self.connected:
                time.sleep(0.5)
                continue

            message_str = self._receive_message()
            if message_str is None:
                logging.warning("Lost connection to server via load balancer")
                self.handle_disconnection()
                continue

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
        if not self.connected:
            return
        
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        with self.lock:
            self.latest_state = None
        
        self.connection_info = {
            'status': 'Connection Lost!',
            'detail': 'Please go to main menu and try again.'
        }
        logging.info("Disconnected from game server.")

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
    
    # State untuk mengelola tampilan: "main_menu", "game_active", "ingame_menu", "game_over_screen"
    game_display_state = "main_menu" 
    
    # Rects untuk tombol menu utama
    main_menu_start_rect = None
    main_menu_restart_rect = None
    main_menu_quit_rect = None

    # Rects untuk tombol menu in-game
    ingame_menu_restart_rect = None
    ingame_menu_quit_rect = None

    client.running = True
    while client.running:
        current_game_state = client.get_state()
        connection_info = client.get_connection_info()

        # Logika transisi state game_display_state
        if game_display_state == "game_active":
            if not client.connected: # Jika koneksi putus saat game aktif
                logging.warning("Connection lost during game_active state. Returning to main menu.")
                game_display_state = "main_menu"
                client.latest_state = None # Clear state for menu display
            elif current_game_state and current_game_state['status'] == 'game_over':
                logging.info("Game Over detected from server. Transitioning to game_over_screen.")
                game_display_state = "game_over_screen"
        
        # Penanganan Event Pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.running = False
            
            # Deteksi tombol ESC untuk membuka/menutup menu in-game
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_display_state == "game_active":
                    game_display_state = "ingame_menu"
                    logging.info("In-game menu opened.")
                elif game_display_state == "ingame_menu":
                    game_display_state = "game_active"
                    logging.info("In-game menu closed. Resuming game.")
            
            # Penanganan klik mouse berdasarkan state
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos

                if game_display_state == "main_menu" or game_display_state == "game_over_screen":
                    # Klik di menu utama (atau setelah game over)
                    if main_menu_start_rect and main_menu_start_rect.collidepoint(mouse_pos):
                        logging.info("Main menu: Start Game clicked.")
                        if not client.connected:
                            if client.connect():
                                client.start_listening_thread()
                                game_display_state = "game_active"
                                client.latest_state = None # Reset state
                            else:
                                renderer.draw_connection_status(connection_info)
                                pygame.display.flip()
                                pygame.time.wait(1000)
                        else: # Sudah terhubung, langsung masuk game
                            game_display_state = "game_active"
                            client.latest_state = None
                            logging.info("Already connected, starting new game session.")
                    elif main_menu_restart_rect and main_menu_restart_rect.collidepoint(mouse_pos) and game_display_state == "game_over_screen":
                        logging.info("Main menu: Restart Game clicked.")
                        # Jika terhubung, cukup ubah state. Server akan mereset game secara otomatis
                        # saat kedua pemain aktif kembali (jika itu logikanya).
                        # Jika tidak terhubung, coba koneksi ulang.
                        if client.connected:
                            game_display_state = "game_active"
                            client.latest_state = None
                        else:
                            if client.connect():
                                client.start_listening_thread()
                                game_display_state = "game_active"
                                client.latest_state = None
                            else:
                                renderer.draw_connection_status(connection_info)
                                pygame.display.flip()
                                pygame.time.wait(1000)
                    elif main_menu_quit_rect and main_menu_quit_rect.collidepoint(mouse_pos):
                        logging.info("Main menu: Quit clicked.")
                        client.running = False

                elif game_display_state == "ingame_menu":
                    # Klik di menu in-game
                    if ingame_menu_restart_rect and ingame_menu_restart_rect.collidepoint(mouse_pos):
                        logging.info("In-game menu: Restart Game clicked.")
                        # Logika restart di sini. Kita akan kembali ke menu utama untuk memicu restart dari sana.
                        game_display_state = "main_menu"
                        client.latest_state = None # Clear state
                    elif ingame_menu_quit_rect and ingame_menu_quit_rect.collidepoint(mouse_pos):
                        logging.info("In-game menu: Quit Game clicked.")
                        client.running = False
            
            # Update posisi paddle hanya saat game aktif dan bukan di menu in-game
            if game_display_state == "game_active" and event.type == pygame.MOUSEMOTION:
                client.send_paddle_update(pygame.mouse.get_pos())
            # Juga kirim update posisi saat klik (jika ingin paddle bergerak saat mouse diklik)
            if game_display_state == "game_active" and event.type == pygame.MOUSEBUTTONDOWN:
                client.send_paddle_update(pygame.mouse.get_pos())


        # Proses Rendering berdasarkan game_display_state
        if game_display_state == "main_menu":
            # Tampilkan menu utama (sebelum game dimulai atau setelah game over)
            main_menu_start_rect, main_menu_restart_rect, main_menu_quit_rect = renderer.draw_main_menu(
                "game_over" if current_game_state and current_game_state['status'] == 'game_over' else "main"
            )
        elif game_display_state == "game_active":
            # Tampilkan game jika terhubung, game aktif, dan ada state
            if client.connected and current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info)
            else: # Jika tidak terhubung/ada masalah, tampilkan status koneksi
                renderer.draw_connection_status(connection_info)
                pygame.display.flip() # Pastikan ini di-flip
        elif game_display_state == "ingame_menu":
            # Pertama gambar game di belakang, lalu overlay menu
            if client.connected and current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info) # Gambar game sebagai background
            else: # Jika koneksi putus saat di in-game menu
                renderer.draw_connection_status(connection_info)
                pygame.display.flip()

            ingame_menu_restart_rect, ingame_menu_quit_rect = renderer.draw_ingame_menu()
        elif game_display_state == "game_over_screen":
            # Tampilkan layar game over, lalu transisi kembali ke main_menu
            if client.connected and current_game_state:
                renderer.draw(current_game_state, client.player_id, connection_info)
            else: # Jika koneksi putus saat di layar game over
                renderer.draw_connection_status(connection_info)
                pygame.display.flip()
            # Tidak perlu memanggil draw_main_menu lagi di sini,
            # karena transisinya sudah diatur di loop event.
            # Ini akan menyebabkan tampilan main_menu dipanggil di iterasi berikutnya.

        clock.tick(FPS)
    
    client.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()