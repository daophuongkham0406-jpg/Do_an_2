from ai.feedback_analyzer import analyze_feedback
import unittest


class FeedbackAnalyzerTest(unittest.TestCase):
    def test_feedback_liked_exercise(self):
        out = analyze_feedback("U1", [{"user_id": "U1", "exercise_id": "EX1", "exercise_preference": "Like", "sentiment": "Positive"}])
        self.assertIn("EX1", out["liked_exercises"])
