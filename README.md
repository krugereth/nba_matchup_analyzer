# NBA Matchup Analyzer

A **Flask web application** that compares two NBA teams using recent game performance and generates a matchup analysis with a favored team, confidence level, score difference, and explanation.

---

## Overview

**NBA Matchup Analyzer** allows users to select two NBA teams and analyze their recent performance.

The application fetches NBA game data from the **BALLDONTLIE API**, calculates recent-form metrics, and applies a rule-based scoring model to determine which team has the stronger matchup profile.

This project was built to practice:

- Python
- Flask
- API integration
- Data processing
- Backend project structure

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
