# NBA Matchup Analyzer
## Overview

**NBA Matchup Analyzer** allows users to select two NBA teams and analyze their recent performance.

The application fetches NBA game data from the **BALLDONTLIE API** free tier for now, calculates recent metrics, and applies a a rule based scoring model to determine which team has the stronger matchup profile. It assigns each team a "matchup score" and the teaam with the highest matchup score would be favored to win head-to-head. The analysis also displays a confidence score based on how different the matchup score are between the two teams. It also provides an explanation in English as to why one team was favored over the other.

This project was built to combine my favorite sport/interest and practice the following: 

- Python
- Flask
- API integration (REST API)
- Data processing
- Backend

---

## Features

- Select two NBA teams from dropdown menus
- Choose an optional home team
- Fetch recent NBA game data from an external API
- Calculate recent performance metrics, including:
  - Recent wins and losses
  - Average points scored
  - Average points allowed
  - Point differential
- Generate a matchup score for each team
- Display a favored team and confidence level
- Provide a plain-English explanation for the result
- Handle API errors and rate limits
- History dashboard for previous analysis with search/filter/delete optiions

## Tech Stack
- Python
- Flash
- HTML/CSS
- BALLDONTLIE API
- Jinja2

## How It Works
1. The user first selects two distinct NBA teams
2. The app uses the BALLDONTLIE API to retrieve team and game data
3. Recent games are processed for each team
4. The app calculates the metrics retrieved from the games
5. A rule based prediction model calculates a matchup score using those metrics
6. The results page displays the favored team, the confidence level, matchup score, score differentials, recent games played for both teams

## How to Run It Locally

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/nba-matchup-analyzer.git
cd nba-matchup-analyzer
```

### 2. Create a Virtual Environment

#### On Windows

```bash
py -3 -m venv .venv
.venv\Scripts\activate
```

#### On macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Your Environment File

Create a `.env` file in the project root and add your BALLDONTLIE API key:

```env
BALLDONTLIE_API_KEY=your_api_key_here
```

You can use `.env.example` as a reference.

### 5. Run the Application

```bash
flask --app app run --debug
```

Then open the application in your browser:

```text
http://127.0.0.1:5000
```

## BALLDONTLIE API Setup

This project uses the free tier of the [BALLDONTLIE API](https://www.balldontlie.io/).

1. Create an account.
2. Go to **Account > API Key**.
3. Copy your free API key.
4. Add it to your `.env` file:

```env
BALLDONTLIE_API_KEY=your_api_key_here
```



## Future Improvements
- Add head-to-head matchup history between the two selected teams
- Replace the rule-based scoring model with a smarter machine learning oriented model
- Change the simple English explanation for the favorite team to an LLM model that better synthesizes (still in a short format) why one of the selected teams is favored.
- Upgrade to the BALLDONTLIE paid tier to fetch more data like offensive rating, defensive rating, star player injuries, etc which would improve the matchup score accuracy
- Select different numbers of recent games played
- Deploy the app online


