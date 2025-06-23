# run_load_balancer.py
import logging
from src.load_balancer.balancer import LoadBalancer
from src.common.settings import (
    LOAD_BALANCER_HOST,
    LOAD_BALANCER_PORT,
    AVAILABLE_SERVER_PORTS,
    BACKEND_SERVER_TARGET_HOST
)

def main():
    """Runner untuk Load Balancer dengan konfigurasi dinamis."""
    print("=" * 60)
    print(" " * 20, "LOAD BALANCER RUNNER")
    print("=" * 60)
    print(f"Load Balancer akan memantau server di host '{BACKEND_SERVER_TARGET_HOST}'")
    print(f"pada port berikut: {AVAILABLE_SERVER_PORTS}")
    print("-" * 60)

    try:
        # Load balancer sekarang diinisialisasi dengan daftar port potensial
        lb = LoadBalancer(
            host=LOAD_BALANCER_HOST,
            port=LOAD_BALANCER_PORT,
            target_host=BACKEND_SERVER_TARGET_HOST,
            potential_ports=AVAILABLE_SERVER_PORTS
        )
        lb.start()
    except Exception as e:
        logging.critical(f"Gagal memulai Load Balancer: {e}")

if __name__ == "__main__":
    main()