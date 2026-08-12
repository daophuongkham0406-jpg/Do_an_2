# Stage 6D Integration Test Report

## 1. Executive Summary
Stage 6D Status: **PASS WITH NOTES**
Ready for Backend/App: **YES**
Users tested: 500
Unsafe final actions: 0
Errors: 0
Warnings: 1

## 2. Model Loading
Model files loaded: {'recommendation': True, 'preference': True, 'safety': True}
Load errors: []

## 3. Feature Builder
Missing features filled: 0
Schema matching: feature rows are aligned to `models/feature_columns.json`.

## 4. ML Prediction
Prediction success count: 500
ML recommendation distribution: `{'Reduce Difficulty': 241, 'Keep': 213, 'Review Safety': 19, 'Reduce Volume': 23, 'Increase Difficulty': 1, 'Replace Exercise': 3}`

## 5. Hybrid Decision Engine
Decision source distribution: `{'ml_and_rule_agree': 409, 'ml_recommendation': 10, 'preference_dislike_adjustment': 66, 'rule_safety_priority': 12, 'fallback_to_rule_based': 3}`
Fallback to rule count: 3

## 6. Safety Lock
Override count: 0
Unsafe final action count: 0
Rule safety distribution: `{'Safe': 476, 'Review': 12, 'Monitor': 12}`

## 7. Final Action Distribution
`{'Reduce Difficulty': 240, 'Keep': 144, 'Replace Exercise': 69, 'Review Safety': 22, 'Reduce Volume': 24, 'Increase Difficulty': 1}`

## 8. Prediction Logging
Log file: `prediction_log_sample.csv`
Ground truth limitation: prediction logs become training signal only after real user feedback after action is attached.

## 9. API / Backend Integration
Mock Flask routes are available in `ml_integration/api_routes.py`.

## 10. Limitations
Recommendation macro F1 still low. Preference model has proxy leakage risk. Safety model may be rule distillation. Guarded mode required.

## 11. Next Step
Proceed to backend/app integration or collect real feedback for retraining.
