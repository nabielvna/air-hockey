from datetime import datetime
import html
import uuid
from server.database import GameDB

class HttpServer:
    def __init__(self):
        self.sessions = {} 
        self.types = { '.html': 'text/html', '.json': 'application/json' }
        self.db = GameDB()

    def response(self, code=404, message='Not Found', body=b'', headers={}):
        date_str = datetime.now().strftime('%c')
        response_line = f"HTTP/1.0 {code} {message}\r\n"
        headers_list = [f"Date: {date_str}", "Connection: close", "Server: MyAirHockeyServer/1.0", f"Content-Length: {len(body)}"]
        for key, value in headers.items():
            headers_list.append(f"{key}: {value}")
        header_str = "\r\n".join(headers_list)
        return response_line.encode() + header_str.encode() + b'\r\n\r\n' + body

    def http_get(self, path):
        try:
            if path == '/leaderboard':
                player_data = self.db.get_leaderboard_data()
                html_body = self.generate_leaderboard_html(player_data)
                return self.response(200, 'OK', html_body.encode('utf-8'), {'Content-Type': 'text/html'})
            
            elif path == '/leaderboard/json':
                import json
                player_data = self.db.get_leaderboard_data()
                return self.response(200, 'OK', json.dumps(player_data, indent=2).encode(), 
                                   {'Content-Type': 'application/json'})
            
            elif path.startswith('/stats/'):
                import json
                username = path.split('/')[-1]
                stats = self.db.get_player_stats(username)
                
                if not stats:
                    return self.response(404, 'Not Found', b'{"error": "Player not found"}')
                
                return self.response(200, 'OK', json.dumps(stats, indent=2).encode(), 
                                   {'Content-Type': 'application/json'})
            
            else:
                return self.response(404, 'Not Found', b'{"error": "Endpoint not found"}')
                
        except Exception as e:
            print(f"Error in http_get: {e}")
            return self.response(500, 'Internal Server Error', b'{"error": "Database error"}')

    def http_post(self, path, body_str):
        import json
        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError:
            return self.response(400, 'Bad Request', b'{"error": "Invalid JSON"}')

        try:
            if path == '/register':
                return self.handle_register(payload)
            elif path == '/login':
                return self.handle_login(payload)
            elif path == '/game-result':
                return self.handle_game_result(payload)
            else:
                return self.response(404, 'Not Found', b'{"error": "Endpoint not found"}')
        except Exception as e:
            print(f"Error in http_post: {e}")
            return self.response(500, 'Internal Server Error', b'{"error": "Database error"}')

    def generate_leaderboard_html(self, player_data):
        table_rows = []
        if not player_data:
            table_rows.append('<tr><td colspan="8" style="text-align:center;">No scores yet. Play a game!</td></tr>')
        else:
            for rank, player in enumerate(player_data, 1):
                safe_name = html.escape(player['name'])
                
                # Color coding for win rate
                win_rate_color = '#28a745' if player['win_rate'] >= 60 else '#ffc107' if player['win_rate'] >= 40 else '#dc3545'
                
                row = f'''
                <tr>
                    <td class="rank">{rank}</td>
                    <td><strong>{safe_name}</strong></td>
                    <td>{player['score']}</td>
                    <td>{player['games_played']}</td>
                    <td style="color: #28a745;">{player['wins']}</td>
                    <td style="color: #dc3545;">{player['losses']}</td>
                    <td style="color: {win_rate_color}; font-weight: bold;">{player['win_rate']}%</td>
                    <td>{player['goals_scored']}-{player['goals_conceded']}</td>
                </tr>
                '''
                table_rows.append(row)
        
        table_body_html = "\n".join(table_rows)
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8"><title>Air Hockey Leaderboard</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 20px; }}
                .container {{ max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                h1 {{ text-align: center; border-bottom: 2px solid #eaeaea; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                th, td {{ padding: 8px 10px; text-align: center; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #007bff; color: white; font-weight: bold; }}
                tr:nth-child(even) {{ background-color: #f8f9fa; }}
                tr:hover {{ background-color: #e9ecef; }}
                .rank {{ font-weight: bold; font-size: 16px; }}
                .stats-note {{ text-align: center; margin-top: 10px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏆 Air Hockey Leaderboard 🏆</h1>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Player</th>
                            <th>Points</th>
                            <th>Games</th>
                            <th>Wins</th>
                            <th>Losses</th>
                            <th>Win Rate</th>
                            <th>Goals (F-A)</th>
                        </tr>
                    </thead>
                    <tbody>{table_body_html}</tbody>
                </table>
                <p class="stats-note">F-A = Goals For - Goals Against</p>
            </div>
        </body>
        </html>
        """
        return html_template

    def process_request(self, data):
        requests = data.split("\r\n")
        request_line = requests[0].strip()
        body_start_index = data.find('\r\n\r\n') + 4
        body_str = data[body_start_index:]
        try:
            method, path, _ = request_line.split(" ")
            if method == 'GET':
                return self.http_get(path)
            elif method == 'POST':
                return self.http_post(path, body_str)
            else:
                return self.response(400, 'Bad Request', b'{"error": "Unsupported method"}')
        except ValueError:
            return self.response(400, 'Bad Request', b'{"error": "Malformed request line"}')

    def handle_register(self, payload):
        import json
        username = payload.get('name')
        password = payload.get('password')
        
        if not username or not password:
            return self.response(400, 'Bad Request', b'{"error": "Username and password required"}')
        
        if self.db.register_player(username, password):
            message = {"message": "User registered successfully"}
            return self.response(201, 'Created', json.dumps(message).encode(), 
                               {'Content-Type': 'application/json'})
        else:
            return self.response(409, 'Conflict', b'{"error": "Username already exists"}')

    def handle_login(self, payload):
        import json
        username = payload.get('name')
        password = payload.get('password')
        
        if not username or not password:
            return self.response(400, 'Bad Request', b'{"error": "Username and password required"}')
        
        if self.db.authenticate_player(username, password):
            token = uuid.uuid4().hex
            self.sessions[token] = username
            message = {"message": "Login successful", "token": token}
            return self.response(200, 'OK', json.dumps(message).encode(), 
                               {'Content-Type': 'application/json'})
        else:
            return self.response(401, 'Unauthorized', b'{"error": "Invalid username or password"}')

    def handle_game_result(self, payload):
        import json
        token = payload.get('token')
        won = payload.get('won', False)
        goals_scored = payload.get('goals_scored', 0)
        goals_conceded = payload.get('goals_conceded', 0)
        score_change = payload.get('score_change', 0)
        
        username = self.sessions.get(token)
        if not username:
            return self.response(401, 'Unauthorized', b'{"error": "Invalid or expired token"}')
        
        if self.db.update_game_result(username, won, goals_scored, goals_conceded, score_change):
            message = {"message": "Game result and score updated successfully"}
            return self.response(200, 'OK', json.dumps(message).encode(), 
                               {'Content-Type': 'application/json'})
        else:
            return self.response(401, 'Unauthorized', b'{"error": "Player not found"}')