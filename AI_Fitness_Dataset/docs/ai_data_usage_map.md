# AI Data Usage Map

| AI Task | Input Tables | Important Columns | Feature Type | Output | Reason |
| --- | --- | --- | --- | --- | --- |
| Generate Beginner Plan | User_Profile, Exercise_Master | training_level, primary_goal, available_days, available_equipment, injury, difficulty_level, primary_muscles | static profile + exercise metadata | Workout_Plan, Workout_Plan_Items | Select safe and feasible exercises. |
| Generate Strength Plan | User_Profile, Exercise_Master | goal, training_level, equipment, movement_pattern, recommended_goals | goal matching | Workout_Plan_Items | Match exercise mechanics and loading style to strength goals. |
| Log Workout History | Workout_Plan, Workout_Plan_Items | sets, reps, target_intensity, rest_seconds | planned prescription | Workout_History_Sessions, Workout_History_Items | Capture actual execution against plan. |
| Adjust Next Plan | User_Profile, Workout_Plan, Workout_History_Sessions, Workout_History_Items, User_Feedback | completion_pct, set_completion_pct, actual_rpe, fatigue_after, sentiment, requested_action | behavioral feedback | Updated Workout_Plan | Adapt volume, difficulty, exercise selection and recovery. |
| Safety Review | User_Profile, Exercise_Master, Workout_History_Items, User_Feedback | injury, contraindications, pain_areas, pain_feedback | safety signal | Review Safety / Replace Exercise | Avoid harmful recommendations. |
| Preference Memory | User_Feedback, Workout_History_Items, Exercise_Master | preference, exercise_enjoyment, feedback_signal, exercise_id | preference learning | Prefer/Avoid exercise profile | Personalize future exercise choices. |
