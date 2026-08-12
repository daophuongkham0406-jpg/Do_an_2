# Stage 6B ML Training Dataset Builder

Stage 6B builds clean `features -> label` datasets for Stage 6C model training. It does not train ML models and does not create `.pkl` files.

## Inputs

- `exports/csv/*.csv` from Stage 4.
- `ai_outputs/ml_signal_samples.json` and related Stage 6A Revised outputs.

## Command

```bash
python ml/run_stage_6b.py
python ml/run_stage_6b.py --input-csv-dir exports/csv --ai-output-dir ai_outputs --output-dir ml_outputs
```

## Outputs

- `ml_outputs/recommendation_training_dataset.csv`
- `ml_outputs/preference_training_dataset.csv`
- `ml_outputs/safety_training_dataset.csv`
- `ml_outputs/ml_training_dataset.csv`
- task-specific train/validation/test split files
- `ml_outputs/feature_dictionary.json`
- `ml_outputs/ml_dataset_summary.json`
- `ml_outputs/ml_dataset_report.md`
- `ml_outputs/ml_dataset_issues.csv`

## Split

Train/validation/test split uses seed `42` and is grouped by `user_id`, so a user appears in only one split.

## Stage 6C

Stage 6C can use these CSV files to train recommendation, preference and safety risk models.
