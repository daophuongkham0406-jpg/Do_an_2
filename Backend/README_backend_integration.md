# Backend + Frontend AI Integration

## 1. Backend Purpose

Backend Flask exposes a safe API layer for the FIT ME web page. The frontend calls Flask, and Flask calls `AI_Fitness_Dataset` Stage 6D. The frontend never loads `.pkl` model files directly.

## 2. Install Dependencies

```powershell
cd D:\git_hub\Do_an_2
.\.venv\Scripts\Activate.ps1
pip install -r Backend\requirements.txt
```

Required ML dependencies include `pandas`, `numpy`, `scikit-learn`, and `joblib`.

## 3. Run Flask

```powershell
cd D:\git_hub\Do_an_2
.\.venv\Scripts\Activate.ps1
python Backend\app.py
```

Flask runs on:

```text
http://localhost:5000
```

## 4. API Endpoints

```text
GET  /api/ml/health
POST /api/ml/generate-plan
```

## 5. Example Request

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/ml/generate-plan" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"goal":"Tăng cơ","level":"Trung bình","height":170,"weight":65,"age":24,"equipment":"Phòng Gym đầy đủ","duration_days":7,"note":"đau lưng nhẹ"}'
```

## 6. Frontend Call

`Fontend/function_proc/lotrinh.js` calls:

```text
http://localhost:5000/api/ml/generate-plan
```

The backend returns both:

- `plan`: stable API response shape with `final_action`, `decision_source`, and explanations.
- `plan_data`: UI-compatible shape used by the existing `renderPlan(...)` function.

## 7. AI Dataset Connection

`Backend/services/ml_integration_service.py` loads:

```text
AI_Fitness_Dataset/ml_integration/web_adapter.py
```

The adapter calls the Stage 6D integration pipeline through `run_for_user(...)`, loads CSV data, loads the model bundle once, runs ML + rule safety + hybrid decision, then formats the result for the web.

## 8. Current Mode

Current mode: Real Stage 6D adapter.

If ML dependencies are missing, install `Backend/requirements.txt` before testing `generate-plan`.

## 9. Prediction Logs

Web calls append JSONL logs to:

```text
AI_Fitness_Dataset/integration_outputs/web_prediction_logs.jsonl
```

Prediction log chưa phải ground truth cho đến khi user gửi feedback sau buổi tập.

## 10. Known Limitations

The existing page still has older secondary calls to `http://localhost:5001` for apply-plan, check-in, nutrition, and active-plan workflows. The AI generation button is integrated with Flask `5000`; migrating every legacy endpoint is a separate follow-up.

## 11. Next Steps

1. Install backend dependencies.
2. Run Flask on port `5000`.
3. Open `http://localhost:5173/lotrinh.html`.
4. Test the button `Tạo Lộ Trình Bằng AI`.
