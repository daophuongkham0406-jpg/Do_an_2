# README Export

## 1. Giai đoạn 4 dùng để làm gì
Export bộ master dataset đã PASS validator sang CSV, JSON flat, JSON nested, JSONL AI training, SQL PostgreSQL và MongoDB seed.

## 2. File input cần có
5 workbook trong `master/` và report Stage 3 trong `reports/stage_3_validation/`.

## 3. Cách chạy export_all.py
```bash
python export_all.py
```

## 4. Cách chạy từng exporter
```bash
python export_csv.py
python export_json.py
python export_sql.py
python export_mongodb.py
```

## 5. Output folder structure
Output nằm trong `exports/csv`, `exports/json`, `exports/sql`, `exports/mongodb`.

## 6. Cách import CSV
Dùng file trong `exports/csv/` với encoding `utf-8-sig`.

## 7. Cách import SQL
```bash
psql "$DATABASE_URL" -f exports/sql/schema.sql
psql "$DATABASE_URL" -f exports/sql/inserts.sql
psql "$DATABASE_URL" -f exports/sql/indexes.sql
```

## 8. Cách import MongoDB
```bash
cd exports/mongodb
bash mongo_import_commands.sh
```

## 9. Cách dùng JSON flat
Mỗi file trong `exports/json/flat` là một bảng dạng records.

## 10. Cách dùng JSON nested
`plans_with_items`, `users_with_plans`, `history_by_session`, `feedback_by_user` dùng cho API/RAG.

## 11. Cách dùng JSONL cho AI training
Mỗi dòng là một sample task trong `exports/json/ai_training`.

## 12. Điều kiện export PASS
Stage 3 PASS/PASS WITH WARNINGS, ERROR=0, export_ready=true, stage_4_ready=true.

## 13. Cách đọc export_manifest.json
Manifest ghi source files, validation status, file đã export, row counts, warnings và export_status.

## 14. Cách debug nếu export fail
Đọc `exports/export_report.txt`, kiểm tra readiness Stage 3 và warning trong manifest.
