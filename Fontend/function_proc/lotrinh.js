// ════════════════════════════════════════════════════════════════
// lotrinh.js — Bản hoàn chỉnh
// ════════════════════════════════════════════════════════════════
const AI_SERVER_URL = "http://localhost:5001";
const TODAY = new Date().toISOString().split("T")[0];

// Thay thế đoạn cũ bằng đoạn này
let USER_ID = "guest";
try {
  const userStr = localStorage.getItem("loggedInUser");
  console.log("👉 1. Chuỗi trong localStorage:", userStr); // Xem có lấy được gì không

  if (userStr) {
    const userObj = JSON.parse(userStr);
    console.log("👉 2. Object User giải mã được:", userObj); // Xem bên trong có những biến gì
    // Thử lấy id theo nhiều tên gọi khác nhau
    USER_ID =
      userObj._id || userObj.id || userObj.user_id || userObj.userid || "guest";

    console.log("👉 3. ID chốt lại gửi đi là:", USER_ID); // Xem kết quả cuối cùng
  } else {
    console.log(
      "👉 Dữ liệu loggedInUser bị TRỐNG (null). Bạn chưa đăng nhập trên tab này!",
    );
  }
} catch (e) {
  console.error("Lỗi đọc user:", e);
}

let currentDisplayDayIndex = 0;
let selectedDays = 7;
let currentPlanData = null;
let currentPlanId = null;
let todayNutrition = { calories: 0, protein: 0, carbs: 0, fat: 0 };
let todayTarget = { calories: 2000, protein: 130 };
let todayIsRest = false;
let planStartDateStr = null;

// ════════════════════════════════════════
// CHỌN ĐỘ DÀI LỘ TRÌNH
// ════════════════════════════════════════
function selectDur(el, days) {
  if (el.classList.contains("disabled")) return;
  document
    .querySelectorAll(".dur-btn")
    .forEach((b) => b.classList.remove("active"));
  el.classList.add("active");
  selectedDays = days;
}

function unlockLongPlans() {
  document.querySelectorAll(".dur-btn.disabled").forEach((b) => {
    b.classList.remove("disabled");
    const lock = b.querySelector(".lock");
    if (lock) lock.remove();
    const days = parseInt(b.dataset.days);
    b.onclick = () => selectDur(b, days);
  });
  const hint = document.getElementById("durationHint");
  if (hint)
    hint.innerHTML =
      '✅ <span style="color:var(--accent);font-weight:bold;">Tài khoản Premium</span>. Bạn có thể sử dụng mọi tính năng!';
}

function checkPremiumStatus() {
  const userStr = localStorage.getItem("loggedInUser");
  if (!userStr) return;
  const localUser = JSON.parse(userStr);
  if (localUser.isPremium === true || localUser.role === "premium")
    unlockLongPlans();
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
  if (!h || !w || h < 100 || w < 20) {
    previewEl.style.display = "none";
    return;
  }
  const bmi = (w / (h / 100) ** 2).toFixed(1);
  let cat = "",
    cls = "";
  if (bmi < 18.5) {
    cat = "Thiếu cân";
    cls = "bmi-under";
  } else if (bmi < 25) {
    cat = "Bình thường";
    cls = "bmi-ok";
  } else if (bmi < 30) {
    cat = "Thừa cân";
    cls = "bmi-over";
  } else {
    cat = "Béo phì";
    cls = "bmi-obese";
  }
  previewEl.style.display = "flex";
  previewEl.innerHTML = `<span class="bmi-num ${cls}">${bmi}</span><span class="bmi-cat-lbl ${cls}">${cat}</span>`;
}

document.addEventListener("DOMContentLoaded", () => {
  const hInput = document.getElementById("height");
  const wInput = document.getElementById("weight");
  if (hInput) hInput.addEventListener("input", updateBmiPreview);
  if (wInput) wInput.addEventListener("input", updateBmiPreview);
});

// ════════════════════════════════════════
// NÚT TẠO LỘ TRÌNH → BMI check trước
// ════════════════════════════════════════
document.getElementById("btn-generate").addEventListener("click", async () => {
  const goal = document.getElementById("goal").value;
  const level = document.getElementById("level").value;
  const equipment = document.getElementById("equipment").value;
  const userInfo = document.getElementById("userInfo").value;
  const height = document.getElementById("height").value;
  const weight = document.getElementById("weight").value;
  const age = document.getElementById("age").value;

  if (!height || !weight || !age) {
    showToast("⚠️ Vui lòng nhập chiều cao, cân nặng và tuổi!", "error");
    return;
  }

  try {
    const bmiRes = await fetch(`${AI_SERVER_URL}/api/analyze-bmi`, {
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
          doGeneratePlan(
            finalGoal,
            level,
            equipment,
            userInfo,
            height,
            weight,
            age,
          );
        },
        () => {
          doGeneratePlan(goal, level, equipment, userInfo, height, weight, age);
        },
      );
      return;
    }
  } catch (e) {
    console.warn("BMI check lỗi, tiếp tục tạo:", e);
  }

  doGeneratePlan(goal, level, equipment, userInfo, height, weight, age);
});

// ════════════════════════════════════════
// MODAL TƯ VẤN BMI
// ════════════════════════════════════════
function showBmiAdviceModal(bmiData, onAccept, onReject) {
  const flagIcon =
    { underweight: "⚠️", overweight: "📊", obese: "🔴" }[bmiData.flag] || "📊";
  const flagColor =
    { underweight: "#4da8ff", overweight: "#e8ff47", obese: "#ff6b6b" }[
      bmiData.flag
    ] || "#e8ff47";

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
            ${
              bmiData.suggested_goal &&
              bmiData.suggested_goal !== bmiData.original_goal
                ? `
            <div class="bmi-suggestion-box">
                <span class="bmi-sug-label">Gợi ý điều chỉnh mục tiêu</span>
                <div class="bmi-sug-row">
                    <span class="bmi-sug-old">❌ ${bmiData.original_goal}</span>
                    <span class="bmi-sug-arrow">→</span>
                    <span class="bmi-sug-new">✅ ${bmiData.suggested_goal}</span>
                </div>
            </div>`
                : ""
            }
            <div class="bmi-advice-actions">
                <button class="bmi-btn-accept" id="bmiAccept">✅ Đồng ý, điều chỉnh mục tiêu</button>
                <button class="bmi-btn-reject" id="bmiReject">Giữ mục tiêu ban đầu và tiếp tục</button>
            </div>
        </div>`;

  document.body.appendChild(modal);
  requestAnimationFrame(() => modal.classList.add("open"));
  document.getElementById("bmiAccept").onclick = () => {
    modal.remove();
    onAccept();
  };
  document.getElementById("bmiReject").onclick = () => {
    modal.remove();
    onReject();
  };
}

// ════════════════════════════════════════
// GỌI API TẠO LỘ TRÌNH
// ════════════════════════════════════════
async function doGeneratePlan(
  goal,
  level,
  equipment,
  userInfo,
  height,
  weight,
  age,
) {
  document.getElementById("plan-title").innerText =
    `LỘ TRÌNH ${goal.toUpperCase()} — ${selectedDays} NGÀY`;
  document.getElementById("plan-sub").innerText =
    `${level} · ${height}cm · ${weight}kg · ${age} tuổi`;

  const container = document.getElementById("plan-container");
  container.innerHTML = `
        <div class="empty-state">
            <div class="loading-spinner"></div>
            <p>AI đang phân tích và tạo lộ trình ${selectedDays} ngày cho bạn...</p>
            <p style="font-size:12px;margin-top:6px;opacity:0.5">${goal} · ${level} · ${height}cm · ${weight}kg</p>
        </div>`;

  const btn = document.getElementById("btn-generate");
  btn.disabled = true;
  btn.innerText = "Đang tạo...";
  document.getElementById("progressWrap").classList.remove("show");
  currentPlanData = null;
  currentPlanId = null;

  // try {
  // //     const response = await fetch(`${AI_SERVER_URL}/api/generate-plan`, {
  // //         method: 'POST',
  // //         headers: { 'Content-Type': 'application/json' },
  // //         body: JSON.stringify({ goal, level, equipment, userInfo, height, weight, age, duration: selectedDays })
  // //     });
  // //     const data = await response.json();

  // //     if (data.plan_data) {
  // //         currentPlanData = data.plan_data;
  // //         renderPlan(data.plan_data, container);
  // //         appendPlanActions(container, data.plan_data);
  // //     } else if (data.error) {
  // //         const is429 = data.error.includes('429') || data.error.includes('Quota');
  // //         container.innerHTML = `<div class="empty-state" style="color:${is429 ? 'var(--accent)' : '#e74c3c'}">
  // //             ${is429 ? '⏳ AI đang bận, vui lòng chờ 15 giây rồi thử lại.' : '❌ Lỗi AI: ' + data.error}
  // //         </div>`;
  // //     }
  // // }

  // catch (err) {
  //     container.innerHTML = `<div class="empty-state" style="color:#e74c3c">
  //         <p>❌ Không thể kết nối máy chủ AI.</p>
  //         <p style="font-size:12px;margin-top:8px;opacity:0.6">Hãy chạy: <code>python ai_server.py</code> tại cổng 5001</p>
  //     </div>`;
  // } finally {
  //     btn.disabled = false;
  //
  // try {
  // console.log("🚀 Đang gửi yêu cầu lên AI Server...");

  // const response = await fetch(`${AI_SERVER_URL}/api/generate-plan`, {
  //     method: 'POST',
  //     headers: { 'Content-Type': 'application/json' },
  //     body: JSON.stringify({ goal, level, equipment, userInfo, height, weight, age, duration: selectedDays })
  // });

  // console.log("📥 Đã nhận phản hồi từ Server. Trạng thái:", response.status);

  // // Kiểm tra nếu server trả về lỗi 500 (Lỗi code Python hoặc AI sập)
  // // Kiểm tra nếu server trả về lỗi 500
  // if (!response.ok) {
  //     // Cố gắng đọc xem server Python gửi về nguyên nhân gì
  //     const errorData = await response.json();
  //     throw new Error(`${errorData.error || response.status}`);
  // }

  // const data = await response.json();
  // console.log("📦 Dữ liệu AI trả về:", data);

  // if (data.plan_data) {
  //     currentPlanData = data.plan_data;
  //     renderPlan(data.plan_data, container);
  //     appendPlanActions(container, data.plan_data);
  // } else if (data.error) {
  //     const is429 = data.error.includes('429') || data.error.includes('Quota');
  //     container.innerHTML = `<div class="empty-state" style="color:${is429 ? 'var(--accent)' : '#ff6060'}">
  //         ${is429 ? '⏳ AI đang bận quá tải, vui lòng chờ 15 giây rồi thử lại.' : '❌ Lỗi AI: ' + data.error}
  //     </div>`;
  // }
  // } catch (error) {
  // console.error("🔥 BẮT ĐƯỢC LỖI TẠI FRONTEND:", error);
  // // TẮT VÒNG XOAY VÀ HIỆN LỖI RA MÀN HÌNH
  // container.innerHTML = `<div class="empty-state" style="color:#ff6060;">
  //     ❌ Bị mất kết nối hoặc AI phản hồi quá lâu.<br>
  //     <span style="font-size:12px; color:#888;">Chi tiết lỗi: ${error.message}</span><br>
  //     <button class="btn" style="margin-top:15px;" onclick="location.reload()">Tải lại trang</button>
  // </div>`;
  // }
  try {
    console.log("🚀 Đang gửi yêu cầu lên AI Server...");

    // Đặt đồng hồ đếm ngược 60 giây. Quá 60s mà AI không xong là ngắt luôn!
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 900000);

    const response = await fetch(`${AI_SERVER_URL}/api/generate-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        goal,
        level,
        equipment,
        userInfo,
        height,
        weight,
        age,
        duration: selectedDays,
      }),
      signal: controller.signal, // Gắn công tắc ngắt vào
    });

    clearTimeout(timeoutId); // Nếu AI trả lời sớm thì tắt đồng hồ đếm ngược
    console.log("📥 Đã nhận phản hồi từ Server. Trạng thái:", response.status);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Mã lỗi server: ${response.status}`);
    }

    const data = await response.json();
    console.log("📦 Dữ liệu AI trả về:", data);

    if (data.plan_data) {
      currentPlanData = data.plan_data;
      renderPlan(data.plan_data, container);
      appendPlanActions(container, data.plan_data);
    } else if (data.error) {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error("🔥 LỖI FRONTEND:", error);

    // Bắt riêng cái lỗi quá thời gian chờ (AbortError)
    let errorMsg = error.message;
    if (error.name === "AbortError") {
      errorMsg =
        "⏳ AI đang suy nghĩ quá lâu (vượt quá 60 giây). Vui lòng thử lại!";
    }

    container.innerHTML = `<div class="empty-state" style="color:#ff6060;">
        ❌ Lỗi: ${errorMsg}<br>
        <button class="btn" style="margin-top:15px;" onclick="location.reload()">Tải lại trang</button>
    </div>`;
  }
}

// ════════════════════════════════════════
// RENDER KẾ HOẠCH
// ════════════════════════════════════════
function renderPlan(planData, container, progress = null) {
  container.innerHTML = "";
  const totalDays = planData.days.length;
  let completedDaysCount = 0;
  currentDisplayDayIndex = 0;

  const defaultCalWorkout = planData.daily_calories_workout || 2200;
  const defaultCalRest = planData.daily_calories_rest || 1900;
  const defaultProtWorkout = planData.daily_protein_workout || 150;
  const defaultProtRest = planData.daily_protein_rest || 120;

  planData.days.forEach((day, index) => {
    // ─── BƯỚC 1: KIỂM TRA XEM NGÀY NÀY ĐÃ ĐƯỢC MỞ KHÓA CHƯA ───
    const unlocked = isDayUnlocked(day.day_number);

    const dayCard = document.createElement("div");
    // Thêm class 'future-locked' nếu chưa đến ngày
    dayCard.className = `day-card open ${index === 0 ? "" : "hidden-day"} ${!unlocked ? "future-locked" : ""}`;
    dayCard.dataset.dayNumber = day.day_number;

    let exProgress = {};
    let pd = null;
    if (progress) {
      pd = progress.find((p) => p.day_number === day.day_number);
      if (pd && pd.exercises) {
        pd.exercises.forEach((e) => {
          exProgress[e.name] = e.completed;
        });
      }
    }

    let targetCal, targetProt;
    if (day.is_rest) {
      targetCal =
        (pd && pd.target_calories) || day.target_calories || defaultCalRest;
      targetProt =
        (pd && pd.target_protein) || day.target_protein || defaultProtRest;
    } else {
      targetCal =
        (pd && pd.target_calories) || day.target_calories || defaultCalWorkout;
      targetProt =
        (pd && pd.target_protein) || day.target_protein || defaultProtWorkout;
    }
    targetCal =
      Number(targetCal) || (day.is_rest ? defaultCalRest : defaultCalWorkout);
    targetProt =
      Number(targetProt) ||
      (day.is_rest ? defaultProtRest : defaultProtWorkout);

    let dayDone = false;
    if (day.is_rest) {
      const localRestState = localStorage.getItem(
        `rest_${currentPlanId}_day_${day.day_number}`,
      );
      dayDone =
        localRestState !== null
          ? localRestState === "true"
          : pd && pd.day_done === true;
    } else {
      if (day.exercises && day.exercises.length > 0) {
        dayDone = day.exercises.every((ex) => exProgress[ex.name] === true);
      }
    }

    if (dayDone) {
      dayCard.classList.add("day-done-card");
      completedDaysCount++;
    }

    dayCard.innerHTML = `
            <div class="day-header">
                <div class="day-header-left">
                    <span class="day-num-badge">Ngày ${day.day_number}</span>
                    <span class="day-name">${day.day_name || ""}</span>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <span class="day-focus">${day.is_rest ? "NGHỈ NGƠI" : day.focus || ""}</span>
                    <span class="day-check-badge ${dayDone ? "show" : ""}">✓ Hoàn thành</span>
                </div>
            </div>
            <div class="day-nutrition-bar">
                <div class="dn-item">
                    <span class="dn-icon">🔥</span>
                    <span class="dn-label">Calo mục tiêu</span>
                    <span class="dn-val">${targetCal} <small>kcal</small></span>
                </div>
                <div class="dn-divider"></div>
                <div class="dn-item">
                    <span class="dn-icon">💪</span>
                    <span class="dn-label">Protein mục tiêu</span>
                    <span class="dn-val">${targetProt}g <small>protein</small></span>
                </div>
                <div class="dn-divider"></div>
                <div class="dn-item">
                    <span class="dn-icon">${day.is_rest ? "🛌" : "🏋️"}</span>
                    <span class="dn-label">Loại ngày</span>
                    <span class="dn-val" style="color:${day.is_rest ? "#a78bfa" : "#4ecdc4"}">${day.is_rest ? "Nghỉ ngơi" : "Ngày tập"}</span>
                </div>
            </div>
            <div class="day-body" id="day-body-${day.day_number}"></div>`;

    container.appendChild(dayCard);
    const body = document.getElementById(`day-body-${day.day_number}`);

    if (day.is_rest) {
      body.innerHTML = `
                <div class="rest-check-box ${dayDone ? "completed" : ""}" id="rest-btn-${day.day_number}">
                    <div class="ex-checkbox" style="background:${dayDone ? "#4ecdc4" : "transparent"};border-color:${dayDone ? "#4ecdc4" : "var(--border-hover)"};color:${dayDone ? "#0a0a0a" : "transparent"}">
                        ${dayDone ? "✓" : ""}
                    </div>
                    <span style="font-weight:600;color:${dayDone ? "#4ecdc4" : "inherit"}">Xác nhận đã nghỉ ngơi & phục hồi</span>
                </div>`;
      const restBtn = document.getElementById(`rest-btn-${day.day_number}`);
      restBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        checkinExercise(
          currentPlanId,
          day.day_number,
          "RestDay",
          !restBtn.classList.contains("completed"),
          restBtn,
          dayCard,
          true,
        );
      });
    } else {
      day.exercises.forEach((ex) => {
        const done = exProgress[ex.name] || false;
        const exEl = document.createElement("div");
        exEl.className = `routine-item${done ? " completed" : ""}`;
        exEl.innerHTML = `
                    <div class="ex-checkbox-wrap">
                        <div class="ex-checkbox">${done ? "✓" : ""}</div>
                    </div>
                    <div class="routine-item-info">
                        <h4>${ex.name}</h4>
                        <div class="tags">
                            <span class="tag tag-muscle">${ex.muscle || "Toàn thân"}</span>
                            <span class="tag tag-sets">${ex.sets} sets × ${ex.reps} reps</span>
                            <span class="tag tag-rest">⏱ ${ex.rest}s</span>
                        </div>
                    </div>
                    <button class="btn-ex-detail" title="Xem chi tiết">›</button>`;

        exEl
          .querySelector(".ex-checkbox-wrap")
          .addEventListener("click", (e) => {
            e.stopPropagation();
            checkinExercise(
              currentPlanId,
              day.day_number,
              ex.name,
              !exEl.classList.contains("completed"),
              exEl,
              dayCard,
              false,
            );
          });
        exEl
          .querySelector(".routine-item-info")
          .addEventListener("click", (e) => {
            e.stopPropagation();
            openExerciseModal(ex);
          });
        exEl.querySelector(".btn-ex-detail").addEventListener("click", (e) => {
          e.stopPropagation();
          openExerciseModal(ex);
        });
        body.appendChild(exEl);
      });
    }

    // ─── BƯỚC 2: LOGIC KHÓA UI NGÀY TẬP & NGÀY TƯƠNG LAI ───
    const isDayLocked = pd && pd.is_locked === true;
    if (isDayLocked) {
      dayCard.classList.add("day-locked");
    }

    // Chỉ hiện nút khóa/cảnh báo khi lộ trình đã được lưu (currentPlanId tồn tại)
    if (currentPlanId) {
      const lockDayWrap = document.createElement("div");
      lockDayWrap.style.marginTop = "16px";

      if (isDayLocked) {
        // Đã hoàn thành và chốt sổ
        lockDayWrap.innerHTML = `<div class="locked-success-msg">✅ Ngày này đã được chốt sổ!</div>`;
      } else if (!unlocked) {
        // CHƯA TỚI NGÀY -> Hiện thông báo chờ thay vì nút chốt
        lockDayWrap.innerHTML = `<div class="locked-future-msg">⏳ Bài tập sẽ mở khóa vào ngày thứ ${day.day_number} của lộ trình</div>`;
      } else {
        // HÔM NAY -> Hiện nút chốt sổ
        lockDayWrap.innerHTML = `<button class="btn-lock-target" onclick="askLockPlanDay('${currentPlanId}', ${day.day_number})">🔒 HOÀN THÀNH & CHỐT SỔ NGÀY ${day.day_number}</button>`;
      }
      body.appendChild(lockDayWrap);
    }
    // ───────────────────────────────────────────────────────
  });

  const navWrap = document.createElement("div");
  navWrap.className = "day-nav-controls";
  navWrap.innerHTML = `
        <button class="btn-nav-day" id="btn-prev-day" onclick="navigateDay(-1)" disabled>← Ngày trước</button>
        <button class="btn-nav-day" id="btn-next-day" onclick="navigateDay(1)" ${totalDays <= 1 ? "disabled" : ""}>Ngày tiếp theo →</button>`;
  container.appendChild(navWrap);

  updateProgressBar(completedDaysCount, totalDays);
}

// ════════════════════════════════════════
// CHUYỂN NGÀY
// ════════════════════════════════════════
window.navigateDay = function (direction) {
  const cards = document.querySelectorAll(".day-card");
  const totalDays = cards.length;
  if (cards[currentDisplayDayIndex])
    cards[currentDisplayDayIndex].classList.add("hidden-day");
  currentDisplayDayIndex = Math.max(
    0,
    Math.min(totalDays - 1, currentDisplayDayIndex + direction),
  );
  if (cards[currentDisplayDayIndex])
    cards[currentDisplayDayIndex].classList.remove("hidden-day");
  document.getElementById("btn-prev-day").disabled =
    currentDisplayDayIndex === 0;
  document.getElementById("btn-next-day").disabled =
    currentDisplayDayIndex === totalDays - 1;
};

// ════════════════════════════════════════
// NÚT ÁP DỤNG / TẠO LẠI
// ════════════════════════════════════════
function appendPlanActions(container, planData) {
  const wrap = document.createElement("div");
  wrap.className = "plan-actions";
  wrap.id = "plan-action-buttons";
  wrap.innerHTML = `
        <button class="btn-apply" id="btn-apply">💾 Áp dụng lộ trình này</button>
        <button class="btn-retry" id="btn-retry">🔄 Tạo lại</button>`;
  container.appendChild(wrap);

  const cancelBtn = document.createElement("button");
  cancelBtn.className = "btn-danger";
  cancelBtn.id = "btn-cancel-plan";
  // Nếu có lộ trình rồi thì hiện nút Hủy, chưa có thì ẩn
  cancelBtn.style.display = currentPlanId ? "block" : "none";
  cancelBtn.innerHTML = "🗑️ HỦY LỘ TRÌNH ĐANG TẬP";

  // CHỈ DÙNG DÒNG NÀY ĐỂ MỞ MODAL
  cancelBtn.onclick = askCancelPlan;

  container.appendChild(cancelBtn);

  // Gán sự kiện cho 2 nút còn lại
  document
    .getElementById("btn-apply")
    .addEventListener("click", () => savePlan(planData));
  document
    .getElementById("btn-retry")
    .addEventListener("click", () =>
      document.getElementById("btn-generate").click(),
    );
}

/// ════════════════════════════════════════
// LƯU LỘ TRÌNH
// ════════════════════════════════════════
async function savePlan(planData) {
  const height = document.getElementById("height").value;
  const weight = document.getElementById("weight").value;
  const age = document.getElementById("age").value;
  const btn = document.getElementById("btn-apply");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "Đang lưu...";
  }

  try {
    const res = await fetch(`${AI_SERVER_URL}/api/save-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan_data: planData,
        userId: USER_ID,
        height,
        weight,
        age,
      }),
    });
    const result = await res.json();

    if (result.success) {
      currentPlanId = result.plan_id;

      // ─── THÊM 2 DÒNG NÀY: Lưu lại ngày bắt đầu lúc vừa tạo ───
      const tObj = new Date();
      planStartDateStr = `${tObj.getDate().toString().padStart(2, "0")}/${(tObj.getMonth() + 1).toString().padStart(2, "0")}/${tObj.getFullYear()}`;
      // ─────────────────────────────────────────────────────────

      showToast("✅ Lộ trình đã kích hoạt! Bắt đầu tập thôi!", "success");
      updateProgressBar(0, planData.duration_days || selectedDays);

      document.getElementById("plan-action-buttons").style.display = "none";
      document.getElementById("btn-cancel-plan").classList.add("show");
      document.getElementById("btn-generate").disabled = true;
      document.getElementById("btn-generate").innerText = "LỘ TRÌNH ĐANG CHẠY";
      document.getElementById("btn-generate").style.opacity = "0.5";

      switchToNutritionSidebar(planData);

      // Render lại plan để giao diện cập nhật trạng thái khóa/mở khóa các ngày
      renderPlan(planData, document.getElementById("plan-container"));
    } else {
      showToast("❌ Lỗi lưu: " + result.error, "error");
    }
  } catch (e) {
    showToast("❌ Không kết nối được server", "error");
  } finally {
    if (btn && btn.style.display !== "none") {
      btn.disabled = false;
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
  const todayDay = planData.days
    ? planData.days.find((d) => d.day_number === todayDayNum) ||
      planData.days[0]
    : null;
  todayIsRest = todayDay ? Boolean(todayDay.is_rest) : false;

  const calWorkout = Number(planData.daily_calories_workout) || 2200;
  const calRest = Number(planData.daily_calories_rest) || 1900;
  const protWorkout = Number(planData.daily_protein_workout) || 150;
  const protRest = Number(planData.daily_protein_rest) || 120;

  if (todayIsRest) {
    todayTarget.calories =
      (todayDay && Number(todayDay.target_calories)) || calRest;
    todayTarget.protein =
      (todayDay && Number(todayDay.target_protein)) || protRest;
  } else {
    todayTarget.calories =
      (todayDay && Number(todayDay.target_calories)) || calWorkout;
    todayTarget.protein =
      (todayDay && Number(todayDay.target_protein)) || protWorkout;
  }

  sidebar.innerHTML = `
        <div class="nutr-sidebar">
            <div class="nutr-header">
                <h2>🥗 Dinh dưỡng hôm nay</h2>
                <p class="nutr-date">${new Date().toLocaleDateString("vi-VN", { weekday: "long", day: "numeric", month: "long" })}</p>
            </div>

            <div class="nutr-target-card">
                <div class="nutr-target-row">
                    <span class="nutr-target-lbl">🔥 Calo mục tiêu</span>
                    <span class="nutr-target-val">${todayTarget.calories} kcal</span>
                </div>
                <div class="nutr-target-row">
                    <span class="nutr-target-lbl">💪 Protein mục tiêu</span>
                    <span class="nutr-target-val">${todayTarget.protein}g</span>
                </div>
                <div class="nutr-day-type ${todayIsRest ? "rest" : "workout"}">
                    ${todayIsRest ? "🛌 Ngày nghỉ — ăn nhẹ hơn" : "🏋️ Ngày tập — nạp đủ năng lượng"}
                </div>
            </div>

            <div class="nutr-progress-wrap">
                <div class="nutr-progress-row">
                    <span>Calo đã nạp</span>
                    <span id="ntCalDone">0 / ${todayTarget.calories} kcal</span>
                </div>
                <div class="nutr-bar-bg">
                    <div class="nutr-bar-fill cal-bar" id="ntCalBar" style="width:0%"></div>
                </div>
                <div class="nutr-progress-row" style="margin-top:10px;">
                    <span>Protein đã nạp</span>
                    <span id="ntProtDone">0 / ${todayTarget.protein}g</span>
                </div>
                <div class="nutr-bar-bg">
                    <div class="nutr-bar-fill prot-bar" id="ntProtBar" style="width:0%"></div>
                </div>
            </div>

            <div class="nutr-tabs">
                <button class="nutr-tab on" data-tab="manual" onclick="switchNutrTab('manual', this)">✏️ Nhập tay</button>
                <button class="nutr-tab" data-tab="ai" onclick="switchNutrTab('ai', this)">🤖 Nhập món ăn</button>
            </div>

            <div class="nutr-tab-pane on" id="nutr-pane-manual">
                <div class="nutr-input-group">
                    <label>Calories (kcal)</label>
                    <input type="number" id="ni_cal" placeholder="VD: 500" min="0" max="5000">
                </div>
                <div class="nutr-input-group">
                    <label>Protein (g)</label>
                    <input type="number" id="ni_prot" placeholder="VD: 35" min="0" max="500">
                </div>
                <div class="nutr-input-group">
                    <label>Carbs (g) <span style="opacity:.5;font-size:10px;">tuỳ chọn</span></label>
                    <input type="number" id="ni_carbs" placeholder="VD: 60" min="0" max="1000">
                </div>
                <div class="nutr-input-group">
                    <label>Fat (g) <span style="opacity:.5;font-size:10px;">tuỳ chọn</span></label>
                    <input type="number" id="ni_fat" placeholder="VD: 15" min="0" max="500">
                </div>
                <button class="nutr-btn-add" onclick="addManualNutrition()">+ Cộng vào hôm nay</button>
            </div>

            <div class="nutr-tab-pane" id="nutr-pane-ai">
                <div class="nutr-ai-hint">Nhập tên & lượng món ăn, AI sẽ tự tính dinh dưỡng cho bạn.</div>
                <textarea id="ni_food" class="nutr-food-input"
                    placeholder="VD: 200g ức gà, 1 bát cơm trắng, 1 quả trứng luộc..." rows="3"></textarea>
                <button class="nutr-btn-analyze" id="btnAnalyzeFood" onclick="analyzeAndAddFood()">
                    🔍 Phân tích & Thêm vào
                </button>
                <div id="foodAnalysisResult" class="food-analysis-result" style="display:none;"></div>
            </div>

            ${
              planData.nutrition_note
                ? `
            <div class="nutr-note-box">
                <span class="nutr-note-icon">💡</span>
                <span>${planData.nutrition_note}</span>
            </div>`
                : ""
            }
        </div>`;

  loadTodayNutrition();
}

// ════════════════════════════════════════
// CHUYỂN TAB DINH DƯỠNG
// ════════════════════════════════════════
function switchNutrTab(tabId, btn) {
  document
    .querySelectorAll(".nutr-tab")
    .forEach((t) => t.classList.remove("on"));
  document
    .querySelectorAll(".nutr-tab-pane")
    .forEach((p) => p.classList.remove("on"));
  btn.classList.add("on");
  document.getElementById("nutr-pane-" + tabId).classList.add("on");
}

// ════════════════════════════════════════
// NHẬP TAY DINH DƯỠNG
// ════════════════════════════════════════
async function addManualNutrition() {
  const cal = parseFloat(document.getElementById("ni_cal").value) || 0;
  const prot = parseFloat(document.getElementById("ni_prot").value) || 0;
  const carbs = parseFloat(document.getElementById("ni_carbs").value) || 0;
  const fat = parseFloat(document.getElementById("ni_fat").value) || 0;

  if (!cal && !prot) {
    showToast("⚠️ Vui lòng nhập ít nhất Calories hoặc Protein", "error");
    return;
  }
  await saveNutritionToServer(cal, prot, carbs, fat, "Nhập tay");
  ["ni_cal", "ni_prot", "ni_carbs", "ni_fat"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  showToast("✅ Đã cập nhật dinh dưỡng!", "success");
}

// ════════════════════════════════════════
// AI PHÂN TÍCH MÓN ĂN
// ════════════════════════════════════════
async function analyzeAndAddFood() {
  const foodTextEl = document.getElementById("ni_food");
  const foodText = foodTextEl ? foodTextEl.value.trim() : "";

  if (!foodText) {
    showToast("⚠️ Hãy nhập món ăn trước", "error");
    return;
  }

  const btn = document.getElementById("btnAnalyzeFood");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Đang phân tích...";
  }

  const resultBox = document.getElementById("foodAnalysisResult");
  if (resultBox) resultBox.style.display = "none";

  try {
    const res = await fetch(`${AI_SERVER_URL}/api/analyze-food`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ food_text: foodText, userId: USER_ID }),
    });

    const data = await res.json();

    if (!data.success || !data.data) {
      showToast("❌ " + (data.error || "AI không phân tích được"), "error");
      return;
    }

    const { total, items, summary } = data.data;

    const safeTotal = {
      calories: Number(total.calories) || 0,
      protein: Number(total.protein) || 0,
      carbs: Number(total.carbs) || 0,
      fat: Number(total.fat) || 0,
    };

    if (resultBox) {
      resultBox.style.display = "block";
      resultBox.innerHTML = `
                <div class="fa-summary">${summary || ""}</div>
                <div class="fa-items">
                    ${(items || [])
                      .map(
                        (item) => `
                        <div class="fa-item">
                            <span class="fa-item-name">${item.name} <small>${item.amount}</small></span>
                            <span class="fa-item-nums">${item.calories} kcal · ${item.protein}g P</span>
                        </div>`,
                      )
                      .join("")}
                </div>
                <div class="fa-total">
                    <div class="fa-total-row"><span>🔥 Tổng Calories</span><strong>${safeTotal.calories} kcal</strong></div>
                    <div class="fa-total-row"><span>💪 Protein</span><strong>${safeTotal.protein}g</strong></div>
                    <div class="fa-total-row"><span>🍞 Carbs</span><strong>${safeTotal.carbs}g</strong></div>
                    <div class="fa-total-row"><span>🧈 Fat</span><strong>${safeTotal.fat}g</strong></div>
                </div>
                <button class="nutr-btn-add" id="btnConfirmFood">✅ Thêm vào hôm nay</button>`;

      document.getElementById("btnConfirmFood").onclick = () => {
        confirmAddFoodNutrition(
          safeTotal.calories,
          safeTotal.protein,
          safeTotal.carbs,
          safeTotal.fat,
        );
      };
    }
  } catch (e) {
    console.error("analyzeAndAddFood error:", e);
    showToast("❌ Lỗi kết nối AI", "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = "🔍 Phân tích & Thêm vào";
    }
  }
}

async function confirmAddFoodNutrition(cal, prot, carbs, fat) {
  const foodEl = document.getElementById("ni_food");
  const note = foodEl ? foodEl.value : "";
  await saveNutritionToServer(cal, prot, carbs, fat, note);
  if (foodEl) foodEl.value = "";
  const resultBox = document.getElementById("foodAnalysisResult");
  if (resultBox) resultBox.style.display = "none";
  showToast("✅ Đã thêm dinh dưỡng từ món ăn!", "success");
}

// ════════════════════════════════════════
// LƯU DINH DƯỠNG
// ════════════════════════════════════════
// async function saveNutritionToServer(cal, prot, carbs, fat, note) {
//   try {
//     const res = await fetch(`${AI_SERVER_URL}/api/save-nutrition`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({
//         userId: USER_ID,
//         date: TODAY,
//         calories: cal,
//         protein: prot,
//         carbs,
//         fat,
//         note,
//       }),
//     });
//     const data = await res.json();
//     if (data.success && data.today) {
//       todayNutrition = data.today;
//       updateNutritionUI();
//     }
//   } catch (e) {
//     todayNutrition.calories = (todayNutrition.calories || 0) + cal;
//     todayNutrition.protein = (todayNutrition.protein || 0) + prot;
//     updateNutritionUI();
//   }
// }
// ════════════════════════════════════════
// LƯU DINH DƯỠNG (Đã nâng cấp chống lỗi 400)
// ════════════════════════════════════════
async function saveNutritionToServer(cal, prot, carbs, fat, note) {
  try {
    // 1. Chuẩn bị gói hàng (Gửi cả 2 kiểu tên biến phòng hờ Python bắt bẻ)
    const payload = {
      userId: USER_ID,
      user_id: USER_ID, // Thêm dòng này để fix lỗi 400 cực hiệu quả!
      date: getCurrentDateStr(), 
      calories: cal,
      protein: prot,
      carbs: carbs,
      fat: fat,
      note: note,
    };
    
    console.log("📤 Đang gửi dữ liệu ăn uống lên:", payload);

    const res = await fetch(`${AI_SERVER_URL}/api/save-nutrition`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    // 2. Nếu Python báo lỗi (400) thì sẽ hiện thông báo đỏ lên màn hình
    if (!res.ok || !data.success) {
      console.error("❌ Bị Python từ chối (400):", data);
      showToast("❌ Lỗi lưu DB: " + (data.error || data.message || "Sai định dạng dữ liệu"), "error");
      return; // Dừng lại, không cập nhật giao diện
    }

    // 3. Nếu thành công thì mới cập nhật thanh UI
    if (data.success && data.today) {
      todayNutrition = data.today;
      updateNutritionUI();
      showToast("✅ Đã cộng thêm dinh dưỡng!", "success");
    }
  } catch (e) {
    console.error("❌ Lỗi mất mạng hoặc sập server:", e);
    showToast("❌ Lỗi mạng: Không thể lưu dinh dưỡng!", "error");
  }
}

// async function loadTodayNutrition() {
//   try {
//     const res = await fetch(
//       `${AI_SERVER_URL}/api/get-nutrition?userId=${USER_ID}&date=${TODAY}`,
//     );
//     const data = await res.json();
//     todayNutrition = data;
//     updateNutritionUI();
//   } catch (e) {
//     console.warn("Không tải được dinh dưỡng hôm nay");
//   }
// }
async function loadTodayNutrition() {
  try {
    // 1. Dùng getCurrentDateStr() thay vì TODAY để ép lấy ngày thực tế
    const res = await fetch(
      `${AI_SERVER_URL}/api/get-nutrition?userId=${USER_ID}&date=${getCurrentDateStr()}`
    );
    
    // Nếu server báo lỗi (ví dụ 404 do ngày mới chưa có ai nhập), tự động nhảy xuống catch
    if (!res.ok) throw new Error("Chưa có dữ liệu ngày mới");

    const data = await res.json();
    
    // 2. Chặn trường hợp server trả về success: false
    if (data.success === false || data.calories === undefined) {
      todayNutrition = { calories: 0, protein: 0, carbs: 0, fat: 0, is_locked: false };
    } else {
      todayNutrition = data; // Nhận dữ liệu thực tế nếu có
    }
    
    updateNutritionUI();
  } catch (e) {
    console.warn("✨ Đã qua ngày mới hoặc chưa có dữ liệu. Reset bảng dinh dưỡng về 0.");
    
    // 3. ĐOẠN QUAN TRỌNG NHẤT: Ép biến lưu trữ về 0
    todayNutrition = { 
        calories: 0, 
        protein: 0, 
        carbs: 0, 
        fat: 0, 
        is_locked: false 
    };
    
    // 4. Vẽ lại giao diện với các con số 0 vừa được gán
    updateNutritionUI();
  }
}

function updateNutritionUI() {
  const calDoneEl = document.getElementById("ntCalDone");
  const protDoneEl = document.getElementById("ntProtDone");
  const calBarEl = document.getElementById("ntCalBar");
  const protBarEl = document.getElementById("ntProtBar");
  if (!calDoneEl || !todayTarget.calories) return;

  const calPct = Math.min(
    100,
    Math.round((todayNutrition.calories / todayTarget.calories) * 100),
  );
  const protPct = Math.min(
    100,
    Math.round((todayNutrition.protein / todayTarget.protein) * 100),
  );

  calDoneEl.textContent = `${Math.round(todayNutrition.calories)} / ${todayTarget.calories} kcal`;
  protDoneEl.textContent = `${Math.round(todayNutrition.protein)}g / ${todayTarget.protein}g`;

  setTimeout(() => {
    if (calBarEl) {
      calBarEl.style.width = calPct + "%";
      calBarEl.style.background = calPct >= 100 ? "#4ecdc4" : "";
    }
    if (protBarEl) {
      protBarEl.style.width = protPct + "%";
      protBarEl.style.background = protPct >= 100 ? "#4ecdc4" : "";
    }
  }, 50);

  // --- LOGIC KHÓA UI DINH DƯỠNG ---
  const nutrTabsBox = document.querySelector(".nutr-tabs");
  const nutrPanes = document.querySelectorAll(".nutr-tab-pane");

  // Xóa nút chốt cũ nếu có
  const oldLockBtn = document.getElementById("btnLockNutrition");
  if (oldLockBtn) oldLockBtn.remove();

  if (todayNutrition.is_locked) {
    if (nutrTabsBox) nutrTabsBox.style.display = "none";
    nutrPanes.forEach((p) => (p.style.display = "none"));

    // Thêm thông báo đã khóa
    const lockedMsg = document.createElement("div");
    lockedMsg.id = "btnLockNutrition";
    lockedMsg.className = "locked-success-msg";
    lockedMsg.innerHTML =
      "✅ Đã chốt sổ dinh dưỡng hôm nay. Hẹn gặp bạn vào ngày mai!";
    document.querySelector(".nutr-sidebar").appendChild(lockedMsg);
  } else {
    // Nếu đạt >= 95% mục tiêu, hiện nút chốt sổ
    if (calPct >= 95 && protPct >= 95) {
      const lockBtn = document.createElement("button");
      lockBtn.id = "btnLockNutrition";
      lockBtn.className = "btn-lock-target";
      lockBtn.innerHTML = "🔒 HOÀN THÀNH MỤC TIÊU HÔM NAY";
      lockBtn.onclick = lockNutritionDay;
      document.querySelector(".nutr-sidebar").appendChild(lockBtn);
    }
  }
}

// ════════════════════════════════════════
// CHECK-IN BÀI TẬP
// ════════════════════════════════════════
async function checkinExercise(
  planId,
  dayNumber,
  exName,
  completed,
  exEl,
  dayCard,
  isRest = false,
) {
  // ─── ĐOẠN MỚI THÊM: CHẶN CHECK-IN NẾU NGÀY ĐÃ BỊ KHÓA (CHỐT SỔ) ───
  if (dayCard.classList.contains("day-locked")) {
    showToast("⚠️ Ngày này đã chốt sổ, không thể thay đổi!", "error");
    return;
  }
  // ──────────────────────────────────────────────────────────────────

  if (isRest) {
    localStorage.setItem(`rest_${planId}_day_${dayNumber}`, completed);
    if (completed) {
      exEl.classList.add("completed");
      exEl.querySelector(".ex-checkbox").textContent = "✓";
      dayCard.classList.add("day-done-card");
      const badge = dayCard.querySelector(".day-check-badge");
      if (badge) {
        badge.textContent = "✓ Hoàn thành";
        badge.classList.add("show");
      }
    } else {
      exEl.classList.remove("completed");
      exEl.querySelector(".ex-checkbox").textContent = "";
      dayCard.classList.remove("day-done-card");
      const badge = dayCard.querySelector(".day-check-badge");
      if (badge) badge.classList.remove("show");
    }
  } else {
    if (completed) {
      exEl.classList.add("completed");
      exEl.querySelector(".ex-checkbox").textContent = "✓";
    } else {
      exEl.classList.remove("completed");
      exEl.querySelector(".ex-checkbox").textContent = "";
    }
    const body = document.getElementById(`day-body-${dayNumber}`);
    const allDone = [...body.querySelectorAll(".routine-item")].every((el) =>
      el.classList.contains("completed"),
    );
    const badge = dayCard.querySelector(".day-check-badge");
    if (allDone) {
      dayCard.classList.add("day-done-card");
      if (badge) {
        badge.textContent = "✓ Hoàn thành";
        badge.classList.add("show");
      }
    } else {
      dayCard.classList.remove("day-done-card");
      if (badge) badge.classList.remove("show");
    }
  }

  const totalDaysCount = document.querySelectorAll(".day-card").length;
  const completedDaysCount = document.querySelectorAll(".day-done-card").length;
  updateProgressBar(completedDaysCount, totalDaysCount);

  if (completedDaysCount === totalDaysCount && totalDaysCount > 0) {
    showToast("🎉 Tuyệt vời! Bạn đã hoàn thành toàn bộ lộ trình!", "success");
  }

  try {
    fetch(`${AI_SERVER_URL}/api/checkin-exercise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        planId,
        dayNumber,
        exerciseName: exName,
        completed,
      }),
    });
  } catch (e) {
    console.error("Lỗi mạng khi lưu ngầm:", e);
  }
}

// ════════════════════════════════════════
// THANH TIẾN ĐỘ
// ════════════════════════════════════════
function updateProgressBar(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  document.getElementById("progressWrap").classList.add("show");
  document.getElementById("progressPct").textContent = pct + "%";
  document.getElementById("progressBar").style.width = pct + "%";
  document.getElementById("progressDays").textContent =
    `${done} / ${total} ngày hoàn thành`;
}

// ════════════════════════════════════════
// TOAST
// ════════════════════════════════════════
function showToast(msg, type = "success") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
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

// Bước 2: Đóng Modal
function closeCancelModal() {
  const modal = document.getElementById("cancelPlanOverlay");
  if (modal) modal.classList.remove("open");
}

// Bước 3: Thực hiện xóa lộ trình (Chuyển logic cũ vào đây)
async function executeCancelPlan() {
  closeCancelModal(); // Đóng modal trước

  try {
    const res = await fetch(`${AI_SERVER_URL}/api/cancel-plan/${USER_ID}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    });
    const result = await res.json();

    if (result.success) {
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
    const res = await fetch(
      `${AI_SERVER_URL}/api/get-active-plan?userId=${USER_ID}`,
    );
    const data = await res.json();

    if (data.plan) {
      currentPlanId = data.plan._id || data.plan.id;
      currentPlanData = data.plan.plan_data;

      // ─── THÊM DÒNG NÀY: Lấy ngày bắt đầu từ Database để khóa ngày tương lai ───
      planStartDateStr = data.plan.created_at;
      // ─────────────────────────────────────────────────────────────────────────

      document.getElementById("plan-title").innerText =
        "LỘ TRÌNH ĐANG THỰC HIỆN";
      const container = document.getElementById("plan-container");

      renderPlan(currentPlanData, container, data.plan.daily_progress);
      appendPlanActions(container, currentPlanData);

      document.getElementById("plan-action-buttons").style.display = "none";
      document.getElementById("btn-cancel-plan").classList.add("show");

      const btnGen = document.getElementById("btn-generate");
      btnGen.disabled = true;
      btnGen.innerText = "LỘ TRÌNH ĐANG CHẠY";
      btnGen.style.opacity = "0.5";

      switchToNutritionSidebar(currentPlanData);
    }
  } catch (e) {
    console.log("Không có lộ trình active hoặc server tắt");
  }
}
checkActivePlanOnLoad();

// ════════════════════════════════════════════════════════════════
// MODAL CHI TIẾT BÀI TẬP
// ════════════════════════════════════════════════════════════════
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
  document.getElementById("exModalOverlay").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeExerciseModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeExerciseModal();
  });
  document.querySelectorAll(".em-tab").forEach((btn) => {
    btn.onclick = () => {
      document
        .querySelectorAll(".em-tab")
        .forEach((t) => t.classList.remove("on"));
      document
        .querySelectorAll(".em-pane")
        .forEach((t) => t.classList.remove("on"));
      btn.classList.add("on");
      document.getElementById("em-pane-" + btn.dataset.t).classList.add("on");
    };
  });
})();

function openExerciseModal(ex) {
  const diffLabel = { B: "Người mới", I: "Trung bình", A: "Nâng cao" };
  const diffCls = { B: "badge-b", I: "badge-i", A: "badge-a" };
  document.getElementById("emIcon").textContent = ex.icon || "🏋️";
  document.getElementById("emMuscle").textContent = (
    ex.muscle || ""
  ).toUpperCase();
  document.getElementById("emName").textContent = ex.name;
  document.getElementById("emBadges").innerHTML = `
        <span class="em-badge ${diffCls[ex.diff] || "badge-i"}">${diffLabel[ex.diff] || ex.diff || "Trung bình"}</span>
        <span class="em-badge" style="background:rgba(77,160,255,.12);color:#4da0ff;border:1px solid rgba(77,160,255,.25)">${ex.equip || "Dụng cụ"}</span>`;
  document.getElementById("emStats").innerHTML = `
        <div class="em-stat"><div class="em-stat-num">${ex.sets}</div><div class="em-stat-lbl">Sets</div></div>
        <div class="em-stat"><div class="em-stat-num">${ex.reps}</div><div class="em-stat-lbl">Reps</div></div>
        <div class="em-stat"><div class="em-stat-num">${ex.rest}s</div><div class="em-stat-lbl">Nghỉ</div></div>`;
  const stepsHtml =
    ex.steps && ex.steps.length > 0
      ? `<ol class="em-steps">${ex.steps
          .map(
            (s, i) =>
              `<li class="em-step"><span class="em-step-num">0${i + 1}</span><div class="em-step-text">${s}</div></li>`,
          )
          .join("")}</ol>`
      : `<p style="color:var(--text-muted);font-size:14px;padding:16px 0;">Chưa có hướng dẫn.</p>`;
  document.getElementById("em-pane-steps").innerHTML = stepsHtml;
  const allMuscles = [{ role: "Cơ chính", name: ex.muscle }];
  if (ex.sec && ex.sec.length > 0)
    ex.sec.forEach((s) => allMuscles.push({ role: "Cơ phụ", name: s }));
  document.getElementById("em-pane-muscles").innerHTML = `
        <div class="em-muscle-list">${allMuscles
          .map(
            (m) =>
              `<div class="em-muscle-item"><div class="em-muscle-role">${m.role}</div><div class="em-muscle-name">${m.name}</div></div>`,
          )
          .join("")}</div>`;
  const tipsHtml =
    ex.tips && ex.tips.length > 0
      ? `<ul class="em-tips">${ex.tips
          .map(
            (t) =>
              `<li class="em-tip"><span class="em-tip-icon">⚡</span><span>${t}</span></li>`,
          )
          .join("")}</ul>`
      : `<p style="color:var(--text-muted);font-size:14px;padding:16px 0;">Không có lưu ý.</p>`;
  document.getElementById("em-pane-tips").innerHTML = tipsHtml;
  document.querySelectorAll(".em-tab").forEach((t) => t.classList.remove("on"));
  document
    .querySelectorAll(".em-pane")
    .forEach((t) => t.classList.remove("on"));
  document.querySelector('.em-tab[data-t="steps"]').classList.add("on");
  document.getElementById("em-pane-steps").classList.add("on");
  document.getElementById("exModalOverlay").classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeExerciseModal() {
  document.getElementById("exModalOverlay").classList.remove("open");
  document.body.style.overflow = "";
}

// ════════════════════════════════════════════════════════════════
// CSS INJECT
// ════════════════════════════════════════════════════════════════
(function injectCSS() {
  const s = document.createElement("style");
  s.textContent = `
    #bmiPreview { display:none; align-items:center; gap:10px; background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:8px; padding:10px 14px; margin-top:8px; }
    .bmi-num { font-size:22px; font-weight:800; }
    .bmi-cat-lbl { font-size:12px; font-weight:600; }
    .bmi-under { color:#4da8ff; } .bmi-ok { color:#4ecdc4; } .bmi-over { color:#e8ff47; } .bmi-obese { color:#ff6b6b; }

    .bmi-advice-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.8); backdrop-filter:blur(8px); z-index:9999; display:flex; align-items:center; justify-content:center; padding:20px; opacity:0; pointer-events:none; transition:opacity 0.25s; }
    .bmi-advice-overlay.open { opacity:1; pointer-events:all; }
    .bmi-advice-box { background:var(--bg-card,#161616); border:1px solid var(--border,#2a2a2a); border-radius:20px; padding:32px 28px; max-width:460px; width:100%; transform:scale(0.95); transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1); }
    .bmi-advice-overlay.open .bmi-advice-box { transform:scale(1); }
    .bmi-advice-header { display:flex; align-items:center; gap:14px; margin-bottom:24px; }
    .bmi-advice-icon { font-size:32px; }
    .bmi-advice-title { font-size:18px; font-weight:700; color:var(--text-primary,#f0f0f0); }
    .bmi-advice-sub { font-size:12px; color:var(--text-muted,#666); margin-top:3px; }
    .bmi-score-row { display:flex; align-items:center; gap:16px; background:rgba(255,255,255,0.03); border:1px solid var(--border,#2a2a2a); border-radius:12px; padding:16px 20px; margin-bottom:20px; }
    .bmi-score-num { font-size:40px; font-weight:800; line-height:1; }
    .bmi-score-cat { font-size:16px; font-weight:700; }
    .bmi-score-desc { font-size:11px; color:var(--text-muted,#666); margin-top:4px; }
    .bmi-advice-text { font-size:14px; line-height:1.7; color:var(--text-secondary,#ccc); margin-bottom:20px; }
    .bmi-suggestion-box { background:rgba(232,255,71,0.04); border:1px solid rgba(232,255,71,0.15); border-radius:10px; padding:14px 16px; margin-bottom:20px; }
    .bmi-sug-label { font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:var(--text-muted,#666); display:block; margin-bottom:10px; }
    .bmi-sug-row { display:flex; align-items:center; gap:10px; font-size:13px; font-weight:600; }
    .bmi-sug-old { color:#ff6b6b; text-decoration:line-through; } .bmi-sug-arrow { color:var(--text-muted,#666); } .bmi-sug-new { color:#4ecdc4; }
    .bmi-advice-actions { display:flex; flex-direction:column; gap:10px; }
    .bmi-btn-accept { width:100%; padding:14px; background:var(--accent,#e8ff47); color:#0a0a0a; border:none; border-radius:10px; font-weight:700; font-size:14px; cursor:pointer; transition:opacity 0.2s; font-family:inherit; }
    .bmi-btn-accept:hover { opacity:0.88; }
    .bmi-btn-reject { width:100%; padding:12px; background:transparent; color:var(--text-muted,#666); border:1px solid var(--border,#2a2a2a); border-radius:10px; font-size:13px; font-weight:500; cursor:pointer; transition:all 0.2s; font-family:inherit; }
    .bmi-btn-reject:hover { color:var(--text-primary); border-color:var(--border-hover); }

    .day-nutrition-bar { display:flex; align-items:center; background:rgba(255,255,255,0.015); border-bottom:1px solid var(--border,#2a2a2a); padding:10px 22px; }
    .dn-item { flex:1; display:flex; align-items:center; gap:7px; padding:4px 0; }
    .dn-icon { font-size:14px; }
    .dn-label { font-size:10px; color:var(--text-muted,#666); letter-spacing:0.5px; }
    .dn-val { font-size:13px; font-weight:700; color:var(--text-primary,#f0f0f0); margin-left:auto; }
    .dn-val small { font-size:9px; font-weight:400; color:var(--text-muted,#666); }
    .dn-divider { width:1px; height:28px; background:var(--border,#2a2a2a); margin:0 12px; }

    .nutr-sidebar { display:flex; flex-direction:column; gap:16px; }
    .nutr-header h2 { font-size:18px; font-weight:700; letter-spacing:1px; color:var(--accent,#e8ff47); text-transform:uppercase; margin-bottom:4px; }
    .nutr-date { font-size:11px; color:var(--text-muted,#666); }
    .nutr-target-card { background:rgba(232,255,71,0.04); border:1px solid rgba(232,255,71,0.12); border-radius:12px; padding:16px; display:flex; flex-direction:column; gap:10px; }
    .nutr-target-row { display:flex; justify-content:space-between; align-items:center; font-size:13px; }
    .nutr-target-lbl { color:var(--text-secondary,#aaa); }
    .nutr-target-val { font-weight:700; color:var(--accent,#e8ff47); }
    .nutr-day-type { font-size:11px; font-weight:600; padding:6px 10px; border-radius:6px; text-align:center; letter-spacing:0.5px; }
    .nutr-day-type.workout { background:rgba(78,205,196,0.1); color:#4ecdc4; }
    .nutr-day-type.rest    { background:rgba(167,139,250,0.1); color:#a78bfa; }
    .nutr-progress-wrap { display:flex; flex-direction:column; gap:6px; }
    .nutr-progress-row { display:flex; justify-content:space-between; font-size:11px; color:var(--text-secondary,#888); }
    .nutr-bar-bg { height:6px; background:var(--border,#2a2a2a); border-radius:3px; overflow:hidden; }
    .nutr-bar-fill { height:100%; border-radius:3px; transition:width 0.5s ease; }
    .cal-bar { background:#e8ff47; } .prot-bar { background:#4ecdc4; }
    .nutr-tabs { display:flex; gap:4px; background:var(--bg-secondary,#111); border-radius:10px; padding:4px; }
    .nutr-tab { flex:1; padding:9px; border:none; border-radius:8px; background:transparent; color:var(--text-muted,#666); font-size:11px; font-weight:600; cursor:pointer; transition:all 0.2s; font-family:inherit; }
    .nutr-tab.on { background:var(--accent,#e8ff47); color:#0a0a0a; }
    .nutr-tab-pane { display:none; flex-direction:column; gap:10px; }
    .nutr-tab-pane.on { display:flex; }
    .nutr-input-group { display:flex; flex-direction:column; gap:5px; }
    .nutr-input-group label { font-size:10px; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; color:var(--text-muted,#666); }
    .nutr-input-group input { background:var(--bg-secondary,#111); border:1px solid var(--border,#2a2a2a); border-radius:8px; padding:10px 12px; color:var(--text-primary,#f0f0f0); font-size:13px; font-family:inherit; outline:none; transition:border-color 0.2s; box-sizing:border-box; width:100%; }
    .nutr-input-group input:focus { border-color:var(--accent,#e8ff47); }
    .nutr-btn-add { width:100%; padding:12px; background:var(--accent,#e8ff47); color:#0a0a0a; border:none; border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; transition:opacity 0.2s; font-family:inherit; }
    .nutr-btn-add:hover { opacity:0.88; }
    .nutr-ai-hint { font-size:12px; color:var(--text-muted,#666); line-height:1.5; padding:8px 0; }
    .nutr-food-input { background:var(--bg-secondary,#111); border:1px solid var(--border,#2a2a2a); border-radius:8px; padding:10px 12px; color:var(--text-primary,#f0f0f0); font-size:13px; font-family:inherit; resize:vertical; outline:none; transition:border-color 0.2s; width:100%; box-sizing:border-box; }
    .nutr-food-input:focus { border-color:var(--accent,#e8ff47); }
    .nutr-btn-analyze { width:100%; padding:12px; background:rgba(78,205,196,0.12); color:#4ecdc4; border:1px solid rgba(78,205,196,0.3); border-radius:8px; font-weight:700; font-size:13px; cursor:pointer; transition:all 0.2s; font-family:inherit; }
    .nutr-btn-analyze:hover:not(:disabled) { background:rgba(78,205,196,0.2); }
    .nutr-btn-analyze:disabled { opacity:0.5; cursor:not-allowed; }
    .food-analysis-result { background:var(--bg-secondary,#111); border:1px solid var(--border,#2a2a2a); border-radius:10px; padding:14px; display:flex; flex-direction:column; gap:10px; }
    .fa-summary { font-size:12px; color:var(--text-muted,#666); line-height:1.5; font-style:italic; }
    .fa-items { display:flex; flex-direction:column; gap:6px; }
    .fa-item { display:flex; justify-content:space-between; align-items:center; font-size:12px; padding:6px 0; border-bottom:1px solid var(--border,#2a2a2a); }
    .fa-item:last-child { border-bottom:none; }
    .fa-item-name { color:var(--text-primary,#f0f0f0); font-weight:500; }
    .fa-item-name small { color:var(--text-muted,#666); margin-left:4px; }
    .fa-item-nums { color:var(--accent,#e8ff47); font-weight:600; font-size:11px; }
    .fa-total { display:flex; flex-direction:column; gap:6px; padding-top:8px; border-top:1px solid var(--border,#2a2a2a); }
    .fa-total-row { display:flex; justify-content:space-between; font-size:13px; }
    .fa-total-row strong { color:var(--accent,#e8ff47); }
    .nutr-note-box { display:flex; gap:10px; align-items:flex-start; background:rgba(167,139,250,0.05); border:1px solid rgba(167,139,250,0.15); border-radius:8px; padding:12px; font-size:12px; color:var(--text-secondary,#aaa); line-height:1.5; }
    .nutr-note-icon { font-size:14px; flex-shrink:0; margin-top:1px; }

    .routine-item { display:flex; align-items:center; gap:14px; }
    .ex-checkbox-wrap { flex-shrink:0; cursor:pointer; padding:4px; }
    .routine-item-info { flex:1; cursor:pointer; padding:2px 0; }
    .routine-item-info:hover h4 { color:var(--accent,#e8ff47); }
    .tag-rest { color:#a78bfa; background:rgba(167,139,250,0.08); }
    .btn-ex-detail { width:32px; height:32px; border-radius:8px; border:1px solid var(--border,#2a2a2a); background:transparent; color:var(--text-muted,#666); font-size:20px; line-height:1; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:all 0.2s; }
    .btn-ex-detail:hover { border-color:var(--accent); color:var(--accent); background:rgba(232,255,71,0.06); }

    .ex-modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.75); backdrop-filter:blur(6px); z-index:9000; display:flex; align-items:flex-end; justify-content:center; opacity:0; pointer-events:none; transition:opacity 0.25s ease; }
    .ex-modal-overlay.open { opacity:1; pointer-events:all; }
    .ex-modal-overlay.open .ex-modal { transform:translateY(0); }
    .ex-modal { width:100%; max-width:560px; max-height:88vh; overflow-y:auto; background:var(--bg-card,#161616); border:1px solid var(--border,#2a2a2a); border-radius:20px 20px 0 0; padding:28px 28px 40px; position:relative; transform:translateY(40px); transition:transform 0.3s cubic-bezier(0.34,1.56,0.64,1); }
    .ex-modal-close { position:absolute; top:16px; right:16px; width:32px; height:32px; border-radius:50%; border:1px solid var(--border,#2a2a2a); background:var(--bg-secondary,#111); color:var(--text-muted,#666); font-size:14px; cursor:pointer; display:flex; align-items:center; justify-content:center; transition:all 0.2s; z-index:10; }
    .ex-modal-close:hover { background:#e74c3c; border-color:#e74c3c; color:#fff; }
    .ex-modal-hero { display:flex; align-items:center; gap:18px; margin-bottom:24px; padding-top:8px; }
    .ex-modal-icon { width:72px; height:72px; border-radius:16px; background:rgba(232,255,71,0.06); border:1px solid rgba(232,255,71,0.15); display:flex; align-items:center; justify-content:center; font-size:28px; font-weight:800; color:var(--accent,#e8ff47); flex-shrink:0; }
    .ex-modal-muscle { font-size:10px; font-weight:700; letter-spacing:2px; color:var(--accent,#e8ff47); margin-bottom:6px; }
    .ex-modal-name { font-size:22px; font-weight:700; color:var(--text-primary,#f0f0f0); line-height:1.2; margin-bottom:10px; }
    .ex-modal-badges { display:flex; gap:6px; flex-wrap:wrap; }
    .em-badge { font-size:10px; font-weight:700; padding:3px 10px; border-radius:20px; letter-spacing:0.5px; }
    .badge-b { background:rgba(78,205,196,0.12); color:#4ecdc4; border:1px solid rgba(78,205,196,0.25); }
    .badge-i { background:rgba(232,255,71,0.10); color:#e8ff47; border:1px solid rgba(232,255,71,0.25); }
    .badge-a { background:rgba(231,76,60,0.12); color:#e74c3c; border:1px solid rgba(231,76,60,0.25); }
    .ex-modal-stats { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:24px; }
    .em-stat { background:var(--bg-secondary,#111); border:1px solid var(--border,#2a2a2a); border-radius:10px; padding:14px 10px; text-align:center; }
    .em-stat-num { font-size:22px; font-weight:700; color:var(--accent,#e8ff47); line-height:1; margin-bottom:4px; }
    .em-stat-lbl { font-size:10px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; color:var(--text-muted,#666); }
    .ex-modal-tabs { display:flex; gap:4px; background:var(--bg-secondary,#111); border-radius:10px; padding:4px; margin-bottom:20px; }
    .em-tab { flex:1; padding:9px; border:none; border-radius:8px; background:transparent; color:var(--text-muted,#666); font-size:12px; font-weight:600; cursor:pointer; transition:all 0.2s; font-family:inherit; }
    .em-tab.on { background:var(--accent,#e8ff47); color:#0a0a0a; }
    .em-pane { display:none; } .em-pane.on { display:block; }
    .em-steps { list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:12px; }
    .em-step { display:flex; align-items:flex-start; gap:14px; padding:14px 16px; background:var(--bg-secondary,#111); border:1px solid var(--border,#2a2a2a); border-radius:10px; }
    .em-step-num { font-size:11px; font-weight:800; color:var(--accent,#e8ff47); letter-spacing:1px; flex-shrink:0; margin-top:1px; }
    .em-step-text { font-size:13px; color:var(--text-primary,#f0f0f0); line-height:1.6; }
    .em-muscle-list { display:flex; flex-direction:column; gap:10px; }
    .em-muscle-item { display:flex; align-items:center; justify-content:space-between; padding:14px 16px; background:var(--bg-secondary,#111); border:1px solid var(--border,#2a2a2a); border-radius:10px; }
    .em-muscle-role { font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:var(--text-muted,#666); }
    .em-muscle-name { font-size:14px; font-weight:600; color:var(--text-primary,#f0f0f0); }
    .em-tips { list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:10px; }
    .em-tip { display:flex; align-items:flex-start; gap:12px; padding:14px 16px; background:rgba(232,255,71,0.03); border:1px solid rgba(232,255,71,0.1); border-radius:10px; font-size:13px; color:var(--text-primary,#f0f0f0); line-height:1.6; }
    .em-tip-icon { font-size:14px; flex-shrink:0; margin-top:1px; }
    @media (min-width:600px) { .ex-modal-overlay { align-items:center; } .ex-modal { border-radius:20px; } }
    `;
  document.head.appendChild(s);
})();

// ════════════════════════════════════════
// MODAL CHỐT SỔ NGÀY TẬP
// ════════════════════════════════════════
let pendingLockPlanId = null;
let pendingLockDayNumber = null;

// 1. Mở Modal hỏi xác nhận
function askLockPlanDay(planId, dayNumber) {
  pendingLockPlanId = planId;
  pendingLockDayNumber = dayNumber;

  // Cập nhật số ngày hiển thị trên Modal
  const displaySpan = document.getElementById("lockDayNumDisplay");
  if (displaySpan) displaySpan.textContent = `Ngày ${dayNumber}`;

  const modal = document.getElementById("lockDayModalOverlay");
  if (modal) modal.classList.add("open");
}

// 2. Đóng Modal
function closeLockDayModal() {
  const modal = document.getElementById("lockDayModalOverlay");
  if (modal) modal.classList.remove("open");
  pendingLockPlanId = null;
  pendingLockDayNumber = null;
}

// 3. Thực thi Chốt sổ (Gọi API)
async function executeLockPlanDay() {
  // 1. Nếu biến tạm bị rỗng, thử lấy lại từ giao diện hoặc biến toàn cục
  const pId = pendingLockPlanId || currentPlanId;
  const dNum = pendingLockDayNumber || currentDisplayDayIndex + 1;

  if (!pId) {
    showToast("❌ Không tìm thấy ID lộ trình!", "error");
    return;
  }

  closeLockDayModal();

  try {
    console.log(`🔒 Đang chốt sổ: Plan ${pId}, Ngày ${dNum}`);

    const res = await fetch(`${AI_SERVER_URL}/api/lock-plan-day`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        planId: pId,
        plan_id: pId,
        dayNumber: dNum,
        day_number: dNum,
      }),
    });

    const data = await res.json();
    if (data.success) {
      showToast(data.message || "✅ Đã chốt sổ thành công!", "success");
      // Đợi 1 giây để người dùng kịp thấy thông báo rồi mới load lại
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast("❌ Lỗi: " + (data.error || "Không rõ nguyên nhân"), "error");
    }
  } catch (e) {
    console.error("Lỗi fetch:", e);
    showToast("❌ Lỗi kết nối máy chủ", "error");
  }
}

// GỌI API KHÓA DINH DƯỠNG
async function lockNutritionDay() {
  try {
    const res = await fetch(`${AI_SERVER_URL}/api/lock-nutrition`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: USER_ID, date: TODAY }),
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, "success");
      todayNutrition.is_locked = true;
      updateNutritionUI(); // Render lại UI ẩn đi nút nhập
    }
  } catch (e) {
    showToast("Lỗi kết nối", "error");
  }
}
// ════════════════════════════════════════
// HÀM KIỂM TRA NGÀY ĐÃ ĐƯỢC MỞ KHÓA CHƯA
// ════════════════════════════════════════
function isDayUnlocked(dayNumber) {
  if (!planStartDateStr) return true; // Fallback nếu lỗi

  // Cắt chuỗi "DD/MM/YYYY" từ backend gửi về
  const parts = planStartDateStr.split("/");
  if (parts.length !== 3) return true;

  // Tạo object Date cho ngày bắt đầu (Đưa về 00:00:00)
  const startDate = new Date(parts[2], parts[1] - 1, parts[0]);
  startDate.setHours(0, 0, 0, 0);

  // Tạo object Date cho ngày hiện tại (Đưa về 00:00:00)
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Tính số ngày chênh lệch
  const diffTime = today.getTime() - startDate.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  // Ngày 1: diff = 0. Ngày 2: diff = 1...
  return dayNumber - 1 <= diffDays;
}
// ════════════════════════════════════════
// HÀM LẤY NGÀY HIỆN TẠI & TỰ ĐỘNG RESET GIAO DIỆN KHI QUA ĐÊM
// ════════════════════════════════════════

// 1. Cung cấp hàm lấy giờ thực tế (Bắt buộc phải có)
function getCurrentDateStr() {
    // Ép múi giờ về giờ Việt Nam (hoặc múi giờ local của máy)
    const tzOffset = new Date().getTimezoneOffset() * 60000;
    const localISOTime = new Date(Date.now() - tzOffset).toISOString().slice(0, -1);
    return localISOTime.split("T")[0];
}

// 2. Logic lén kiểm tra đồng hồ mỗi 1 phút
let lastLoadedDate = getCurrentDateStr();
console.log("⏰ Đồng hồ hệ thống hiện tại:", lastLoadedDate);

setInterval(() => {
    const liveDate = getCurrentDateStr();
    
    // Nếu phát hiện đồng hồ hệ thống đã nhảy sang ngày mới
    if (liveDate !== lastLoadedDate) {
        console.log("🕛 Đã qua ngày mới! Tự động reset bảng dinh dưỡng...");
        lastLoadedDate = liveDate; // Cập nhật lại ngày chốt
        
        // Gọi lại hàm tải dinh dưỡng để reset thanh Bar về 0
        if (typeof loadTodayNutrition === "function") {
            loadTodayNutrition(); 
        }
    }
}, 60000);
