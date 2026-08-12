# Stage 6D Guarded ML Integration

Stage 6D integrates the Stage 6C ML models into a guarded decision pipeline.

## Architecture

```text
Input user/profile/history/feedback
Feature Builder
ML Recommendation + ML Preference + ML Safety
Hybrid Decision Engine
Rule-Based Safety Lock
Final Recommendation
Prediction Logging
```

ML outputs are advisory. Rule-based safety lock is the final authority.

## Required Model Files

- `models/recommendation_model.pkl`
- `models/preference_model.pkl`
- `models/safety_risk_model.pkl`
- corresponding preprocessors and label encoders
- `models/feature_columns.json`

## Run Integration Test

```bash
python ml_integration/integration_pipeline.py --sample-size 100
python ml_integration/integration_pipeline.py --sample-size all
python ml_integration/integration_pipeline.py --user-id U000001
```

## Feature Builder

The feature builder matches `models/feature_columns.json`. Missing numeric features are filled with `0`, and missing categorical features are filled with `Unknown`.

## Safety Lock

`Increase Difficulty` and `Increase Volume` are blocked when rule safety or ML safety says `Review`/`Avoid`, risk score is high, or blocking safety flags are present.

## API

`api_routes.py` contains Flask blueprint examples. They are mocks until wired into a backend service.

## Logging

Prediction logs are not ground truth until paired with real user feedback after action, such as completion, rating, pain report, adherence and preference.

## Limitations

Recommendation macro F1 is still low. Preference has proxy leakage risk. Safety ML may be rule distillation. Guarded mode is required.
