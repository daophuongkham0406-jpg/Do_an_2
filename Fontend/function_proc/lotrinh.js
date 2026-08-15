// ════════════════════════════════════════════════════════════════
// lotrinh.js — Bản hoàn chỉnh
// Thay đổi: 4 gói 7/14/21/30 ngày, lưu tạm draft vào localStorage
// ════════════════════════════════════════════════════════════════
const AI_SERVER_URL = "http://localhost:5001";
const BACKEND_API_URL = "http://localhost:5000";
const TODAY = new Date().toISOString().split("T")[0];
const WEEKDAY_LABELS = {
  1: "Thứ 2",
  2: "Thứ 3",
  3: "Thứ 4",
  4: "Thứ 5",
  5: "Thứ 6",
  6: "Thứ 7",
  7: "Chủ nhật",
};

let USER_ID = "guest";
try {
  const userStr = localStorage.getItem("loggedInUser");
  if (userStr) {
    const userObj = JSON.parse(userStr);
    USER_ID = userObj._id || userObj.id || userObj.user_id || userObj.userid || "guest";
    console.log("👤 USER_ID:", USER_ID);
  }
} catch (e) {
  console.error("Lỗi đọc user:", e);
}

// Key lưu draft vào localStorage
const DRAFT_KEY = `fitme_draft_plan_${USER_ID}`;

let currentDisplayDayIndex = 0;
let selectedDays           = 7;
let currentPlanData        = null;
let currentPlanId          = null;
let todayNutrition         = { calories: 0, protein: 0, carbs: 0, fat: 0 };
let todayTarget            = { calories: 2000, protein: 130, carbs: 250, fat: 60 };
let todayIsRest            = false;
let planStartDateStr       = null;
let lastAiPlanResponse     = null;
let planTextRefreshTried   = false;

// ════════════════════════════════════════
// CHỌN ĐỘ DÀI LỘ TRÌNH (7/14/21/30 ngày)
// ════════════════════════════════════════
function selectDur(el, days) {
  if (el.classList.contains("disabled")) return;
  document.querySelectorAll(".dur-btn").forEach(b => b.classList.remove("active"));
  el.classList.add("active");
  selectedDays = days;
  updateWeekdayHint();
}

function unlockLongPlans(planType) {
  document.querySelectorAll(".dur-btn.disabled").forEach(b => {
    b.classList.remove("disabled");
    const lock = b.querySelector(".lock");
    if (lock) lock.remove();
    const days = parseInt(b.dataset.days);
    b.onclick = () => selectDur(b, days);
  });
  const hint = document.getElementById("durationHint");
  if (hint) {
    const planLabel = planType === "vip_3month" ? "Premium 3 Tháng" : "Premium 1 Tháng";
    hint.innerHTML = `✅ <span style="color:#ffd700;font-weight:bold;">👑 ${planLabel}</span> — Mọi tính năng đã mở khóa!`;
  }
}

async function checkPremiumStatus() {
  const userStr = localStorage.getItem("loggedInUser");
  if (!userStr) return;
  const localUser = JSON.parse(userStr);
  const isPremium = localUser.isPremium === true || localUser.role === "premium";

  try {
    const uid = localUser._id || localUser.id;
    if (uid) {
      const res  = await fetch(`http://localhost:5000/api/payment/status/${uid}`);
      const data = await res.json();
      if (data.isPremium) {
        localUser.isPremium = true;
        localStorage.setItem("loggedInUser", JSON.stringify(localUser));
        unlockLongPlans(data.plan);
        return;
      }
    }
  } catch (e) {
    console.warn("Không kiểm tra được premium:", e);
  }

  if (isPremium) unlockLongPlans();
}
checkPremiumStatus();

// ════════════════════════════════════════
// BMI LIVE PREVIEW
// ════════════════════════════════════════
function updateBmiPreview() {
  const h = parseFloat(document.getElementById("height").value);
  const w = parseFloat(document.getElementById("weight").value);
  const previewEl = document.getElementById("bmiPreview");
  if (!previewEl) return;
  if (!h || !w || h < 100 || w < 20) { previewEl.style.display = "none"; return; }
  const bmi = (w / (h / 100) ** 2).toFixed(1);
  let cat = "", cls = "";
  if (bmi < 18.5)      { cat = "Thiếu cân"; cls = "bmi-under"; }
  else if (bmi < 25)   { cat = "Bình thường"; cls = "bmi-ok"; }
  else if (bmi < 30)   { cat = "Thừa cân"; cls = "bmi-over"; }
  else                 { cat = "Béo phì"; cls = "bmi-obese"; }
  previewEl.style.display = "flex";
  previewEl.innerHTML = `<span class="bmi-num ${cls}">${bmi}</span><span class="bmi-cat-lbl ${cls}">${cat}</span>`;
}

document.addEventListener("DOMContentLoaded", () => {
  const hInput = document.getElementById("height");
  const wInput = document.getElementById("weight");
  if (hInput) hInput.addEventListener("input", updateBmiPreview);
  if (wInput) wInput.addEventListener("input", updateBmiPreview);
  setupWeekdayPicker();
});

// ════════════════════════════════════════
// NÚT TẠO LỘ TRÌNH
// ════════════════════════════════════════
document.getElementById("btn-generate").addEventListener("click", async () => {
  const goal      = document.getElementById("goal").value;
  const level     = document.getElementById("level").value;
  const userInfo  = document.getElementById("userInfo").value;
  const height    = document.getElementById("height").value;
  const weight    = document.getElementById("weight").value;
  const age       = document.getElementById("age").value;
  const survey    = collectSurveyPayload();

  if (!height || !weight || !age) {
    showToast("⚠️ Vui lòng nhập chiều cao, cân nặng và tuổi!", "error");
    return;
  }
  if (!survey.available_training_day_numbers.length) {
    showToast("⚠️ Vui lòng chọn ít nhất 1 ngày rảnh trong tuần!", "error");
    return;
  }

  try {
    const bmiRes  = await fetch(`${AI_SERVER_URL}/api/analyze-bmi`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ height, weight, age, goal, level }),
    });
    const bmiData = await bmiRes.json();
    if (bmiData.need_advice) {
      showBmiAdviceModal(
        bmiData,
        () => {
          const finalGoal = bmiData.suggested_goal || goal;
          document.getElementById("goal").value = finalGoal;
          doGeneratePlan(finalGoal, level, userInfo, height, weight, age, survey);
        },
        () => doGeneratePlan(goal, level, userInfo, height, weight, age, survey)
      );
      return;
    }
  } catch (e) {
    console.warn("BMI check lỗi:", e);
  }

  doGeneratePlan(goal, level, userInfo, height, weight, age, survey);
});

function collectSurveyPayload() {
  const valueOf = (id, fallback = "") => document.getElementById(id)?.value || fallback;
  const selectedWeekdays = getSelectedWeekdays();
  return {
    gender: valueOf("gender", "Prefer not to say"),
    training_days_per_week: selectedWeekdays.length || Number(valueOf("trainingDays", 3)),
    available_training_days: selectedWeekdays.map(day => WEEKDAY_LABELS[day]),
    available_training_day_numbers: selectedWeekdays,
    session_duration_minutes: Number(valueOf("sessionMinutes", 60)),
    intensity_preference: valueOf("intensityPreference", "Vừa phải"),
    priority_muscles: valueOf("priorityMuscles", ""),
    avoid_notes: valueOf("avoidNotes", ""),
  };
}

function setupWeekdayPicker() {
  document.querySelectorAll(".weekday-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      btn.classList.toggle("active");
      const trainingDaysInput = document.getElementById("trainingDays");
      if (trainingDaysInput) trainingDaysInput.value = Math.max(1, getSelectedWeekdays().length);
      updateWeekdayHint();
    });
  });
  updateWeekdayHint();
}

function getSelectedWeekdays() {
  return [...document.querySelectorAll(".weekday-btn.active")]
    .map(btn => Number(btn.dataset.weekday))
    .filter(day => day >= 1 && day <= 7)
    .sort((a, b) => a - b);
}

function setSelectedWeekdays(days) {
  const normalized = new Set((days || []).map(Number).filter(day => day >= 1 && day <= 7));
  document.querySelectorAll(".weekday-btn").forEach(btn => {
    btn.classList.toggle("active", normalized.has(Number(btn.dataset.weekday)));
  });
  const trainingDaysInput = document.getElementById("trainingDays");
  if (trainingDaysInput) trainingDaysInput.value = Math.max(1, normalized.size || Number(trainingDaysInput.value || 3));
  updateWeekdayHint();
}

function updateWeekdayHint() {
  const hint = document.getElementById("weekdayHint");
  if (!hint) return;
  const selectedWeekdays = getSelectedWeekdays();
  if (!selectedWeekdays.length) {
    hint.textContent = "Chọn ít nhất 1 ngày rảnh để AI xếp lịch tập.";
    return;
  }
  const labels = selectedWeekdays.map(day => WEEKDAY_LABELS[day]).join(", ");
  hint.textContent = `Lộ trình ${selectedDays} ngày sẽ xếp ngày tập vào: ${labels}. Các ngày còn lại là nghỉ/phục hồi.`;
}

// ════════════════════════════════════════
// MODAL TƯ VẤN BMI
// ════════════════════════════════════════
function showBmiAdviceModal(bmiData, onAccept, onReject) {
  const flagIcon  = { underweight:"⚠️", overweight:"📊", obese:"🔴" }[bmiData.flag] || "📊";
  const flagColor = { underweight:"#4da8ff", overweight:"#e8ff47", obese:"#ff6b6b" }[bmiData.flag] || "#e8ff47";

  const modal = document.createElement("div");
  modal.id = "bmiAdviceModal";
  modal.className = "bmi-advice-overlay";
  modal.innerHTML = `
    <div class="bmi-advice-box">
      <div class="bmi-advice-header">
        <span class="bmi-advice-icon">${flagIcon}</span>
        <div>
          <div class="bmi-advice-title">Phân tích chỉ số BMI</div>
          <div class="bmi-advice-sub">Trước khi tạo lộ trình</div>
        </div>
      </div>
      <div class="bmi-score-row">
        <div class="bmi-score-num" style="color:${flagColor}">${bmiData.bmi}</div>
        <div class="bmi-score-info">
          <div class="bmi-score-cat" style="color:${flagColor}">${bmiData.category}</div>
          <div class="bmi-score-desc">Chỉ số khối cơ thể (BMI)</div>
        </div>
      </div>
      <div class="bmi-advice-text">${bmiData.advice}</div>
      ${bmiData.suggested_goal && bmiData.suggested_goal !== bmiData.original_goal ? `
        <div class="bmi-suggestion-box">
          <span class="bmi-sug-label">Gợi ý điều chỉnh mục tiêu</span>
          <div class="bmi-sug-row">
            <span class="bmi-sug-old">❌ ${bmiData.original_goal}</span>
            <span class="bmi-sug-arrow">→</span>
            <span class="bmi-sug-new">✅ ${bmiData.suggested_goal}</span>
          </div>
        </div>` : ""}
      <div class="bmi-advice-actions">
        <button class="bmi-btn-accept" id="bmiAccept">✅ Đồng ý, điều chỉnh mục tiêu</button>
        <button class="bmi-btn-reject" id="bmiReject">Giữ mục tiêu ban đầu và tiếp tục</button>
      </div>
    </div>`;

  document.body.appendChild(modal);
  requestAnimationFrame(() => modal.classList.add("open"));
  document.getElementById("bmiAccept").onclick = () => { modal.remove(); onAccept(); };
  document.getElementById("bmiReject").onclick = () => { modal.remove(); onReject(); };
}

// ════════════════════════════════════════
// GỌI API TẠO LỘ TRÌNH
// ════════════════════════════════════════
async function doGeneratePlan(goal, level, userInfo, height, weight, age, survey = {}) {
  document.getElementById("plan-title").innerText = `LỘ TRÌNH ${goal.toUpperCase()} — ${selectedDays} NGÀY`;
  document.getElementById("plan-sub").innerText   = `${level} · ${height}cm · ${weight}kg · ${age} tuổi`;

  const container = document.getElementById("plan-container");
  container.innerHTML = `
    <div class="empty-state">
      <div class="loading-spinner"></div>
      <p>AI đang phân tích và tạo lộ trình ${selectedDays} ngày cho bạn...</p>
      <p style="font-size:12px;margin-top:6px;opacity:0.5">${goal} · ${level} · ${height}cm · ${weight}kg</p>
    </div>`;

  const btn = document.getElementById("btn-generate");
  btn.disabled  = true;
  btn.innerText = "Đang tạo...";
  document.getElementById("progressWrap").classList.remove("show");
  currentPlanData = null;
  currentPlanId   = null;
  lastAiPlanResponse = null;

  // Xoá draft cũ khi bắt đầu tạo mới
  localStorage.removeItem(DRAFT_KEY);

  try {
    const controller = new AbortController();
    const timeoutId  = setTimeout(() => controller.abort(), 900000);

    const response = await fetch(`${BACKEND_API_URL}/api/ml/generate-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        goal,
        level,
        note: [userInfo, survey.avoid_notes].filter(Boolean).join(". "),
        userInfo,
        height,
        weight,
        age,
        duration_days: selectedDays,
        ...survey,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData = {};
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = {};
      }
      throw new Error(errorData.message || errorData.error || `Mã lỗi server: ${response.status}`);
    }

    const data = await response.json();
    if (data.status === "OK" && data.plan_data) {
      currentPlanData = data.plan_data;
      lastAiPlanResponse = data;

      // ✅ LƯU DRAFT VÀO LOCALSTORAGE
      saveDraftPlan(currentPlanData, { goal, level, userInfo, height, weight, age, survey });

      renderPlan(data.plan_data, container);
      appendPlanActions(container, data.plan_data);
    } else if (data.message || data.error) {
      throw new Error(data.message || data.error);
    }
  } catch (error) {
    let errorMsg = error.message;
    if (error.name === "AbortError") errorMsg = "⏳ AI đang suy nghĩ quá lâu. Vui lòng thử lại!";
    container.innerHTML = `
      <div class="empty-state" style="color:#ff6060;">
        ❌ Lỗi: ${errorMsg}<br>
        <button class="btn" style="margin-top:15px;" onclick="location.reload()">Tải lại trang</button>
      </div>`;
  } finally {
    btn.disabled  = false;
    btn.innerText = "⚡ Tạo Lộ Trình Bằng AI";
  }
}

// ════════════════════════════════════════
// LƯU / ĐỌC DRAFT VÀO LOCALSTORAGE
// ════════════════════════════════════════
function saveDraftPlan(planData, formInputs) {
  try {
    const draft = {
      planData,
      formInputs,
      savedAt: Date.now(),
    };
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    console.log("💾 Đã lưu draft lộ trình vào localStorage");
  } catch (e) {
    console.warn("Không lưu được draft:", e);
  }
}

function loadDraftPlan() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const draft = JSON.parse(raw);
    // Draft hết hạn sau 2 giờ
    if (Date.now() - draft.savedAt > 2 * 60 * 60 * 1000) {
      localStorage.removeItem(DRAFT_KEY);
      return null;
    }
    return draft;
  } catch (e) {
    return null;
  }
}

function clearDraftPlan() {
  localStorage.removeItem(DRAFT_KEY);
}

// ════════════════════════════════════════
// PHỤC HỒI DRAFT KHI VÀO TRANG
// ════════════════════════════════════════
function restoreDraftIfNeeded() {
  // Chỉ phục hồi nếu chưa có lộ trình active
  if (currentPlanId) return;

  const draft = loadDraftPlan();
  if (!draft || !draft.planData) return;

  const minutesAgo = Math.floor((Date.now() - draft.savedAt) / 60000);

  // Hiện banner thông báo có draft
  const container = document.getElementById("plan-container");
  const banner    = document.createElement("div");
  banner.id       = "draftBanner";
  banner.style.cssText = `
    background:rgba(232,255,71,0.08); border:1px solid rgba(232,255,71,0.3);
    border-radius:12px; padding:16px 20px; margin-bottom:16px;
    display:flex; align-items:center; justify-content:space-between; gap:12px;
  `;
  banner.innerHTML = `
    <div>
      <div style="font-size:13px; font-weight:700; color:#e8ff47; margin-bottom:4px;">
        📋 Bạn có lộ trình chưa lưu (${minutesAgo} phút trước)
      </div>
      <div style="font-size:12px; color:#64748b;">
        "${draft.planData.plan_name || 'Lộ trình AI'}" — ${draft.planData.duration_days || selectedDays} ngày
      </div>
    </div>
    <div style="display:flex; gap:8px; flex-shrink:0;">
      <button onclick="applyDraft()" style="
        background:#e8ff47; color:#0a0a0a; border:none;
        padding:8px 16px; border-radius:8px; font-weight:700;
        font-size:12px; cursor:pointer;
      ">📂 Khôi phục</button>
      <button onclick="dismissDraft()" style="
        background:transparent; color:#64748b; border:1px solid #334155;
        padding:8px 12px; border-radius:8px; font-size:12px; cursor:pointer;
      ">✕ Bỏ qua</button>
    </div>
  `;

  container.insertBefore(banner, container.firstChild);
}

function applyDraft() {
  const draft = loadDraftPlan();
  if (!draft || !draft.planData) return;

  currentPlanData = draft.planData;

  // Điền lại form
  if (draft.formInputs) {
    const fi = draft.formInputs;
    if (fi.height)    document.getElementById("height").value    = fi.height;
    if (fi.weight)    document.getElementById("weight").value    = fi.weight;
    if (fi.age)       document.getElementById("age").value       = fi.age;
    if (fi.goal)      document.getElementById("goal").value      = fi.goal;
    if (fi.level)     document.getElementById("level").value     = fi.level;
    if (fi.userInfo)  document.getElementById("userInfo").value  = fi.userInfo;
    if (fi.survey?.available_training_day_numbers) setSelectedWeekdays(fi.survey.available_training_day_numbers);
    updateBmiPreview();
  }

  // Chọn lại duration button
  const totalDays = draft.planData.duration_days || draft.planData.days?.length || 7;
  selectedDays    = totalDays;
  document.querySelectorAll(".dur-btn").forEach(b => {
    b.classList.remove("active");
    if (parseInt(b.dataset.days) === totalDays && !b.classList.contains("disabled")) {
      b.classList.add("active");
    }
  });

  document.getElementById("plan-title").innerText = draft.planData.plan_name || `LỘ TRÌNH ${totalDays} NGÀY`;

  const container = document.getElementById("plan-container");
  const banner    = document.getElementById("draftBanner");
  if (banner) banner.remove();

  renderPlan(draft.planData, container);
  appendPlanActions(container, draft.planData);

  showToast("✅ Đã khôi phục lộ trình chưa lưu!", "success");
}

function dismissDraft() {
  clearDraftPlan();
  const banner = document.getElementById("draftBanner");
  if (banner) banner.remove();
}

// ════════════════════════════════════════
// RENDER KẾ HOẠCH
// ════════════════════════════════════════
function renderPlan(planData, container, progress = null) {
  container.innerHTML = "";
  const totalDays = planData.days.length;
  let completedDaysCount = 0;
  currentDisplayDayIndex = 0;

  const defaultCalWorkout  = planData.daily_calories_workout  || 2200;
  const defaultCalRest     = planData.daily_calories_rest     || 1900;
  const defaultProtWorkout = planData.daily_protein_workout   || 150;
  const defaultProtRest    = planData.daily_protein_rest      || 120;

  planData.days.forEach((day, index) => {
    const unlocked = isDayUnlocked(day.day_number);
    const dayCard  = document.createElement("div");
    dayCard.className       = `day-card open ${index === 0 ? "" : "hidden-day"} ${!unlocked ? "future-locked" : ""}`;
    dayCard.dataset.dayNumber = day.day_number;

    let exProgress = {}, pd = null;
    if (progress) {
      pd = progress.find(p => p.day_number === day.day_number);
      if (pd?.exercises) pd.exercises.forEach(e => { exProgress[e.name] = e.completed; });
    }

    const targetCal  = Number((pd?.target_calories) || day.target_calories || (day.is_rest ? defaultCalRest : defaultCalWorkout));
    const targetProt = Number((pd?.target_protein)  || day.target_protein  || (day.is_rest ? defaultProtRest : defaultProtWorkout));
    const targetCarbs = Number(day.target_carbs || 0);
    const targetFat = Number(day.target_fat || 0);

    let dayDone = false;
    if (day.is_rest) {
      const localRestState = localStorage.getItem(`rest_${currentPlanId}_day_${day.day_number}`);
      dayDone = localRestState !== null ? localRestState === "true" : (pd?.day_done === true);
    } else {
      if (day.exercises?.length > 0) dayDone = day.exercises.every(ex => exProgress[ex.name] === true);
    }
    const totalExercisesInDay = day.is_rest ? 0 : (day.exercises?.length || 0);
    const completedExercisesInDay = day.is_rest ? 0 : (pd?.completed_exercises_count ?? day.exercises?.filter(ex => exProgress[ex.name] === true).length ?? 0);
    if (dayDone) { dayCard.classList.add("day-done-card"); completedDaysCount++; }

    dayCard.innerHTML = `
      <div class="day-header">
        <div class="day-header-left">
          <span class="day-num-badge">Ngày ${day.day_number}</span>
          <span class="day-name">${day.day_name || ""}</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          ${day.is_rest ? "" : `<span class="day-ex-count" id="day-ex-count-${day.day_number}">${completedExercisesInDay}/${totalExercisesInDay} bài</span>`}
          <span class="day-focus">${day.is_rest ? "NGHỈ NGƠI" : day.focus || ""}</span>
          <span class="day-check-badge ${dayDone ? "show" : ""}">✓ Hoàn thành</span>
        </div>
      </div>
      <div class="day-nutrition-bar">
        <div class="dn-item"><span class="dn-icon">🔥</span><span class="dn-label">Calo mục tiêu</span><span class="dn-val">${targetCal} <small>kcal</small></span></div>
        <div class="dn-divider"></div>
        <div class="dn-item"><span class="dn-icon">💪</span><span class="dn-label">Protein mục tiêu</span><span class="dn-val">${targetProt}g <small>protein</small></span></div>
        <div class="dn-divider"></div>
        ${targetCarbs ? `<div class="dn-item"><span class="dn-icon">🍚</span><span class="dn-label">Carb gợi ý</span><span class="dn-val">${targetCarbs}g</span></div><div class="dn-divider"></div>` : ""}
        ${targetFat ? `<div class="dn-item"><span class="dn-icon">🥑</span><span class="dn-label">Fat gợi ý</span><span class="dn-val">${targetFat}g</span></div><div class="dn-divider"></div>` : ""}
        <div class="dn-item"><span class="dn-icon">${day.is_rest ? "🛌" : "🏋️"}</span><span class="dn-label">Loại ngày</span><span class="dn-val" style="color:${day.is_rest ? "#a78bfa" : "#4ecdc4"}">${day.is_rest ? "Nghỉ ngơi" : "Ngày tập"}</span></div>
      </div>
      <div class="day-body" id="day-body-${day.day_number}"></div>`;

    container.appendChild(dayCard);
    const body = document.getElementById(`day-body-${day.day_number}`);

    if (day.is_rest) {
      body.innerHTML = `
        <div class="rest-check-box ${dayDone ? "completed" : ""}" id="rest-btn-${day.day_number}">
          <div class="ex-checkbox" style="background:${dayDone ? "#4ecdc4" : "transparent"};border-color:${dayDone ? "#4ecdc4" : "var(--border-hover)"};color:${dayDone ? "#0a0a0a" : "transparent"}">${dayDone ? "✓" : ""}</div>
          <span style="font-weight:600;color:${dayDone ? "#4ecdc4" : "inherit"}">Xác nhận đã nghỉ ngơi & phục hồi</span>
        </div>`;
      const restBtn = document.getElementById(`rest-btn-${day.day_number}`);
      restBtn.addEventListener("click", e => {
        e.stopPropagation();
        checkinExercise(currentPlanId, day.day_number, "RestDay", !restBtn.classList.contains("completed"), restBtn, dayCard, true);
      });
    } else {
            // ... trong hàm renderPlan, phần xử lý ngày tập (else của day.is_rest)
      day.exercises.forEach((ex) => {
          const done = exProgress[ex.name] || false;
          const exerciseImages = getExerciseImages(ex);
          const thumbImage = exerciseImages[0]?.url || "";
          const exEl = document.createElement("div");
          
          // Nếu chưa áp dụng lộ trình (currentPlanId là null), thêm class 'preview-only'
          const isPreview = !currentPlanId;
          exEl.className = `routine-item${done ? " completed" : ""}${isPreview ? " preview-only" : ""}`;
          
          exEl.innerHTML = `
              <div class="ex-checkbox-wrap">
                  <div class="ex-checkbox">${done ? "✓" : ""}</div>
              </div>
              ${thumbImage ? `<button class="routine-thumb" type="button" title="Xem ảnh hướng dẫn"><img src="${thumbImage}" alt="${ex.name_vi || ex.name}"></button>` : `<button class="routine-thumb no-image" type="button" title="Chưa có ảnh">🏋️</button>`}
              <div class="routine-item-info">
                  <h4>${ex.name_vi || ex.name}</h4>
                  <div class="tags">
                      <span class="tag tag-muscle">${ex.muscle || "Toàn thân"}</span>
                      ${ex.goal ? `<span class="tag tag-goal">${ex.goal}</span>` : ""}
                      <span class="tag tag-sets">${ex.sets} sets × ${ex.reps} reps</span>
                      <span class="tag tag-rest">⏱ ${ex.rest}s</span>
                  </div>
              </div>
              <button class="btn-ex-complete" type="button" ${done ? "disabled" : ""}>${done ? "Đã hoàn thành" : "Hoàn thành"}</button>
              <button class="btn-ex-detail" title="Xem chi tiết">›</button>`;

          const completeExercise = (e) => {
              e.stopPropagation();
              
              // NẾU LÀ BẢN XEM TRƯỚC -> HIỆN THÔNG BÁO, KHÔNG CHO CLICK
              if (isPreview) {
                  showToast("📍 Nhấn 'Áp dụng lộ trình này' để bắt đầu tập và tích hoàn thành!", "error");
                  return;
              }
              if (exEl.classList.contains("completed")) {
                  showToast("✅ Bài này đã hoàn thành và không thể hoàn tác.", "success");
                  return;
              }

              checkinExercise(
                  currentPlanId,
                  day.day_number,
                  ex.name,
                  true,
                  exEl,
                  dayCard,
                  false
              );
          };

          // XỬ LÝ SỰ KIỆN CLICK CHECKBOX / NÚT HOÀN THÀNH
          exEl.querySelector(".ex-checkbox-wrap").addEventListener("click", completeExercise);
          exEl.querySelector(".btn-ex-complete").addEventListener("click", completeExercise);

          // Xem chi tiết thì vẫn cho xem bình thường ở cả 2 chế độ
          exEl.querySelector(".routine-thumb").onclick = (e) => { e.stopPropagation(); openExerciseModal(ex); };
          exEl.querySelector(".routine-item-info").onclick = (e) => { e.stopPropagation(); openExerciseModal(ex); };
          exEl.querySelector(".btn-ex-detail").onclick = (e) => { e.stopPropagation(); openExerciseModal(ex); };

          body.appendChild(exEl);
      });
    }

    const isDayLocked = pd?.is_locked === true;
    if (isDayLocked) dayCard.classList.add("day-locked");

    if (currentPlanId) {
      const lockDayWrap = document.createElement("div");
      lockDayWrap.style.marginTop = "16px";
      if (isDayLocked) {
        lockDayWrap.innerHTML = `<div class="locked-success-msg">✅ Ngày này đã được chốt sổ!</div>`;
      } else if (!unlocked) {
        lockDayWrap.innerHTML = `<div class="locked-future-msg">⏳ Bài tập sẽ mở khóa vào ngày thứ ${day.day_number} của lộ trình</div>`;
      } else {
        lockDayWrap.innerHTML = `<button class="btn-lock-target" onclick="askLockPlanDay('${currentPlanId}', ${day.day_number})">🔒 HOÀN THÀNH & CHỐT SỔ NGÀY ${day.day_number}</button>`;
      }
      body.appendChild(lockDayWrap);
    }
  });

  const navWrap = document.createElement("div");
  navWrap.className = "day-nav-controls";
  navWrap.innerHTML = `
    <button class="btn-nav-day" id="btn-prev-day" onclick="navigateDay(-1)" disabled>← Ngày trước</button>
    <button class="btn-nav-day" id="btn-next-day" onclick="navigateDay(1)" ${totalDays <= 1 ? "disabled" : ""}>Ngày tiếp theo →</button>`;
  container.appendChild(navWrap);

  updateProgressBar(completedDaysCount, totalDays);
}

function planNeedsTextRefresh(planData) {
  const staleMarkers = [
    "Thực hiện bước này chậm",
    "Chuẩn bị tư thế cho bài",
    "Thực hiện pha chính của bài",
    "Giữ kỹ thuật ổn định trong bước này",
    "Thực hiện pha chính dứt khoát",
    "Chuẩn bị đúng tư thế",
    "Nắm hoặc giữ chắc điểm tựa",
  ];
  return (planData?.days || []).some(day =>
    (day.exercises || []).some(ex =>
      !getExerciseImages(ex).length ||
      (ex.steps || []).some(step => staleMarkers.some(marker => String(step || "").includes(marker)))
    )
  );
}

async function refreshActivePlanTextIfNeeded(planId, planData) {
  if (!planId || planTextRefreshTried || !planNeedsTextRefresh(planData)) return false;
  planTextRefreshTried = true;
  try {
    const res = await fetch(`${BACKEND_API_URL}/api/plans/refresh-ai-plan-text/${planId}`, { method: "POST" });
    const data = await res.json();
    if (!data.success || !data.plan) return false;
    currentPlanData = data.plan.plan_data;
    const container = document.getElementById("plan-container");
    renderPlan(currentPlanData, container, data.plan.daily_progress);
    appendPlanActions(container, currentPlanData);
    document.getElementById("plan-action-buttons").style.display = "none";
    document.getElementById("btn-cancel-plan").classList.add("show");
    switchToNutritionSidebar(currentPlanData);
    showToast("✅ Đã làm mới hướng dẫn và ảnh bài tập.", "success");
    return true;
  } catch (e) {
    console.warn("Không làm mới được hướng dẫn bài tập:", e);
    return false;
  }
}

// ════════════════════════════════════════
// CHUYỂN NGÀY
// ════════════════════════════════════════
window.navigateDay = function(direction) {
  const cards     = document.querySelectorAll(".day-card");
  const totalDays = cards.length;
  if (cards[currentDisplayDayIndex]) cards[currentDisplayDayIndex].classList.add("hidden-day");
  currentDisplayDayIndex = Math.max(0, Math.min(totalDays - 1, currentDisplayDayIndex + direction));
  if (cards[currentDisplayDayIndex]) cards[currentDisplayDayIndex].classList.remove("hidden-day");
  document.getElementById("btn-prev-day").disabled = currentDisplayDayIndex === 0;
  document.getElementById("btn-next-day").disabled = currentDisplayDayIndex === totalDays - 1;
};

// ════════════════════════════════════════
// NÚT ÁP DỤNG / TẠO LẠI
// ════════════════════════════════════════
function appendPlanActions(container, planData) {
  const wrap  = document.createElement("div");
  wrap.className = "plan-actions";
  wrap.id        = "plan-action-buttons";
  wrap.innerHTML = `
    <button class="btn-apply" id="btn-apply">💾 Áp dụng lộ trình này</button>
    <button class="btn-retry" id="btn-retry">🔄 Tạo lại</button>`;
  container.appendChild(wrap);

  const cancelBtn = document.createElement("button");
  cancelBtn.className = "btn-danger";
  cancelBtn.id        = "btn-cancel-plan";
  cancelBtn.style.display = currentPlanId ? "block" : "none";
  cancelBtn.innerHTML = "🗑️ HỦY LỘ TRÌNH ĐANG TẬP";
  cancelBtn.onclick   = askCancelPlan;
  container.appendChild(cancelBtn);

  document.getElementById("btn-apply").addEventListener("click", () => savePlan(planData));
  document.getElementById("btn-retry").addEventListener("click", () => {
    clearDraftPlan();
    document.getElementById("btn-generate").click();
  });
}

// ════════════════════════════════════════
// LƯU LỘ TRÌNH
// ════════════════════════════════════════
async function savePlan(planData) {
  const height = document.getElementById("height").value;
  const weight = document.getElementById("weight").value;
  const age    = document.getElementById("age").value;
  const btn    = document.getElementById("btn-apply");
  if (btn) { btn.disabled = true; btn.innerText = "Đang lưu..."; }

  try {
    const res = await fetch(`${BACKEND_API_URL}/api/plans/save-ai-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan_data: planData,
        userId: USER_ID,
        height,
        weight,
        age,
        source: lastAiPlanResponse?.source || "ai_exercises_csv_rule_engine",
        input_snapshot: lastAiPlanResponse?.input || collectSurveyPayload(),
        ai_decision: lastAiPlanResponse?.ai_decision || {},
      }),
    });
    const result = await res.json();

    if (result.success) {
      currentPlanId = result.plan_id;

      // Xoá draft sau khi lưu thành công
      clearDraftPlan();

      const tObj = new Date();
      planStartDateStr = `${tObj.getDate().toString().padStart(2,"0")}/${(tObj.getMonth()+1).toString().padStart(2,"0")}/${tObj.getFullYear()}`;

      showToast("✅ Lộ trình đã kích hoạt! Bắt đầu tập thôi!", "success");
      updateProgressBar(0, planData.duration_days || selectedDays);

      document.getElementById("plan-action-buttons").style.display = "none";
      document.getElementById("btn-cancel-plan").classList.add("show");
      document.getElementById("btn-generate").disabled  = true;
      document.getElementById("btn-generate").innerText = "LỘ TRÌNH ĐANG CHẠY";
      document.getElementById("btn-generate").style.opacity = "0.5";

      switchToNutritionSidebar(planData);
      renderPlan(planData, document.getElementById("plan-container"));
    } else {
      showToast("❌ Lỗi lưu: " + result.error, "error");
    }
  } catch (e) {
    showToast("❌ Không kết nối được server", "error");
  } finally {
    if (btn && btn.style.display !== "none") {
      btn.disabled  = false;
      btn.innerText = "💾 Áp dụng lộ trình này";
    }
  }
}

// ════════════════════════════════════════
// SIDEBAR DINH DƯỠNG
// ════════════════════════════════════════
function switchToNutritionSidebar(planData) {
  const sidebar = document.querySelector(".app-sidebar");
  if (!sidebar) return;

  const todayDayNum = currentDisplayDayIndex + 1;
  const todayDay    = planData.days ? (planData.days.find(d => d.day_number === todayDayNum) || planData.days[0]) : null;
  todayIsRest       = todayDay ? Boolean(todayDay.is_rest) : false;

  const calWorkout  = Number(planData.daily_calories_workout) || 2200;
  const calRest     = Number(planData.daily_calories_rest)    || 1900;
  const protWorkout = Number(planData.daily_protein_workout)  || 150;
  const protRest    = Number(planData.daily_protein_rest)     || 120;
  const defaultWorkoutDay = (planData.days || []).find(d => !d.is_rest) || {};
  const defaultRestDay = (planData.days || []).find(d => d.is_rest) || {};

  todayTarget.calories = todayIsRest
    ? (Number(todayDay?.target_calories) || calRest)
    : (Number(todayDay?.target_calories) || calWorkout);
  todayTarget.protein = todayIsRest
    ? (Number(todayDay?.target_protein) || protRest)
    : (Number(todayDay?.target_protein) || protWorkout);
  todayTarget.carbs = todayIsRest
    ? (Number(todayDay?.target_carbs) || Number(defaultRestDay.target_carbs) || 220)
    : (Number(todayDay?.target_carbs) || Number(defaultWorkoutDay.target_carbs) || 280);
  todayTarget.fat = todayIsRest
    ? (Number(todayDay?.target_fat) || Number(defaultRestDay.target_fat) || 55)
    : (Number(todayDay?.target_fat) || Number(defaultWorkoutDay.target_fat) || 70);

  sidebar.innerHTML = `
    <div class="nutr-sidebar">
      <div class="nutr-header">
        <h2>🥗 Dinh dưỡng hôm nay</h2>
        <p class="nutr-date">${new Date().toLocaleDateString("vi-VN",{weekday:"long",day:"numeric",month:"long"})}</p>
      </div>
      <div class="nutr-target-card">
        <div class="nutr-target-row"><span class="nutr-target-lbl">🔥 Calo mục tiêu</span><span class="nutr-target-val">${todayTarget.calories} kcal</span></div>
        <div class="nutr-target-row"><span class="nutr-target-lbl">💪 Protein mục tiêu</span><span class="nutr-target-val">${todayTarget.protein}g</span></div>
        <div class="nutr-target-row"><span class="nutr-target-lbl">🍚 Carb mục tiêu</span><span class="nutr-target-val">${todayTarget.carbs}g</span></div>
        <div class="nutr-target-row"><span class="nutr-target-lbl">🥑 Fat mục tiêu</span><span class="nutr-target-val">${todayTarget.fat}g</span></div>
        <div class="nutr-day-type ${todayIsRest ? "rest" : "workout"}">${todayIsRest ? "🛌 Ngày nghỉ — ăn nhẹ hơn" : "🏋️ Ngày tập — nạp đủ năng lượng"}</div>
      </div>
      <div class="nutr-progress-wrap">
        <div class="nutr-progress-row"><span>Calo đã nạp</span><span id="ntCalDone">0 / ${todayTarget.calories} kcal</span></div>
        <div class="nutr-bar-bg"><div class="nutr-bar-fill cal-bar" id="ntCalBar" style="width:0%"></div></div>
        <div class="nutr-progress-row" style="margin-top:10px;"><span>Protein đã nạp</span><span id="ntProtDone">0 / ${todayTarget.protein}g</span></div>
        <div class="nutr-bar-bg"><div class="nutr-bar-fill prot-bar" id="ntProtBar" style="width:0%"></div></div>
        <div class="nutr-progress-row" style="margin-top:10px;"><span>Carb đã nạp</span><span id="ntCarbsDone">0 / ${todayTarget.carbs}g</span></div>
        <div class="nutr-bar-bg"><div class="nutr-bar-fill carbs-bar" id="ntCarbsBar" style="width:0%"></div></div>
        <div class="nutr-progress-row" style="margin-top:10px;"><span>Fat đã nạp</span><span id="ntFatDone">0 / ${todayTarget.fat}g</span></div>
        <div class="nutr-bar-bg"><div class="nutr-bar-fill fat-bar" id="ntFatBar" style="width:0%"></div></div>
      </div>
      <div id="nutritionStatusNotice" class="nutr-status-notice" style="display:none;"></div>
      <div class="nutr-tabs">
        <button class="nutr-tab on" data-tab="manual" onclick="switchNutrTab('manual',this)">✏️ Nhập tay</button>
        <button class="nutr-tab" data-tab="ai" onclick="switchNutrTab('ai',this)">🤖 Nhập món ăn</button>
      </div>
      <div class="nutr-tab-pane on" id="nutr-pane-manual">
        <div class="nutr-input-group"><label>Calories (kcal)</label><input type="number" id="ni_cal" placeholder="VD: 500" min="0" max="5000"></div>
        <div class="nutr-input-group"><label>Protein (g)</label><input type="number" id="ni_prot" placeholder="VD: 35" min="0" max="500"></div>
        <div class="nutr-input-group"><label>Carbs (g)</label><input type="number" id="ni_carbs" placeholder="VD: 60" min="0" max="800"></div>
        <div class="nutr-input-group"><label>Fat (g)</label><input type="number" id="ni_fat" placeholder="VD: 15" min="0" max="300"></div>
        <button class="nutr-btn-add" onclick="addManualNutrition()">+ Cộng vào hôm nay</button>
      </div>
      <div class="nutr-tab-pane" id="nutr-pane-ai">
        <div class="nutr-ai-hint">Nhập tên & lượng món ăn, AI sẽ tự tính dinh dưỡng cho bạn.</div>
        <textarea id="ni_food" class="nutr-food-input" placeholder="VD: 200g ức gà, 1 bát cơm trắng, 1 quả trứng luộc..." rows="3"></textarea>
        <button class="nutr-btn-analyze" id="btnAnalyzeFood" onclick="analyzeAndAddFood()">🔍 Phân tích & Thêm vào</button>
        <div id="foodAnalysisResult" class="food-analysis-result" style="display:none;"></div>
      </div>
      ${planData.nutrition_note ? `<div class="nutr-note-box"><span class="nutr-note-icon">💡</span><span>${planData.nutrition_note}</span></div>` : ""}
    </div>`;

  loadTodayNutrition();
}

function switchNutrTab(tabId, btn) {
  document.querySelectorAll(".nutr-tab").forEach(t => t.classList.remove("on"));
  document.querySelectorAll(".nutr-tab-pane").forEach(p => p.classList.remove("on"));
  btn.classList.add("on");
  document.getElementById("nutr-pane-" + tabId).classList.add("on");
}

async function addManualNutrition() {
  const cal   = parseFloat(document.getElementById("ni_cal").value) || 0;
  const prot  = parseFloat(document.getElementById("ni_prot").value) || 0;
  const carbs = parseFloat(document.getElementById("ni_carbs").value) || 0;
  const fat   = parseFloat(document.getElementById("ni_fat").value) || 0;
  if (!cal && !prot && !carbs && !fat) { showToast("⚠️ Vui lòng nhập ít nhất một chỉ số dinh dưỡng", "error"); return; }
  await saveNutritionToServer(cal, prot, carbs, fat, "Nhập tay");
  ["ni_cal","ni_prot","ni_carbs","ni_fat"].forEach(id => { const el = document.getElementById(id); if (el) el.value = ""; });
  showToast("✅ Đã cập nhật dinh dưỡng!", "success");
}

async function analyzeAndAddFood() {
  const foodTextEl = document.getElementById("ni_food");
  const foodText   = foodTextEl?.value.trim() || "";
  if (!foodText) { showToast("⚠️ Hãy nhập món ăn trước", "error"); return; }

  const btn       = document.getElementById("btnAnalyzeFood");
  const resultBox = document.getElementById("foodAnalysisResult");
  if (btn) { btn.disabled = true; btn.innerText = "⏳ Đang phân tích..."; }
  if (resultBox) resultBox.style.display = "none";

  try {
    const res  = await fetch(`${BACKEND_API_URL}/api/analyze-food`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ food_text: foodText, userId: USER_ID }),
    });
    const data = await res.json();
    if (!data.success || !data.data) { showToast("⚠️ " + (data.error || "Chưa đủ dữ liệu để phân tích món này"), "error"); return; }

    const { total, items, summary } = data.data;
    const needsManualInput = Boolean(data.data.needs_manual_input);
    const safeTotal = {
      calories: Number(total.calories) || 0,
      protein:  Number(total.protein)  || 0,
      carbs:    Number(total.carbs)    || 0,
      fat:      Number(total.fat)      || 0,
    };

    if (resultBox) {
      resultBox.style.display = "block";
      resultBox.innerHTML = `
        <div class="fa-summary">${summary || ""}</div>
        <div class="fa-items">${(items || []).map(item => `
          <div class="fa-item">
            <span class="fa-item-name">${item.name} <small>${item.amount}</small></span>
            <span class="fa-item-nums">${item.calories} kcal · ${item.protein}g P · ${item.carbs}g C · ${item.fat}g F</span>
          </div>`).join("")}</div>
        <div class="fa-total">
          <div class="fa-total-row"><span>🔥 Tổng Calories</span><strong>${safeTotal.calories} kcal</strong></div>
          <div class="fa-total-row"><span>💪 Protein</span><strong>${safeTotal.protein}g</strong></div>
          <div class="fa-total-row"><span>🍞 Carbs</span><strong>${safeTotal.carbs}g</strong></div>
          <div class="fa-total-row"><span>🧈 Fat</span><strong>${safeTotal.fat}g</strong></div>
        </div>
        ${needsManualInput ? `<div class="fa-manual-note">Bạn hãy nhập tay kcal, protein, carbs và fat nếu có nhãn dinh dưỡng hoặc khối lượng chính xác.</div>` : `<button class="nutr-btn-add" id="btnConfirmFood">✅ Thêm vào hôm nay</button>`}`;
      const confirmBtn = document.getElementById("btnConfirmFood");
      if (confirmBtn) {
        confirmBtn.onclick = () =>
          confirmAddFoodNutrition(safeTotal.calories, safeTotal.protein, safeTotal.carbs, safeTotal.fat);
      }
    }
  } catch (e) {
    showToast("❌ Lỗi kết nối AI", "error");
  } finally {
    if (btn) { btn.disabled = false; btn.innerText = "🔍 Phân tích & Thêm vào"; }
  }
}

async function confirmAddFoodNutrition(cal, prot, carbs, fat) {
  const foodEl = document.getElementById("ni_food");
  const note   = foodEl?.value || "";
  await saveNutritionToServer(cal, prot, carbs, fat, note);
  if (foodEl) foodEl.value = "";
  const resultBox = document.getElementById("foodAnalysisResult");
  if (resultBox) resultBox.style.display = "none";
  showToast("✅ Đã thêm dinh dưỡng từ món ăn!", "success");
}

async function saveNutritionToServer(cal, prot, carbs, fat, note) {
  try {
    const res  = await fetch(`${BACKEND_API_URL}/api/save-nutrition`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: USER_ID, date: TODAY, calories: cal, protein: prot, carbs, fat, note }),
    });
    const data = await res.json();
    if (data.success && data.today) { todayNutrition = data.today; updateNutritionUI(); }
  } catch (e) {
    todayNutrition.calories = (todayNutrition.calories || 0) + cal;
    todayNutrition.protein  = (todayNutrition.protein  || 0) + prot;
    todayNutrition.carbs    = (todayNutrition.carbs    || 0) + carbs;
    todayNutrition.fat      = (todayNutrition.fat      || 0) + fat;
    updateNutritionUI();
  }
}

async function loadTodayNutrition() {
  try {
    const res  = await fetch(`${BACKEND_API_URL}/api/get-nutrition?userId=${USER_ID}&date=${TODAY}`);
    const data = await res.json();
    todayNutrition = data;
    updateNutritionUI();
  } catch (e) {}
}

function updateNutritionUI() {
  const calDoneEl  = document.getElementById("ntCalDone");
  const protDoneEl = document.getElementById("ntProtDone");
  const carbsDoneEl = document.getElementById("ntCarbsDone");
  const fatDoneEl = document.getElementById("ntFatDone");
  const calBarEl   = document.getElementById("ntCalBar");
  const protBarEl  = document.getElementById("ntProtBar");
  const carbsBarEl = document.getElementById("ntCarbsBar");
  const fatBarEl = document.getElementById("ntFatBar");
  if (!calDoneEl || !todayTarget.calories) return;

  const currentCalories = Number(todayNutrition.calories) || 0;
  const currentProtein = Number(todayNutrition.protein) || 0;
  const currentCarbs = Number(todayNutrition.carbs) || 0;
  const currentFat = Number(todayNutrition.fat) || 0;
  const calPct  = Math.min(100, Math.round((currentCalories / todayTarget.calories) * 100));
  const protPct = Math.min(100, Math.round((currentProtein / todayTarget.protein)  * 100));
  const carbsPct = Math.min(100, Math.round((currentCarbs / todayTarget.carbs) * 100));
  const fatPct = Math.min(100, Math.round((currentFat / todayTarget.fat) * 100));

  calDoneEl.textContent  = `${Math.round(currentCalories)} / ${todayTarget.calories} kcal`;
  protDoneEl.textContent = `${Math.round(currentProtein)}g / ${todayTarget.protein}g`;
  if (carbsDoneEl) carbsDoneEl.textContent = `${Math.round(currentCarbs)}g / ${todayTarget.carbs}g`;
  if (fatDoneEl) fatDoneEl.textContent = `${Math.round(currentFat)}g / ${todayTarget.fat}g`;
  updateNutritionStatusNotice({ currentCalories, currentProtein, currentCarbs, currentFat });

  setTimeout(() => {
    if (calBarEl)  { calBarEl.style.width  = calPct  + "%"; calBarEl.style.background  = calPct  >= 100 ? "#4ecdc4" : ""; }
    if (protBarEl) { protBarEl.style.width = protPct + "%"; protBarEl.style.background = protPct >= 100 ? "#4ecdc4" : ""; }
    if (carbsBarEl) { carbsBarEl.style.width = carbsPct + "%"; carbsBarEl.style.background = carbsPct >= 100 ? "#4ecdc4" : ""; }
    if (fatBarEl) { fatBarEl.style.width = fatPct + "%"; fatBarEl.style.background = fatPct >= 100 ? "#4ecdc4" : ""; }
  }, 50);

  const nutrTabsBox = document.querySelector(".nutr-tabs");
  const nutrPanes   = document.querySelectorAll(".nutr-tab-pane");
  const oldLockBtn  = document.getElementById("btnLockNutrition");
  if (oldLockBtn) oldLockBtn.remove();

  if (todayNutrition.is_locked) {
    if (nutrTabsBox) nutrTabsBox.style.display = "none";
    nutrPanes.forEach(p => p.style.display = "none");
    const lockedMsg = document.createElement("div");
    lockedMsg.id        = "btnLockNutrition";
    lockedMsg.className = "locked-success-msg";
    lockedMsg.innerHTML = "✅ Đã chốt sổ dinh dưỡng hôm nay. Hẹn gặp bạn vào ngày mai!";
    document.querySelector(".nutr-sidebar")?.appendChild(lockedMsg);
  } else if (calPct >= 95 && protPct >= 95) {
    const lockBtn = document.createElement("button");
    lockBtn.id        = "btnLockNutrition";
    lockBtn.className = "btn-lock-target";
    lockBtn.innerHTML = "🔒 HOÀN THÀNH MỤC TIÊU HÔM NAY";
    lockBtn.onclick   = lockNutritionDay;
    document.querySelector(".nutr-sidebar")?.appendChild(lockBtn);
  }
}

// ════════════════════════════════════════
// CHECK-IN BÀI TẬP
// ════════════════════════════════════════
async function checkinExercise(planId, dayNumber, exName, completed, exEl, dayCard, isRest = false) {
  if (dayCard.classList.contains("day-locked")) { showToast("⚠️ Ngày này đã chốt sổ!", "error"); return; }

  if (isRest) {
    localStorage.setItem(`rest_${planId}_day_${dayNumber}`, completed);
    if (completed) {
      exEl.classList.add("completed"); exEl.querySelector(".ex-checkbox").textContent = "✓";
      dayCard.classList.add("day-done-card");
      const badge = dayCard.querySelector(".day-check-badge");
      if (badge) { badge.textContent = "✓ Hoàn thành"; badge.classList.add("show"); }
    } else {
      exEl.classList.remove("completed"); exEl.querySelector(".ex-checkbox").textContent = "";
      dayCard.classList.remove("day-done-card");
      const badge = dayCard.querySelector(".day-check-badge");
      if (badge) badge.classList.remove("show");
    }
  } else {
    if (!completed && exEl.classList.contains("completed")) {
      showToast("✅ Bài này đã hoàn thành và không thể hoàn tác.", "success");
      return;
    }
    if (completed) { exEl.classList.add("completed"); exEl.querySelector(".ex-checkbox").textContent = "✓"; }
    const completeBtn = exEl.querySelector(".btn-ex-complete");
    if (completeBtn) {
      completeBtn.textContent = "Đã hoàn thành";
      completeBtn.disabled = true;
    }
    const body    = document.getElementById(`day-body-${dayNumber}`);
    const exerciseItems = [...body.querySelectorAll(".routine-item")];
    const completedItems = exerciseItems.filter(el => el.classList.contains("completed")).length;
    const allDone = exerciseItems.length > 0 && completedItems === exerciseItems.length;
    updateDayExerciseCount(dayNumber, completedItems, exerciseItems.length);
    const badge   = dayCard.querySelector(".day-check-badge");
    if (allDone) {
      dayCard.classList.add("day-done-card");
      if (badge) { badge.textContent = "✓ Hoàn thành"; badge.classList.add("show"); }
    } else {
      dayCard.classList.remove("day-done-card");
      if (badge) badge.classList.remove("show");
    }
  }

  const totalDaysCount     = document.querySelectorAll(".day-card").length;
  const completedDaysCount = document.querySelectorAll(".day-done-card").length;
  updateProgressBar(completedDaysCount, totalDaysCount);

  if (completedDaysCount === totalDaysCount && totalDaysCount > 0) {
    showToast("🎉 Tuyệt vời! Bạn đã hoàn thành toàn bộ lộ trình!", "success");
  }

  try {
    const res = await fetch(`${BACKEND_API_URL}/api/plans/checkin-exercise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ planId, dayNumber, exerciseName: exName, completed }),
    });
    const data = await res.json();
    if (!data.success) showToast("⚠️ Chưa lưu được tiến độ: " + (data.error || "Lỗi máy chủ"), "error");
    if (data.day_progress) {
      updateDayExerciseCount(
        dayNumber,
        Number(data.day_progress.completed_exercises_count) || 0,
        Number(data.day_progress.total_exercises_count) || 0,
      );
    }
  } catch (e) {
    showToast("⚠️ Mất kết nối, tiến độ chỉ mới cập nhật trên màn hình.", "error");
  }
}

function updateNutritionStatusNotice(values) {
  const box = document.getElementById("nutritionStatusNotice");
  if (!box) return;

  const alerts = [];
  const calDiff = Math.round(values.currentCalories - todayTarget.calories);
  if (calDiff >= 100) {
    alerts.push(`<strong>Đã dư năng lượng ${calDiff} kcal.</strong> Bữa tiếp theo nên ưu tiên đồ nhẹ, ít dầu và giàu rau.`);
  } else if (calDiff >= 0) {
    alerts.push(`<strong>Đã đủ năng lượng hôm nay.</strong> Bạn nên giữ bữa còn lại nhẹ để không vượt mục tiêu.`);
  } else if (values.currentCalories >= todayTarget.calories * 0.9) {
    alerts.push(`Bạn sắp đủ năng lượng, còn khoảng <strong>${Math.abs(calDiff)} kcal</strong>.`);
  }

  const macroAlerts = [
    ["Protein", values.currentProtein, todayTarget.protein, "protein"],
    ["Carbs", values.currentCarbs, todayTarget.carbs, "carbs"],
    ["Fat", values.currentFat, todayTarget.fat, "fat"],
  ]
    .filter(([, current, target]) => target && current >= target)
    .map(([label, current, target, cls]) => `<span class="nutr-status-chip ${cls}">${label}: ${Math.round(current)}/${target}g</span>`);

  if (!alerts.length && !macroAlerts.length) {
    box.style.display = "none";
    box.innerHTML = "";
    return;
  }

  box.className = `nutr-status-notice ${calDiff >= 100 ? "over" : "enough"}`;
  box.innerHTML = `${alerts.map(text => `<div>${text}</div>`).join("")}${macroAlerts.length ? `<div class="nutr-status-chips">${macroAlerts.join("")}</div>` : ""}`;
  box.style.display = "flex";
}

function updateDayExerciseCount(dayNumber, completedCount, totalCount) {
  const countEl = document.getElementById(`day-ex-count-${dayNumber}`);
  if (countEl) countEl.textContent = `${completedCount}/${totalCount} bài`;
}

// ════════════════════════════════════════
// TIẾN ĐỘ & TOAST
// ════════════════════════════════════════
function updateProgressBar(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  document.getElementById("progressWrap").classList.add("show");
  document.getElementById("progressPct").textContent  = pct + "%";
  document.getElementById("progressBar").style.width  = pct + "%";
  document.getElementById("progressDays").textContent = `${done} / ${total} ngày hoàn thành`;
}

function showToast(msg, type = "success") {
  const t = document.createElement("div");
  t.className   = `toast ${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ════════════════════════════════════════
// HỦY LỘ TRÌNH
// ════════════════════════════════════════
function askCancelPlan() {
  const modal = document.getElementById("cancelPlanOverlay");
  if (modal) modal.classList.add("open");
}
function closeCancelModal() {
  const modal = document.getElementById("cancelPlanOverlay");
  if (modal) modal.classList.remove("open");
}
async function executeCancelPlan() {
  closeCancelModal();
  try {
    const res    = await fetch(`${BACKEND_API_URL}/api/plans/cancel-active/${USER_ID}`, { method: "DELETE" });
    const result = await res.json();
    if (result.success) {
      clearDraftPlan();
      showToast("Đã hủy lộ trình thành công.", "success");
      setTimeout(() => location.reload(), 1000);
    } else {
      showToast("Lỗi: " + (result.message || result.error), "error");
    }
  } catch (e) {
    showToast("Lỗi kết nối máy chủ.", "error");
  }
}

// ════════════════════════════════════════
// KIỂM TRA LỘ TRÌNH KHI VÀO TRANG
// ════════════════════════════════════════
async function checkActivePlanOnLoad() {
  try {
    const res  = await fetch(`${BACKEND_API_URL}/api/plans/get-active-plan?userId=${USER_ID}`);
    const data = await res.json();

    if (data.plan) {
      currentPlanId     = data.plan._id || data.plan.id;
      currentPlanData   = data.plan.plan_data;
      planStartDateStr  = data.plan.created_at;

      document.getElementById("plan-title").innerText = "LỘ TRÌNH ĐANG THỰC HIỆN";
      const container = document.getElementById("plan-container");

      renderPlan(currentPlanData, container, data.plan.daily_progress);
      appendPlanActions(container, currentPlanData);
      refreshActivePlanTextIfNeeded(currentPlanId, currentPlanData);

      document.getElementById("plan-action-buttons").style.display = "none";
      document.getElementById("btn-cancel-plan").classList.add("show");

      const btnGen = document.getElementById("btn-generate");
      btnGen.disabled  = true;
      btnGen.innerText = "LỘ TRÌNH ĐANG CHẠY";
      btnGen.style.opacity = "0.5";

      switchToNutritionSidebar(currentPlanData);

      // Xoá draft cũ vì đã có plan active
      clearDraftPlan();
    } else {
      // Không có plan active → kiểm tra draft
      restoreDraftIfNeeded();
    }
  } catch (e) {
    console.log("Không có lộ trình active:", e);
    restoreDraftIfNeeded();
  }
}
checkActivePlanOnLoad();

// ════════════════════════════════════════
// MODAL CHI TIẾT BÀI TẬP
// ════════════════════════════════════════
let exerciseImageIndex = 0;
let exerciseModalImages = [];

function resolveExerciseImageUrl(url) {
  const value = String(url || "").trim();
  if (!value) return "";
  if (/^https?:\/\//i.test(value) || value.startsWith("data:")) return value;
  if (value.includes("images/flat/") || value.includes("image/flat/") || /\.webp$/i.test(value)) {
    const filename = value.replace(/\\/g, "/").split("/").filter(Boolean).pop();
    return `${BACKEND_API_URL}/api/ml/exercise-image/${filename}`;
  }
  return `${BACKEND_API_URL}${value.startsWith("/") ? value : `/${value}`}`;
}

function getExerciseImages(ex) {
  const list = Array.isArray(ex?.images) ? ex.images : [];
  const images = list
    .map((item, index) => ({
      label: item.label || (index === 0 ? "Tư thế bắt đầu" : "Tư thế chính"),
      url: resolveExerciseImageUrl(item.url || item.path || item.filename || item),
    }))
    .filter(item => item.url);

  if (!images.length && ex?.image) {
    images.push({ label: "Minh họa", url: resolveExerciseImageUrl(ex.image) });
  }
  return images;
}

function renderExerciseImage() {
  const stage = document.getElementById("emImageStage");
  const img = document.getElementById("emImage");
  const label = document.getElementById("emImageLabel");
  const count = document.getElementById("emImageCount");
  const prev = document.getElementById("emImagePrev");
  const next = document.getElementById("emImageNext");
  if (!stage || !img || !label || !count || !prev || !next) return;

  if (!exerciseModalImages.length) {
    stage.classList.add("is-empty");
    img.removeAttribute("src");
    img.alt = "";
    label.textContent = "Chưa có ảnh hướng dẫn";
    count.textContent = "";
    prev.disabled = true;
    next.disabled = true;
    return;
  }

  const current = exerciseModalImages[exerciseImageIndex] || exerciseModalImages[0];
  stage.classList.remove("is-empty");
  img.src = current.url;
  img.alt = current.label;
  label.textContent = current.label;
  count.textContent = `${exerciseImageIndex + 1}/${exerciseModalImages.length}`;
  prev.disabled = exerciseModalImages.length <= 1;
  next.disabled = exerciseModalImages.length <= 1;
}

function changeExerciseImage(step) {
  if (exerciseModalImages.length <= 1) return;
  exerciseImageIndex = (exerciseImageIndex + step + exerciseModalImages.length) % exerciseModalImages.length;
  renderExerciseImage();
}

(function createExerciseModal() {
  const modalHTML = `
    <div id="exModalOverlay" class="ex-modal-overlay">
      <div class="ex-modal">
        <button class="ex-modal-close" id="exModalClose">✕</button>
        <div class="ex-modal-hero">
          <div class="ex-modal-icon" id="emIcon">🏋️</div>
          <div class="ex-modal-hero-info">
            <div class="ex-modal-muscle" id="emMuscle">NGỰC</div>
            <div class="ex-modal-name" id="emName">Tên bài tập</div>
            <div class="ex-modal-badges" id="emBadges"></div>
          </div>
        </div>
        <div class="em-image-viewer">
          <button class="em-image-nav" id="emImagePrev" type="button" title="Ảnh trước">‹</button>
          <div class="em-image-stage" id="emImageStage">
            <img id="emImage" alt="">
            <div class="em-image-empty">Chưa có ảnh hướng dẫn</div>
          </div>
          <button class="em-image-nav" id="emImageNext" type="button" title="Ảnh tiếp theo">›</button>
        </div>
        <div class="em-image-meta">
          <span id="emImageLabel">Minh họa</span>
          <span id="emImageCount"></span>
        </div>
        <div class="ex-modal-stats" id="emStats"></div>
        <div class="ex-modal-tabs">
          <button class="em-tab on" data-t="steps">Hướng dẫn</button>
          <button class="em-tab" data-t="muscles">Nhóm cơ</button>
          <button class="em-tab" data-t="tips">Lưu ý</button>
        </div>
        <div class="em-pane on" id="em-pane-steps"></div>
        <div class="em-pane" id="em-pane-muscles"></div>
        <div class="em-pane" id="em-pane-tips"></div>
      </div>
    </div>`;
  document.body.insertAdjacentHTML("beforeend", modalHTML);
  document.getElementById("exModalClose").onclick = closeExerciseModal;
  document.getElementById("emImagePrev").onclick = () => changeExerciseImage(-1);
  document.getElementById("emImageNext").onclick = () => changeExerciseImage(1);
  document.getElementById("exModalOverlay").addEventListener("click", e => { if (e.target === e.currentTarget) closeExerciseModal(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeExerciseModal(); });
  document.querySelectorAll(".em-tab").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".em-tab").forEach(t => t.classList.remove("on"));
      document.querySelectorAll(".em-pane").forEach(t => t.classList.remove("on"));
      btn.classList.add("on");
      document.getElementById("em-pane-" + btn.dataset.t).classList.add("on");
    };
  });
})();

function openExerciseModal(ex) {
  const diffLabel = { B:"Người mới", I:"Trung bình", A:"Nâng cao" };
  const diffCls   = { B:"badge-b", I:"badge-i", A:"badge-a" };
  const difficulty = ex.difficulty || diffLabel[ex.diff] || "Trung bình";
  const met = Number(ex.met || 0);
  exerciseModalImages = getExerciseImages(ex);
  exerciseImageIndex = 0;
  renderExerciseImage();
  document.getElementById("emIcon").textContent   = ex.icon || "🏋️";
  document.getElementById("emMuscle").textContent = (ex.muscle || "").toUpperCase();
  document.getElementById("emName").textContent   = ex.name_vi || ex.name;
  document.getElementById("emBadges").innerHTML   = `
    <span class="em-badge ${diffCls[ex.diff] || "badge-i"}">${difficulty}</span>
    ${ex.category ? `<span class="em-badge" style="background:rgba(77,160,255,.12);color:#4da0ff;border:1px solid rgba(77,160,255,.25)">${ex.category}</span>` : ""}
    ${ex.goal ? `<span class="em-badge" style="background:rgba(78,205,196,.12);color:#4ecdc4;border:1px solid rgba(78,205,196,.25)">${ex.goal}</span>` : ""}`;
  document.getElementById("emStats").innerHTML = `
    <div class="em-stat"><div class="em-stat-num">${ex.sets}</div><div class="em-stat-lbl">Sets</div></div>
    <div class="em-stat"><div class="em-stat-num">${ex.reps}</div><div class="em-stat-lbl">Reps</div></div>
    <div class="em-stat"><div class="em-stat-num">${ex.rest}s</div><div class="em-stat-lbl">Nghỉ</div></div>
    ${met ? `<div class="em-stat"><div class="em-stat-num">${met}</div><div class="em-stat-lbl">MET</div></div>` : ""}`;
  document.getElementById("em-pane-steps").innerHTML = ex.steps?.length
    ? `<ol class="em-steps">${ex.steps.map((s,i) => `<li class="em-step"><span class="em-step-num">0${i+1}</span><div class="em-step-text">${s}</div></li>`).join("")}</ol>`
    : `<p style="color:var(--text-muted);font-size:14px;padding:16px 0;">Chưa có hướng dẫn.</p>`;
  const muscles = [{ role:"Cơ chính", name:ex.muscle }];
  if (ex.body_part) muscles.push({ role:"Vùng cơ", name:ex.body_part });
  if (ex.muscle_keys) muscles.push({ role:"Mã nhóm cơ", name:ex.muscle_keys });
  if (ex.sec?.length) ex.sec.forEach(s => muscles.push({ role:"Cơ phụ", name:s }));
  document.getElementById("em-pane-muscles").innerHTML = `
    <div class="em-muscle-list">${muscles.map(m => `
      <div class="em-muscle-item">
        <div class="em-muscle-role">${m.role}</div>
        <div class="em-muscle-name">${m.name}</div>
      </div>`).join("")}</div>`;
  document.getElementById("em-pane-tips").innerHTML = ex.tips?.length
    ? `<ul class="em-tips">${ex.tips.map(t => `<li class="em-tip"><span class="em-tip-icon">⚡</span><span>${t}</span></li>`).join("")}</ul>`
    : `<p style="color:var(--text-muted);font-size:14px;padding:16px 0;">Không có lưu ý.</p>`;
  document.querySelectorAll(".em-tab").forEach(t => t.classList.remove("on"));
  document.querySelectorAll(".em-pane").forEach(t => t.classList.remove("on"));
  document.querySelector('.em-tab[data-t="steps"]').classList.add("on");
  document.getElementById("em-pane-steps").classList.add("on");
  document.getElementById("exModalOverlay").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeExerciseModal() {
  document.getElementById("exModalOverlay").classList.remove("open");
  document.body.style.overflow = "";
}

// ════════════════════════════════════════
// MODAL CHỐT SỔ
// ════════════════════════════════════════
let pendingLockPlanId = null, pendingLockDayNumber = null;

function askLockPlanDay(planId, dayNumber) {
  pendingLockPlanId    = planId;
  pendingLockDayNumber = dayNumber;
  const displaySpan = document.getElementById("lockDayNumDisplay");
  if (displaySpan) displaySpan.textContent = `Ngày ${dayNumber}`;
  const modal = document.getElementById("lockDayModalOverlay");
  if (modal) modal.classList.add("open");
}
function closeLockDayModal() {
  const modal = document.getElementById("lockDayModalOverlay");
  if (modal) modal.classList.remove("open");
  pendingLockPlanId = pendingLockDayNumber = null;
}
async function executeLockPlanDay() {
  const pId  = pendingLockPlanId  || currentPlanId;
  const dNum = pendingLockDayNumber || currentDisplayDayIndex + 1;
  if (!pId) { showToast("❌ Không tìm thấy ID lộ trình!", "error"); return; }
  closeLockDayModal();
  try {
    const res  = await fetch(`${BACKEND_API_URL}/api/plans/lock-day`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ planId: pId, plan_id: pId, dayNumber: dNum, day_number: dNum }),
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || "✅ Đã chốt sổ thành công!", "success");
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast("❌ Lỗi: " + (data.error || "Không rõ nguyên nhân"), "error");
    }
  } catch (e) {
    showToast("❌ Lỗi kết nối máy chủ", "error");
  }
}

async function lockNutritionDay() {
  try {
    const res  = await fetch(`${BACKEND_API_URL}/api/lock-nutrition`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: USER_ID, date: TODAY }),
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, "success");
      todayNutrition.is_locked = true;
      updateNutritionUI();
    }
  } catch (e) {
    showToast("Lỗi kết nối", "error");
  }
}

// ════════════════════════════════════════
// KIỂM TRA NGÀY MỞ KHÓA
// ════════════════════════════════════════
function isDayUnlocked(dayNumber) {
  if (!planStartDateStr) return true;
  const parts = planStartDateStr.split("/");
  if (parts.length !== 3) return true;
  const startDate = new Date(parts[2], parts[1] - 1, parts[0]);
  startDate.setHours(0, 0, 0, 0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.floor((today - startDate) / (1000 * 60 * 60 * 24));
  return dayNumber - 1 <= diffDays;
}

// ════════════════════════════════════════
// INJECT CSS
// ════════════════════════════════════════
(function injectCSS() {
  const s = document.createElement("style");
  s.textContent = `
    #bmiPreview { display:none; align-items:center; gap:10px; background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:8px; padding:10px 14px; margin-top:8px; }
    .bmi-num { font-size:22px; font-weight:800; } .bmi-cat-lbl { font-size:12px; font-weight:600; }
    .bmi-under{color:#4da8ff;} .bmi-ok{color:#4ecdc4;} .bmi-over{color:#e8ff47;} .bmi-obese{color:#ff6b6b;}
    .bmi-advice-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.8);backdrop-filter:blur(8px);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px;opacity:0;pointer-events:none;transition:opacity 0.25s;}
    .bmi-advice-overlay.open{opacity:1;pointer-events:all;}
    .bmi-advice-box{background:var(--bg-card,#161616);border:1px solid var(--border,#2a2a2a);border-radius:20px;padding:32px 28px;max-width:460px;width:100%;transform:scale(0.95);transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1);}
    .bmi-advice-overlay.open .bmi-advice-box{transform:scale(1);}
    .bmi-advice-header{display:flex;align-items:center;gap:14px;margin-bottom:24px;}
    .bmi-advice-icon{font-size:32px;} .bmi-advice-title{font-size:18px;font-weight:700;color:var(--text-primary,#f0f0f0);} .bmi-advice-sub{font-size:12px;color:var(--text-muted,#666);margin-top:3px;}
    .bmi-score-row{display:flex;align-items:center;gap:16px;background:rgba(255,255,255,0.03);border:1px solid var(--border,#2a2a2a);border-radius:12px;padding:16px 20px;margin-bottom:20px;}
    .bmi-score-num{font-size:40px;font-weight:800;line-height:1;} .bmi-score-cat{font-size:16px;font-weight:700;} .bmi-score-desc{font-size:11px;color:var(--text-muted,#666);margin-top:4px;}
    .bmi-advice-text{font-size:14px;line-height:1.7;color:var(--text-secondary,#ccc);margin-bottom:20px;}
    .bmi-suggestion-box{background:rgba(232,255,71,0.04);border:1px solid rgba(232,255,71,0.15);border-radius:10px;padding:14px 16px;margin-bottom:20px;}
    .bmi-sug-label{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted,#666);display:block;margin-bottom:10px;}
    .bmi-sug-row{display:flex;align-items:center;gap:10px;font-size:13px;font-weight:600;}
    .bmi-sug-old{color:#ff6b6b;text-decoration:line-through;} .bmi-sug-arrow{color:var(--text-muted,#666);} .bmi-sug-new{color:#4ecdc4;}
    .bmi-advice-actions{display:flex;flex-direction:column;gap:10px;}
    .bmi-btn-accept{width:100%;padding:14px;background:var(--accent,#e8ff47);color:#0a0a0a;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;font-family:inherit;}
    .bmi-btn-reject{width:100%;padding:12px;background:transparent;color:var(--text-muted,#666);border:1px solid var(--border,#2a2a2a);border-radius:10px;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;}
    .day-nutrition-bar{display:flex;align-items:center;background:rgba(255,255,255,0.015);border-bottom:1px solid var(--border,#2a2a2a);padding:10px 22px;}
    .dn-item{flex:1;display:flex;align-items:center;gap:7px;padding:4px 0;} .dn-icon{font-size:14px;} .dn-label{font-size:10px;color:var(--text-muted,#666);letter-spacing:0.5px;} .dn-val{font-size:13px;font-weight:700;color:var(--text-primary,#f0f0f0);margin-left:auto;} .dn-val small{font-size:9px;font-weight:400;color:var(--text-muted,#666);} .dn-divider{width:1px;height:28px;background:var(--border,#2a2a2a);margin:0 12px;}
    .nutr-sidebar{display:flex;flex-direction:column;gap:16px;}
    .nutr-header h2{font-size:18px;font-weight:700;letter-spacing:1px;color:var(--accent,#e8ff47);text-transform:uppercase;margin-bottom:4px;} .nutr-date{font-size:11px;color:var(--text-muted,#666);}
    .nutr-target-card{background:rgba(232,255,71,0.04);border:1px solid rgba(232,255,71,0.12);border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:10px;}
    .nutr-target-row{display:flex;justify-content:space-between;align-items:center;font-size:13px;} .nutr-target-lbl{color:var(--text-secondary,#aaa);} .nutr-target-val{font-weight:700;color:var(--accent,#e8ff47);}
    .nutr-day-type{font-size:11px;font-weight:600;padding:6px 10px;border-radius:6px;text-align:center;letter-spacing:0.5px;} .nutr-day-type.workout{background:rgba(78,205,196,0.1);color:#4ecdc4;} .nutr-day-type.rest{background:rgba(167,139,250,0.1);color:#a78bfa;}
    .nutr-progress-wrap{display:flex;flex-direction:column;gap:6px;} .nutr-progress-row{display:flex;justify-content:space-between;font-size:11px;color:var(--text-secondary,#888);} .nutr-bar-bg{height:6px;background:var(--border,#2a2a2a);border-radius:3px;overflow:hidden;} .nutr-bar-fill{height:100%;border-radius:3px;transition:width 0.5s ease;} .cal-bar{background:#e8ff47;} .prot-bar{background:#4ecdc4;} .carbs-bar{background:#4da0ff;} .fat-bar{background:#f59e0b;}
    .nutr-status-notice{flex-direction:column;gap:8px;border-radius:10px;padding:12px 14px;font-size:12px;line-height:1.55;border:1px solid rgba(78,205,196,0.22);background:rgba(78,205,196,0.08);color:var(--text-primary,#f0f0f0);} .nutr-status-notice.over{border-color:rgba(245,158,11,0.35);background:rgba(245,158,11,0.10);} .nutr-status-notice strong{color:#e8ff47;} .nutr-status-notice.over strong{color:#f59e0b;} .nutr-status-chips{display:flex;flex-wrap:wrap;gap:6px;} .nutr-status-chip{font-size:10px;font-weight:800;border-radius:20px;padding:4px 8px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);} .nutr-status-chip.protein{color:#4ecdc4;} .nutr-status-chip.carbs{color:#4da0ff;} .nutr-status-chip.fat{color:#f59e0b;}
    .nutr-tabs{display:flex;gap:4px;background:var(--bg-secondary,#111);border-radius:10px;padding:4px;} .nutr-tab{flex:1;padding:9px;border:none;border-radius:8px;background:transparent;color:var(--text-muted,#666);font-size:11px;font-weight:600;cursor:pointer;transition:all 0.2s;font-family:inherit;} .nutr-tab.on{background:var(--accent,#e8ff47);color:#0a0a0a;}
    .nutr-tab-pane{display:none;flex-direction:column;gap:10px;} .nutr-tab-pane.on{display:flex;}
    .nutr-input-group{display:flex;flex-direction:column;gap:5px;} .nutr-input-group label{font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--text-muted,#666);}
    .nutr-input-group input{background:var(--bg-secondary,#111);border:1px solid var(--border,#2a2a2a);border-radius:8px;padding:10px 12px;color:var(--text-primary,#f0f0f0);font-size:13px;font-family:inherit;outline:none;transition:border-color 0.2s;box-sizing:border-box;width:100%;}
    .nutr-input-group input:focus{border-color:var(--accent,#e8ff47);}
    .nutr-btn-add{width:100%;padding:12px;background:var(--accent,#e8ff47);color:#0a0a0a;border:none;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;}
    .nutr-ai-hint{font-size:12px;color:var(--text-muted,#666);line-height:1.5;padding:8px 0;}
    .nutr-food-input{background:var(--bg-secondary,#111);border:1px solid var(--border,#2a2a2a);border-radius:8px;padding:10px 12px;color:var(--text-primary,#f0f0f0);font-size:13px;font-family:inherit;resize:vertical;outline:none;width:100%;box-sizing:border-box;}
    .nutr-food-input:focus{border-color:var(--accent,#e8ff47);}
    .nutr-btn-analyze{width:100%;padding:12px;background:rgba(78,205,196,0.12);color:#4ecdc4;border:1px solid rgba(78,205,196,0.3);border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;}
    .nutr-btn-analyze:disabled{opacity:0.5;cursor:not-allowed;}
    .food-analysis-result{background:var(--bg-secondary,#111);border:1px solid var(--border,#2a2a2a);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:10px;}
    .fa-summary{font-size:12px;color:var(--text-muted,#666);line-height:1.5;font-style:italic;} .fa-items{display:flex;flex-direction:column;gap:6px;} .fa-item{display:flex;justify-content:space-between;align-items:center;font-size:12px;padding:6px 0;border-bottom:1px solid var(--border,#2a2a2a);} .fa-item:last-child{border-bottom:none;} .fa-item-name{color:var(--text-primary,#f0f0f0);font-weight:500;} .fa-item-name small{color:var(--text-muted,#666);margin-left:4px;} .fa-item-nums{color:var(--accent,#e8ff47);font-weight:600;font-size:11px;}
    .fa-total{display:flex;flex-direction:column;gap:6px;padding-top:8px;border-top:1px solid var(--border,#2a2a2a);} .fa-total-row{display:flex;justify-content:space-between;font-size:13px;} .fa-total-row strong{color:var(--accent,#e8ff47);}
    .fa-manual-note{font-size:12px;line-height:1.5;color:#f59e0b;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:8px;padding:10px 12px;}
    .nutr-note-box{display:flex;gap:10px;align-items:flex-start;background:rgba(167,139,250,0.05);border:1px solid rgba(167,139,250,0.15);border-radius:8px;padding:12px;font-size:12px;color:var(--text-secondary,#aaa);line-height:1.5;} .nutr-note-icon{font-size:14px;flex-shrink:0;margin-top:1px;}
    .routine-item{display:flex;align-items:center;gap:14px;} .ex-checkbox-wrap{flex-shrink:0;cursor:pointer;padding:4px;} .routine-thumb{width:58px;height:58px;border-radius:8px;border:1px solid var(--border,#2a2a2a);background:var(--bg-secondary,#111);padding:0;overflow:hidden;display:flex;align-items:center;justify-content:center;flex-shrink:0;cursor:pointer;color:var(--text-muted,#666);font-size:20px;} .routine-thumb img{width:100%;height:100%;object-fit:contain;display:block;background:#101827;} .routine-thumb:hover{border-color:var(--accent,#e8ff47);} .routine-thumb.no-image{background:rgba(255,255,255,0.03);}
    .routine-item-info{flex:1;cursor:pointer;padding:2px 0;} .routine-item-info:hover h4{color:var(--accent,#e8ff47);} .tag-rest{color:#a78bfa;background:rgba(167,139,250,0.08);}
    .day-ex-count{min-width:58px;text-align:center;font-size:11px;font-weight:800;padding:4px 10px;border-radius:20px;background:rgba(77,160,255,0.1);color:#4da0ff;border:1px solid rgba(77,160,255,0.18);}
    .btn-ex-complete{border:1px solid rgba(78,205,196,0.32);background:rgba(78,205,196,0.08);color:#4ecdc4;border-radius:8px;padding:9px 12px;min-width:112px;font-size:11px;font-weight:800;cursor:pointer;transition:all 0.2s;flex-shrink:0;font-family:inherit;}
    .btn-ex-complete:hover{background:rgba(78,205,196,0.16);border-color:#4ecdc4;} .routine-item.completed .btn-ex-complete{background:#4ecdc4;color:#0a0a0a;} .btn-ex-complete:disabled{opacity:0.9;cursor:not-allowed;} .routine-item.preview-only .btn-ex-complete{opacity:0.55;cursor:not-allowed;}
    .btn-ex-detail{width:32px;height:32px;border-radius:8px;border:1px solid var(--border,#2a2a2a);background:transparent;color:var(--text-muted,#666);font-size:20px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all 0.2s;}
    .btn-ex-detail:hover{border-color:var(--accent);color:var(--accent);}
    .ex-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);z-index:9000;display:flex;align-items:flex-end;justify-content:center;opacity:0;pointer-events:none;transition:opacity 0.25s ease;}
    .ex-modal-overlay.open{opacity:1;pointer-events:all;} .ex-modal-overlay.open .ex-modal{transform:translateY(0);}
    .ex-modal{width:100%;max-width:560px;max-height:88vh;overflow-y:auto;background:var(--bg-card,#161616);border:1px solid var(--border,#2a2a2a);border-radius:20px 20px 0 0;padding:28px 28px 40px;position:relative;transform:translateY(40px);transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1);}
    .ex-modal-close{position:absolute;top:16px;right:16px;width:32px;height:32px;border-radius:50%;border:1px solid var(--border,#2a2a2a);background:var(--bg-secondary,#111);color:var(--text-muted,#666);font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.2s;z-index:10;}
    .ex-modal-close:hover{background:#e74c3c;border-color:#e74c3c;color:#fff;}
    .ex-modal-hero{display:flex;align-items:center;gap:18px;margin-bottom:24px;padding-top:8px;}
    .ex-modal-icon{width:72px;height:72px;border-radius:16px;background:rgba(232,255,71,0.06);border:1px solid rgba(232,255,71,0.15);display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:800;color:var(--accent,#e8ff47);flex-shrink:0;}
    .ex-modal-muscle{font-size:10px;font-weight:700;letter-spacing:2px;color:var(--accent,#e8ff47);margin-bottom:6px;} .ex-modal-name{font-size:22px;font-weight:700;color:var(--text-primary,#f0f0f0);line-height:1.2;margin-bottom:10px;} .ex-modal-badges{display:flex;gap:6px;flex-wrap:wrap;}
    .em-badge{font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;letter-spacing:0.5px;} .badge-b{background:rgba(78,205,196,0.12);color:#4ecdc4;border:1px solid rgba(78,205,196,0.25);} .badge-i{background:rgba(232,255,71,0.10);color:#e8ff47;border:1px solid rgba(232,255,71,0.25);} .badge-a{background:rgba(231,76,60,0.12);color:#e74c3c;border:1px solid rgba(231,76,60,0.25);}
    .em-image-viewer{display:grid;grid-template-columns:38px 1fr 38px;gap:10px;align-items:center;margin:-6px 0 8px;} .em-image-stage{height:220px;border-radius:12px;border:1px solid var(--border,#2a2a2a);background:#101827;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;} .em-image-stage img{width:100%;height:100%;object-fit:contain;display:block;} .em-image-stage.is-empty img{display:none;} .em-image-empty{display:none;color:var(--text-muted,#666);font-size:13px;} .em-image-stage.is-empty .em-image-empty{display:block;} .em-image-nav{width:38px;height:38px;border-radius:8px;border:1px solid var(--border,#2a2a2a);background:var(--bg-secondary,#111);color:var(--text-primary,#f0f0f0);font-size:24px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;} .em-image-nav:hover:not(:disabled){border-color:var(--accent,#e8ff47);color:var(--accent,#e8ff47);} .em-image-nav:disabled{opacity:0.35;cursor:not-allowed;} .em-image-meta{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:18px;font-size:11px;font-weight:700;color:var(--text-muted,#666);letter-spacing:0.5px;}
    .ex-modal-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:24px;} .em-stat{background:var(--bg-secondary,#111);border:1px solid var(--border,#2a2a2a);border-radius:10px;padding:14px 10px;text-align:center;} .em-stat-num{font-size:22px;font-weight:700;color:var(--accent,#e8ff47);line-height:1;margin-bottom:4px;} .em-stat-lbl{font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted,#666);}
    .ex-modal-tabs{display:flex;gap:4px;background:var(--bg-secondary,#111);border-radius:10px;padding:4px;margin-bottom:20px;} .em-tab{flex:1;padding:9px;border:none;border-radius:8px;background:transparent;color:var(--text-muted,#666);font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;font-family:inherit;} .em-tab.on{background:var(--accent,#e8ff47);color:#0a0a0a;}
    .em-pane{display:none;} .em-pane.on{display:block;}
    .em-steps{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:12px;} .em-step{display:flex;align-items:flex-start;gap:14px;padding:14px 16px;background:var(--bg-secondary,#111);border:1px solid var(--border,#2a2a2a);border-radius:10px;} .em-step-num{font-size:11px;font-weight:800;color:var(--accent,#e8ff47);letter-spacing:1px;flex-shrink:0;margin-top:1px;} .em-step-text{font-size:13px;color:var(--text-primary,#f0f0f0);line-height:1.6;}
    .em-muscle-list{display:flex;flex-direction:column;gap:10px;} .em-muscle-item{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:var(--bg-secondary,#111);border:1px solid var(--border,#2a2a2a);border-radius:10px;} .em-muscle-role{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-muted,#666);} .em-muscle-name{font-size:14px;font-weight:600;color:var(--text-primary,#f0f0f0);}
    .em-tips{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:10px;} .em-tip{display:flex;align-items:flex-start;gap:12px;padding:14px 16px;background:rgba(232,255,71,0.03);border:1px solid rgba(232,255,71,0.1);border-radius:10px;font-size:13px;color:var(--text-primary,#f0f0f0);line-height:1.6;} .em-tip-icon{font-size:14px;flex-shrink:0;margin-top:1px;}
    @media (min-width:600px){.ex-modal-overlay{align-items:center;} .ex-modal{border-radius:20px;}}
    @keyframes spin{to{transform:rotate(360deg)}}
  `;
  document.head.appendChild(s);
})();
