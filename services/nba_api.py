import os
from datetime import date, timedelta
from functools import lru_cache
from time import monotonic

import requests

BASE_URL = "https://api.balldontlie.io/v1"
RECENT_GAMES_CACHE_SECONDS = 15 * 60
TEAM_NAME_ALIASES = {"LA Clippers": "Los Angeles Clippers"}

TEAM_LOGO_SLUGS = {
    "Atlanta Hawks": "atl",
    "Boston Celtics": "bos",
    "Brooklyn Nets": "bkn",
    "Charlotte Hornets": "cha",
    "Chicago Bulls": "chi",
    "Cleveland Cavaliers": "cle",
    "Dallas Mavericks": "dal",
    "Denver Nuggets": "den",
    "Detroit Pistons": "det",
    "Golden State Warriors": "gsw",
    "Houston Rockets": "hou",
    "Indiana Pacers": "ind",
    "Los Angeles Clippers": "lac",
    "Los Angeles Lakers": "lal",
    "Memphis Grizzlies": "mem",
    "Miami Heat": "mia",
    "Milwaukee Bucks": "mil",
    "Minnesota Timberwolves": "min",
    "New Orleans Pelicans": "nola",
    "New York Knicks": "nyk",
    "Oklahoma City Thunder": "okc",
    "Orlando Magic": "orl",
    "Philadelphia 76ers": "phi",
    "Phoenix Suns": "phx",
    "Portland Trail Blazers": "por",
    "Sacramento Kings": "sac",
    "San Antonio Spurs": "sas",
    "Toronto Raptors": "tor",
    "Utah Jazz": "uta",
    "Washington Wizards": "wsh",
}


class APIConfigurationError(RuntimeError):
    pass


def get_team_logo_url(team_name):
    team_name = TEAM_NAME_ALIASES.get(team_name, team_name)
    slug = TEAM_LOGO_SLUGS.get(team_name)

    if not slug:
        return ""

    return f"https://a.espncdn.com/i/teamlogos/nba/500/{slug}.png"


def get_headers():
    api_key = os.getenv("BALLDONTLIE_API_KEY")
    if not api_key:
        raise APIConfigurationError("BALLDONTLIE_API_KEY is missing from .env")
    return {"Authorization": api_key}


@lru_cache(maxsize=1)
def get_team_lookup():
    response = requests.get(
        f"{BASE_URL}/teams",
        headers=get_headers(),
        timeout=15
    )
    response.raise_for_status()

    teams = response.json().get("data", [])
    return {
        TEAM_NAME_ALIASES.get(team["full_name"], team["full_name"]): team["id"]
        for team in teams
    }


def get_recent_games_for_team(team_id, limit=10):
    today = date.today()
    cache_window = int(monotonic() // RECENT_GAMES_CACHE_SECONDS)
    return _get_recent_games_for_team(team_id, today, cache_window)[:limit]


@lru_cache(maxsize=60)
def _get_recent_games_for_team(team_id, today, cache_window):
    # Date and time-window keys keep cached games fresh during long-running sessions.
    start_date = today - timedelta(days=300)

    params = {
        "team_ids[]": team_id,
        "season_type": "regular",
        "per_page": 100,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
    }

    games = []
    cursor = None
    while True:
        page_params = dict(params)
        if cursor is not None:
            page_params["cursor"] = cursor

        response = requests.get(
            f"{BASE_URL}/games",
            headers=get_headers(),
            params=page_params,
            timeout=15
        )
        response.raise_for_status()

        payload = response.json()
        games.extend(payload.get("data", []))
        cursor = payload.get("meta", {}).get("next_cursor")
        if cursor is None:
            break

    final_games = [game for game in games if game.get("status") == "Final"]
    final_games.sort(key=lambda g: g.get("date", ""), reverse=True)

    return final_games


def build_team_summary(team_name, team_lookup, games_limit=10):
    team_name = TEAM_NAME_ALIASES.get(team_name, team_name)
    if team_name not in team_lookup:
        raise ValueError(f"Could not find team: {team_name}")

    team_id = team_lookup[team_name]
    games = get_recent_games_for_team(team_id, limit=games_limit)

    if len(games) < 3:
        raise ValueError(f"Not enough recent completed games for {team_name}")

    wins = 0
    losses = 0
    points_for = 0
    points_against = 0

    recent_games = []

    for game in games:
        home_team = game["home_team"]
        visitor_team = game["visitor_team"]

        if home_team["id"] == team_id:
            scored = game["home_team_score"]
            allowed = game["visitor_team_score"]
            opponent = visitor_team["full_name"]
            location = "Home"
        else:
            scored = game["visitor_team_score"]
            allowed = game["home_team_score"]
            opponent = home_team["full_name"]
            location = "Away"

        if scored > allowed:
            wins += 1
        else:
            losses += 1

        points_for += scored
        points_against += allowed

        result = "W" if scored > allowed else "L"

        recent_games.append({
            "date": game.get("date", "")[:10],
            "opponent": TEAM_NAME_ALIASES.get(opponent, opponent),
            "location": location,
            "result": result,
            "scored": scored,
            "allowed": allowed,
        })

    games_used = len(games)

    return {
        "name": team_name,
        "team_id": team_id,
        "logo_url": get_team_logo_url(team_name),
        "games_used": games_used,
        "wins": wins,
        "losses": losses,
        "avg_points_for": round(points_for / games_used, 1),
        "avg_points_against": round(points_against / games_used, 1),
        "point_diff": round((points_for - points_against) / games_used, 1),
        "recent_games": recent_games,
    }
