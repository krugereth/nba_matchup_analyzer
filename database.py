import sqlite3
from datetime import datetime

DATABASE_NAME = "matchups.db"


def get_connection():
    return sqlite3.connect(DATABASE_NAME)


def init_db():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matchup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_a TEXT NOT NULL,
            team_b TEXT NOT NULL,
            favored_team TEXT NOT NULL,
            confidence TEXT NOT NULL,
            score_difference REAL NOT NULL,
            explanation TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_matchup_result(matchup):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO matchup_history (
            team_a,
            team_b,
            favored_team,
            confidence,
            score_difference,
            explanation,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        matchup["team_a"]["name"],
        matchup["team_b"]["name"],
        matchup["favored_team"],
        matchup["confidence"],
        matchup["score_difference"],
        matchup["explanation"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    connection.commit()
    connection.close()


def get_recent_matchups(limit=20, team_query=None, confidence_filter=None):
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    query = """
        SELECT *
        FROM matchup_history
        WHERE 1 = 1
    """

    params = []

    if team_query:
        query += """
            AND (
                team_a LIKE ?
                OR team_b LIKE ?
                OR favored_team LIKE ?
            )
        """
        search_value = f"%{team_query}%"
        params.extend([search_value, search_value, search_value])

    if confidence_filter:
        query += """
            AND confidence = ?
        """
        params.append(confidence_filter)

    query += """
        ORDER BY created_at DESC
        LIMIT ?
    """
    params.append(limit)

    cursor.execute(query, params)
    matchups = cursor.fetchall()

    connection.close()
    return matchups

def delete_matchup(matchup_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM matchup_history
        WHERE id = ?
    """, (matchup_id,))

    connection.commit()
    connection.close()