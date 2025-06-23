# src/load_balancer/balancer.py
import socket
import threading
import time
import logging
from src.common.settings import HEALTH_CHECK_INTERVAL, MAX_CONNECTIONS_PER_SERVER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LoadBalancer:
    def __init__(self, host, port, target_host, potential_ports):
        self.host = host
        self.port = port
        self.servers = []
        self.current_server_index = 0
        self.running = True

        # Inisialisasi daftar server dari port potensial
        for p_port in potential_ports:
            self.servers.append({
                'host': target_host,
                'port': p_port,
                'healthy': False,  # Awalnya semua dianggap tidak sehat
                'connections': 0,
                'max_connections': MAX_CONNECTIONS_PER_SERVER
            })
        
        logging.info(f"Load Balancer dikonfigurasi untuk memantau {len(self.servers)} port potensial.")

    def health_check(self):
        while self.running:
            for server in self.servers:
                was_healthy = server['healthy']
                try:
                    with socket.create_connection((server['host'], server['port']), timeout=2):
                        server['healthy'] = True
                except (socket.error, socket.timeout):
                    server['healthy'] = False
                
                if was_healthy != server['healthy']:
                    status = "UP" if server['healthy'] else "DOWN"
                    logging.info(f"Server di {server['host']}:{server['port']} sekarang {status}")
            
            time.sleep(HEALTH_CHECK_INTERVAL)

    def get_available_server(self):
        # Filter hanya server yang sehat
        healthy_servers = [s for s in self.servers if s['healthy']]
        if not healthy_servers:
            return None

        # Coba beberapa kali untuk menemukan server dengan slot kosong (round-robin)
        for _ in range(len(healthy_servers)):
            server = healthy_servers[self.current_server_index % len(healthy_servers)]
            self.current_server_index += 1
            if server['connections'] < server['max_connections']:
                server['connections'] += 1
                logging.info(f"Mengarahkan klien ke server {server['host']}:{server['port']} ({server['connections']}/{server['max_connections']})")
                return server
        
        logging.warning("Semua server yang sehat sedang penuh.")
        return None

    def release_server(self, server):
        if server and server['connections'] > 0:
            server['connections'] -= 1
            logging.info(f"Koneksi dilepaskan dari {server['host']}:{server['port']} ({server['connections']}/{server['max_connections']})")

    def proxy_connection(self, client_socket, client_addr):
        selected_server = self.get_available_server()
        if not selected_server:
            error_msg = '{"error": "Tidak ada server yang tersedia atau semua penuh."}\n'
            try:
                client_socket.sendall(error_msg.encode('utf-8'))
            finally:
                client_socket.close()
                logging.warning(f"Menolak klien {client_addr} - tidak ada server tersedia.")
            return

        backend_socket = None
        try:
            backend_socket = socket.create_connection((selected_server['host'], selected_server['port']))
            logging.info(f"Proxying {client_addr} <-> {selected_server['host']}:{selected_server['port']}")

            def forward(source, destination, server_to_release_on_close):
                try:
                    while True:
                        data = source.recv(4096)
                        if not data:
                            break
                        destination.sendall(data)
                except (socket.error, ConnectionResetError):
                    logging.debug(f"Koneksi proxy ditutup.")
                finally:
                    source.close()
                    destination.close()
                    # Hanya thread yang membaca dari klien yang akan merilis server
                    if server_to_release_on_close:
                        self.release_server(server_to_release_on_close)

            # Thread dari klien ke server. Jika ini berakhir, koneksi dilepaskan.
            threading.Thread(target=forward, args=(client_socket, backend_socket, selected_server), daemon=True).start()
            # Thread dari server ke klien.
            threading.Thread(target=forward, args=(backend_socket, client_socket, None), daemon=True).start()

        except Exception as e:
            logging.error(f"Error proxy untuk {client_addr}: {e}")
            if client_socket:
                client_socket.close()
            if backend_socket:
                backend_socket.close()
            self.release_server(selected_server)

    def start(self):
        health_thread = threading.Thread(target=self.health_check, daemon=True)
        health_thread.start()
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(10)
        logging.info(f"Load Balancer berjalan di {self.host}:{self.port}")
        
        try:
            while self.running:
                client_socket, client_addr = server_socket.accept()
                logging.info(f"Koneksi klien baru dari {client_addr}")
                proxy_thread = threading.Thread(target=self.proxy_connection, args=(client_socket, client_addr), daemon=True)
                proxy_thread.start()
        except KeyboardInterrupt:
            print("\nMematikan load balancer...")
        finally:
            self.running = False
            server_socket.close()