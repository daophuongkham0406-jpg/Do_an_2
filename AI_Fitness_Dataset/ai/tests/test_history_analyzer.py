from ai.history_analyzer import analyze_history
import unittest


class HistoryAnalyzerTest(unittest.TestCase):
    def test_history_counts_completion(self):
        out = analyze_history("U1", [{"user_id": "U1", "completion_status": "Completed", "completion_pct": "100"}], [])
        self.assertEqual(out["completion_rate"], 1.0)
