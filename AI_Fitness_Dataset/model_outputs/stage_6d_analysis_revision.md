# Phân tích Hiện trạng Mô hình và Kiến trúc Stage 6D

## 1. Phân tích Hiện trạng Mô hình

### 1.1 Recommendation Model — Advisory Model

Recommendation Model hiện đạt:

```text
Accuracy : 0.8267
Macro F1 : 0.4122
```

Khoảng cách giữa Accuracy và Macro F1 là dấu hiệu mạnh của class imbalance và/hoặc việc model học yếu ở các lớp thiểu số. Nói cách khác, model có thể dự đoán khá tốt trên các lớp xuất hiện nhiều như `Keep` và `Reduce Difficulty`, nhưng chưa học đều các action ít mẫu như:

```text
Increase Difficulty
Replace Exercise
Reduce Volume
Review Safety
```

Điều này không có nghĩa model vô dụng. Nó cho thấy model phù hợp hơn với vai trò **advisory model**: đưa ra gợi ý ban đầu dựa trên dữ liệu history, feedback và profile, nhưng không nên là nơi quyết định cuối cùng.

Trong Stage 6D, Recommendation Model nên được dùng như một nguồn tín hiệu trong Hybrid Decision Engine. Final action bắt buộc phải đi qua:

```text
Hybrid Decision Engine
Rule-Based Safety Lock
```

Đặc biệt, mọi action kiểu:

```text
Increase Difficulty
Increase Volume
```

không được áp dụng trực tiếp nếu safety layer phát hiện rủi ro.

### 1.2 Preference Model — Proxy Leakage Risk

Preference Model hiện đạt:

```text
Accuracy : 1.0000
Macro F1 : 1.0000
```

Kết quả này rất cao, nhưng không nên diễn giải là model đã hiểu đầy đủ sở thích tập luyện của user trong mọi ngữ cảnh. Cách diễn giải chính xác hơn là: **Preference Model có rủi ro proxy leakage rất cao**.

Các feature như:

```text
rating
sentiment
enjoyment_rating
exercise_enjoyment
requested_action
difficulty_feedback
progression_preference
```

có quan hệ rất gần với `exercise_preference`. Ví dụ, nếu một feedback có `rating = 5`, `sentiment = Positive`, `requested_action = Keep`, thì model có thể suy ra `Like` khá dễ. Đây là tín hiệu hợp lệ nếu mục tiêu là phân tích preference sau khi user đã phản hồi, nhưng nó không chứng minh model dự đoán tốt trong trường hợp user chưa từng tương tác.

Vì vậy, Preference Model nên dùng trong các tình huống:

```text
User đã có feedback-like signals
User đã có lịch sử rating/sentiment/enjoyment
Hệ thống cần ranking hoặc điều chỉnh bài dựa trên phản hồi đã quan sát
```

Không nên dùng Preference Model làm model chính cho cold-start user. Với cold-start user, nên dùng chiến lược:

```text
rule-based filtering
content-based recommendation
goal / level / equipment matching
safety-first constraints
```

### 1.3 Safety Model — Auxiliary Safety Signal

Safety Model hiện đạt:

```text
Accuracy              : 1.0000
Macro F1              : 1.0000
Monitor/Review recall : 1.0000
```

Kết quả này cũng cần được hiểu thận trọng. Nếu `safety_label` được sinh từ các rule như `risk_score`, `risk_flag_count`, `pain_rate`, và những feature này vẫn được đưa vào training, thì Safety Model có thể đang học lại logic của Rule-Based Safety Engine.

Cách gọi chính xác hơn là:

```text
auxiliary safety signal
rule distillation model
```

Model này có thể hữu ích như một tín hiệu phụ trong hệ thống, ví dụ để xếp hạng mức rủi ro hoặc hỗ trợ kiểm tra tự động. Tuy nhiên, nó không thay thế được Rule-Based Safety Engine, vì hard safety constraints trong fitness cần rõ ràng, có thể kiểm soát và ưu tiên tuyệt đối.

Kết luận cho Safety Model:

```text
ML Safety hỗ trợ đánh giá
Rule-Based Safety Engine kiểm duyệt cuối
Hard safety constraints luôn có quyền cao nhất
```

## 2. Kiến trúc Tích hợp Đề xuất cho Stage 6D

### 2.1 Luồng tổng thể

Stage 6D nên triển khai theo hướng **guarded ML integration**. Luồng tổng thể nên là:

```text
Input user / profile / history / feedback
↓
Feature Builder
↓
ML Recommendation + ML Preference + ML Safety
↓
Hybrid Decision Engine
↓
Rule-Based Safety Lock
↓
Final Recommendation
↓
Prediction Logging
```

Trong kiến trúc này, ML không tự quyết định toàn bộ kết quả. ML tạo tín hiệu cá nhân hóa, còn Hybrid Decision Engine tổng hợp các tín hiệu đó với rule hiện có. Cuối cùng, Rule-Based Safety Lock kiểm duyệt action trước khi trả về final recommendation.

### 2.2 Thứ tự quyền ưu tiên

Thứ tự quyền ưu tiên nên rõ ràng:

```text
Rule-Based Safety Lock
>
Rule-Based Safety Engine
>
ML Safety
>
ML Recommendation / ML Preference
```

Viết ngắn gọn hơn:

```text
Rule-Based Safety Lock > ML outputs
```

Điều này nghĩa là nếu ML đề xuất tăng độ khó nhưng rule safety phát hiện rủi ro, hệ thống phải ưu tiên safety.

### 2.3 Ví dụ Safety Override

Ví dụ bắt buộc trong Stage 6D:

```text
ML Recommendation : Increase Difficulty
ML Safety         : Safe
Rule Safety       : Review
Final Action      : Review Safety
```

Lý do: dù ML Safety dự đoán `Safe`, Rule-Based Safety Engine đã phát hiện tình huống cần `Review`. Vì vậy Rule-Based Safety Lock phải override action tăng độ khó.

Một ví dụ khác:

```text
ML Recommendation : Increase Volume
ML Preference     : Like
ML Safety         : Monitor
Rule Safety       : Avoid
Final Action      : Review Safety / Replace Exercise
```

Trong fitness, tín hiệu user thích bài tập không được vượt qua constraint an toàn.

## 3. Monitoring và Tối ưu Sau Tích hợp

### 3.1 Permutation Feature Importance

Permutation Feature Importance nên được thêm sau khi tích hợp để đánh giá Recommendation Model rõ hơn. Phương pháp này không “giải mã tuyệt đối” mô hình, nhưng giúp ước lượng feature nào ảnh hưởng nhiều đến performance.

Nó đặc biệt hữu ích vì Recommendation Model hiện dùng `HistGradientBoostingClassifier`, trong khi feature importance trực tiếp chưa khả dụng trong report hiện tại.

Các feature cần theo dõi gồm:

```text
pain_rate
average_rpe
average_fatigue
completion_rate
set_completion_rate
skipped_rate
safety_status
risk_score
sentiment_positive_count
sentiment_negative_count
too_easy_count
too_hard_count
```

Nếu permutation importance cho thấy model phụ thuộc quá nhiều vào một vài feature proxy hoặc bỏ qua safety/history signals quan trọng, cần điều chỉnh feature set hoặc training dataset.

### 3.2 Production Logging

Stage 6D nên log đầy đủ cả raw ML prediction và final decision sau override. Log tối thiểu nên gồm:

```text
user_id
exercise_id
raw_ml_recommendation
ml_recommendation_confidence
ml_preference_prediction
ml_safety_prediction
rule_safety_status
risk_score
final_action
was_overridden
override_reason
user_feedback_after_action
timestamp
```

Điểm quan trọng: production log chưa phải ground truth ngay lập tức. Ground truth mới cần đến từ phản hồi thực tế sau hành động, ví dụ:

```text
rating
completion
pain report
adherence
exercise preference
session RPE
fatigue after session
```

Vì vậy log nên được thiết kế để nối prediction với outcome sau đó, không chỉ lưu prediction tại thời điểm đề xuất.

### 3.3 Retraining về sau

Retraining nên dựa trên dữ liệu thật tích lũy sau Stage 6D, đặc biệt là các case hiện còn ít mẫu:

```text
Increase Difficulty
Replace Exercise
Reduce Volume
Review Safety
Avoid
```

Khi có dữ liệu thực tế, nên đánh giá lại:

```text
macro_f1
balanced_accuracy
recall cho class safety-sensitive
unsafe_prediction_count_before_override
unsafe_prediction_count_after_override
override rate
```

Nếu hệ thống thấy override rate cao, điều đó có thể nghĩa là Recommendation Model thường đề xuất action không phù hợp với safety constraints. Khi đó cần retrain hoặc chỉnh Hybrid Decision Engine.

## 4. Kết luận

Stage 6D nên triển khai theo hướng **guarded ML integration**:

```text
ML hỗ trợ cá nhân hóa và gợi ý.
Rule-based safety kiểm duyệt cuối.
Prediction logging tạo nền dữ liệu thực tế cho retraining.
```

Các model Stage 6C có thể dùng để tích hợp thử, nhưng không nên diễn giải quá mạnh:

```text
Recommendation Model: advisory, vì macro F1 thấp ở class thiểu số.
Preference Model: hữu ích khi có feedback-like signals, không phù hợp làm cold-start model chính.
Safety Model: auxiliary/rule-distillation signal, không thay thế hard safety rules.
```

Quyết định cuối cùng trong hệ thống fitness phải luôn ưu tiên an toàn:

```text
Final Recommendation = ML personalization + Hybrid decision + Rule-Based Safety Lock
```
