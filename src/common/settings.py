# src/common/settings.py

# Pengaturan Jaringan
SERVER_HOST = '0.0.0.0' # Gunakan 0.0.0.0 agar bisa diakses dari jaringan
LOAD_BALANCER_HOST = '0.0.0.0'
LOAD_BALANCER_PORT = 8888

# DAFTAR PORT UNTUK SERVER GAME
# Server akan mencoba berjalan di port ini secara berurutan.
# Load balancer juga akan memantau port-port ini.
AVAILABLE_SERVER_PORTS = [9999, 10000, 10001, 10002, 10003, 10004, 10005]
BACKEND_SERVER_TARGET_HOST = '127.0.0.1' 

# Pengaturan Pygame
WIDTH, HEIGHT = 1200, 800
FPS = 60

# Pengaturan Game
PADDLE_RADIUS = 35
PUCK_RADIUS = 20
WINNING_SCORE = 5

# Pengaturan Countdown
COUNTDOWN_DURATION = 3  # durasi countdown dalam detik (start, resume, goal)
COUNTDOWN_START_ENABLED = True  # enable countdown saat game start
COUNTDOWN_RESUME_ENABLED = True  # enable countdown saat resume

# BARU: Pengaturan Restart Voting
RESTART_VOTING_TIMEOUT = 30  # detik - waktu maksimal untuk voting (opsional untuk implementasi future)
RESTART_REQUIRE_ALL_PLAYERS = True  # apakah perlu semua player setuju untuk restart

# Pengaturan Gawang
GOAL_WIDTH = 20
GOAL_HEIGHT = 200
GOAL_Y_START = (HEIGHT - GOAL_HEIGHT) / 2

# Pengaturan Load Balancer
HEALTH_CHECK_INTERVAL = 10 # detik
MAX_CONNECTIONS_PER_SERVER = 2

# Warna - Dark Theme
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
LIGHT_RED = (255, 100, 100)
LIGHT_BLUE = (100, 100, 255)
GLOW_COLOR = (75, 0, 130)
SHADOW_COLOR = (50, 50, 50)

# Warna Countdown
COUNTDOWN_START_COLOR = (100, 100, 255)  # Biru untuk start
COUNTDOWN_RESUME_COLOR = (255, 255, 0)   # Kuning untuk resume
COUNTDOWN_GOAL_COLOR = (75, 0, 130)      # Ungu untuk goal

# Warna untuk Restart Request UI
VOTING_YES_COLOR = (0, 255, 0)          # Hijau untuk ACCEPT
VOTING_NO_COLOR = (255, 100, 100)       # Merah untuk REJECT
VOTING_PENDING_COLOR = (200, 200, 200)  # Abu-abu untuk pending
RESTART_REQUEST_BACKGROUND = (0, 0, 0)   # Background solid hitam untuk restart UI