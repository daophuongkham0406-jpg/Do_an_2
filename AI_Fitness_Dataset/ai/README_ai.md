# Stage 6A AI Baseline

## 1. Giai đoạn 6 dùng để làm gì
Tạo baseline AI rule-based cho recommendation, workout generation, history/feedback analysis, plan adjustment, safety review và AI Coach demo. Giai đoạn này chưa train ML và chưa tạo file model `.pkl`.

## 2. Kiến trúc AI pipeline
`ai_pipeline.py` load CSV export, phân tích history/feedback, chạy safety review trước recommendation, chạy workout generator, plan adjustment và coach explanation.

## 3. File input cần có
Các CSV trong `exports/csv/`.

## 4. Cách chạy từng module
Các module là Python functions có thể import từ package `ai`.

## 5. Cách chạy ai_pipeline.py
```bash
python ai/ai_pipeline.py
python ai/ai_pipeline.py --sample-size 100
python ai/ai_pipeline.py --sample-size all
python ai/ai_pipeline.py --user-id U000001
```

## 6. Rule-based recommendation logic
Safety first, sau đó xét pain, completion, RPE, fatigue, difficulty feedback, sentiment và skipped rate.

## 7. Workout generator logic
Lọc exercise theo goal, level, equipment và contraindication, sau đó chọn bài theo movement pattern / muscle balance. Full Body ưu tiên lower, push, pull, core; Upper Lower và Push Pull Legs dùng target theo từng ngày. Generator không chọn bài `Avoid`; bài `Review` chỉ dùng fallback khi thiếu lựa chọn an toàn.

## 8. History analyzer logic
Tính completion, set completion, skipped/partial rate, RPE, fatigue, pain rate và trend.

## 9. Feedback analyzer logic
Tổng hợp sentiment, liked/disliked exercises, too easy/hard, pain-related exercises và requested actions.

## 10. Safety review logic
So khớp injuries với contraindications/joint stress, pain areas, pain feedback, complexity và training level.

## 11. AI Coach / RAG logic
Demo text response có kiểm soát từ context; không chẩn đoán y khoa và không bịa dữ liệu. Câu trả lời bám theo `recommended_action`, `reason_codes`, safety status, risk flags, completion, RPE, fatigue và pain rate.

## 12. Evaluation metrics
invalid recommendation, unsafe recommendation, schema error, missing explanation, action distribution, safety distribution, adjustment distribution, empty plan/session, duplicate exercise trong session, safety block, average recommendation confidence và average safety risk score.

## 13. PASS / PASS WITH NOTES / NEED FIX
PASS khi unsafe=0, invalid=0, schema_error=0, missing_explanation=0, empty_generated_plan=0, empty_exercise_session=0 và duplicate_exercise_in_session=0.

## 14. Giới hạn hiện tại
Chưa train model, chưa dùng vector database, AI Coach vẫn là rule-based explanation. Output `ai_outputs/ml_signal_samples.json` chỉ là dữ liệu trung gian để chuẩn bị Stage 6B ML Training Dataset Builder.

## 15. Hướng phát triển tiếp theo
Stage 6B có thể dùng `ml_signal_samples.json` để xây training dataset cho recommendation/preference/safety risk model. Sau đó mới thêm API backend, retrieval index, LLM JSON guardrails và offline evaluation mở rộng.

## 16. Stage 6A revision notes
Plan Adjustment hiện nhận `safety_review` thật từ pipeline, không còn giả định mọi bài đều Safe. Nếu safety là Review/Avoid hoặc có flag rủi ro chính, action tăng độ khó/volume sẽ bị chặn và chuyển sang review/giảm độ khó phù hợp.
