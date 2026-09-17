"""Scoring charts must represent the existing analyzed games without changing them."""

from copy import deepcopy
import math
import re
import unittest

from utils.charts import build_scoring_trends


def team_summary(name, scores, allowed):
    games = [
        {
            "date": f"2026-09-{index + 1:02}",
            "opponent": f"Fixture Opponent {index + 1}",
            "location": "Home" if index % 2 == 0 else "Away",
            "result": "W" if scored > conceded else "L",
            "scored": scored,
            "allowed": conceded,
        }
        for index, (scored, conceded) in enumerate(zip(scores, allowed))
    ]
    return {"name": name, "games_used": len(games), "recent_games": list(reversed(games))}


def svg_points(value):
    numbers = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value)
    return [tuple(map(float, numbers[index:index + 2])) for index in range(0, len(numbers), 2)]


class ScoringTrendTests(unittest.TestCase):
    def assert_valid_coordinates(self, chart):
        self.assertGreater(chart["y_max"], chart["y_min"])
        scored_points = svg_points(chart["scored_points"])
        allowed_points = svg_points(chart["allowed_points"])
        self.assertEqual(len(scored_points), len(chart["games"]))
        self.assertEqual(len(allowed_points), len(chart["games"]))
        for game, scored_point, allowed_point in zip(chart["games"], scored_points, allowed_points):
            self.assertTrue(all(math.isfinite(value) for value in scored_point + allowed_point))
            self.assertGreaterEqual(game["x"], 48)
            self.assertLessEqual(game["x"], 580)
            for metric, coordinate, point in [
                ("scored", "scored_y", scored_point),
                ("allowed", "allowed_y", allowed_point),
            ]:
                with self.subTest(date=game["date"], metric=metric):
                    self.assertGreaterEqual(game[coordinate], 24)
                    self.assertLessEqual(game[coordinate], 250)
                    expected_y = 250 - (
                        (game[metric] - chart["y_min"])
                        / (chart["y_max"] - chart["y_min"])
                    ) * (250 - 24)
                    self.assertAlmostEqual(game[coordinate], expected_y, delta=0.02)
                    self.assertAlmostEqual(point[0], game["x"], delta=0.02)
                    self.assertAlmostEqual(point[1], game[coordinate], delta=0.02)

    def test_selected_game_counts_preserve_values_order_and_inputs(self):
        for size in [5, 10, 15]:
            with self.subTest(size=size):
                team_a = team_summary(
                    "Los Angeles Lakers", [95 + index % 7 for index in range(size)],
                    [90 + index % 9 for index in range(size)],
                )
                team_b = team_summary(
                    "Boston Celtics", [100 + index % 11 for index in range(size)],
                    [98 + index % 5 for index in range(size)],
                )
                # Supply a mixed order too, so reversing the input alone is insufficient.
                team_b["recent_games"] = (
                    team_b["recent_games"][::2] + team_b["recent_games"][1::2]
                )
                before = deepcopy([team_a, team_b])
                charts = build_scoring_trends(team_a, team_b)
                self.assertEqual(len(charts), 2)
                for source, chart in zip([team_a, team_b], charts):
                    self.assertEqual(len(chart["games"]), size)
                    self.assertIsNot(chart["games"], source["recent_games"])
                    expected = sorted(source["recent_games"], key=lambda game: game["date"])
                    for original, plotted in zip(expected, chart["games"]):
                        self.assertIsNot(plotted, original)
                        self.assertEqual({key: plotted[key] for key in original}, original)
                    xs = [game["x"] for game in chart["games"]]
                    self.assertEqual(xs, sorted(set(xs)))
                    self.assert_valid_coordinates(chart)
                self.assertEqual([team_a, team_b], before)

    def test_both_teams_share_padded_rounded_bounds(self):
        team_a = team_summary("Toronto Raptors", [72, 83], [91, 88])
        team_b = team_summary("Golden State Warriors", [132, 145, 150], [157, 139, 148])
        charts = build_scoring_trends(team_a, team_b)
        for chart in charts:
            self.assertGreaterEqual(chart["y_min"], 0)
            self.assertLessEqual(chart["y_min"], 60)
            self.assertGreaterEqual(chart["y_max"], 170)
            self.assertEqual(chart["y_min"] % 10, 0)
            self.assertEqual(chart["y_max"] % 10, 0)
            self.assert_valid_coordinates(chart)
        self.assertEqual(len(charts[0]["games"]), 2)
        self.assertEqual(len(charts[1]["games"]), 3)
        self.assertEqual(charts[0]["y_min"], charts[1]["y_min"])
        self.assertEqual(charts[0]["y_max"], charts[1]["y_max"])
        self.assertEqual(charts[0]["y_ticks"], charts[1]["y_ticks"])

    def test_ticks_show_endpoint_dates_and_use_the_chart_scale(self):
        team_a = team_summary("A", [20 + index * 16 for index in range(15)], [75] * 15)
        team_b = team_summary("B", [100] * 15, [110] * 15)
        for chart in build_scoring_trends(team_a, team_b):
            x_ticks = chart["x_ticks"]
            self.assertLessEqual(len(x_ticks), 6)
            self.assertEqual(x_ticks[0]["label"], chart["games"][0]["date"][5:])
            self.assertEqual(x_ticks[-1]["label"], chart["games"][-1]["date"][5:])
            self.assertEqual(x_ticks[0]["x"], chart["games"][0]["x"])
            self.assertEqual(x_ticks[-1]["x"], chart["games"][-1]["x"])
            for tick in x_ticks:
                self.assertRegex(tick["label"], r"^\d{2}-\d{2}$")
                self.assertIn(tick["x"], [game["x"] for game in chart["games"]])

            y_ticks = chart["y_ticks"]
            self.assertGreaterEqual(len(y_ticks), 2)
            self.assertLessEqual(len(y_ticks), 8)
            values = sorted(tick["value"] for tick in y_ticks)
            self.assertTrue(all(right - left >= 10 for left, right in zip(values, values[1:])))
            for tick in y_ticks:
                self.assertGreaterEqual(tick["value"], chart["y_min"])
                self.assertLessEqual(tick["value"], chart["y_max"])
                expected_y = 250 - (
                    (tick["value"] - chart["y_min"])
                    / (chart["y_max"] - chart["y_min"])
                ) * (250 - 24)
                self.assertAlmostEqual(tick["y"], expected_y, delta=0.02)

    def test_equal_zero_and_small_scores_have_finite_coordinates(self):
        for score in [0, 2, 100]:
            with self.subTest(score=score):
                team_a = team_summary("A", [score] * 5, [score] * 5)
                team_b = team_summary("B", [score] * 5, [score] * 5)
                for chart in build_scoring_trends(team_a, team_b):
                    self.assertGreaterEqual(chart["y_min"], 0)
                    self.assertLessEqual(chart["y_min"], score)
                    self.assertGreater(chart["y_max"], score)
                    self.assert_valid_coordinates(chart)
                    self.assertEqual(chart["scored_points"], chart["allowed_points"])
                    self.assertEqual(len({game["scored_y"] for game in chart["games"]}), 1)

    def test_single_game_is_centered(self):
        charts = build_scoring_trends(
            team_summary("A", [110], [105]), team_summary("B", [98], [109]),
        )
        for chart in charts:
            self.assertEqual(len(chart["games"]), 1)
            self.assertAlmostEqual(chart["games"][0]["x"], (48 + 580) / 2)
            self.assertEqual(len(chart["x_ticks"]), 1)
            self.assertEqual(chart["x_ticks"][0]["label"], "09-01")
            self.assert_valid_coordinates(chart)

    def test_empty_teams_have_safe_empty_charts(self):
        team_a = team_summary("A", [], [])
        team_b = team_summary("B", [], [])
        before = deepcopy([team_a, team_b])
        charts = build_scoring_trends(team_a, team_b)
        self.assertEqual(len(charts), 2)
        for chart in charts:
            self.assertEqual(chart["games"], [])
            self.assertEqual(chart["scored_points"], "")
            self.assertEqual(chart["allowed_points"], "")
            self.assertEqual(chart["x_ticks"], [])
            self.assertGreaterEqual(chart["y_min"], 0)
            self.assert_valid_coordinates(chart)
        self.assertEqual([team_a, team_b], before)

    def test_one_empty_team_still_uses_the_other_teams_scale(self):
        charts = build_scoring_trends(
            team_summary("A", [], []), team_summary("B", [115, 130], [90, 112]),
        )
        self.assertEqual(charts[0]["games"], [])
        for chart in charts:
            self.assertGreaterEqual(chart["y_min"], 0)
            self.assertLessEqual(chart["y_min"], 80)
            self.assertGreaterEqual(chart["y_max"], 140)
            self.assert_valid_coordinates(chart)
        self.assertEqual(charts[0]["y_min"], charts[1]["y_min"])
        self.assertEqual(charts[0]["y_max"], charts[1]["y_max"])


if __name__ == "__main__":
    unittest.main()
