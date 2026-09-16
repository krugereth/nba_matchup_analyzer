import unittest
from unittest.mock import patch

from utils.predictor import build_matchup_result, calculate_team_score


class PredictorTests(unittest.TestCase):
    def setUp(self):
        self.team_a = {
            "name": "Los Angeles Lakers", "wins": 6, "losses": 4,
            "avg_points_for": 110, "avg_points_against": 108, "point_diff": 2,
        }
        self.team_b = dict(self.team_a, name="Boston Celtics")

    def test_formula_and_home_adjustment(self):
        self.assertEqual(calculate_team_score(self.team_a), 33.8)
        self.assertEqual(calculate_team_score(self.team_a, self.team_a["name"]), 36.8)
        result = build_matchup_result(self.team_a, self.team_b, self.team_b["name"])
        self.assertEqual(result["favored_team"], self.team_b["name"])
        self.assertEqual(result["score_difference"], 3)
        self.assertEqual(result["confidence"], "Low")
        self.assertIn("Boston Celtics receives the home-court adjustment", result["explanation"])

    def test_tie_explanation_never_favors_even(self):
        # Different metrics can cancel out to the same model score.
        self.team_b.update(wins=5, point_diff=4)
        result = build_matchup_result(self.team_a, self.team_b)
        self.assertEqual(result["favored_team"], "Even")
        self.assertEqual(result["confidence"], "Low")
        self.assertIn("scores are even", result["explanation"])
        self.assertNotIn("Even are favored", result["explanation"])

    def test_explanation_reports_opposing_edges_as_comparisons(self):
        self.team_b.update(wins=7, avg_points_for=100, avg_points_against=110, point_diff=-10)
        result = build_matchup_result(self.team_a, self.team_b)
        self.assertEqual(result["favored_team"], self.team_a["name"])
        self.assertIn("Boston Celtics has more wins in the games analyzed", result["explanation"])
        self.assertIn("Los Angeles Lakers has allowed fewer points", result["explanation"])
        self.assertNotIn("favored because Boston Celtics", result["explanation"])

    def test_unequal_sample_sizes_describe_win_counts(self):
        self.team_a.update(wins=3, losses=0, games_used=3)
        self.team_b.update(wins=4, losses=6, games_used=10)
        result = build_matchup_result(self.team_a, self.team_b)
        self.assertIn("Boston Celtics has more wins in the games analyzed", result["explanation"])
        self.assertNotIn("stronger recent record", result["explanation"])

    def test_confidence_matches_displayed_difference_at_boundaries(self):
        for scores, difference, expected in [
            ([8.1, 4.1], 4, "Medium"),
            ([12.2, 4.2], 8, "High"),
            ([8.09, 4.1], 3.99, "Low"),
            ([12.19, 4.2], 7.99, "Medium"),
        ]:
            with self.subTest(scores=scores), patch(
                "utils.predictor.calculate_team_score", side_effect=scores
            ):
                result = build_matchup_result(self.team_a, self.team_b)
                self.assertEqual(result["score_difference"], difference)
                self.assertEqual(result["confidence"], expected)


if __name__ == "__main__":
    unittest.main()
