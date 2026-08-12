# README Validator

## 1. Validator dùng để làm gì
`validate.py` kiểm tra tổng hợp 5 master dataset, relationship, cross-consistency, distribution, metadata và readiness cho Stage 4 Export.

## 2. File input cần có
`exercise_master.xlsx`, `user_master.xlsx`, `workout_plan_master.xlsx`, `workout_history_master.xlsx`, `user_feedback_master.xlsx` và các artifact Stage 2 trong `docs/`.

## 3. Cách chạy
Chạy nhanh từ thư mục project:

```bash
python validate.py
```

Chạy đầy đủ với path tùy chỉnh:

```bash
python validate.py --exercise-master master/exercise_master.xlsx --user-master master/user_master.xlsx --plan-master master/workout_plan_master.xlsx --history-master master/workout_history_master.xlsx --feedback-master master/user_feedback_master.xlsx --report-dir reports/stage_3_validation
```

## 4. Output tạo ra
`validation_report.txt`, `validation_report.json`, `validation_issues.csv`, `dataset_statistics.json`, `readiness_report.json`, `validation_config.json`.

## 5. Ý nghĩa ERROR / WARNING / INFO
ERROR là lỗi blocking cần sửa trước export/training. WARNING là lệch nhẹ hoặc metadata/phân bố cần xem xét. INFO là ghi chú không chặn.

## 6. Điều kiện PASS
ERROR = 0 và WARNING = 0.

## 7. Điều kiện AI Training Ready
ERROR = 0. WARNING nếu có phải là non-blocking và được chấp nhận.

## 8. Điều kiện Ready for Stage 4
ERROR = 0, relationship PASS và cross-consistency PASS.

## 9. Cách đọc validation_issues.csv
Mỗi dòng có `severity, rule_id, domain, file, sheet, row, column, value, message, suggestion`.

## 10. Cách thêm rule mới
Thêm logic vào hàm domain tương ứng hoặc thêm FK vào `RELATIONSHIPS`, cross rule vào `CROSS_RULES`, sau đó chạy lại `python validate.py`.
