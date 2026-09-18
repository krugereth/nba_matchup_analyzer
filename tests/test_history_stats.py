"""History dashboard aggregates use every saved row in an isolated database."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import database


class HistoryStatsTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = self.enterContext(
            tempfile.TemporaryDirectory(prefix="nba-history-stats-tests-")
        )
        self.enterContext(patch.object(
            database, "DATABASE_NAME", str(Path(temporary_directory) / "test-matchups.db"),
        ))
        database.init_db()

    def save(self, team_a, team_b, favored_team, confidence="Low"):
        database.save_matchup_result({
            "team_a": {"name": team_a},
            "team_b": {"name": team_b},
            "favored_team": favored_team,
            "confidence": confidence,
            "score_difference": 0 if favored_team == "Even" else 3,
            "explanation": "Synthetic fixture for history statistics.",
        })

    def test_empty_history_has_zero_counts_and_no_leaders(self):
        self.assertEqual(database.get_history_stats(), {
            "total_matchups": 0,
            "confidence_counts": {"High": 0, "Medium": 0, "Low": 0},
            "most_analyzed_teams": [],
            "most_analyzed_count": 0,
            "most_favored_teams": [],
            "most_favored_count": 0,
        })

    def test_statistics_include_rows_beyond_the_twenty_row_list(self):
        for index in range(25):
            confidence = "High" if index < 9 else "Medium" if index < 16 else "Low"
            self.save("Los Angeles Lakers", "Boston Celtics", "Los Angeles Lakers", confidence)
        self.assertEqual(len(database.get_recent_matchups()), 20)
        stats = database.get_history_stats()
        self.assertEqual(stats["total_matchups"], 25)
        self.assertEqual(stats["confidence_counts"], {"High": 9, "Medium": 7, "Low": 9})
        self.assertEqual(stats["most_analyzed_teams"], ["Boston Celtics", "Los Angeles Lakers"])
        self.assertEqual(stats["most_analyzed_count"], 25)
        self.assertEqual(stats["most_favored_teams"], ["Los Angeles Lakers"])
        self.assertEqual(stats["most_favored_count"], 25)
        # Reading a filtered, limited list cannot alter the full-history summary.
        self.assertEqual(len(database.get_recent_matchups(limit=2, confidence_filter="High")), 2)
        self.assertEqual(database.get_recent_matchups(team_query="Toronto Raptors"), [])
        self.assertEqual(database.get_history_stats(), stats)

    def test_team_appearances_include_both_sides_and_sorted_ties(self):
        self.save("Toronto Raptors", "Boston Celtics", "Toronto Raptors", "High")
        self.save("Los Angeles Lakers", "Toronto Raptors", "Los Angeles Lakers", "Medium")
        self.save("Boston Celtics", "Los Angeles Lakers", "Even")
        self.save("Golden State Warriors", "Miami Heat", "Even")
        stats = database.get_history_stats()
        self.assertEqual(stats["most_analyzed_teams"], [
            "Boston Celtics", "Los Angeles Lakers", "Toronto Raptors",
        ])
        self.assertEqual(stats["most_analyzed_count"], 2)
        self.assertEqual(stats["most_favored_teams"], ["Los Angeles Lakers", "Toronto Raptors"])
        self.assertEqual(stats["most_favored_count"], 1)

    def test_even_results_are_excluded_only_from_favored_leaders(self):
        for _ in range(3):
            self.save("Toronto Raptors", "Boston Celtics", "Even")
        self.save("Los Angeles Lakers", "Miami Heat", "Los Angeles Lakers", "High")
        stats = database.get_history_stats()
        self.assertEqual(stats["total_matchups"], 4)
        self.assertEqual(stats["confidence_counts"], {"High": 1, "Medium": 0, "Low": 3})
        self.assertEqual(stats["most_analyzed_teams"], ["Boston Celtics", "Toronto Raptors"])
        self.assertEqual(stats["most_analyzed_count"], 3)
        self.assertEqual(stats["most_favored_teams"], ["Los Angeles Lakers"])
        self.assertEqual(stats["most_favored_count"], 1)

    def test_all_even_results_have_no_favored_leader(self):
        self.save("Boston Celtics", "Toronto Raptors", "Even")
        self.save("Los Angeles Lakers", "Toronto Raptors", "Even")
        stats = database.get_history_stats()
        self.assertEqual(stats["total_matchups"], 2)
        self.assertEqual(stats["confidence_counts"], {"High": 0, "Medium": 0, "Low": 2})
        self.assertEqual(stats["most_analyzed_teams"], ["Toronto Raptors"])
        self.assertEqual(stats["most_analyzed_count"], 2)
        self.assertEqual(stats["most_favored_teams"], [])
        self.assertEqual(stats["most_favored_count"], 0)

    def test_deletions_recompute_counts_and_leaders(self):
        self.save("Toronto Raptors", "Boston Celtics", "Toronto Raptors", "High")
        self.save("Toronto Raptors", "Boston Celtics", "Toronto Raptors", "High")
        self.save("Los Angeles Lakers", "Toronto Raptors", "Los Angeles Lakers", "Medium")
        before = database.get_history_stats()
        self.assertEqual(before["most_analyzed_teams"], ["Toronto Raptors"])
        self.assertEqual(before["most_analyzed_count"], 3)
        self.assertEqual(before["most_favored_teams"], ["Toronto Raptors"])
        self.assertEqual(before["most_favored_count"], 2)
        toronto_win = next(row for row in database.get_recent_matchups()
                           if row["favored_team"] == "Toronto Raptors")
        database.delete_matchup(toronto_win["id"])
        after = database.get_history_stats()
        self.assertEqual(after["total_matchups"], 2)
        self.assertEqual(after["confidence_counts"], {"High": 1, "Medium": 1, "Low": 0})
        self.assertEqual(after["most_analyzed_count"], 2)
        self.assertEqual(after["most_favored_teams"], ["Los Angeles Lakers", "Toronto Raptors"])
        self.assertEqual(after["most_favored_count"], 1)
        for row in database.get_recent_matchups():
            database.delete_matchup(row["id"])
        self.assertEqual(database.get_history_stats()["total_matchups"], 0)
        self.assertEqual(database.get_history_stats()["most_analyzed_teams"], [])
        self.assertEqual(database.get_history_stats()["most_favored_teams"], [])


if __name__ == "__main__":
    unittest.main()
