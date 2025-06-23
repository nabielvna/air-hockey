# run_server.py
import socket
import logging
from src.server.network import GameServer
from src.common.settings import SERVER_HOST, AVAILABLE_SERVER_PORTS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_port_available(host, port):
    """Memeriksa apakah kombinasi host dan port tersedia."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def main():
    """
    Runner untuk Game Server dengan pemilihan port otomatis.
    Skrip akan mencoba menjalankan server pada port pertama yang tersedia
    dari daftar di settings.py.
    """
    print("=" * 60)
    print(" " * 20, "AIR HOCKEY - SERVER")
    print("=" * 60)
    print(f"Mencari port yang tersedia dari daftar: {AVAILABLE_SERVER_PORTS}")

    selected_port = None
    for port in AVAILABLE_SERVER_PORTS:
        if check_port_available(SERVER_HOST, port):
            selected_port = port
            break
    
    if selected_port is None:
        logging.error("Tidak ada port yang tersedia dari daftar yang dikonfigurasi.")
        print("\nSemua port yang dikonfigurasi sedang digunakan!")
        print("Silakan matikan salah satu instance server atau perbarui daftar port di settings.py.")
        return

    print(f"\nPort {selected_port} tersedia. Memulai server...")
    print("-" * 60)

    try:
        server = GameServer(SERVER_HOST, selected_port)
        server.run()
    except KeyboardInterrupt:
        print(f"\nServer di port {selected_port} dimatikan...")
    except Exception as e:
        print(f"Terjadi error pada server: {e}")

if __name__ == "__main__":
    main()