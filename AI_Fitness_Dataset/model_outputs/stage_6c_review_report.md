# Stage 6C Review Report

## 1. Final Verdict
Stage 6C Review Status: **PASS WITH NOTES**

Ready for Stage 6D: **YES**

Main reason: all model, preprocessor, encoder, metrics and report files exist; prediction demo runs; direct label leakage was not found; unsafe prediction count after safety override is 0. The notes are important: recommendation still has weak rare-class performance, preference has proxy leakage risk, and safety is mostly distilling the rule-based safety engine.

## 2. Files Checked
All required model files were found:

- `models/recommendation_model.pkl`
- `models/preference_model.pkl`
- `models/safety_risk_model.pkl`
- `models/recommendation_preprocessor.pkl`
- `models/preference_preprocessor.pkl`
- `models/safety_preprocessor.pkl`
- `models/recommendation_label_encoder.pkl`
- `models/preference_label_encoder.pkl`
- `models/safety_label_encoder.pkl`
- `models/feature_columns.json`
- `models/model_metrics.json`
- `models/model_registry.json`

All required report files were found:

- `model_outputs/model_evaluation_summary.json`
- `model_outputs/model_evaluation_report.md`
- `model_outputs/model_training_log.txt`
- `model_outputs/confusion_matrices.json`
- `model_outputs/feature_importance.json`
- `model_outputs/unsafe_prediction_report.json`
- `model_outputs/prediction_examples.json`
- `model_outputs/recommendation_classification_report.json`
- `model_outputs/preference_classification_report.json`
- `model_outputs/safety_classification_report.json`

## 3. Model Summary
Recommendation:

- Best model: `HistGradientBoostingClassifier`
- Accuracy: 0.8267
- Balanced accuracy: 0.4151
- Macro F1: 0.4122
- Weighted F1: 0.7924
- Unsafe before override: 0
- Unsafe after override: 0

Preference:

- Best model: `LogisticRegression`
- Accuracy: 1.0000
- Balanced accuracy: 1.0000
- Macro F1: 1.0000
- Dislike recall: 1.0000

Safety:

- Best model: `LogisticRegression`
- Accuracy: 1.0000
- Balanced accuracy: 1.0000
- Macro F1: 1.0000
- Monitor/Review recall: 1.0000

## 4. Recommendation Model Review
Accuracy is fairly strong, but macro F1 is low. This means the model is doing well on majority classes (`Keep`, `Reduce Difficulty`) while rare classes are weak.

Class details from the test set:

- `Increase Difficulty`: support 1, precision 0.0000, recall 0.0000, F1 0.0000. The model did not learn this class.
- `Keep`: support 29, precision 0.7714, recall 0.9310, F1 0.8438. This class is learned well.
- `Reduce Difficulty`: support 36, precision 0.9189, recall 0.9444, F1 0.9315. This class is learned well.
- `Reduce Volume`: support 4, precision 0.0000, recall 0.0000, F1 0.0000. The model does not currently capture this rare class.
- `Replace Exercise`: support 0 in test. Cannot evaluate test performance for this class.
- `Review Safety`: support 5, precision 0.5000, recall 0.2000, F1 0.2857. The model detects some safety-review cases, but recall is too low to rely on ML alone.

Confusion matrix findings:

- Actual `Increase Difficulty` was predicted as `Keep`.
- Actual `Reduce Volume` was predicted as `Keep`.
- Actual `Review Safety` was predicted as `Keep` twice, `Reduce Difficulty` twice, and `Review Safety` once.
- No actual `Review Safety` case was predicted as `Increase Difficulty` or `Increase Volume`, so no critical safety issue was found.

Verdict: usable for Stage 6D trial as an advisory model, but not strong enough to be the sole recommendation decision maker.

## 5. Preference Model Review
The preference model reports perfect metrics. This should not be interpreted as general intelligence. Direct label leakage was not found because `exercise_preference` is excluded from feature columns, and ID columns are excluded.

Leakage/proxy risk is high. Top important features include:

- `sentiment_Neutral`
- `requested_action_No Preference`
- `enjoyment_rating`
- `rating`
- `sentiment_Positive`
- `requested_action_Keep`
- `exercise_enjoyment`
- `difficulty_feedback_Appropriate`
- `progression_preference_Maintain`
- `sentiment_Negative`

These are legitimate post-feedback signals, but they are very close to the label. For example, `rating`, `sentiment`, `enjoyment_rating`, `exercise_enjoyment`, `requested_action`, and `difficulty_feedback` can almost reveal whether a user liked or disliked an exercise.

Verdict: useful when the app already has feedback signals for a user/exercise. Do not use it as a cold-start preference model.

## 6. Safety Model Review
The safety model also reports perfect metrics. Direct label leakage was not found because `safety_label` is excluded from features, but rule-distillation risk is high.

Top important features include:

- `risk_score`
- `risk_flag_count`
- `pain_rate`
- `limitation_count`
- `injury_count`
- `available_equipment_count`
- `technical_complexity_score`
- `training_level_Beginner`
- `primary_goal_Fat Loss`
- `preferred_split_Auto`

The biggest signal is `risk_score`, and the label was derived from safety status/risk logic. This means the model is mostly learning the output of the rule-based safety engine, not independently discovering real-world injury risk.

Verdict: useful as a distilled support model, but the rule-based Safety Review Engine must remain the final authority.

## 7. Safety Override Review
Unsafe before: 0

Unsafe after: 0

Override count: 0

The safety override rule is present and prediction demo applies it after recommendation prediction. `unsafe_prediction_report.json` currently has no unsafe/overridden cases, which matches the summary metrics.

Verdict: PASS.

## 8. Feature Importance Review
Recommendation feature importance is unavailable because the selected `HistGradientBoostingClassifier` does not expose compatible feature importance through the current extractor. This is acceptable but should be improved later with permutation importance.

Preference top features are plausible for post-feedback prediction but are proxy-heavy.

Safety top features are plausible for rule distillation but too dependent on `risk_score` and `risk_flag_count` to claim independent safety understanding.

## 9. Data Leakage Review
Direct leakage: not found.

Proxy leakage:

- Preference: high risk from `rating`, `sentiment`, `enjoyment_rating`, `exercise_enjoyment`, `requested_action`, `difficulty_feedback`, and `progression_preference`.
- Safety: expected rule-distillation risk from `risk_score`, `risk_flag_count`, `pain_rate`, `injury_count`, and related rule-generated features.

ID leakage: not found. `sample_id`, `user_id`, `plan_id`, `exercise_id`, `feedback_id`, `history_session_id`, `history_item_id`, and `plan_item_id` are excluded from training features.

Test leakage: not found. Candidate models are selected using validation metrics, and the final metrics are computed on test. Train/validation/test user overlap is 0.

## 10. Prediction Examples Review
Examples checked: recommendation, preference, safety.

The CLI `ml/predict.py` was run successfully for all three tasks using `model_outputs/prediction_examples.json`.

Suspicious cases:

- Preference example predicts `Dislike` with probability 0.9999. This is plausible from negative feedback signals but also shows overconfidence from proxy features/synthetic data.
- Safety example predicts `Safe` with probability 0.9985. This is plausible because risk score is 0, but it also shows the model heavily mirrors rule-generated risk features.

Overconfidence: present for preference and safety. Treat probabilities as internal ranking signals, not calibrated probabilities.

## 11. Issues and Fixes
ERROR:

- None.

WARNING:

- Recommendation macro F1 is low.
- `Increase Difficulty` and `Reduce Volume` have zero recall in test.
- `Replace Exercise` has no test support.
- `Review Safety` recall is only 0.2000.
- Preference metrics are likely inflated by proxy features.
- Safety metrics are likely inflated by rule-distillation features.
- Safety dataset has no `Avoid` class in the evaluated labels.

INFO:

- All required files exist.
- Predict demo runs.
- Unsafe after override is 0.
- User overlap across train/validation/test is 0.

## 12. Final Decision
**PASS WITH NOTES**

Stage 6C is technically valid and can move to Stage 6D, but the models should be integrated as guarded advisory components rather than full decision makers.

## 13. Next Step
Proceed to Stage 6D — ML Integration with Safety Engine.

Stage 6D should keep these conditions:

- Rule-based Safety Engine remains final authority.
- Recommendation ML output must pass safety override.
- Preference model should be used only when feedback-like signals exist.
- Track rare class performance and collect more `Increase Difficulty`, `Replace Exercise`, `Reduce Volume`, `Review Safety`, and `Avoid` examples.
