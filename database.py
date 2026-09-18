import sqlite3
from contextlib import closing
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
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    """
    params.append(limit)

    cursor.execute(query, params)
    matchups = cursor.fetchall()

    connection.close()
    return matchups


def get_history_stats():
    """Summarize all saved matchups, independently of history list filters."""
    with closing(get_connection()) as connection:
        counts = connection.execute("""
            SELECT COUNT(*),
                COALESCE(SUM(CASE WHEN confidence = ? THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN confidence = ? THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN confidence = ? THEN 1 ELSE 0 END), 0)
            FROM matchup_history
        """, ("High", "Medium", "Low")).fetchone()

        appearances = connection.execute("""
            SELECT team, COUNT(*) AS appearances
            FROM (
                SELECT team_a AS team FROM matchup_history
                UNION ALL
                SELECT team_b AS team FROM matchup_history
            )
            GROUP BY team
            ORDER BY appearances DESC, team ASC
        """).fetchall()

        favorites = connection.execute("""
            SELECT favored_team, COUNT(*) AS favored_count
            FROM matchup_history
            WHERE favored_team != ?
            GROUP BY favored_team
            ORDER BY favored_count DESC, favored_team ASC
        """, ("Even",)).fetchall()

    most_analyzed_count = appearances[0][1] if appearances else 0
    most_favored_count = favorites[0][1] if favorites else 0
    return {
        "total_matchups": counts[0],
        "confidence_counts": dict(zip(("High", "Medium", "Low"), counts[1:])),
        "most_analyzed_teams": [team for team, count in appearances if count == most_analyzed_count],
        "most_analyzed_count": most_analyzed_count,
        "most_favored_teams": [team for team, count in favorites if count == most_favored_count],
        "most_favored_count": most_favored_count,
    }


def delete_matchup(matchup_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM matchup_history
        WHERE id = ?
    """, (matchup_id,))

    connection.commit()
    connection.close()
