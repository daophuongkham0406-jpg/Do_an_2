from ai.safety_review_engine import review_safety
import unittest


class SafetyReviewTest(unittest.TestCase):
    def test_injury_contraindication_review(self):
        out = review_safety({"training_level": "Beginner", "injuries_or_limitations": '["Shoulder"]'}, {"minimum_training_level": "Beginner", "contraindications": '["Shoulder"]'})
        self.assertIn(out["safety_status"], {"Review", "Avoid"})
