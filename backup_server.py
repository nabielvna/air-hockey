# quick_backup_server.py
# Script cepat untuk setup backup server

import sys
import socket
import subprocess
from air_hockey_server import GameServer

def get_local_ip():
    """Get local IP address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def check_port_available(port):
    """Check if port is available"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', port))
        s.close()
        return True
    except:
        return False

def main():
    print("=" * 60)
    print("    QUICK BACKUP SERVER SETUP")
    print("=" * 60)
    print()
    
    # Get port input
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Error: Port must be a number")
            return
    else:
        try:
            port_input = input("Enter backup server port (default: 10000): ").strip()
            port = int(port_input) if port_input else 10000
        except ValueError:
            print("Error: Invalid port number")
            return
    
    # Check if port is available
    if not check_port_available(port):
        print(f"Error: Port {port} is already in use!")
        print("Try a different port or stop the service using that port.")
        return
    
    local_ip = get_local_ip()
    
    print(f"Starting Backup Server...")
    print(f"Port: {port}")
    print(f"Local IP: {local_ip}")
    print()
    print("CONFIGURATION FOR FAILOVER CLIENT:")
    print("Add this line to SERVER_LIST in air_hockey_client_failover.py:")
    print(f"    ('{local_ip}', {port}, 'Backup Server'),")
    print()
    print("CONFIGURATION FOR LOAD BALANCER:")
    print("Add this line to BACKEND_SERVERS in simple_load_balancer.py:")
    print(f"    ('{local_ip}', {port}),")
    print()
    print("-" * 60)
    print("Server is starting... Press Ctrl+C to stop")
    print()
    
    try:
        # Start the server with custom host and port
        server = GameServer('0.0.0.0', port)
        server.run()
        
    except KeyboardInterrupt:
        print(f"\nBackup server on port {port} shutting down...")
    except Exception as e:
        print(f"Server error: {e}")

if __name__ == "__main__":
    main()