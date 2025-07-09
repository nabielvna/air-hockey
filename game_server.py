import socket
import threading
import json
import time
import random
import requests
import server.physics as physics

HTTP_SERVER_URL = 'http://127.0.0.1:8000'
GAME_PORT = 9999
WIDTH, HEIGHT = 1200, 800
WINNING_SCORE = 5

waiting_players = []
lock = threading.Lock()

def report_game_result_to_http_server(token, won, goals_scored, goals_conceded, score_change):
    try:
        payload = {
            'token': token, 
            'won': won, 
            'goals_scored': goals_scored, 
            'goals_conceded': goals_conceded,
            'score_change': score_change
        }
        requests.post(f"{HTTP_SERVER_URL}/game-result", json=payload, timeout=5)
        result = "WON" if won else "LOST"
        print(f"Reported game result for token {token[:8]}...: {result} ({goals_scored}-{goals_conceded}), score change: {score_change:+}")
    except requests.RequestException as e:
        print(f"Could not report game result: {e}")

class GameSession(threading.Thread):
    def __init__(self, p1_conn, p1_name, p1_token, p2_conn, p2_name, p2_token):
        super().__init__()
        self.p1_conn, self.p1_name, self.p1_token = p1_conn, p1_name, p1_token
        self.p2_conn, self.p2_name, self.p2_token = p2_conn, p2_name, p2_token
        self.game_state = {
            'puck_pos': [WIDTH / 2, HEIGHT / 2], 'puck_vel': [random.choice([-3, 3]), random.choice([-3, 3])],
            'p1_pos': [WIDTH / 4, HEIGHT / 2],
            'p2_pos': [WIDTH * 3 / 4, HEIGHT / 2],
            'score': [0, 0], 'game_over': False,
            'p1_name': self.p1_name, 'p2_name': self.p2_name
        }
        
        self.prev_p1_pos = [WIDTH / 4, HEIGHT / 2]
        self.prev_p2_pos = [WIDTH * 3 / 4, HEIGHT / 2]

    def reset_puck(self):
        self.game_state['puck_pos'] = [WIDTH / 2, HEIGHT / 2]
        self.game_state['puck_vel'] = [random.choice([-3, 3]), random.choice([-3, 3])]
        time.sleep(1)

    def run(self):
        print(f"Game session started between {self.p1_name} and {self.p2_name}.")
        try:
            self.p1_conn.sendall(json.dumps({'player_id': 1}).encode())
            self.p2_conn.sendall(json.dumps({'player_id': 2}).encode())
        except socket.error:
            self.close_connections()
            return

        PADDLE_RADIUS, PUCK_RADIUS = 25, 15
        GOAL_HEIGHT = 150
        GOAL_TOP_Y = HEIGHT/2 - GOAL_HEIGHT/2
        GOAL_BOTTOM_Y = HEIGHT/2 + GOAL_HEIGHT/2

        while not self.game_state['game_over']:
            try:
                p1_input = json.loads(self.p1_conn.recv(1024).decode())
                p2_input = json.loads(self.p2_conn.recv(1024).decode())

                # Update paddle positions 
                p1_x = max(PADDLE_RADIUS, min(p1_input['x'], WIDTH / 2 - PADDLE_RADIUS))
                p1_y = max(PADDLE_RADIUS, min(p1_input['y'], HEIGHT - PADDLE_RADIUS))
                
                p2_x = max(WIDTH / 2 + PADDLE_RADIUS, min(p2_input['x'], WIDTH - PADDLE_RADIUS))
                p2_y = max(PADDLE_RADIUS, min(p2_input['y'], HEIGHT - PADDLE_RADIUS))
                
                # Count paddle velocities
                p1_vel = [p1_x - self.prev_p1_pos[0], p1_y - self.prev_p1_pos[1]]
                p2_vel = [p2_x - self.prev_p2_pos[0], p2_y - self.prev_p2_pos[1]]
                
                self.game_state['p1_pos'] = [p1_x, p1_y]
                self.game_state['p2_pos'] = [p2_x, p2_y]

                # Use physics module
                self.game_state['puck_vel'] = physics.apply_friction(self.game_state['puck_vel'])

                self.game_state['puck_pos'][0] += self.game_state['puck_vel'][0]
                self.game_state['puck_pos'][1] += self.game_state['puck_vel'][1]

                self.game_state['puck_pos'], self.game_state['puck_vel'] = physics.handle_wall_collision(
                    self.game_state['puck_pos'], self.game_state['puck_vel'], PUCK_RADIUS, HEIGHT
                )

                self.game_state['puck_pos'], self.game_state['puck_vel'] = physics.handle_paddle_collision(
                    self.game_state['puck_pos'], self.game_state['puck_vel'], 
                    self.game_state['p1_pos'], PADDLE_RADIUS, PUCK_RADIUS, p1_vel, is_player1=True
                )

                self.game_state['puck_pos'], self.game_state['puck_vel'] = physics.handle_paddle_collision(
                    self.game_state['puck_pos'], self.game_state['puck_vel'], 
                    self.game_state['p2_pos'], PADDLE_RADIUS, PUCK_RADIUS, p2_vel, is_player1=False
                )

                self.prev_p1_pos = [p1_x, p1_y]
                self.prev_p2_pos = [p2_x, p2_y]

                self.game_state['puck_vel'] = physics.clamp_velocity(self.game_state['puck_vel'])

                puck = self.game_state['puck_pos']
                if puck[0] < PUCK_RADIUS:
                    if GOAL_TOP_Y < puck[1] < GOAL_BOTTOM_Y:
                        self.game_state['score'][1] += 1
                        self.reset_puck()
                    else: 
                        puck[0] = PUCK_RADIUS
                        self.game_state['puck_vel'][0] = abs(self.game_state['puck_vel'][0]) * 0.95
                elif puck[0] > WIDTH - PUCK_RADIUS:
                    if GOAL_TOP_Y < puck[1] < GOAL_BOTTOM_Y:
                        self.game_state['score'][0] += 1
                        self.reset_puck()
                    else: 
                        puck[0] = WIDTH - PUCK_RADIUS
                        self.game_state['puck_vel'][0] = -abs(self.game_state['puck_vel'][0]) * 0.95
                
                # Check win condition
                if self.game_state['score'][0] >= WINNING_SCORE or self.game_state['score'][1] >= WINNING_SCORE:
                    self.game_state['game_over'] = True

                # Send game state
                self.p1_conn.sendall(json.dumps(self.game_state).encode())
                self.p2_conn.sendall(json.dumps(self.game_state).encode())
                
                time.sleep(1 / 60)
            except (socket.error, json.JSONDecodeError):
                break
        
        self.calculate_and_report_final_scores()
        self.close_connections()

    def calculate_and_report_final_scores(self):
        """Calculate and report both score changes and detailed game statistics"""
        p1_goals = self.game_state['score'][0]
        p2_goals = self.game_state['score'][1]
        score_diff = abs(p1_goals - p2_goals)
        
        if p1_goals > p2_goals:
            # Player 1 won
            report_game_result_to_http_server(self.p1_token, True, p1_goals, p2_goals, score_diff)
            report_game_result_to_http_server(self.p2_token, False, p2_goals, p1_goals, -score_diff)
            
        elif p2_goals > p1_goals:
            # Player 2 won
            report_game_result_to_http_server(self.p2_token, True, p2_goals, p1_goals, score_diff)
            report_game_result_to_http_server(self.p1_token, False, p1_goals, p2_goals, -score_diff)

    def close_connections(self):
        try: self.p1_conn.close(); self.p2_conn.close()
        except socket.error: pass

def run_game_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', GAME_PORT))
    server_socket.listen(2)
    print(f"Game server listening on port {GAME_PORT}...")
    while True:
        conn, addr = server_socket.accept()
        try:
            login_data = json.loads(conn.recv(1024).decode())
            name, token = login_data['name'], login_data['token']
            print(f"Player '{name}' connected from {addr} with token {token[:8]}...")
            with lock:
                waiting_players.append({'conn': conn, 'name': name, 'token': token})
                if len(waiting_players) >= 2:
                    p1, p2 = waiting_players.pop(0), waiting_players.pop(0)
                    GameSession(p1['conn'], p1['name'], p1['token'], p2['conn'], p2['name'], p2['token']).start()
        except (socket.error, json.JSONDecodeError, KeyError) as e:
            print(f"Error receiving login data: {e}")
            conn.close()

if __name__ == "__main__":
    run_game_server()