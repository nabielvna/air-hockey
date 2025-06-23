# src/server/game.py
import time
import random
import logging
from src.common.settings import *

class Puck:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT / 2
        self.vx = 0
        self.vy = 0

    def reset(self, direction):
        self.x = WIDTH / 2
        self.y = HEIGHT / 2
        self.vx = 5 * direction
        self.vy = random.uniform(-5, 5)

    def move(self):
        self.x += self.vx
        self.y += self.vy

class Paddle:
    def __init__(self, player_id):
        self.id = player_id
        self.x = 100 if player_id == 1 else WIDTH - 100
        self.y = HEIGHT / 2
        
    def update_pos(self, x, y):
        self.y = max(PADDLE_RADIUS, min(y, HEIGHT - PADDLE_RADIUS))
        if self.id == 1:
            self.x = max(PADDLE_RADIUS, min(x, WIDTH / 2 - PADDLE_RADIUS))
        else:
            self.x = max(WIDTH / 2 + PADDLE_RADIUS, min(x, WIDTH - PADDLE_RADIUS))

class Game:
    def __init__(self):
        self.puck = Puck()
        self.paddles = {1: Paddle(1), 2: Paddle(2)}
        self.scores = {1: 0, 2: 0}
        self.status = 'waiting'
        self.winner = None
        
        # Sistem countdown yang lebih komprehensif
        self.countdown = 0
        self.countdown_start_time = 0
        self.countdown_type = None  # 'start', 'resume', 'goal'
        self.countdown_duration = COUNTDOWN_DURATION
        
        # Pause state per player
        self.paused_players = set()
        
        # Sistem restart request-response
        self.restart_requester = None  # ID player yang request restart
        self.restart_request_active = False

    def update(self):
        # Handle countdown states
        if self.countdown_start_time > 0:
            elapsed_time = time.time() - self.countdown_start_time
            remaining_time = self.countdown_duration - elapsed_time
            
            if remaining_time > 0:
                self.countdown = int(remaining_time) + 1
                return  # Jangan update game physics selama countdown
            else:
                # Countdown selesai
                self.countdown = 0
                self.countdown_start_time = 0
                
                if self.countdown_type == 'start':
                    logging.info("Game start countdown finished - game is now active")
                    self.status = 'active'
                elif self.countdown_type == 'resume':
                    logging.info("Resume countdown finished - game resumed")
                elif self.countdown_type == 'goal':
                    logging.info("Goal countdown finished - continuing game")
                
                self.countdown_type = None
        
        # Game hanya berjalan jika tidak ada countdown dan tidak ada player yang pause
        if self.countdown_start_time > 0 or self.paused_players:
            return
            
        if self.status != 'active':
            return
            
        self.puck.move()
        self.check_collisions()

    def check_collisions(self):
        if self.puck.y - PUCK_RADIUS <= 0 or self.puck.y + PUCK_RADIUS >= HEIGHT:
            self.puck.vy *= -1
        for paddle in self.paddles.values():
            dist_x = self.puck.x - paddle.x
            dist_y = self.puck.y - paddle.y
            distance = (dist_x**2 + dist_y**2)**0.5
            if distance < PADDLE_RADIUS + PUCK_RADIUS:
                norm_x, norm_y = dist_x / distance, dist_y / distance
                self.puck.vx = norm_x * 9
                self.puck.vy = norm_y * 9
                self.puck.vy += random.uniform(-0.5, 0.5)
        if self.puck.x - PUCK_RADIUS <= GOAL_WIDTH and self.puck.y > GOAL_Y_START and self.puck.y < GOAL_Y_START + GOAL_HEIGHT:
            self.score_goal(2)
        elif self.puck.x + PUCK_RADIUS >= WIDTH - GOAL_WIDTH and self.puck.y > GOAL_Y_START and self.puck.y < GOAL_Y_START + GOAL_HEIGHT:
            self.score_goal(1)
        elif self.puck.x - PUCK_RADIUS <= 0 or self.puck.x + PUCK_RADIUS >= WIDTH:
            self.puck.vx *= -1

    def score_goal(self, player_id):
        self.scores[player_id] += 1
        logging.info(f"Goal for Player {player_id}! Score: {self.scores[1]}-{self.scores[2]}")
        if self.scores[player_id] >= WINNING_SCORE:
            self.status = 'game_over'
            self.winner = player_id
            logging.info(f"Player {player_id} wins the game!")
        else:
            direction = -1 if player_id == 1 else 1
            self.puck.reset(direction)
            self.start_countdown('goal')

    def start_countdown(self, countdown_type='start'):
        self.countdown_type = countdown_type
        self.countdown_start_time = time.time()
        self.countdown = self.countdown_duration
        
        if countdown_type == 'start':
            logging.info("Starting game countdown...")
        elif countdown_type == 'resume':
            logging.info("Starting resume countdown...")
        elif countdown_type == 'goal':
            logging.info("Starting goal countdown...")

    def start_game(self):
        if self.status == 'waiting':
            self.status = 'starting'
            self.start_countdown('start')
            logging.info("Game starting with countdown...")
            return True
        return False

    def pause_game(self, player_id):
        # Tidak bisa pause jika ada restart request aktif
        if self.restart_request_active:
            logging.info(f"Player {player_id} cannot pause - restart request pending")
            return False
            
        if (self.status in ['active', 'starting'] and 
            not (self.countdown_start_time > 0 and self.countdown_type == 'resume')):
            if player_id not in self.paused_players:
                self.paused_players.add(player_id)
                logging.info(f"Player {player_id} paused the game. Paused players: {self.paused_players}")
                return True
        return False

    def resume_game(self, player_id):
        if player_id in self.paused_players:
            self.paused_players.remove(player_id)
            logging.info(f"Player {player_id} resumed the game. Paused players: {self.paused_players}")
            
            if len(self.paused_players) == 0:
                self.start_countdown('resume')
                logging.info("All players resumed - starting resume countdown")
            
            return True
        return False

    def is_paused(self):
        return len(self.paused_players) > 0

    def remove_player_pause_state(self, player_id):
        if player_id in self.paused_players:
            self.paused_players.remove(player_id)
            logging.info(f"Removed Player {player_id} from pause state due to disconnect")

    # DIUBAH: Helper method untuk auto-resume setelah restart request cancel/reject
    def auto_resume_after_restart_action(self):
        """
        Otomatis resume game setelah restart request dibatalkan atau ditolak
        Menghapus semua player dari pause state dan memulai countdown resume
        """
        had_paused_players = len(self.paused_players) > 0
        
        if had_paused_players:
            # Clear semua player dari pause state
            self.paused_players.clear()
            logging.info("Cleared all players from pause state after restart request cancel/reject")
            
            # Mulai countdown resume
            self.start_countdown('resume')
            logging.info("Starting resume countdown after restart request cancel/reject")
            return True
        else:
            # Tidak ada player yang pause, game langsung aktif
            logging.info("No paused players - game continues immediately after restart request cancel/reject")
            return False

    def request_restart(self, player_id):
        """Player meminta restart game"""
        if not self.restart_request_active:
            self.restart_requester = player_id
            self.restart_request_active = True
            logging.info(f"Player {player_id} requested restart")
            return True
        return False

    def respond_restart(self, player_id, accept):
        """Player merespons restart request"""
        if (self.restart_request_active and 
            self.restart_requester and 
            player_id != self.restart_requester):
            
            if accept:
                logging.info(f"Player {player_id} accepted restart request")
                self.execute_restart()
                return 'accepted'
            else:
                logging.info(f"Player {player_id} rejected restart request")
                self.cancel_restart_request()
                # DIUBAH: Auto resume setelah restart ditolak
                self.auto_resume_after_restart_action()
                return 'rejected'
        return 'invalid'

    def cancel_restart_request(self, player_id=None):
        """Cancel restart request"""
        if self.restart_request_active:
            if player_id is None or player_id == self.restart_requester:
                logging.info(f"Restart request cancelled by Player {player_id or 'system'}")
                self.restart_requester = None
                self.restart_request_active = False
                # DIUBAH: Auto resume akan dipanggil dari caller
                return True
        return False

    def execute_restart(self):
        """Eksekusi restart setelah diterima"""
        logging.info("Executing restart - request accepted")
        self.reset()
        return True

    def remove_player_restart_state(self, player_id):
        """Hapus state restart saat player disconnect"""
        if self.restart_request_active and self.restart_requester == player_id:
            logging.info(f"Restart request cancelled - requester Player {player_id} disconnected")
            had_restart_request = self.cancel_restart_request()
            
            # DIUBAH: Auto resume setelah restart request dibatalkan karena disconnect
            if had_restart_request:
                self.auto_resume_after_restart_action()
            
            return True
        return False

    def get_restart_request_info(self):
        """Get informasi restart request"""
        if self.restart_request_active and self.restart_requester:
            other_player = 1 if self.restart_requester == 2 else 2
            return {
                'active': True,
                'requester': self.restart_requester,
                'responder': other_player
            }
        return {'active': False}

    def reset(self):
        logging.info("Resetting game state.")
        # Reset semua state termasuk restart request
        self.__init__()

    def get_state(self):
        base_state = {
            'status': self.status, 
            'winner': self.winner, 
            'countdown': self.countdown,
            'countdown_type': self.countdown_type,
            'puck': {'x': self.puck.x, 'y': self.puck.y},
            'paddles': {pid: {'x': p.x, 'y': p.y} for pid, p in self.paddles.items()},
            'scores': self.scores,
            'is_paused': self.is_paused(),
            'paused_players': list(self.paused_players)
        }
        
        # Tambahkan informasi restart request
        base_state['restart_request'] = self.get_restart_request_info()
        
        return base_state