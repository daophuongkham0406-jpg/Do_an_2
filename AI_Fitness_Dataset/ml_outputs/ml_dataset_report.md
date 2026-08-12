# Stage 6B ML Dataset Report

## 1. Executive Summary
Stage 6B Status: **PASS WITH NOTES**
Ready for Stage 6C Training: **YES**
Error count: 0
Warning count: 2

## 2. Input Files
- D:\AI_Fitness_Dataset\exports\csv\exercises.csv: FOUND
- D:\AI_Fitness_Dataset\exports\csv\users.csv: FOUND
- D:\AI_Fitness_Dataset\exports\csv\workout_plans.csv: FOUND
- D:\AI_Fitness_Dataset\exports\csv\workout_plan_items.csv: FOUND
- D:\AI_Fitness_Dataset\exports\csv\workout_history_sessions.csv: FOUND
- D:\AI_Fitness_Dataset\exports\csv\workout_history_items.csv: FOUND
- D:\AI_Fitness_Dataset\exports\csv\workout_history_summary.csv: FOUND
- D:\AI_Fitness_Dataset\exports\csv\user_feedback.csv: FOUND
- D:\AI_Fitness_Dataset\ai_outputs\ml_signal_samples.json: FOUND
- D:\AI_Fitness_Dataset\ai_outputs\recommendation_examples.json: FOUND
- D:\AI_Fitness_Dataset\ai_outputs\safety_review_examples.json: FOUND
- D:\AI_Fitness_Dataset\ai_outputs\plan_adjustment_examples.json: FOUND
- D:\AI_Fitness_Dataset\ai_outputs\feedback_analysis_examples.json: FOUND
- D:\AI_Fitness_Dataset\ai_outputs\history_analysis_examples.json: FOUND
- D:\AI_Fitness_Dataset\ai_outputs\ai_evaluation_summary.json: FOUND

## 3. Dataset Outputs
- recommendation: 500 rows, 61 columns
- preference: 9000 rows, 62 columns
- safety: 500 rows, 46 columns
- unified: 10000 rows, 91 columns

## 4. Label Distribution
- recommended_action: `{'Reduce Difficulty': 239, 'Keep': 205, 'Reduce Volume': 27, 'Review Safety': 23, 'Replace Exercise': 4, 'Increase Difficulty': 2}`
- exercise_preference: `{'Like': 5384, 'Neutral': 2336, 'Dislike': 1280}`
- safety_label: `{'Safe': 476, 'Review': 12, 'Monitor': 12}`

## 5. Feature Groups
- User features: demographics, body metrics, goals, level, schedule, equipment and limitations.
- Exercise features: category, level, muscles, equipment, movement pattern, complexity and joint stress.
- History features: completion, set completion, skipped/partial rate, RPE, fatigue, pain and trend.
- Feedback features: sentiment, difficulty, enjoyment, fatigue, pain, duration and preference signals.
- Safety features: safety status, risk score, risk flags, contraindication and pain matching counts.

## 6. Split Summary
- Train: 6697 rows, 350 users
- Validation: 1783 rows, 75 users
- Test: 1520 rows, 75 users
- User overlap: 0

## 7. Data Quality Issues
- ERROR: 0
- WARNING: 2
- INFO: 0

## 8. Leakage Check
- recommendation: label `recommended_action` in feature list = False
- preference: label `exercise_preference` in feature list = False
- safety: label `safety_label` in feature list = False

## 9. Limitations
Dữ liệu hiện tại còn synthetic và một số class có thể imbalance, cần cân nhắc class weighting hoặc sampling ở Stage 6C.

## 10. Next Step
Proceed to Stage 6C — Train ML Models nếu status là PASS hoặc PASS WITH NOTES; nếu NEED FIX thì xử lý `ml_dataset_issues.csv` trước.
