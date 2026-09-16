def calculate_team_score(team_summary, home_team=None):
    wins_score = team_summary["wins"] * 4
    point_diff_score = team_summary["point_diff"] * 2
    offense_score = team_summary["avg_points_for"] * 0.2
    defense_score = -team_summary["avg_points_against"] * 0.15

    home_bonus = 0
    if home_team and home_team == team_summary["name"]:
        home_bonus = 3

    total_score = wins_score + point_diff_score + offense_score + defense_score + home_bonus
    return round(total_score, 2)


def get_confidence(score_difference):
    if score_difference >= 8:
        return "High"
    if score_difference >= 4:
        return "Medium"
    return "Low"


def build_explanation(team_a, team_b, favored_team, home_team=None):
    reasons = []

    if team_a["wins"] != team_b["wins"]:
        better_record_team = team_a["name"] if team_a["wins"] > team_b["wins"] else team_b["name"]
        reasons.append(f"{better_record_team} has more wins in the games analyzed")

    if team_a["point_diff"] != team_b["point_diff"]:
        better_diff_team = team_a["name"] if team_a["point_diff"] > team_b["point_diff"] else team_b["name"]
        reasons.append(f"{better_diff_team} has the better point differential")

    if team_a["avg_points_for"] != team_b["avg_points_for"]:
        better_offense_team = team_a["name"] if team_a["avg_points_for"] > team_b["avg_points_for"] else team_b["name"]
        reasons.append(f"{better_offense_team} has the stronger recent offense")

    if team_a["avg_points_against"] != team_b["avg_points_against"]:
        better_defense_team = team_a["name"] if team_a["avg_points_against"] < team_b["avg_points_against"] else team_b["name"]
        reasons.append(f"{better_defense_team} has allowed fewer points recently")

    if home_team in {team_a["name"], team_b["name"]}:
        reasons.append(f"{home_team} receives the home-court adjustment")

    if favored_team == "Even":
        summary = "The rule-based matchup scores are even."
    else:
        summary = f"{favored_team} is favored by the rule-based scoring model."

    if not reasons:
        return summary + " Both teams have identical recent-form metrics."

    return summary + " " + ". ".join(reasons) + "."


def build_matchup_result(team_a, team_b, home_team=None):
    team_a_score = calculate_team_score(team_a, home_team)
    team_b_score = calculate_team_score(team_b, home_team)

    if team_a_score > team_b_score:
        favored_team = team_a["name"]
        score_difference = team_a_score - team_b_score
    elif team_b_score > team_a_score:
        favored_team = team_b["name"]
        score_difference = team_b_score - team_a_score
    else:
        favored_team = "Even"
        score_difference = 0

    score_difference = round(score_difference, 2)
    confidence = get_confidence(score_difference)
    explanation = build_explanation(team_a, team_b, favored_team, home_team)

    return {
        "team_a": team_a,
        "team_b": team_b,
        "team_a_score": team_a_score,
        "team_b_score": team_b_score,
        "favored_team": favored_team,
        "confidence": confidence,
        "score_difference": score_difference,
        "home_team": home_team,
        "explanation": explanation,
    }
