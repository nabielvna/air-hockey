# src/server/network.py
import socket
import threading
import json
import time
import logging
from src.common.settings import FPS
from src.server.game import Game

class GameServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
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
                disconnected_clients = []
                for pid, conn in list(self.clients.items()):
                    try:
                        conn.sendall(message.encode('utf-8'))
                    except (socket.error, BrokenPipeError):
                        disconnected_clients.append(pid)
            for pid in disconnected_clients:
                self.handle_disconnection(pid)
            time.sleep(1 / FPS)

    def client_handler(self, conn, player_id):
        buffer = ""
        while True:
            try:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while '\n' in buffer:
                    command_str, buffer = buffer.split('\n', 1)
                    command = json.loads(command_str)
                    
                    if command['type'] == 'update_paddle':
                        with self.lock:
                            # Hanya blokir paddle saat pause atau countdown resume
                            is_blocked = (self.game.is_paused() or 
                                        (self.game.countdown_start_time > 0 and 
                                         self.game.countdown_type == 'resume'))
                            if not is_blocked:
                                self.game.paddles[player_id].update_pos(command['pos'][0], command['pos'][1])
                    
                    # Request restart (bukan langsung reset)
                    elif command['type'] == 'request_restart':
                        with self.lock:
                            success = self.game.request_restart(player_id)
                            if success:
                                logging.info(f"Player {player_id} initiated restart request")
                            else:
                                logging.info(f"Player {player_id} restart request failed - already active")
                    
                    # Respond to restart request
                    elif command['type'] == 'respond_restart':
                        with self.lock:
                            accept = command.get('accept', False)
                            result = self.game.respond_restart(player_id, accept)
                            
                            if result == 'accepted':
                                # Restart diterima, mulai game lagi jika ada 2 player
                                if len(self.clients) == 2:
                                    self.game.start_game()
                                    logging.info("Game restarted and starting with countdown")
                                else:
                                    self.game.status = 'waiting'
                            elif result == 'rejected':
                                # DIUBAH: Restart ditolak, auto resume sudah dipanggil di game.py
                                logging.info("Restart request rejected - auto resuming game")
                            # Jika invalid, tidak ada aksi khusus
                    
                    # Cancel restart request
                    elif command['type'] == 'cancel_restart_request':
                        with self.lock:
                            success = self.game.cancel_restart_request(player_id)
                            if success:
                                # DIUBAH: Auto resume setelah restart request dicancel
                                self.game.auto_resume_after_restart_action()
                                logging.info(f"Player {player_id} cancelled restart request - auto resuming game")
                    
                    elif command['type'] == 'pause_game':
                        with self.lock:
                            success = self.game.pause_game(player_id)
                            if success:
                                logging.info(f"Player {player_id} paused the game")
                            else:
                                logging.info(f"Player {player_id} cannot pause - restart request pending")
                    
                    elif command['type'] == 'resume_game':
                        with self.lock:
                            success = self.game.resume_game(player_id)
                            if success:
                                logging.info(f"Player {player_id} resumed the game")
                                
            except (socket.error, json.JSONDecodeError, ConnectionResetError):
                break
        self.handle_disconnection(player_id)

    def handle_disconnection(self, player_id):
        with self.lock:
            if player_id in self.clients:
                logging.info(f"Player {player_id} disconnected.")
                self.clients.pop(player_id, None)
                
                # Hapus player dari pause state
                self.game.remove_player_pause_state(player_id)
                
                # DIUBAH: Hapus restart request state jika player yang disconnect adalah requester
                # Auto resume sudah dipanggil di dalam remove_player_restart_state
                if self.game.restart_request_active:
                    self.game.remove_player_restart_state(player_id)
                
                if not self.clients:
                    self.game.reset()
                else:
                    self.game.status = 'waiting'
                    self.game.winner = 'opponent_disconnected'
                    # Reset countdown jika ada yang disconnect
                    self.game.countdown = 0
                    self.game.countdown_start_time = 0
                    self.game.countdown_type = None

    def run(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        logging.info(f"Server listening on {self.host}:{self.port}")

        threading.Thread(target=self.broadcast, daemon=True).start()
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
                init_msg = json.dumps({'type': 'init', 'player_id': player_id}) + '\n'
                conn.sendall(init_msg.encode('utf-8'))
                
                # Mulai game dengan countdown ketika 2 player terhubung
                if len(self.clients) == 2:
                    logging.info("Two players connected. Starting game with countdown.")
                    self.game.reset()
                    self.game.start_game()
                    
                threading.Thread(target=self.client_handler, args=(conn, player_id), daemon=True).start()

    def game_loop(self):
        while True:
            with self.lock:
                self.game.update()
            time.sleep(1/120)