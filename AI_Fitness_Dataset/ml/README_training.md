# Stage 6C Train ML Models

Stage 6C trains three scikit-learn models from Stage 6B datasets:

- Recommendation Action Model -> `recommended_action`
- Exercise Preference Model -> `exercise_preference`
- Safety Risk Model -> `safety_label`

## Train

```bash
python ml/train_all_models.py
python ml/train_all_models.py --input-dir ml_outputs --model-dir models --output-dir model_outputs
python ml/train_all_models.py --task recommendation
```

Candidate models:

- `LogisticRegression(class_weight="balanced", max_iter=2000)`
- `RandomForestClassifier(class_weight="balanced", random_state=42)`
- `HistGradientBoostingClassifier(random_state=42)`

## Predict

```bash
python ml/predict.py --task recommendation --input-json model_outputs/prediction_examples.json
```

Rule-based safety override remains the final guardrail. If safety status is `Review`/`Avoid`, or risk score is high, increase actions are overridden to `Review Safety`.
