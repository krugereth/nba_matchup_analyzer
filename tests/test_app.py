"""Route regressions using synthetic summaries and an isolated SQLite database."""

import importlib
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flask import template_rendered
import requests

import database


def team_summary(name, team_id):
    games = [
        {"date": "2026-09-12", "opponent": "Fixture Opponent One",
         "location": "Home", "result": "W", "scored": 110, "allowed": 100},
        {"date": "2026-09-10", "opponent": "Fixture Opponent Two",
         "location": "Away", "result": "L", "scored": 95, "allowed": 105},
        {"date": "2026-09-08", "opponent": "Fixture Opponent Three",
         "location": "Home", "result": "W", "scored": 110, "allowed": 95},
    ]
    return {
        "name": name, "team_id": team_id, "logo_url": "", "games_used": 3,
        "wins": 2, "losses": 1, "avg_points_for": 105.0,
        "avg_points_against": 100.0, "point_diff": 5.0, "recent_games": games,
    }


class AppRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory(prefix="nba-route-tests-")
        cls.database_patch = patch.object(
            database, "DATABASE_NAME",
            str(Path(cls.temporary_directory.name) / "test-matchups.db"),
        )
        cls.database_patch.start()
        # app initializes SQLite during import: patch the path before importing it.
        cls.web = importlib.import_module("app")
        database.init_db()
        cls.web.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.database_patch.stop()
        cls.temporary_directory.cleanup()

    def setUp(self):
        with closing(database.get_connection()) as connection:
            connection.execute("DELETE FROM matchup_history")
            connection.commit()
        self.client = self.web.app.test_client()
        self.rendered = []
        template_rendered.connect(self.record_template, self.web.app)
        self.addCleanup(template_rendered.disconnect, self.record_template, self.web.app)
        self.team_names = [
            "Los Angeles Lakers", "Boston Celtics",
            "Toronto Raptors", "Golden State Warriors",
        ]
        self.summaries = {
            name: team_summary(name, index)
            for index, name in enumerate(self.team_names, start=1)
        }
        self.lookup = self.enterContext(patch.object(
            self.web, "get_team_lookup",
            return_value={name: value["team_id"] for name, value in self.summaries.items()},
        ))
        self.summary = self.enterContext(patch.object(
            self.web, "build_team_summary",
            side_effect=lambda name, lookup, games_limit: self.summaries[name],
        ))

    def record_template(self, sender, template, context, **extra):
        self.rendered.append((template.name, context))

    def analyze(self, team_a="Los Angeles Lakers", team_b="Boston Celtics", home_team="", games_limit=None):
        form = {"team_a": team_a, "team_b": team_b, "home_team": home_team}
        if games_limit is not None:
            form["games_limit"] = games_limit
        return self.client.post("/analyze", data={
            **form,
        })

    def assert_error(self, response, status, expected_text):
        self.assertEqual(response.status_code, status)
        self.assertEqual(self.rendered[-1][0], "error.html")
        self.assertIn(expected_text, response.get_data(as_text=True))
        self.assertEqual(database.get_recent_matchups(), [])

    def test_home_and_empty_history_render(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn('name="games_limit"', home.get_data(as_text=True))
        self.assertIn('<option value="10" selected>', home.get_data(as_text=True))
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 200)
        self.assertIn("No matchup history yet", response.get_data(as_text=True))

    def test_route_method_limits(self):
        self.assertEqual(self.client.get("/analyze").status_code, 405)
        self.assertEqual(self.client.get("/history/1/delete").status_code, 405)

    def test_requested_matchups_render_recent_games_and_home_bonus(self):
        for team_a, team_b in [self.team_names[:2], self.team_names[2:]]:
            neutral = None
            for home in ["", team_a, team_b]:
                with self.subTest(team_a=team_a, team_b=team_b, home=home):
                    response = self.analyze(team_a, team_b, home)
                    self.assertEqual(response.status_code, 200)
                    text = response.get_data(as_text=True)
                    self.assertIn(team_a, text)
                    self.assertIn(team_b, text)
                    self.assertEqual(text.count("<td>Fixture Opponent One</td>"), 2)
                    self.assertEqual(text.count("<td>Fixture Opponent Two</td>"), 2)
                    self.assertEqual(text.count("<td>Fixture Opponent Three</td>"), 2)
                    self.assertEqual(text.count("<td>2026-09-12</td>"), 2)
                    self.assertEqual(text.count('class="comparison-table recent-games-table"'), 2)
                    self.assertEqual(text.count('class="table-scroll"'), 2)
                    self.assertIn("110-100", text)
                    matchup = self.rendered[-1][1]["matchup"]
                    self.assertEqual(matchup["home_team"], home or None)
                    if home:
                        selected = "team_a" if home == team_a else "team_b"
                        other = "team_b" if home == team_a else "team_a"
                        self.assertEqual(
                            matchup[selected + "_score"] - neutral[selected + "_score"], 3,
                        )
                        self.assertEqual(matchup[other + "_score"], neutral[other + "_score"])
                    else:
                        neutral = matchup
        self.assertEqual(len(database.get_recent_matchups()), 6)

    def test_invalid_teams_are_rejected_before_api_access(self):
        forms = [
            {}, {"team_a": "Los Angeles Lakers"},
            {"team_a": "Los Angeles Lakers", "team_b": "Los Angeles Lakers"},
            {"team_a": "Unknown Team", "team_b": "Boston Celtics"},
            {"team_a": "Los Angeles Lakers", "team_b": "Unknown Team"},
        ]
        for form in forms:
            with self.subTest(form=form):
                response = self.client.post("/analyze", data=form)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.rendered[-1][0], "error.html")
        self.lookup.assert_not_called()
        self.summary.assert_not_called()
        self.assertEqual(database.get_recent_matchups(), [])

    def test_invalid_home_selection_is_neutral(self):
        response = self.analyze(home_team="Toronto Raptors")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.rendered[-1][1]["matchup"]["home_team"])

    def test_game_limit_is_passed_to_both_teams_with_default(self):
        for value, expected in [(None, 10), ("5", 5), ("10", 10), ("15", 15)]:
            with self.subTest(value=value):
                self.summary.reset_mock()
                response = self.analyze(games_limit=value)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.summary.call_count, 2)
                self.assertTrue(all(call.args[2] == expected for call in self.summary.call_args_list))

    def test_invalid_game_limits_fail_before_api_or_history_save(self):
        for value in ["", "0", "11", "-5", "5.0", "abc"]:
            with self.subTest(value=value):
                response = self.analyze(games_limit=value)
                self.assert_error(response, 400, "Please choose 5, 10, or 15 recent games")
        self.lookup.assert_not_called()
        self.summary.assert_not_called()

    def test_trends_render_selected_sample_in_chronological_order(self):
        def summary_for_limit(name, lookup, games_limit):
            summary = dict(self.summaries[name])
            summary["recent_games"] = [
                dict(summary["recent_games"][0], date=f"2026-09-{day:02d}", scored=100 + day)
                for day in range(15, 15 - games_limit, -1)
            ]
            summary["games_used"] = games_limit
            return summary

        self.summary.side_effect = summary_for_limit
        for limit in (5, 10, 15):
            with self.subTest(limit=limit):
                response = self.analyze(games_limit=str(limit))
                self.assertEqual(response.status_code, 200)
                text = response.get_data(as_text=True)
                context = self.rendered[-1][1]
                self.assertEqual(text.count('class="trend-chart"'), 2)
                self.assertEqual(text.count('data-detail='), 2 * limit)
                for chart, team_key in zip(context["scoring_trends"], ("team_a", "team_b")):
                    table_games = context["matchup"][team_key]["recent_games"]
                    self.assertEqual(len(chart["games"]), limit)
                    self.assertEqual([game["date"] for game in chart["games"]],
                                     [game["date"] for game in reversed(table_games)])
                    self.assertEqual([game["scored"] for game in chart["games"]],
                                     [game["scored"] for game in reversed(table_games)])

    def test_chart_game_details_escape_html(self):
        self.summaries["Los Angeles Lakers"]["recent_games"][0]["opponent"] = '<script>alert("x")</script>'
        response = self.analyze()
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertNotIn('<script>alert("x")</script>', text)
        self.assertIn('&lt;script&gt;', text)

    def test_missing_api_key_has_configuration_error(self):
        self.lookup.side_effect = self.web.APIConfigurationError("private diagnostic")
        response = self.analyze()
        self.assert_error(response, 503, "API key has not been configured")
        self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_http_api_errors_have_expected_status_and_message(self):
        for status, text in [
            (401, "API key is missing, invalid"),
            (429, "rate limit was reached"),
            (500, "status code 500"),
        ]:
            with self.subTest(status=status):
                upstream_response = requests.Response()
                upstream_response.status_code = status
                self.lookup.side_effect = requests.exceptions.HTTPError(
                    "private diagnostic", response=upstream_response,
                )
                response = self.analyze()
                self.assert_error(response, status, text)
                self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_timeout_errors_have_retry_message(self):
        for error_type in [requests.exceptions.Timeout, requests.exceptions.ConnectTimeout,
                           requests.exceptions.ReadTimeout]:
            with self.subTest(error_type=error_type.__name__):
                self.lookup.side_effect = error_type("private diagnostic")
                response = self.analyze()
                self.assert_error(response, 504, "took too long to respond")
                self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_connection_error_has_connection_message(self):
        self.lookup.side_effect = requests.exceptions.ConnectionError("private diagnostic")
        response = self.analyze()
        self.assert_error(response, 502, "could not be reached")
        self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_other_request_error_has_generic_message(self):
        self.lookup.side_effect = requests.exceptions.RequestException("private diagnostic")
        response = self.analyze()
        self.assert_error(response, 502, "could not be completed")
        self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_malformed_api_json_is_safe_upstream_error(self):
        self.lookup.side_effect = requests.exceptions.JSONDecodeError(
            "private diagnostic", "invalid response", 0,
        )
        response = self.analyze()
        self.assert_error(response, 502, "could not be completed")
        self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_insufficient_games_has_useful_error(self):
        self.summary.side_effect = ValueError("Not enough recent completed games for Boston Celtics")
        self.assert_error(self.analyze(), 400, "Not enough recent completed games")

    def test_unexpected_exception_does_not_expose_diagnostics(self):
        self.lookup.side_effect = RuntimeError("private diagnostic")
        with self.assertLogs(self.web.app.logger, level="ERROR"):
            response = self.analyze()
        self.assert_error(response, 500, "unexpected error occurred")
        self.assertNotIn("private diagnostic", response.get_data(as_text=True))

    def test_history_filters_combine_and_ignore_invalid_confidence(self):
        self.analyze()
        self.analyze(home_team="Los Angeles Lakers")
        self.analyze("Toronto Raptors", "Golden State Warriors")
        with closing(database.get_connection()) as connection:
            rows = connection.execute("SELECT id FROM matchup_history ORDER BY id").fetchall()
            for row, confidence in zip(rows, ["Low", "High", "Medium"]):
                connection.execute("UPDATE matchup_history SET confidence = ? WHERE id = ?",
                                   (confidence, row[0]))
            connection.commit()
        response = self.client.get("/history?team=lAkErS")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.rendered[-1][1]["matchups"]), 2)
        self.client.get("/history?team=Lakers&confidence=High")
        matches = self.rendered[-1][1]["matchups"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["confidence"], "High")
        self.client.get("/history?confidence=invalid")
        self.assertEqual(len(self.rendered[-1][1]["matchups"]), 3)
        response = self.client.get("/history?team=nonexistent")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.rendered[-1][1]["matchups"], [])
        self.assertIn("No saved matchups match these filters", response.get_data(as_text=True))

    def test_same_second_history_is_newest_first(self):
        with patch.object(database, "datetime") as frozen_datetime:
            frozen_datetime.now.return_value.strftime.return_value = "2026-09-16 12:00:00"
            self.analyze()
            self.analyze("Toronto Raptors", "Golden State Warriors")
            self.analyze(home_team="Los Angeles Lakers")
        self.client.get("/history")
        ids = [row["id"] for row in self.rendered[-1][1]["matchups"]]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_deletion_removes_only_selected_record_then_empty_history(self):
        self.analyze()
        self.analyze("Toronto Raptors", "Golden State Warriors")
        first, second = database.get_recent_matchups()
        response = self.client.post(f"/history/{first['id']}/delete", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in database.get_recent_matchups()], [second["id"]])
        self.assertEqual(self.client.post("/history/999999/delete").status_code, 302)
        response = self.client.post(f"/history/{second['id']}/delete", follow_redirects=True)
        self.assertIn("No matchup history yet", response.get_data(as_text=True))
        self.assertEqual(database.get_recent_matchups(), [])


if __name__ == "__main__":
    unittest.main()
