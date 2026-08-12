# Stage 6C Model Evaluation Report

## 1. Executive Summary
Stage 6C Status: **PASS WITH NOTES**
Ready for Stage 6D Integration: **YES**
Models trained: 3
Errors: 0
Warnings: 4

## 2. Input Datasets
- recommendation: train=350, validation=75, test=75, labels={'train': {'Reduce Difficulty': 165, 'Keep': 144, 'Reduce Volume': 20, 'Review Safety': 17, 'Replace Exercise': 3, 'Increase Difficulty': 1}, 'validation': {'Reduce Difficulty': 38, 'Keep': 32, 'Reduce Volume': 3, 'Replace Exercise': 1, 'Review Safety': 1}, 'test': {'Reduce Difficulty': 36, 'Keep': 29, 'Review Safety': 5, 'Reduce Volume': 4, 'Increase Difficulty': 1}}
- preference: train=5997, validation=1633, test=1370, labels={'train': {'Like': 3763, 'Neutral': 1365, 'Dislike': 869}, 'validation': {'Like': 959, 'Neutral': 455, 'Dislike': 219}, 'test': {'Like': 662, 'Neutral': 516, 'Dislike': 192}}
- safety: train=350, validation=75, test=75, labels={'train': {'Safe': 332, 'Review': 9, 'Monitor': 9}, 'validation': {'Safe': 72, 'Monitor': 2, 'Review': 1}, 'test': {'Safe': 72, 'Review': 2, 'Monitor': 1}}

## 3. Recommendation Model
Best model: HistGradientBoostingClassifier
Accuracy: 0.8267
Balanced accuracy: 0.4151
Macro F1: 0.4122
Weighted F1: 0.7924
Confusion matrix labels: `['Increase Difficulty', 'Keep', 'Reduce Difficulty', 'Reduce Volume', 'Replace Exercise', 'Review Safety']`
Confusion matrix: `[[0, 1, 0, 0, 0, 0], [0, 27, 1, 1, 0, 0], [0, 1, 34, 0, 0, 1], [0, 4, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 2, 2, 0, 0, 1]]`
Unsafe before/after override: 0 / 0
Feature importance available: False

## 4. Preference Model
Best model: LogisticRegression
Accuracy: 1.0000
Balanced accuracy: 1.0000
Macro F1: 1.0000
Weighted F1: 1.0000
Confusion matrix labels: `['Dislike', 'Like', 'Neutral']`
Confusion matrix: `[[192, 0, 0], [0, 662, 0], [0, 0, 516]]`
Dislike recall: 1.0000
Feature importance available: True

## 5. Safety Model
Best model: LogisticRegression
Accuracy: 1.0000
Balanced accuracy: 1.0000
Macro F1: 1.0000
Weighted F1: 1.0000
Confusion matrix labels: `['Monitor', 'Review', 'Safe']`
Confusion matrix: `[[1, 0, 0], [0, 2, 0], [0, 0, 72]]`
Unsafe before/after override: 0 / 0
Monitor/Review/Avoid recall: 1.0000
Feature importance available: True

## 6. Safety Override
Rule-based Safety Engine remains the final guardrail over ML predictions.
Override count: 0
Unsafe after override: 0

## 7. Saved Model Files
- `feature_columns.json`
- `model_metrics.json`
- `model_metrics_before_retrain.json`
- `model_registry.json`
- `preference_label_encoder.pkl`
- `preference_model.pkl`
- `preference_preprocessor.pkl`
- `recommendation_label_encoder.pkl`
- `recommendation_model.pkl`
- `recommendation_preprocessor.pkl`
- `safety_label_encoder.pkl`
- `safety_preprocessor.pkl`
- `safety_risk_model.pkl`

## 8. How The Machine Learned
Models learned from user profile, exercise attributes, history adherence, feedback sentiment/difficulty and safety risk features. Rare classes remain harder to learn because Stage 6B has low sample counts for some labels.

## 9. Limitations
- Synthetic data
- Class imbalance
- Low sample class
- Safety ML only supports; rule-based safety remains final

## 10. Next Step
Proceed to Stage 6D — ML Integration with Safety Engine.
