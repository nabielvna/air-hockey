# load_balancer.py
# Enhanced load balancer dengan logging yang lebih baik

import socket
import threading
import time
import logging

# Konfigurasi Load Balancer
LOAD_BALANCER_PORT = 8888
HEALTH_CHECK_INTERVAL = 5

# Daftar Backend Servers (EDIT SESUAI SETUP ANDA)
BACKEND_SERVERS = [
    # Format: (IP_ADDRESS, PORT)
    
    # Local servers (untuk testing lokal)
    ('127.0.0.1', 9999),    # Server utama lokal
    ('127.0.0.1', 10000),   # Backup server lokal  
    
    # Remote servers (untuk setup terdistribusi)
    # Uncomment dan sesuaikan IP dengan komputer Anda:
    # ('192.168.1.100', 9999),  # Server di komputer lain
    # ('192.168.1.101', 10000), # Backup server di komputer lain
    # ('10.0.0.50', 9999),      # Server di network lain
    
    # Tambahkan server lain sesuai kebutuhan
]

# CARA SETUP UNTUK BACKUP SERVER DI KOMPUTER LAIN:
# 1. Jalankan backup_server.py di komputer target
# 2. Catat IP komputer tersebut (gunakan ipconfig/ifconfig)  
# 3. Tambahkan ke BACKEND_SERVERS di atas
# 4. Restart load balancer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LoadBalancer:
    def __init__(self, port):
        self.port = port
        self.servers = []
        self.current_server = 0
        self.running = True
        
        # Initialize server list
        for host, port in BACKEND_SERVERS:
            self.servers.append({
                'host': host,
                'port': port,
                'healthy': True,
                'connections': 0,
                'max_connections': 2  # Air hockey max 2 players per game
            })
        
        logging.info(f"Initialized {len(self.servers)} backend servers")
        for server in self.servers:
            logging.info(f"  - {server['host']}:{server['port']}")
    
    def health_check(self):
        """Check health of all backend servers"""
        while self.running:
            for server in self.servers:
                try:
                    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_socket.settimeout(2)
                    result = test_socket.connect_ex((server['host'], server['port']))
                    test_socket.close()
                    
                    was_healthy = server['healthy']
                    server['healthy'] = (result == 0)
                    
                    if was_healthy != server['healthy']:
                        status = "UP" if server['healthy'] else "DOWN"
                        logging.info(f"Server {server['host']}:{server['port']} is {status}")
                        
                except Exception as e:
                    server['healthy'] = False
                    logging.error(f"Health check failed for {server['host']}:{server['port']}: {e}")
            
            # Log server status summary
            healthy_count = sum(1 for s in self.servers if s['healthy'])
            total_connections = sum(s['connections'] for s in self.servers)
            logging.debug(f"Servers: {healthy_count}/{len(self.servers)} healthy, {total_connections} active connections")
            
            time.sleep(HEALTH_CHECK_INTERVAL)
    
    def get_available_server(self):
        """Get next available server using round-robin with health check"""
        healthy_servers = [s for s in self.servers if s['healthy'] and s['connections'] < s['max_connections']]
        
        if not healthy_servers:
            logging.warning("No available servers!")
            logging.warning("Current server status:")
            for server in self.servers:
                status = "HEALTHY" if server['healthy'] else "DOWN"
                logging.warning(f"  {server['host']}:{server['port']} - {status} ({server['connections']}/{server['max_connections']})")
            return None
        
        # Simple round-robin among healthy servers
        server = healthy_servers[self.current_server % len(healthy_servers)]
        self.current_server += 1
        server['connections'] += 1
        
        logging.info(f"Assigned client to server {server['host']}:{server['port']} ({server['connections']}/{server['max_connections']})")
        return server
    
    def release_server(self, server):
        """Release server connection"""
        if server['connections'] > 0:
            server['connections'] -= 1
            logging.info(f"Released connection from {server['host']}:{server['port']} ({server['connections']}/{server['max_connections']})")
    
    def proxy_connection(self, client_socket, client_addr):
        """Proxy connection between client and backend server"""
        server = self.get_available_server()
        if not server:
            error_msg = '{"error": "No available servers. All servers are down or full."}\n'
            try:
                client_socket.sendall(error_msg.encode('utf-8'))
            except:
                pass
            client_socket.close()
            logging.warning(f"Rejected client {client_addr} - no available servers")
            return
        
        backend_socket = None
        try:
            # Connect to backend server
            backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            backend_socket.settimeout(10)
            backend_socket.connect((server['host'], server['port']))
            
            logging.info(f"Proxying client {client_addr} to server {server['host']}:{server['port']}")
            
            # Create bidirectional proxy threads
            def forward(source, destination, direction):
                try:
                    while True:
                        data = source.recv(4096)
                        if not data:
                            break
                        destination.sendall(data)
                except Exception as e:
                    logging.debug(f"Proxy {direction} ended: {e}")
                finally:
                    try:
                        source.close()
                    except:
                        pass
                    try:
                        destination.close()
                    except:
                        pass
            
            client_to_server = threading.Thread(
                target=forward, 
                args=(client_socket, backend_socket, f"{client_addr}->server"),
                daemon=True
            )
            server_to_client = threading.Thread(
                target=forward,
                args=(backend_socket, client_socket, f"server->{client_addr}"),
                daemon=True
            )
            
            client_to_server.start()
            server_to_client.start()
            
            # Wait for connection to end
            client_to_server.join()
            server_to_client.join()
            
            logging.info(f"Proxy session ended for client {client_addr}")
            
        except Exception as e:
            logging.error(f"Proxy error for client {client_addr}: {e}")
        finally:
            if backend_socket:
                try:
                    backend_socket.close()
                except:
                    pass
            try:
                client_socket.close()
            except:
                pass
            self.release_server(server)
    
    def start(self):
        """Start the load balancer"""
        # Start health check thread
        health_thread = threading.Thread(target=self.health_check, daemon=True)
        health_thread.start()
        
        # Start main server
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.port))
        server_socket.listen(10)
        
        logging.info(f"Load Balancer started on port {self.port}")
        logging.info(f"Backend servers:")
        for server in self.servers:
            logging.info(f"  - {server['host']}:{server['port']}")
        logging.info("Clients can connect to this load balancer and will be automatically routed to available servers.")
        print()
        print("=" * 60)
        print("LOAD BALANCER READY")
        print("=" * 60)
        print(f"Listening on: 0.0.0.0:{self.port}")
        print("Backend servers:")
        for server in self.servers:
            print(f"  - {server['host']}:{server['port']}")
        print()
        print("Clients should connect to this load balancer IP:Port")
        print("Load balancer will automatically route them to available game servers.")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            while self.running:
                client_socket, client_addr = server_socket.accept()
                logging.info(f"New client connection from {client_addr}")
                
                # Handle each client in separate thread
                proxy_thread = threading.Thread(
                    target=self.proxy_connection,
                    args=(client_socket, client_addr),
                    daemon=True
                )
                proxy_thread.start()
                
        except KeyboardInterrupt:
            logging.info("Shutting down load balancer...")
            print("\nLoad Balancer shutting down...")
        finally:
            self.running = False
            server_socket.close()

def get_local_ip():
    """Get local IP address for display"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    print("Starting Load Balancer...")
    print(f"Local IP: {get_local_ip()}")
    print()
    
    lb = LoadBalancer(LOAD_BALANCER_PORT)
    lb.start()