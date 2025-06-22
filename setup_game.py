# setup_game.py
# Script sederhana untuk setup Air Hockey dengan Load Balancer

import subprocess
import sys
import socket
import time
import os

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
        s.bind(('127.0.0.1', port))
        s.close()
        return True
    except:
        return False

def main():
    print("=" * 70)
    print("            AIR HOCKEY SETUP - LOAD BALANCER MODE")
    print("=" * 70)
    print()
    
    local_ip = get_local_ip()
    print(f"Your Local IP: {local_ip}")
    print()
    
    print("Setup Options:")
    print("1. Start Game Server (Main Server - port 9999)")
    print("2. Start Backup Server (Backup Server - port 10000)")
    print("3. Start Load Balancer (port 8888)")
    print("4. Start Client (connects via Load Balancer)")
    print("5. Quick Setup (Start everything locally)")
    print("6. Show Connection Guide")
    print()
    
    choice = input("Choose option (1-6): ").strip()
    
    if choice == "1":
        print("Starting Main Game Server on port 9999...")
        if not check_port_available(9999):
            print("ERROR: Port 9999 is already in use!")
            print("Stop the service using port 9999 first.")
            return
        
        print("Starting server...")
        print("Keep this terminal open. Server will run until you press Ctrl+C")
        subprocess.run([sys.executable, "air_hockey_server.py"])
    
    elif choice == "2":
        print("Starting Backup Server on port 10000...")
        if not check_port_available(10000):
            print("ERROR: Port 10000 is already in use!")
            print("Stop the service using port 10000 first.")
            return
        
        print("Starting backup server...")
        print("Keep this terminal open. Server will run until you press Ctrl+C")
        subprocess.run([sys.executable, "backup_server.py", "10000"])
    
    elif choice == "3":
        print("Starting Load Balancer on port 8888...")
        if not check_port_available(8888):
            print("ERROR: Port 8888 is already in use!")
            print("Stop the service using port 8888 first.")
            return
        
        print("Starting load balancer...")
        print("Keep this terminal open. Load Balancer will run until you press Ctrl+C")
        subprocess.run([sys.executable, "load_balancer.py"])
    
    elif choice == "4":
        print("Starting Client...")
        print("Client will connect via Load Balancer")
        subprocess.run([sys.executable, "air_hockey_client.py"])
    
    elif choice == "5":
        print("Quick Setup - Starting everything locally")
        print()
        
        # Check all required ports
        required_ports = [8888, 9999, 10000]
        for port in required_ports:
            if not check_port_available(port):
                print(f"ERROR: Port {port} is already in use!")
                print("Please stop services on required ports first:")
                print("- Port 8888 (Load Balancer)")
                print("- Port 9999 (Main Server)")
                print("- Port 10000 (Backup Server)")
                return
        
        print("All ports available. Starting components...")
        print()
        print("This will start:")
        print("1. Main Server (port 9999)")
        print("2. Backup Server (port 10000)")  
        print("3. Load Balancer (port 8888)")
        print("4. Client")
        print()
        
        input("Press Enter to continue...")
        
        try:
            # Start servers in background
            print("Starting Main Server...")
            server1 = subprocess.Popen([sys.executable, "air_hockey_server.py"])
            time.sleep(1)
            
            print("Starting Backup Server...")
            server2 = subprocess.Popen([sys.executable, "backup_server.py", "10000"])
            time.sleep(1)
            
            print("Starting Load Balancer...")
            lb = subprocess.Popen([sys.executable, "load_balancer.py"])
            time.sleep(2)
            
            print()
            print("=" * 50)
            print("ALL SERVERS STARTED SUCCESSFULLY!")
            print("=" * 50)
            print(f"Main Server:     127.0.0.1:9999")
            print(f"Backup Server:   127.0.0.1:10000")
            print(f"Load Balancer:   127.0.0.1:8888")
            print(f"Your Local IP:   {local_ip}")
            print()
            print("Starting client...")
            print("The client will connect via Load Balancer automatically.")
            print()
            
            # Start client
            subprocess.run([sys.executable, "air_hockey_client.py"])
            
        except KeyboardInterrupt:
            print("\nShutting down all servers...")
        finally:
            # Cleanup
            for process in [server1, server2, lb]:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    try:
                        process.kill()
                    except:
                        pass
            print("All servers stopped.")
    
    elif choice == "6":
        print()
        print("=" * 70)
        print("                    CONNECTION GUIDE")
        print("=" * 70)
        print()
        print("UNTUK BERMAIN DENGAN TEMAN DI KOMPUTER YANG SAMA:")
        print("1. Jalankan: python setup_game.py")
        print("2. Pilih opsi 5 (Quick Setup)")
        print("3. Buka terminal baru, jalankan: python air_hockey_client.py")
        print("4. Kedua client connect ke: 127.0.0.1 (port 8888)")
        print()
        print("UNTUK BERMAIN DENGAN TEMAN DI KOMPUTER BERBEDA:")
        print()
        print("HOST (yang jadi server):")
        print("1. Jalankan server: python setup_game.py -> pilih 1")
        print("2. Jalankan load balancer: python setup_game.py -> pilih 3")
        print(f"3. Beritahu teman IP Anda: {local_ip}")
        print()
        print("GUEST (yang join):")
        print("1. Jalankan: python air_hockey_client.py")
        print(f"2. Masukkan IP host: {local_ip}")
        print("3. Port: 8888 (default)")
        print()
        print("UNTUK MULTIPLE SERVERS (HIGH AVAILABILITY):")
        print("- Komputer 1: Jalankan main server (port 9999)")
        print("- Komputer 2: Jalankan backup server (port 10000)")
        print("- Komputer 3: Jalankan load balancer (port 8888)")
        print("- Edit BACKEND_SERVERS di load_balancer.py dengan IP masing-masing")
        print("- Client connect ke IP load balancer")
        print()
        print("FIREWALL SETTINGS:")
        print("- Windows: Allow Python through Windows Defender Firewall")
        print("- Linux: sudo ufw allow 8888 && sudo ufw allow 9999")
        print("- Router: Forward ports jika perlu akses dari internet")
        print("=" * 70)
    
    else:
        print("Invalid option. Please run again and choose 1-6.")

if __name__ == "__main__":
    main()