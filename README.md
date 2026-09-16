# NBA Matchup Analyzer

A Flask sports analytics app that compares two NBA teams using recent game results. It calculates recent-form statistics, applies a transparent rule-based scoring model, explains the comparison, and saves analyses in SQLite.

The project combines an interest in basketball with practice in Python, REST API integration, data processing, backend development, and responsive web design. Its matchup score is a comparison rating, not a predicted final game score.

## Features

- Select two different NBA teams, choose the last 5, 10, or 15 completed games to analyze, and optionally give one home-court context.
- Compare recent record, average points scored and allowed, and point differential.
- View each team's matchup score, the favored team, a confidence label, and an explanation of the comparison.
- Inspect the actual games used in the analysis, including date, opponent, location, win/loss badge, and score from the selected team's perspective.
- Save successful analyses automatically; search history by team name, filter by confidence, and delete entries.
- View team logos in a dark dashboard with responsive cards and horizontally scrollable recent-game tables.
- Receive helpful messages for invalid selections, insufficient data, missing or invalid API credentials, rate limits, and connection errors.

The home-team dropdown only offers the two selected teams. The server also rejects a same-team matchup and invalid team names, so the form's browser checks are not the only validation.

## How the analytics work

The [BALLDONTLIE NBA API](https://nba.balldontlie.io/#get-all-games) supplies raw game results. The app retrieves all pages of regular-season games in the previous 300 days, keeps completed games, and sorts them newest first. You can select the last 5, 10, or 15 games per team; the default is 10. At least 3 completed games are required. If fewer than the requested number are available, the app uses the completed games it found and shows the actual count.

For each game, Python determines which score belongs to the selected team and calculates:

```text
Recent record          = wins and losses in the selected games
Average points scored  = total points scored / games used
Average points allowed = total points allowed / games used
Point differential     = (total scored - total allowed) / games used
```

These averages are rounded to one decimal place. The recent-games tables contain the same games used in these calculations; scores always show the analyzed team's points first, including away games.

`utils/predictor.py` calculates the matchup score from those metrics:

```text
Matchup score = (wins × 4)
              + (point differential × 2)
              + (average points scored × 0.20)
              - (average points allowed × 0.15)
              + home-court bonus

Home-court bonus = 3 for the selected home team; otherwise 0
```

Scores are rounded to two decimal places. The higher score determines the favored team; equal scores produce an `Even` result. Confidence depends on the absolute difference between the scores:

| Score difference | Confidence |
| --- | --- |
| 8 or more | High |
| 4 to less than 8 | Medium |
| Less than 4 | Low |

These are heuristic confidence labels, not calibrated probabilities. A matchup score is an analytical rating, not a predicted final game score. The model uses fixed rules rather than machine learning.

## Tech stack and structure

Python, Flask, Jinja2, SQLite (`sqlite3`), HTML/CSS/JavaScript, `requests`, `python-dotenv`, and the BALLDONTLIE API.

```text
app.py                 Flask routes, validation, and error handling
database.py            SQLite storage, history queries, and deletion
services/nba_api.py    API requests, caching, logos, and game aggregation
utils/predictor.py     Matchup scoring, confidence, and explanations
templates/             Home, result, history, error, and base templates
static/styles.css      Dashboard and responsive styling
tests/                 Automated regression tests
.env.example           API-key placeholder
requirements.txt       Python dependencies
```

## Local setup (Windows PowerShell)

Install Python 3 and Git, then clone the project and install its dependencies:

```powershell
git clone https://github.com/krugereth/nba_matchup_analyzer.git nba-matchup-analyzer
cd nba-matchup-analyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Get an API key from [BALLDONTLIE](https://www.balldontlie.io/) and replace the placeholder in your local `.env` file:

```dotenv
BALLDONTLIE_API_KEY=your_api_key_here
```

Start the development server from the project directory:

```powershell
python -m flask --app app run --debug
```

Open <http://127.0.0.1:5000>. SQLite creates `matchups.db` automatically on startup. `.env`, the database, the virtual environment, and Python cache files are ignored by Git. Restart the app after changing the API key.

If you prefer not to activate the virtual environment, run its Python directly for the install and server commands:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app run --debug
```

Stop the development server with `Ctrl+C`.

## Using the app

1. On the home page, select Team A and Team B, choose 5, 10, or 15 recent games, and optionally choose which team is at home. Then click **Analyze Matchup**.
2. On the results page, compare both teams' recent statistics, the favored team, confidence label, explanation, and the two **Recent Games Used in Analysis** tables. A `W` or `L` describes the team named above that table.
3. Open **History** to review saved analyses. Search for a team, filter by confidence, clear the filters, or delete an entry.

Each successful analysis adds a new history entry. Deleting one removes it from the local SQLite database.

## Testing

With dependencies installed, run:

```powershell
python -m unittest discover -s tests -v
```

The tests use Python's standard-library `unittest`, mocked API responses, and temporary SQLite databases. They exercise game selection and aggregation, scoring, request validation, API error handling, and history behavior without a live API key or changes to your saved history.

For a manual smoke test with an API key:

1. Analyze Lakers vs. Celtics, then another pair, with 5, 10, and 15 games and both with and without a home team.
2. Check that home-team choices follow the selected teams and duplicate team selections are prevented.
3. Confirm each recent-games table matches its team's record, averages, and point differential. Away-game scores should still show the selected team's points first.
4. Open `/history`; verify the saved analysis, team search, confidence filter, clear-filters action, and deletion. Check the empty state using a fresh local database or after deleting test entries.
5. At desktop and narrow mobile widths, check card stacking, readable text, and horizontal scrolling within the recent-game tables.

## Data handling and limitations

- Team lookup is cached for the life of the process. Recent-game requests use a bounded in-memory cache with 15-minute time windows and the current date in the cache key. Crossing a window boundary, changing dates, or restarting the app causes fresh requests.
- Data availability depends on BALLDONTLIE access and rate limits. Pagination can require multiple requests, and caching does not eliminate rate limits.
- Teams can have different sample sizes when fewer than the requested number of completed games are available. The wins component uses the win count, so sample size affects the score.
- The fixed weights have not been validated for predictive accuracy. The model does not account for injuries, lineups, opponent strength, or future outcomes.
- History stores a summary of each analysis, not the full game list. The history page shows the latest 20 matching entries; older entries remain in SQLite.
- Team logos load from ESPN's external image CDN. SQLite history is stored locally in `matchups.db`.

## Future features

These are ideas for later development and are **not implemented yet**:

- Display each component of the matchup score beside the total, making the rule-based calculation easier to inspect.
- Add history summary statistics, such as total analyses and confidence counts.
- Add screenshots of the home page, results, recent-games tables, and history page after the final visual review.
- Consider deployment after planning secure API-key configuration and persistent history storage for the hosting environment.
