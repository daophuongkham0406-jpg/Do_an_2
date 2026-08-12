from ai.recommendation_engine import recommend_action
import unittest


class RecommendationEngineTest(unittest.TestCase):
    def test_pain_feedback_reviews_safety(self):
        out = recommend_action({"history_summary": {}, "recent_feedback": [{"pain_feedback": "Pain"}], "safety_review": {"safety_status": "Safe"}})
        self.assertEqual(out["recommended_action"], "Review Safety")

    def test_too_easy_increases_difficulty(self):
        out = recommend_action({"history_summary": {"completion_rate": 0.95, "average_rpe": 6.5, "average_fatigue": 2}, "recent_feedback": [{"difficulty_feedback": "Too Easy", "sentiment": "Positive"}], "safety_review": {"safety_status": "Safe"}})
        self.assertEqual(out["recommended_action"], "Increase Difficulty")

