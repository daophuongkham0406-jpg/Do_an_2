# Backend + AI Fitness Dataset Integration

## 1. Purpose

Flask is the safe API layer for FIT ME. Workout generation uses only the local
`AI_Fitness_Dataset`; it does not call external exercise APIs and does not read
old MongoDB exercise data.

## 2. Workout Generation Flow

```text
User creates workout plan
Frontend sends profile + goal + available days + equipment + health notes
Backend receives request
Backend references only AI_Fitness_Dataset:
  - exercises
  - workout_plans
  - workout_plan_items
  - users
  - workout_history_sessions
  - workout_history_items
  - user_feedback
  - workout_history_summary
Backend applies rules:
  - safety
  - recommendation
  - preference
  - history/adherence/fatigue
Backend selects matching exercises from AI_Fitness_Dataset
Backend returns personalized plan to frontend
User applies the plan
MongoDB stores the generated plan and real user progress
```

## 3. Dataset Files Used

`Backend/services/ml_integration_service.py` reads these CSV exports:

```text
AI_Fitness_Dataset/exports/csv/exercises.csv
AI_Fitness_Dataset/exports/csv/workout_plans.csv
AI_Fitness_Dataset/exports/csv/workout_plan_items.csv
AI_Fitness_Dataset/exports/csv/users.csv
AI_Fitness_Dataset/exports/csv/workout_history_sessions.csv
AI_Fitness_Dataset/exports/csv/workout_history_items.csv
AI_Fitness_Dataset/exports/csv/user_feedback.csv
AI_Fitness_Dataset/exports/csv/workout_history_summary.csv
```

## 4. Storage Rule

MongoDB does not need to store the 350 exercise reference records. MongoDB stores:

- the generated plan selected for the real user
- the input snapshot used to generate it
- AI decision/context metadata
- daily progress
- completed exercise counts
- nutrition and coach-chat context when needed

## 5. API

```text
GET  /api/ml/health
POST /api/ml/generate-plan
POST /api/plans/save-ai-plan
GET  /api/plans/get-active-plan
POST /api/plans/checkin-exercise
```

## 6. Current Source

Current mode: `ai_fitness_dataset_only`.

