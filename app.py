from flask import Flask, render_template, request
from dotenv import load_dotenv

from services.nba_api import get_team_lookup, build_team_summary, compare_recent_form
from utils.predictor import build_matchup_result


load_dotenv()

app = Flask(__name__)

NBA_TEAMS = [
    "Atlanta Hawks",
    "Boston Celtics",
    "Brooklyn Nets",
    "Charlotte Hornets",
    "Chicago Bulls",
    "Cleveland Cavaliers",
    "Dallas Mavericks",
    "Denver Nuggets",
    "Detroit Pistons",
    "Golden State Warriors",
    "Houston Rockets",
    "Indiana Pacers",
    "Los Angeles Clippers",
    "Los Angeles Lakers",
    "Memphis Grizzlies",
    "Miami Heat",
    "Milwaukee Bucks",
    "Minnesota Timberwolves",
    "New Orleans Pelicans",
    "New York Knicks",
    "Oklahoma City Thunder",
    "Orlando Magic",
    "Philadelphia 76ers",
    "Phoenix Suns",
    "Portland Trail Blazers",
    "Sacramento Kings",
    "San Antonio Spurs",
    "Toronto Raptors",
    "Utah Jazz",
    "Washington Wizards",
]

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", teams=NBA_TEAMS)

@app.route("/analyze", methods=["POST"])
def analyze():
    team_a_name = request.form.get("team_a")
    team_b_name = request.form.get("team_b")
    home_team = request.form.get("home_team")

    if not team_a_name or not team_b_name:
        return "Please select both teams.", 400

    if team_a_name == team_b_name:
        return "Please choose two different teams.", 400

    try: 
        team_lookup = get_team_lookup()
        team_a_summary = build_team_summary(team_a_name, team_lookup)
        team_b_summary = build_team_summary(team_b_name, team_lookup)

        matchup = build_matchup_result(team_a_summary, team_b_summary, home_team)

        return render_template("result.html", matchup=matchup)
    
    except Exception as e: 
        return f"Error loading matchup data: {e}", 500
        

if __name__ == "__main__":
    app.run(debug=True)