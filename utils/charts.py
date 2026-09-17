"""Prepare SVG coordinates from the games already used in a matchup."""

from math import ceil, floor


def build_scoring_trends(team_a, team_b):
    teams = (team_a, team_b)
    values = [
        game[key]
        for team in teams
        for game in team["recent_games"]
        for key in ("scored", "allowed")
    ]
    # Both charts use one padded points scale, including when their samples differ.
    y_min = max(0, floor((min(values, default=0) - 10) / 10) * 10)
    y_max = ceil((max(values, default=0) + 10) / 10) * 10
    tick_step = max(10, ceil((y_max - y_min) / 60) * 10)
    y_max = y_min + ceil((y_max - y_min) / tick_step) * tick_step

    def point_y(value):
        return round(250 - (value - y_min) / (y_max - y_min) * 226, 2)

    y_ticks = [
        {"value": value, "y": point_y(value)}
        for value in range(y_min, y_max + 1, tick_step)
    ]
    charts = []
    for team in teams:
        # Do not reverse the newest-first game list used by the existing tables.
        source = sorted(team["recent_games"], key=lambda game: game["date"])
        games = [
            {
                **game,
                "x": round(48 + index / (len(source) - 1) * 532, 2) if len(source) > 1 else 314,
                "scored_y": point_y(game["scored"]),
                "allowed_y": point_y(game["allowed"]),
            }
            for index, game in enumerate(source)
        ]
        # Keep date labels readable at all supported sample sizes, with both endpoints.
        tick_count = min(5, len(games))
        tick_indices = [
            round(index * (len(games) - 1) / (tick_count - 1)) if tick_count > 1 else 0
            for index in range(tick_count)
        ]
        charts.append({
            "name": team["name"],
            "games": games,
            "scored_points": " ".join(f"{game['x']},{game['scored_y']}" for game in games),
            "allowed_points": " ".join(f"{game['x']},{game['allowed_y']}" for game in games),
            "x_ticks": [{"x": games[index]["x"], "label": games[index]["date"][5:10]} for index in tick_indices],
            "y_ticks": y_ticks,
            "y_min": y_min,
            "y_max": y_max,
        })
    return charts
