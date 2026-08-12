# Stage 5 Statistics Report

## 1. Executive Summary
Statistics Status: **PASS**
Ready for Stage 6 AI: **YES**
Risk Level: **Low**

## 2. Dataset Overview
| table | rows | columns | primary_key | unique_primary_keys | duplicate_primary_keys | blank_primary_keys | memory_size_bytes | file_size_bytes | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exercises | 350 | 45 | exercise_id | 350 | 0 | 0 | 1468910 | 641716 | PASS |
| users | 500 | 32 | user_id | 500 | 0 | 0 | 1108626 | 233165 | PASS |
| workout_plans | 1000 | 27 | plan_id | 1000 | 0 | 0 | 2007735 | 500856 | PASS |
| workout_plan_items | 17634 | 32 | plan_item_id | 17634 | 0 | 0 | 50173435 | 19892520 | PASS |
| workout_history_sessions | 18380 | 30 | history_session_id | 18380 | 0 | 0 | 34810643 | 3953086 | PASS |
| workout_history_items | 80634 | 28 | history_item_id | 80634 | 0 | 0 | 144683666 | 18481047 | PASS |
| workout_history_summary | 1000 | 18 | summary_id | 1000 | 0 | 0 | 1111676 | 104825 | PASS |
| user_feedback | 14500 | 28 | feedback_id | 14500 | 0 | 0 | 31589556 | 7033589 | PASS |

## 3. Missing Values Summary
| table | column | rows | missing_count | missing_percent | missing_type | severity | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| workout_history_items | actual_load_kg | 80634 | 80634 | 100.0 | Expected Missing | PASS | Missing is expected for this context. |
| workout_plan_items | duration_seconds | 17634 | 17634 | 100.0 | Expected Missing | PASS | Missing is expected for this context. |
| user_feedback | exercise_id | 14500 | 5500 | 37.931 | Expected Missing | PASS | Optional feedback scope columns may be blank for General/Plan/Session feedback. |
| user_feedback | history_item_id | 14500 | 5500 | 37.931 | Expected Missing | PASS | Optional feedback scope columns may be blank for General/Plan/Session feedback. |
| user_feedback | plan_item_id | 14500 | 5500 | 37.931 | Expected Missing | PASS | Optional feedback scope columns may be blank for General/Plan/Session feedback. |
| workout_history_items | exercise_enjoyment | 80634 | 4737 | 5.875 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| workout_history_items | technique_quality | 80634 | 4737 | 5.875 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| workout_history_items | actual_rpe | 80634 | 4737 | 5.875 | Expected Missing | PASS | Missing is expected for this context. |
| workout_history_items | difficulty_rating | 80634 | 4737 | 5.875 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| user_feedback | history_session_id | 14500 | 1400 | 9.655 | Expected Missing | PASS | Optional feedback scope columns may be blank for General/Plan/Session feedback. |
| workout_history_sessions | fatigue_after | 18380 | 1084 | 5.898 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| workout_history_sessions | session_rpe | 18380 | 1084 | 5.898 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| user_feedback | plan_id | 14500 | 400 | 2.759 | Expected Missing | PASS | Optional feedback scope columns may be blank for General/Plan/Session feedback. |
| workout_history_summary | fatigue_after | 1000 | 58 | 5.8 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| workout_history_summary | avg_enjoyment | 1000 | 58 | 5.8 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| workout_history_summary | session_rpe | 1000 | 58 | 5.8 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| workout_history_summary | avg_difficulty | 1000 | 58 | 5.8 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| exercises | range_of_motion_type | 350 | 19 | 5.429 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| exercises | load_position | 350 | 11 | 3.143 | Acceptable Missing | PASS | Low/acceptable missing rate. |
| exercises | resistance_profile | 350 | 0 | 0.0 | No Missing | PASS | No missing values. |

## 4. Duplicate Summary
| table | column_or_key | duplicate_count | duplicate_percent | duplicate_type | severity | note |
| --- | --- | --- | --- | --- | --- | --- |
| exercises | exercise_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| users | user_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| workout_plans | plan_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| workout_plan_items | plan_item_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| workout_history_sessions | history_session_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| workout_history_items | history_item_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| workout_history_summary | summary_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| user_feedback | feedback_id | 0 | 0.0 | Hard Duplicate | PASS | Primary key duplicate check. |
| exercises | exercise_name | 0 | 0.0 | Soft Duplicate | PASS | Duplicate names may be aliases or real duplicates. |
| workout_plan_items | plan_id+week_number+day_number+exercise_id | 0 | 0.0 | Expected Repetition | PASS | Same exercise can appear in repeated weeks/days; validator already checks order collisions. |
| workout_history_items | history_session_id+exercise_id | 0 | 0.0 | Suspicious Repetition | PASS | Same exercise repeated inside one logged session. |
| user_feedback | feedback_text | 11041 | 76.145 | Expected Repetition | PASS | unique_ratio=0.239; text templates may repeat in synthetic data. |

## 5. Exercise Statistics
- Exercise count: 350
- Category distribution: `{'Resistance Training': 279, 'Bodyweight': 71}`
- Difficulty distribution: `{'Beginner': 152, 'Intermediate': 141, 'Advanced': 57}`

## 6. User Statistics
- User count: 500
- Goal distribution: `{'Athletic Performance': 75, 'Muscle Gain': 70, 'General Fitness': 69, 'Strength': 68, 'Fat Loss': 60, 'Muscular Endurance': 58, 'Mobility and Flexibility': 54, 'Rehabilitation and Joint Health': 46}`
- Training level distribution: `{'Advanced': 176, 'Intermediate': 171, 'Beginner': 153}`

## 7. Workout Plan Statistics
- Plan count: 1000
- Plan items count: 17634
- Items per plan: `{'min': 2, 'mean': 17.634, 'max': 48}`
- Unique plan structures: 590

## 8. Workout History Statistics
- Session count: 18380
- Item count: 80634
- Completion status distribution: `{'Completed': 14857, 'Partial': 2439, 'Skipped': 1084}`
- Pain session percent: 2.873%

## 9. User Feedback Statistics
- Feedback count: 14500
- Scope distribution: `{'Exercise': 9000, 'Session': 4100, 'Plan': 1000, 'General': 400}`
- Sentiment distribution: `{'Positive': 8771, 'Neutral': 3771, 'Negative': 1958}`
- Feedback text unique ratio: 0.239

## 10. Relationship Coverage
| coverage_metric | source_table | target_table | source_count | covered_count | uncovered_count | coverage_percent | status | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| users_with_plans | users | workout_plans | 500 | 500 | 0 | 100.0 | Excellent Coverage | Users represented in workout plans. |
| users_with_history | users | workout_history_sessions | 500 | 500 | 0 | 100.0 | Excellent Coverage | Users represented in workout history. |
| users_with_feedback | users | user_feedback | 500 | 500 | 0 | 100.0 | Excellent Coverage | Users represented in feedback. |
| exercises_used_in_plan_items | exercises | workout_plan_items | 350 | 221 | 129 | 63.143 | Moderate Coverage | Exercise library coverage in generated plans. |
| exercises_used_in_history_items | exercises | workout_history_items | 350 | 220 | 130 | 62.857 | Moderate Coverage | Exercise library coverage in history. |
| exercises_used_in_feedback | exercises | user_feedback | 350 | 220 | 130 | 62.857 | Moderate Coverage | Exercise library coverage in feedback. |
| plans_with_items | workout_plans | workout_plan_items | 1000 | 1000 | 0 | 100.0 | Excellent Coverage | Plans with prescribed items. |
| plans_with_history | workout_plans | workout_history_sessions | 1000 | 1000 | 0 | 100.0 | Excellent Coverage | Plans with logged history. |
| plans_with_feedback | workout_plans | user_feedback | 1000 | 1000 | 0 | 100.0 | Excellent Coverage | Plans with feedback context. |
| history_sessions_with_items | workout_history_sessions | workout_history_items | 18380 | 18380 | 0 | 100.0 | Excellent Coverage | Sessions with item-level logs. |
| history_items_with_feedback | workout_history_items | user_feedback | 80634 | 9000 | 71634 | 11.162 | Needs Improvement | History item coverage in explicit feedback; low is normal because feedback is sampled. |

## 11. Data Balance Assessment
Core history and feedback distributions are inside target ranges. User coverage is complete. Exercise coverage is strong for plans/history and moderate for explicit feedback, which is expected because feedback is sampled.

## 12. AI Training Risk Assessment
Risk level is **Low**. Blocking issues: 0.

## 13. Recommendations
- No blocking or major improvement recommendation.

## 14. Final Stage 5 Status
Statistics Status: **PASS**
Ready for Stage 6 AI: **YES**
