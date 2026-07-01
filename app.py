import requests

from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv

from database import init_db, save_matchup_result, get_recent_matchups, delete_matchup
from services.nba_api import get_team_lookup, build_team_summary, compare_recent_form
from utils.predictor import build_matchup_result


load_dotenv()

app = Flask(__name__)
init_db()

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

    if home_team not in [team_a_name, team_b_name]:
       home_team = None

    if not team_a_name or not team_b_name:
        return "Please select both teams.", 400

    if team_a_name == team_b_name:
        return "Please choose two different teams.", 400

    try: 
        team_lookup = get_team_lookup()
        team_a_summary = build_team_summary(team_a_name, team_lookup)
        team_b_summary = build_team_summary(team_b_name, team_lookup)

        matchup = build_matchup_result(team_a_summary, team_b_summary, home_team)

        save_matchup_result(matchup)
        
        return render_template("result.html", matchup=matchup)
    
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 500

        if status_code == 401:
            return render_template(
                "error.html",
                message="The NBA API key is missing, invalid, or does not have access to this endpoint.",
                suggestion="Check your .env file and make sure BALLDONTLIE_API_KEY is correct."
            ), 401

        if status_code == 429:
            return render_template(
                "error.html",
                message="The NBA API rate limit was reached.",
                suggestion="Wait about a minute, then try again."
            ), 429

        return render_template(
            "error.html",
            message=f"NBA API request failed with status code {status_code}.",
            suggestion="Try again later or choose a different matchup."
        ), 500

    except ValueError as e:
        return render_template(
            "error.html",
            message=str(e),
            suggestion="Go back and try a different matchup."
        ), 400

    except Exception as e:
        return render_template(
            "error.html",
            message="An unexpected error occurred while analyzing the matchup.",
            suggestion=str(e)
        ), 500
    
@app.route("/history", methods=["GET"])
def history():
    matchups = get_recent_matchups()
    return render_template("history.html", matchups=matchups)

@app.route("/history/<int:matchup_id>/delete", methods=["POST"])
def delete_history_item(matchup_id):
    delete_matchup(matchup_id)
    return redirect(url_for("history"))
        

if __name__ == "__main__":
    app.run(debug=True)