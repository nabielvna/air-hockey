SERVER_HOST = '0.0.0.0' # Biarkan 0.0.0.0 agar bisa diakses dari jaringan lokal
SERVER_PORT = 9999
INPUT_SERVER_IP = '127.0.0.1' # IP default yang akan diminta ke klien

# Load Balancer Configuration
LOAD_BALANCER_HOST = '0.0.0.0'
LOAD_BALANCER_PORT = 8888

# Backend Server Ports (untuk multiple instances)
BACKEND_PORTS = [9999, 10000, 10001, 10002]

# Pengaturan Pygame
WIDTH, HEIGHT = 1200, 800
FPS = 60

# Pengaturan Game
PADDLE_RADIUS = 35
PUCK_RADIUS = 20
WINNING_SCORE = 10

# Pengaturan Gawang
GOAL_WIDTH = 20
GOAL_HEIGHT = 200 # Tinggi gawang
GOAL_Y_START = (HEIGHT - GOAL_HEIGHT) / 2 # Posisi Y awal gawang

# Load Balancer Settings
HEALTH_CHECK_INTERVAL = 5  # seconds
MAX_CONNECTIONS_PER_SERVER = 2  # Air hockey support 2 players per game

# Warna - Dark Theme
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
LIGHT_RED = (255, 100, 100)
LIGHT_BLUE = (100, 100, 255)
GLOW_COLOR = (75, 0, 130) # Deep Purple Glow
SHADOW_COLOR = (50, 50, 50)

GRAY = (200, 200, 200) # Digunakan untuk beberapa elemen UI/papan
GREEN = (0, 255, 0) # Already in your settings.py