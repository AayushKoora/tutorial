import sqlite3

DB_PATH = "scores.db"


def connect(db_path=DB_PATH):
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            name TEXT PRIMARY KEY,
            best_score INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            played_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def list_players(connection):
    cursor = connection.execute("SELECT name FROM players ORDER BY name ASC")
    return [row[0] for row in cursor.fetchall()]


def get_or_create_player(connection, name):
    cursor = connection.execute(
        "SELECT best_score FROM players WHERE name = ?", (name,)
    )
    row = cursor.fetchone()
    if row is not None:
        return row[0]

    connection.execute(
        "INSERT INTO players (name, best_score) VALUES (?, 0)", (name,)
    )
    connection.commit()
    return 0


def log_round(connection, name, score, played_at):
    connection.execute(
        "INSERT INTO rounds (player_name, score, played_at) VALUES (?, ?, ?)",
        (name, score, played_at.isoformat()),
    )
    connection.execute(
        "UPDATE players SET best_score = ? WHERE name = ? AND ? > best_score",
        (score, name, score),
    )
    connection.commit()
