SERVER_HOST = '0.0.0.0' # Biarkan 0.0.0.0 agar bisa diakses dari jaringan lokal
SERVER_PORT = 9999
INPUT_SERVER_IP = '127.0.0.1' # IP default yang akan diminta ke klien

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

# Warna
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)