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
- Handle API errors and rate limits with user-friendly messages
- Responsive results page layout
