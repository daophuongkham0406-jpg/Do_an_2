# README Statistics

## 1. Giai đoạn 5 dùng để làm gì
Phân tích profiling, missing values, duplicates, distribution, coverage và readiness cho AI training.

## 2. File input cần có
CSV trong `exports/csv/` và `exports/export_manifest.json`.

## 3. Cách chạy statistics.py
```bash
python statistics.py
python statistics.py --csv-dir exports/csv --manifest exports/export_manifest.json --output-dir reports/stage_5_statistics
```

## 4. Output tạo ra
Markdown, JSON summary, missing/duplicate/coverage CSV, Excel distribution report, readiness JSON và chart PNG.

## 5. Cách đọc statistics_report.md
Đọc Executive Summary, Data Balance Assessment, AI Training Risk Assessment và Final Stage 5 Status.

## 6. Cách đọc missing_values_report.csv
Xem `severity`, `missing_type`, `missing_percent` và `note`.

## 7. Cách đọc duplicate_report.csv
Hard duplicate là lỗi nghiêm trọng; soft/expected repetition cần đánh giá theo ngữ cảnh.

## 8. Cách đọc coverage_report.csv
Coverage cho biết bảng nguồn được đại diện trong bảng đích bao nhiêu phần trăm.

## 9. Ý nghĩa PASS / PASS WITH NOTES / NEED IMPROVEMENT
PASS sạch; PASS WITH NOTES có cải thiện nhưng không chặn; NEED IMPROVEMENT có vấn đề ảnh hưởng training.

## 10. Điều kiện Ready for Stage 6 AI
Không có critical missing, không duplicate primary key, coverage và distribution chính đạt mức dùng được.

## 11. Cách thêm thống kê mới
Thêm hàm phân tích hoặc bổ sung metric vào các hàm `analyze_*` trong `statistics.py`.
