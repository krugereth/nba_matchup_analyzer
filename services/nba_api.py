import os
from datetime import date, timedelta
from functools import lru_cache

import requests

BASE_URL = "https://api.balldontlie.io/v1"


def get_headers():
    api_key = os.getenv("BALLDONTLIE_API_KEY")
    if not api_key:
        raise RuntimeError("BALLDONTLIE_API_KEY is missing from .env")
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
    return {team["full_name"]: team["id"] for team in teams}

@lru_cache(maxsize=60)
def get_recent_games_for_team(team_id, limit=10):
    today = date.today()
    start_date = today - timedelta(days=300)

    params = {
        "team_ids[]": team_id,
        "postseason": "false",
        "per_page": 25,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
    }

    response = requests.get(
        f"{BASE_URL}/games",
        headers=get_headers(),
        params=params,
        timeout=15
    )
    response.raise_for_status()

    games = response.json().get("data", [])
    final_games = [game for game in games if game.get("status") == "Final"]
    final_games.sort(key=lambda g: g.get("date", ""), reverse=True)

    return final_games[:limit]


def build_team_summary(team_name, team_lookup):
    if team_name not in team_lookup:
        raise ValueError(f"Could not find team: {team_name}")

    team_id = team_lookup[team_name]
    games = get_recent_games_for_team(team_id)

    if len(games) < 3:
        raise ValueError(f"Not enough recent completed games for {team_name}")

    wins = 0
    losses = 0
    points_for = 0
    points_against = 0

    for game in games:
        home_team = game["home_team"]

        if home_team["id"] == team_id:
            scored = game["home_team_score"]
            allowed = game["visitor_team_score"]
        else:
            scored = game["visitor_team_score"]
            allowed = game["home_team_score"]

        if scored > allowed:
            wins += 1
        else:
            losses += 1

        points_for += scored
        points_against += allowed

    games_used = len(games)

    return {
        "name": team_name,
        "team_id": team_id,
        "games_used": games_used,
        "wins": wins,
        "losses": losses,
        "avg_points_for": round(points_for / games_used, 1),
        "avg_points_against": round(points_against / games_used, 1),
        "point_diff": round((points_for - points_against) / games_used, 1),
    }


def compare_recent_form(team_a, team_b, home_team=None):
    if team_a["wins"] > team_b["wins"]:
        edge_team = team_a["name"]
        reason = f"{team_a['name']} has the stronger recent record."
    elif team_b["wins"] > team_a["wins"]:
        edge_team = team_b["name"]
        reason = f"{team_b['name']} has the stronger recent record."
    elif team_a["point_diff"] > team_b["point_diff"]:
        edge_team = team_a["name"]
        reason = f"Both teams have similar recent records, but {team_a['name']} has the better scoring margin."
    elif team_b["point_diff"] > team_a["point_diff"]:
        edge_team = team_b["name"]
        reason = f"Both teams have similar recent records, but {team_b['name']} has the better scoring margin."
    else:
        edge_team = "Even"
        reason = "Both teams look very similar based on recent games."

    home_note = None
    if home_team and home_team in {team_a['name'], team_b['name']}:
        home_note = f"Home-court context: {home_team} was selected as the home team."

    return {
        "team_a": team_a,
        "team_b": team_b,
        "edge_team": edge_team,
        "reason": reason,
        "home_note": home_note,
    }



    