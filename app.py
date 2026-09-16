import requests

from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv

from database import init_db, save_matchup_result, get_recent_matchups, delete_matchup
from services.nba_api import APIConfigurationError, get_team_lookup, build_team_summary
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
GAMES_LIMIT_OPTIONS = {5, 10, 15}


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", teams=NBA_TEAMS)


@app.route("/analyze", methods=["POST"])
def analyze():
    team_a_name = request.form.get("team_a")
    team_b_name = request.form.get("team_b")
    home_team = request.form.get("home_team")
    games_limit_value = request.form.get("games_limit", "10")

    if not team_a_name or not team_b_name:
        return render_template(
            "error.html",
            message="Please select two teams before analyzing a matchup.",
            suggestion="Go back and choose both Team A and Team B."
        ), 400

    if team_a_name == team_b_name:
        return render_template(
            "error.html",
            message="A team cannot be compared against itself.",
            suggestion="Please choose two different teams."
        ), 400

    if team_a_name not in NBA_TEAMS or team_b_name not in NBA_TEAMS:
        return render_template(
            "error.html",
            message="Please choose two NBA teams from the available options.",
            suggestion="Go back and select both teams using the dropdown menus."
        ), 400

    if games_limit_value not in {str(limit) for limit in GAMES_LIMIT_OPTIONS}:
        return render_template(
            "error.html",
            message="Please choose 5, 10, or 15 recent games.",
            suggestion="Go back and select a valid sample size."
        ), 400

    games_limit = int(games_limit_value)

    if home_team not in [team_a_name, team_b_name]:
        home_team = None

    try:
        team_lookup = get_team_lookup()
        team_a_summary = build_team_summary(team_a_name, team_lookup, games_limit)
        team_b_summary = build_team_summary(team_b_name, team_lookup, games_limit)

        matchup = build_matchup_result(team_a_summary, team_b_summary, home_team)

        save_matchup_result(matchup)

        return render_template("result.html", matchup=matchup)

    except APIConfigurationError:
        return render_template(
            "error.html",
            message="The NBA API key has not been configured.",
            suggestion="Set BALLDONTLIE_API_KEY in your .env file, restart the app, and try again."
        ), 503

    except requests.exceptions.Timeout:
        return render_template(
            "error.html",
            message="The NBA data service took too long to respond.",
            suggestion="Please wait a moment and try the matchup again."
        ), 504

    except requests.exceptions.ConnectionError:
        return render_template(
            "error.html",
            message="The NBA data service could not be reached.",
            suggestion="Check your internet connection and try again shortly."
        ), 502

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

    except requests.exceptions.RequestException:
        return render_template(
            "error.html",
            message="The request to the NBA data service could not be completed.",
            suggestion="Please try the matchup again shortly."
        ), 502

    except ValueError as e:
        return render_template(
            "error.html",
            message=str(e),
            suggestion="Go back and try a different matchup."
        ), 400

    except Exception:
        app.logger.exception("Unexpected error while analyzing a matchup.")
        return render_template(
            "error.html",
            message="An unexpected error occurred while analyzing the matchup.",
            suggestion="Please try again. If the problem continues, check the application logs."
        ), 500


@app.route("/history", methods=["GET"])
def history():
    team_query = request.args.get("team", "").strip()
    confidence_filter = request.args.get("confidence", "").strip()

    if confidence_filter not in ["Low", "Medium", "High"]:
        confidence_filter = None

    matchups = get_recent_matchups(
        team_query=team_query,
        confidence_filter=confidence_filter
    )

    return render_template(
        "history.html",
        matchups=matchups,
        team_query=team_query,
        confidence_filter=confidence_filter
    )


@app.route("/history/<int:matchup_id>/delete", methods=["POST"])
def delete_history_item(matchup_id):
    delete_matchup(matchup_id)
    return redirect(url_for("history"))


if __name__ == "__main__":
    app.run(debug=True)
