import pandas as pd
from ai.workout_generator import generate_workout_plan
import unittest


class WorkoutGeneratorTest(unittest.TestCase):
    def test_generator_returns_sessions(self):
        exercises = pd.DataFrame([{"exercise_id": "EX0001", "exercise_name": "Push-Up", "equipment": '["Bodyweight"]', "recommended_goals": '["General Fitness"]', "minimum_training_level": "Beginner", "contraindications": "[]"}])
        user = {"user_id": "U000001", "primary_goal": "General Fitness", "training_level": "Beginner", "training_days_per_week": "2", "available_equipment": '["Bodyweight"]'}
        out = generate_workout_plan(user, exercises)
        self.assertEqual(len(out["sessions"]), 2)
