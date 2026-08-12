# Stage 6B ML Outputs

Thư mục này chứa dataset huấn luyện cho Stage 6C. Stage 6B chỉ build dữ liệu, chưa train model và không tạo file `.pkl`.

- `recommendation_training_dataset.csv`: feature -> `recommended_action`.
- `preference_training_dataset.csv`: feature -> `exercise_preference`.
- `safety_training_dataset.csv`: feature -> `safety_label`.
- `ml_training_dataset.csv`: unified dataset gồm recommendation/preference/safety.
- `train.csv`, `validation.csv`, `test.csv`: split theo `user_id` cho unified dataset.
- `feature_dictionary.json`: mô tả feature và encoding gợi ý cho Stage 6C.
- `ml_dataset_summary.json`: summary chạy gần nhất.
- `ml_dataset_issues.csv`: danh sách issues nếu có.

Stage 6B Status: PASS WITH NOTES
Ready for Stage 6C Training: YES
