# src/client/network.py
import socket
import json
import logging
import threading
import time

class LoadBalancerClient:
    def __init__(self, lb_ip, lb_port):
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
        if self.connected: return True
        try:
            self.connection_info = {'status': f'Connecting to {self.lb_address[0]}:{self.lb_address[1]}', 'detail': 'Via Load Balancer...'}
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect(self.lb_address)
            logging.info(f"Connected to load balancer at {self.lb_address}")
            
            init_data_str = self._receive_message()
            if init_data_str:
                data = json.loads(init_data_str)
                if data.get('type') == 'init':
                    self.player_id = data['player_id']
                    self.connected = True
                    self.connection_info = {'server_info': f'{self.lb_address[0]}:{self.lb_address[1]}'}
                    logging.info(f"Assigned Player ID: {self.player_id} via Load Balancer")
                    return True
                elif data.get('error'):
                    self.connection_info = {'status': 'Connection Failed', 'detail': data['error']}
                    logging.error(f"Load Balancer error: {data['error']}")
            else:
                self.connection_info = {'status': 'Connection Failed', 'detail': 'Invalid server response'}
            self.close_socket()
            return False
        except (socket.timeout, socket.error, Exception) as e:
            self.connection_info = {'status': 'Connection Failed', 'detail': str(e)}
            logging.error(f"Connection failed: {e}")
            self.close_socket()
            return False

    def _receive_message(self):
        try:
            while '\n' not in self.buffer:
                if not self.socket: return None
                data = self.socket.recv(4096).decode('utf-8')
                if not data: return None
                self.buffer += data
            message, self.buffer = self.buffer.split('\n', 1)
            return message
        except (socket.error, ConnectionResetError):
            return None

    def listen(self):
        while self.running:
            if not self.connected:
                time.sleep(0.5)
                continue
            message_str = self._receive_message()
            if message_str is None:
                self.handle_disconnection()
                continue
            try:
                state = json.loads(message_str)
                with self.lock:
                    self.latest_state = state
            except json.JSONDecodeError:
                logging.warning(f"Received invalid JSON: {message_str}")

    def handle_disconnection(self):
        if not self.connected: return
        self.connected = False
        self.close_socket()
        with self.lock: self.latest_state = None
        self.connection_info = {'status': 'Connection Lost!', 'detail': 'Please restart from main menu.'}
        logging.info("Disconnected from game server.")

    def send_command(self, command):
        if not self.connected or not self.socket: return
        try:
            self.socket.sendall((json.dumps(command) + '\n').encode('utf-8'))
        except (socket.error, BrokenPipeError):
            self.handle_disconnection()

    def send_paddle_update(self, pos):
        self.send_command({'type': 'update_paddle', 'pos': pos})

    def send_game_command(self, command_type):
        self.send_command({'type': command_type})
        logging.info(f"Sent command to server: {command_type}")

    # DIUBAH: Method untuk restart request-response system
    def send_request_restart(self):
        """Kirim request untuk restart game"""
        self.send_command({'type': 'request_restart'})
        logging.info("Sent restart request")

    def send_respond_restart(self, accept):
        """
        Respond to restart request
        accept: True untuk terima, False untuk tolak
        """
        self.send_command({'type': 'respond_restart', 'accept': accept})
        response_text = "ACCEPT" if accept else "REJECT"
        logging.info(f"Sent restart response: {response_text}")

    def send_cancel_restart_request(self):
        """Cancel restart request yang sedang berjalan"""
        self.send_command({'type': 'cancel_restart_request'})
        logging.info("Sent cancel restart request command")

    def get_state(self):
        with self.lock: return self.latest_state

    def get_connection_info(self):
        return self.connection_info

    def start_listening_thread(self):
        if any(t.name == "ClientListenThread" for t in threading.enumerate()): return
        thread = threading.Thread(target=self.listen, daemon=True, name="ClientListenThread")
        thread.start()

    def close_socket(self):
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None
            
    def close(self):
        self.running = False
        self.connected = False
        self.close_socket()
        logging.info("Client closed.")