import sqlite3
import threading
import bcrypt
import pandas as pd

DB_FILE = '../gamedata.db'

class GameDB:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.lock = threading.Lock()
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    name TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    score INTEGER DEFAULT 0 CHECK (score >= 0),
                    wins INTEGER DEFAULT 0 CHECK (wins >= 0),
                    losses INTEGER DEFAULT 0 CHECK (losses >= 0),
                    goals_scored INTEGER DEFAULT 0 CHECK (goals_scored >= 0),
                    goals_conceded INTEGER DEFAULT 0 CHECK (goals_conceded >= 0),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_players_timestamp 
                AFTER UPDATE ON players
                BEGIN
                    UPDATE players SET updated_at = CURRENT_TIMESTAMP WHERE name = NEW.name;
                END
            ''')
            
            conn.commit()
            print("Database initialized successfully")
            
            db = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' AND name='players'", conn)
            print(db.head)
            

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row 
        return conn

    def hash_password(self, password):
        """Hash password using bcrypt with automatic salt generation"""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, password, hashed_password):
        """Verify password against bcrypt hash"""
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def calculate_win_rate(self, wins, losses):
        total_games = wins + losses
        if total_games == 0:
            return 0.0
        return round((wins / total_games) * 100, 1)

    def get_leaderboard_data(self):
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, score, wins, losses, goals_scored, goals_conceded
                FROM players
                ORDER BY score DESC, wins DESC, name ASC
            ''')
            
            players = []
            for row in cursor.fetchall():
                players.append({
                    'name': row['name'],
                    'score': row['score'],
                    'wins': row['wins'],
                    'losses': row['losses'],
                    'win_rate': self.calculate_win_rate(row['wins'], row['losses']),
                    'goals_scored': row['goals_scored'],
                    'goals_conceded': row['goals_conceded'],
                    'games_played': row['wins'] + row['losses']
                })
            
            return players

    def get_player_stats(self, username):
        """Get specific player statistics"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, score, wins, losses, goals_scored, goals_conceded
                FROM players
                WHERE name = ?
            ''', (username,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'name': row['name'],
                'score': row['score'],
                'wins': row['wins'],
                'losses': row['losses'],
                'games_played': row['wins'] + row['losses'],
                'win_rate': self.calculate_win_rate(row['wins'], row['losses']),
                'goals_scored': row['goals_scored'],
                'goals_conceded': row['goals_conceded']
            }

    def register_player(self, username, password):
        """Register new player"""
        with self.lock:
            try:
                with self.get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO players (name, password_hash)
                        VALUES (?, ?)
                    ''', (username, self.hash_password(password)))
                    conn.commit()
                    return True
            except sqlite3.IntegrityError:
                return False

    def authenticate_player(self, username, password):
        """Authenticate player login using bcrypt"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT password_hash FROM players WHERE name = ?
            ''', (username,))
            
            row = cursor.fetchone()
            if row:
                return self.verify_password(password, row['password_hash'])
            return False

    def update_game_result(self, username, won, goals_scored, goals_conceded, score_change):
        """Update player stats after game"""
        with self.lock:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if player exists
                cursor.execute('SELECT name FROM players WHERE name = ?', (username,))
                if not cursor.fetchone():
                    return False
                
                # Update player statistics
                cursor.execute('''
                    UPDATE players 
                    SET wins = wins + ?,
                        losses = losses + ?,
                        goals_scored = goals_scored + ?,
                        goals_conceded = goals_conceded + ?,
                        score = MAX(0, score + ?)
                    WHERE name = ?
                ''', (
                    1 if won else 0,
                    0 if won else 1,
                    goals_scored,
                    goals_conceded,
                    score_change,
                    username
                ))
                
                conn.commit()
                return True