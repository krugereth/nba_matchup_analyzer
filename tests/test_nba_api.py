import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch

from requests import HTTPError

from services import nba_api


TODAY = date(2026, 9, 16)


def make_game(game_id, days_ago, scored=120, allowed=110, away=False, status="Final"):
    team = {"id": 1, "full_name": "Boston Celtics"}
    opponent = {"id": 13, "full_name": "LA Clippers"}
    return {
        "id": game_id,
        "date": (TODAY - timedelta(days=days_ago)).isoformat(),
        "status": status,
        "home_team": opponent if away else team,
        "visitor_team": team if away else opponent,
        "home_team_score": allowed if away else scored,
        "visitor_team_score": scored if away else allowed,
    }


def response_with(data, next_cursor=None):
    response = Mock()
    response.json.return_value = {
        "data": data,
        "meta": {"next_cursor": next_cursor},
    }
    return response


class RecentGamesTests(unittest.TestCase):
    def setUp(self):
        nba_api._get_recent_games_for_team.cache_clear()
        nba_api.get_team_lookup.cache_clear()
        self.addCleanup(nba_api._get_recent_games_for_team.cache_clear)
        self.addCleanup(nba_api.get_team_lookup.cache_clear)
        self.get = self.enterContext(patch.object(nba_api.requests, "get"))
        self.enterContext(patch.object(nba_api, "get_headers", return_value={}))
        self.clock = self.enterContext(patch.object(nba_api, "monotonic", return_value=0))
        self.date = self.enterContext(patch.object(nba_api, "date"))
        self.date.today.return_value = TODAY

    def test_latest_completed_games_are_selected_across_all_pages(self):
        older_games = [make_game(i, 30 - i) for i in range(25)]
        newer_games = [make_game(i, 30 - i) for i in range(25, 30)]
        newer_games.append(make_game(30, 0, status="4th Qtr"))
        self.get.side_effect = [
            response_with(older_games, next_cursor=25),
            response_with(newer_games),
        ]

        games = nba_api.get_recent_games_for_team(1)

        self.assertEqual([game["id"] for game in games], list(range(29, 19, -1)))
        first_params = self.get.call_args_list[0].kwargs["params"]
        self.assertEqual(first_params, {
            "team_ids[]": 1,
            "season_type": "regular",
            "per_page": 100,
            "start_date": (TODAY - timedelta(days=300)).isoformat(),
            "end_date": TODAY.isoformat(),
        })
        self.assertEqual(self.get.call_args_list[1].kwargs["params"]["cursor"], 25)

    def test_cache_reuses_games_for_different_limits_then_refreshes(self):
        self.get.return_value = response_with([make_game(i, i) for i in range(10)])
        self.assertEqual(len(nba_api.get_recent_games_for_team(1)), 10)
        self.clock.return_value = nba_api.RECENT_GAMES_CACHE_SECONDS - 1
        self.assertEqual(len(nba_api.get_recent_games_for_team(1, limit=5)), 5)
        self.assertEqual(self.get.call_count, 1)

        self.clock.return_value = nba_api.RECENT_GAMES_CACHE_SECONDS
        self.get.return_value = response_with([make_game(100, 0)])
        self.assertEqual(nba_api.get_recent_games_for_team(1)[0]["id"], 100)
        self.assertEqual(self.get.call_count, 2)

        self.date.today.return_value = TODAY + timedelta(days=1)
        nba_api.get_recent_games_for_team(1)
        self.assertEqual(self.get.call_count, 3)

    def test_failed_later_page_does_not_cache_partial_games(self):
        failed_page = Mock()
        failed_page.raise_for_status.side_effect = HTTPError("Unavailable")
        self.get.side_effect = [
            response_with([make_game(1, 20)], next_cursor=1),
            failed_page,
            response_with([make_game(2, 1)]),
        ]

        with self.assertRaises(HTTPError):
            nba_api.get_recent_games_for_team(1)
        self.assertEqual(nba_api.get_recent_games_for_team(1)[0]["id"], 2)
        self.assertEqual(self.get.call_count, 3)

    def test_summary_metrics_and_rows_use_the_same_home_and_away_scores(self):
        games = [
            make_game(1, 1, scored=120, allowed=110),
            make_game(2, 2, scored=105, allowed=115, away=True),
            make_game(3, 3, scored=130, allowed=120),
        ]
        self.get.return_value = response_with(games)

        summary = nba_api.build_team_summary("Boston Celtics", {"Boston Celtics": 1})

        self.assertEqual(summary["games_used"], 3)
        self.assertEqual((summary["wins"], summary["losses"]), (2, 1))
        self.assertEqual(summary["avg_points_for"], 118.3)
        self.assertEqual(summary["avg_points_against"], 115.0)
        self.assertEqual(summary["point_diff"], 3.3)
        rows = summary["recent_games"]
        self.assertEqual([row["result"] for row in rows], ["W", "L", "W"])
        self.assertEqual([row["location"] for row in rows], ["Home", "Away", "Home"])
        self.assertEqual([row["scored"] for row in rows], [120, 105, 130])
        self.assertEqual([row["allowed"] for row in rows], [110, 115, 120])
        self.assertTrue(all(row["opponent"] == "Los Angeles Clippers" for row in rows))
        self.assertEqual(rows[0]["date"], "2026-09-15")

    def test_fewer_than_three_completed_games_are_rejected(self):
        self.get.return_value = response_with([
            make_game(1, 1), make_game(2, 2), make_game(3, 0, status="Halftime")
        ])
        with self.assertRaisesRegex(ValueError, "Not enough recent completed games"):
            nba_api.build_team_summary("Boston Celtics", {"Boston Celtics": 1})

    def test_clippers_lookup_and_logos_use_the_app_name(self):
        for api_name in ("LA Clippers", "Los Angeles Clippers"):
            with self.subTest(api_name=api_name):
                nba_api.get_team_lookup.cache_clear()
                self.get.return_value = response_with([{"id": 13, "full_name": api_name}])
                self.assertEqual(nba_api.get_team_lookup(), {"Los Angeles Clippers": 13})
                self.assertEqual(
                    nba_api.get_team_logo_url(api_name),
                    "https://a.espncdn.com/i/teamlogos/nba/500/lac.png",
                )


class ConfigurationTests(unittest.TestCase):
    def test_missing_key_has_a_specific_configuration_error(self):
        with patch.object(nba_api.os, "getenv", return_value=None):
            with self.assertRaises(nba_api.APIConfigurationError):
                nba_api.get_headers()


if __name__ == "__main__":
    unittest.main()
