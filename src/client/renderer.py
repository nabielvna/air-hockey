# src/client/renderer.py
import pygame
import random
from collections import deque
from src.common.settings import *

# Helper function untuk menggambar lingkaran dengan efek glow
def draw_glow_circle(surface, color, center, radius, glow_strength=5, steps=5):
    for i in range(steps, 0, -1):
        alpha = int(255 * (1 / (steps + 1)) * (1 - i / steps))
        glow_color = (*color, alpha)
        glow_radius = radius + (glow_strength * (i / steps))
        
        temp_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(temp_surf, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(temp_surf, (center[0] - glow_radius, center[1] - glow_radius))

    pygame.draw.circle(surface, color, center, radius)


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        try:
            # Cobalah memuat font kustom jika ada
            font_path = "assets/fonts/Hyperspace.ttf" # Contoh path, sesuaikan!
            self.score_font = pygame.font.Font(font_path, 74)
            self.info_font = pygame.font.Font(font_path, 42)
            self.menu_font = pygame.font.Font(font_path, 60)
            self.small_font = pygame.font.Font(font_path, 28)
            self.countdown_font = pygame.font.Font(font_path, 150)
            self.countdown_text_font = pygame.font.Font(font_path, 48)
            self.restart_font = pygame.font.Font(font_path, 36)  # DIUBAH: Font untuk restart UI
        except FileNotFoundError:
            # Fallback ke font default jika tidak ditemukan
            print("Font kustom tidak ditemukan, menggunakan font default.")
            self.score_font = pygame.font.Font(None, 74)
            self.info_font = pygame.font.Font(None, 50)
            self.menu_font = pygame.font.Font(None, 60)
            self.small_font = pygame.font.Font(None, 36)
            self.countdown_font = pygame.font.Font(None, 150)
            self.countdown_text_font = pygame.font.Font(None, 48)
            self.restart_font = pygame.font.Font(None, 36)  # DIUBAH: Font untuk restart UI

        # State untuk Efek Visual
        self.puck_trail = deque(maxlen=15)
        self.screen_shake = 0
        self.goal_flash_alpha = 0

    def draw_main_menu(self, mode, selected_option=None):
        title_text = self.menu_font.render("Air Hockey", True, WHITE)
        
        # Opsi menjadi dinamis berdasarkan pilihan yang disorot
        start_color = YELLOW if selected_option == "start" else WHITE
        restart_color = YELLOW if selected_option == "restart" else WHITE
        quit_color = YELLOW if selected_option == "quit" else WHITE

        start_text = self.menu_font.render("Start Game", True, start_color)
        restart_text = self.menu_font.render("Restart Game", True, restart_color)
        quit_text = self.menu_font.render("Quit", True, quit_color)
        
        title_rect = title_text.get_rect(center=(WIDTH / 2, HEIGHT / 4))
        start_rect = start_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50))
        restart_rect = restart_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 50))
        quit_rect = quit_text.get_rect(center=(WIDTH / 2, HEIGHT * 3 / 4))

        self.screen.blit(title_text, title_rect)
        if mode != "game_over":
            self.screen.blit(start_text, start_rect)
        if mode == "game_over":
            self.screen.blit(restart_text, restart_rect)
        self.screen.blit(quit_text, quit_rect)
        
        pygame.display.flip()
        return start_rect, restart_rect, quit_rect

    def draw_ingame_menu(self, selected_option=None, is_player_paused=True):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Title berubah sesuai status
        if is_player_paused:
            menu_title = self.menu_font.render("PAUSED", True, WHITE)
            status_text = self.small_font.render("You have paused the game", True, WHITE)
        else:
            menu_title = self.menu_font.render("WAITING", True, YELLOW)
            status_text = self.small_font.render("Waiting for other players to unpause", True, WHITE)
        
        restart_color = YELLOW if selected_option == "restart" else WHITE
        quit_color = YELLOW if selected_option == "quit" else WHITE
        
        restart_game_text = self.info_font.render("Request Restart", True, restart_color)
        quit_game_text = self.info_font.render("Quit Game", True, quit_color)
        
        # Resume text berubah sesuai status
        if is_player_paused:
            resume_game_text = self.small_font.render("Resume (Esc)", True, WHITE)
        else:
            resume_game_text = self.small_font.render("You have already resumed", True, (150, 150, 150))
        
        menu_title_rect = menu_title.get_rect(center=(WIDTH / 2, HEIGHT / 4))
        status_rect = status_text.get_rect(center=(WIDTH / 2, HEIGHT / 4 + 50))
        restart_game_rect = restart_game_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 60))
        quit_game_rect = quit_game_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30))
        resume_game_rect = resume_game_text.get_rect(center=(WIDTH / 2, HEIGHT * 3 / 4))
        
        self.screen.blit(menu_title, menu_title_rect)
        self.screen.blit(status_text, status_rect)
        self.screen.blit(restart_game_text, restart_game_rect)
        self.screen.blit(quit_game_text, quit_game_rect)
        self.screen.blit(resume_game_text, resume_game_rect)
        
        pygame.display.flip()
        return restart_game_rect, quit_game_rect

    # DIUBAH: Method untuk menggambar UI restart request-response
    def draw_restart_request_ui(self, restart_info, player_id, selected_option=None):
        """
        Menggambar UI restart request-response
        restart_info: dict dengan informasi restart request
        player_id: ID player saat ini
        selected_option: opsi yang sedang di-highlight
        """
        # DIPERBAIKI: Background hitam solid, bukan transparan
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))  # Solid black background
        self.screen.blit(overlay, (0, 0))
        
        requester = restart_info.get('requester')
        responder = restart_info.get('responder')
        
        # Title
        title_text = self.restart_font.render("RESTART GAME?", True, YELLOW)
        title_rect = title_text.get_rect(center=(WIDTH / 2, HEIGHT / 3))
        self.screen.blit(title_text, title_rect)
        
        # Status pesan berdasarkan role player
        if player_id == requester:
            # Player yang request restart
            status_text = self.small_font.render(f"You requested restart", True, WHITE)
            status_rect = status_text.get_rect(center=(WIDTH / 2, HEIGHT / 3 + 50))
            self.screen.blit(status_text, status_rect)
            
            wait_text = self.small_font.render(f"Waiting for Player {responder} response...", True, (200, 200, 200))
            wait_rect = wait_text.get_rect(center=(WIDTH / 2, HEIGHT / 3 + 80))
            self.screen.blit(wait_text, wait_rect)
            
            # Tombol cancel untuk requester
            cancel_color = YELLOW if selected_option == "cancel" else WHITE
            cancel_text = self.info_font.render("Cancel Request", True, cancel_color)
            cancel_rect = cancel_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 100))
            self.screen.blit(cancel_text, cancel_rect)
            
            cancel_instruction = self.small_font.render("Press ESC or click to cancel", True, (150, 150, 150))
            cancel_instruction_rect = cancel_instruction.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 150))
            self.screen.blit(cancel_instruction, cancel_instruction_rect)
            
            return None, None, cancel_rect
            
        elif player_id == responder:
            # Player yang menerima request restart
            status_text = self.small_font.render(f"Player {requester} wants to restart", True, WHITE)
            status_rect = status_text.get_rect(center=(WIDTH / 2, HEIGHT / 3 + 50))
            self.screen.blit(status_text, status_rect)
            
            # Tombol YES/NO untuk responder
            yes_color = YELLOW if selected_option == "yes" else VOTING_YES_COLOR
            no_color = YELLOW if selected_option == "no" else VOTING_NO_COLOR
            
            yes_text = self.info_font.render("ACCEPT", True, yes_color)
            no_text = self.info_font.render("REJECT", True, no_color)
            
            yes_rect = yes_text.get_rect(center=(WIDTH / 2 - 120, HEIGHT / 2 + 50))
            no_rect = no_text.get_rect(center=(WIDTH / 2 + 120, HEIGHT / 2 + 50))
            
            self.screen.blit(yes_text, yes_rect)
            self.screen.blit(no_text, no_rect)
            
            # Instruksi
            instruction_text = self.small_font.render("Click your choice or press Y/N", True, WHITE)
            instruction_rect = instruction_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 120))
            self.screen.blit(instruction_text, instruction_rect)
            
            return yes_rect, no_rect, None
        
        # Fallback (shouldn't happen)
        return None, None, None

    def trigger_goal_effect(self):
        self.screen_shake = 20
        self.goal_flash_alpha = 200

    def update_effects(self):
        if self.screen_shake > 0:
            self.screen_shake -= 1
        if self.goal_flash_alpha > 0:
            self.goal_flash_alpha -= 15
            self.goal_flash_alpha = max(0, self.goal_flash_alpha)

    def draw(self, state, player_id, connection_info=None):
        self.update_effects()

        # Terapkan Screen Shake (tapi tidak saat pause atau countdown resume)
        render_offset = [0, 0]
        if (self.screen_shake > 0 and state and 
            not state.get('is_paused', False) and 
            not (state.get('countdown', 0) > 0 and state.get('countdown_type') == 'resume')):
            render_offset[0] = random.randint(-5, 5)
            render_offset[1] = random.randint(-5, 5)
        
        # Gambar elemen ke screen dengan offset
        draw_surface = self.screen.copy()
        draw_surface.fill(BLACK)

        self.draw_border(draw_surface)
        self.draw_board(draw_surface)
        self.draw_goals(draw_surface)

        if not state:
            if connection_info: self.draw_connection_status(draw_surface, connection_info)
            else: self.draw_message(draw_surface, "Connecting to server...")
        else:
            if state['status'] == 'waiting': 
                self.draw_message(draw_surface, "Waiting for opponent...")
            elif state['status'] == 'starting':
                pass  # Biarkan countdown yang bicara
            elif state['status'] == 'game_over':
                winner = state.get('winner')
                if winner == 'opponent_disconnected': 
                    self.draw_message(draw_surface, "Opponent Disconnected", "You win by default")
                elif winner == player_id: 
                    self.draw_message(draw_surface, "YOU WIN!", f"Final Score: {state['scores'].get('1', 0)} - {state['scores'].get('2', 0)}")
                else: 
                    self.draw_message(draw_surface, "YOU LOSE", f"Final Score: {state['scores'].get('1', 0)} - {state['scores'].get('2', 0)}")
            
            if state['status'] in ['active', 'starting']: 
                self.draw_game_elements(draw_surface, state, player_id)
                
                # Tampilkan indikator pause jika game di-pause
                if state.get('is_paused', False):
                    self.draw_pause_indicator(draw_surface, state.get('paused_players', []))
                    
            # Countdown dengan tipe yang berbeda
            if state.get('countdown', 0) > 0: 
                countdown_type = state.get('countdown_type', 'goal')
                self.draw_countdown(draw_surface, state['countdown'], countdown_type)

        # Blit surface yang sudah digambar dengan offset getaran
        self.screen.blit(draw_surface, render_offset)

        # Gambar kilatan gol di atas segalanya (tapi tidak saat pause atau countdown resume)
        if (self.goal_flash_alpha > 0 and state and 
            not state.get('is_paused', False) and 
            not (state.get('countdown', 0) > 0 and state.get('countdown_type') == 'resume')):
            flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, self.goal_flash_alpha))
            self.screen.blit(flash_surface, (0, 0))

    def draw_pause_indicator(self, surface, paused_players):
        # Overlay transparan
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (0, 0))
        
        # Text pause
        pause_text = self.info_font.render("GAME PAUSED", True, YELLOW)
        pause_rect = pause_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 70))
        surface.blit(pause_text, pause_rect)
        
        # Tampilkan daftar player yang pause
        if paused_players:
            if len(paused_players) == 1:
                paused_by_text = self.small_font.render(f"Paused by Player {paused_players[0]}", True, WHITE)
            else:
                players_list = ", ".join([f"Player {p}" for p in sorted(paused_players)])
                paused_by_text = self.small_font.render(f"Paused by: {players_list}", True, WHITE)
            
            paused_by_rect = paused_by_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 20))
            surface.blit(paused_by_text, paused_by_rect)
        
        # Info tambahan
        info_text = self.small_font.render("Game will resume when all players unpause", True, (200, 200, 200))
        info_rect = info_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 70))
        surface.blit(info_text, info_rect)

    def draw_connection_status(self, surface, info):
        self.draw_message(surface, info.get('status', 'Connecting...'), info.get('detail', ''))

    def draw_board(self, surface):
        pygame.draw.line(surface, GLOW_COLOR, (WIDTH / 2, 0), (WIDTH / 2, HEIGHT), 5)
        pygame.draw.circle(surface, GLOW_COLOR, (WIDTH / 2, HEIGHT / 2), 75, 5)

    def draw_border(self, surface):
        # Batas luar lapangan
        border_lines = [
            ((0, 0), (WIDTH, 0)),
            ((0, HEIGHT), (WIDTH, HEIGHT)),
            ((0, 0), (0, GOAL_Y_START)),
            ((0, GOAL_Y_START + GOAL_HEIGHT), (0, HEIGHT)),
            ((WIDTH, 0), (WIDTH, GOAL_Y_START)),
            ((WIDTH, GOAL_Y_START + GOAL_HEIGHT), (WIDTH, HEIGHT))
        ]
        for start, end in border_lines:
            pygame.draw.line(surface, GLOW_COLOR, start, end, 5)

    def draw_goals(self, surface):
        pygame.draw.rect(surface, WHITE, (0, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)
        pygame.draw.rect(surface, WHITE, (WIDTH - GOAL_WIDTH, GOAL_Y_START, GOAL_WIDTH, GOAL_HEIGHT), 5)

    def draw_game_elements(self, surface, state, player_id):
        # Gambar Paddle dengan efek glow
        for pid_str, p_data in state['paddles'].items():
            color = LIGHT_BLUE if int(pid_str) == 1 else LIGHT_RED
            pos = (int(p_data['x']), int(p_data['y']))
            draw_glow_circle(surface, color, pos, PADDLE_RADIUS, glow_strength=10)
            if int(pid_str) == player_id: 
                pygame.draw.circle(surface, WHITE, pos, PADDLE_RADIUS, 3)
        
        puck_pos = (int(state['puck']['x']), int(state['puck']['y']))
        
        # Hanya tambah jejak jika game tidak di-pause dan bukan countdown resume
        if (not state.get('is_paused', False) and 
            not (state.get('countdown', 0) > 0 and state.get('countdown_type') == 'resume')):
            self.puck_trail.append(puck_pos)

        # Gambar Jejak Puck (tidak bergerak saat pause atau countdown)
        for i, pos in enumerate(self.puck_trail):
            alpha = int(255 * (i / len(self.puck_trail)))
            trail_color = (*WHITE, alpha)
            radius = PUCK_RADIUS * (i / len(self.puck_trail))
            
            trail_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, trail_color, (radius, radius), radius)
            surface.blit(trail_surf, (pos[0] - radius, pos[1] - radius))
        
        # Gambar Puck utama dengan efek glow
        draw_glow_circle(surface, WHITE, puck_pos, PUCK_RADIUS, glow_strength=8)
        
        # Gambar Skor
        scores = state['scores']
        p1_score = self.score_font.render(str(scores.get('1', 0)), True, LIGHT_BLUE)
        p2_score = self.score_font.render(str(scores.get('2', 0)), True, LIGHT_RED)
        surface.blit(p1_score, (WIDTH / 4, 10))
        surface.blit(p2_score, (WIDTH * 3 / 4 - p2_score.get_width(), 10))

    def draw_message(self, surface, line1, line2=None):
        text1 = self.info_font.render(line1, True, WHITE)
        rect1 = text1.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 20))
        surface.blit(text1, rect1)
        if line2:
            text2 = self.small_font.render(line2, True, WHITE)
            rect2 = text2.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30))
            surface.blit(text2, rect2)

    def draw_countdown(self, surface, number, countdown_type='goal'):
        # Tentukan warna dan pesan berdasarkan tipe countdown
        if countdown_type == 'start':
            color = COUNTDOWN_START_COLOR
            message = "GAME STARTING"
        elif countdown_type == 'resume':
            color = COUNTDOWN_RESUME_COLOR
            message = "RESUMING"
        else:  # goal atau default
            color = COUNTDOWN_GOAL_COLOR
            message = ""
        
        # Gambar angka countdown
        number_text = self.countdown_font.render(str(number), True, color)
        number_rect = number_text.get_rect(center=(WIDTH/2, HEIGHT/2))
        surface.blit(number_text, number_rect)
        
        # Gambar pesan jika ada
        if message:
            message_text = self.countdown_text_font.render(message, True, color)
            message_rect = message_text.get_rect(center=(WIDTH/2, HEIGHT/2 + 120))
            surface.blit(message_text, message_rect)