from ai.ai_pipeline import evaluate
import unittest


class AiPipelineTest(unittest.TestCase):
    def test_evaluation_accepts_safe_result(self):
        result = {
            "recommendation": {"recommended_action": "Keep", "explanation": "ok", "confidence": 0.8},
            "safety_review": {"safety_status": "Safe", "risk_score": 0},
            "generated_plan": {"sessions": [{"exercises": [{"exercise_id": "EX0001"}]}]},
            "history_analysis": {},
            "feedback_analysis": {},
            "plan_adjustment": {"adjustment_status": "Maintain"},
            "ai_coach": {"answer": "ok"},
        }
        out = evaluate([result])
        self.assertEqual(out["stage_6_status"], "PASS")
