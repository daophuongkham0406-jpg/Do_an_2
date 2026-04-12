// ═══════════════════════════════════════════════════════
// THÊM ĐOẠN NÀY VÀO CUỐI FILE Tcn.js (function_proc/Tcn.js)
// Hiển thị lộ trình đang active lên trang hồ sơ cá nhân
// ═══════════════════════════════════════════════════════

const AI_SERVER = "http://localhost:5001";
const CURRENT_UID = localStorage.getItem("userId") || "guest";

// ── Gọi khi trang load xong ──
document.addEventListener("DOMContentLoaded", () => {
  loadActivePlan();
  loadAllPlansHistory();
});

// ════════════════════════════════════════
// 1. LỘ TRÌNH ĐANG ACTIVE (hiển thị tiến độ)
// ════════════════════════════════════════
async function loadActivePlan() {
  try {
    const res = await fetch(
      `${AI_SERVER}/api/get-active-plan?userId=${CURRENT_UID}`,
    );
    const data = await res.json();

    const wrap = document.getElementById("activePlanWrap");
    if (!wrap) return;

    if (!data.plan) {
      wrap.innerHTML = `
                <div style="padding:24px;text-align:center;color:var(--text-muted);font-size:13px;">
                    Chưa có lộ trình nào đang hoạt động.
                    <br><a href="lotrinh.html" style="color:var(--accent);font-weight:700;margin-top:8px;display:inline-block;">→ Tạo lộ trình ngay</a>
                </div>`;
      return;
    }

    const plan = data.plan;
    const done = plan.days_done || 0;
    const total = plan.duration_days || 7;
    const pct = Math.round((done / total) * 100);
    const dailyProg = plan.daily_progress || [];

    // Header + progress bar
    wrap.innerHTML = `
            <div class="active-plan-header">
                <div>
                    <div class="active-plan-name">${plan.plan_name || "Lộ trình"}</div>
                    <div class="active-plan-meta">${plan.goal} · ${plan.level} · Tạo ngày ${plan.created_at}</div>
                </div>
                <a href="lotrinh.html" class="btn-view-plan">Xem chi tiết →</a>
            </div>

            <div class="active-progress-wrap">
                <div class="active-progress-top">
                    <span>Tiến độ</span>
                    <span style="color:var(--accent);font-weight:700;">${pct}% · ${done}/${total} ngày</span>
                </div>
                <div class="progress-bar-bg" style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;">
                    <div style="height:100%;width:${pct}%;background:var(--accent);border-radius:3px;transition:width .4s;"></div>
                </div>
            </div>

            <div class="active-days-grid" id="activeDaysGrid"></div>`;

    // Render mini day-dots
    const grid = document.getElementById("activeDaysGrid");
    dailyProg.forEach((day) => {
      const dot = document.createElement("div");
      dot.className = `day-dot ${day.day_done ? "done" : day.is_rest ? "rest" : "pending"}`;
      dot.title = `${day.day_name} — ${day.focus || "Nghỉ"}`;
      dot.innerHTML = day.day_done ? "✓" : day.is_rest ? "💤" : day.day_number;
      grid.appendChild(dot);
    });
  } catch (e) {
    console.warn("Không tải được lộ trình active:", e);
  }
}

// ════════════════════════════════════════
// 2. LỊCH SỬ TẤT CẢ LỘ TRÌNH (thành tích)
// ════════════════════════════════════════
async function loadAllPlansHistory() {
  try {
    const res = await fetch(
      `${AI_SERVER}/api/get-all-plans?userId=${CURRENT_UID}`,
    );
    const data = await res.json();

    // Cập nhật số lộ trình hoàn thành lên hero pills
    const completed = (data.plans || []).filter(
      (p) => p.status === "completed",
    );
    const pRoutines = document.getElementById("pRoutines");
    if (pRoutines) pRoutines.textContent = completed.length;

    const countEl = document.getElementById("routineCount");
    if (countEl) countEl.textContent = completed.length;

    // Render danh sách lộ trình đã xong
    const list = document.getElementById("routineList");
    if (!list) return;

    if (completed.length === 0) {
      list.innerHTML = `<div style="padding:16px;color:var(--text-muted);font-size:13px;">Chưa hoàn thành lộ trình nào.</div>`;
      return;
    }

    list.innerHTML = "";
    completed.forEach((plan) => {
      const item = document.createElement("div");
      item.className = "routine-item-tcn";
      item.innerHTML = `
                <div class="ri-icon">🏆</div>
                <div class="ri-info">
                    <div class="ri-name">${plan.plan_name || "Lộ trình"}</div>
                    <div class="ri-meta">${plan.goal} · ${plan.duration_days} ngày · Hoàn thành ${plan.created_at}</div>
                </div>
                <div class="ri-badge">Xong</div>`;
      list.appendChild(item);
    });
  } catch (e) {
    console.warn("Không tải được lịch sử lộ trình:", e);
  }
}

// ═══════════════════════════════════════════════════════
// CÁC HÀM VẼ BIỂU ĐỒ & GIAO DIỆN TỪ DỮ LIỆU THẬT
// ═══════════════════════════════════════════════════════

// ── 1. Render Buổi tập gần đây ──
// workoutsData là mảng: [{name: "Tăng cơ Ngực", date: "Hôm qua", time: "45 phút", vol: "3200 kg"}, ...]
function renderRecentWorkouts(workoutsData) {
  const list = document.getElementById("wlogList");
  if (!list) return;

  if (!workoutsData || workoutsData.length === 0) {
    list.innerHTML = `<div style="padding:16px 0;color:var(--text-muted);font-size:13px;text-align:center;">Chưa có lịch sử tập luyện.</div>`;
    return;
  }

  let html = "";
  workoutsData.forEach((log) => {
    html += `
            <div style="display:flex; justify-content:space-between; align-items:center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                <div>
                    <div style="font-size:14px; font-weight:600; color:var(--text-main); margin-bottom:4px;">${log.name}</div>
                    <div style="font-size:11px; color:var(--text-muted);">🕒 ${log.time || "--"} · 🏋️ Tổng tạ: ${log.vol || "--"}</div>
                </div>
                <div style="font-size:12px; color:var(--text-muted); font-weight:500;">${log.date}</div>
            </div>
        `;
  });
  list.innerHTML = html;
}

// ── 2. Vẽ Biểu đồ Tần suất ──
// freqData là mảng chứa số buổi tập các tuần: [3, 4, 4, 2, 5, 4, 3, 4]
function drawFreqChart(freqData) {
  const cv = document.getElementById("freqChart");
  if (!cv) return;
  if (!freqData || freqData.length === 0) freqData = [0, 0, 0, 0, 0, 0, 0, 0]; // Mặc định nếu ko có data

  const W = cv.offsetWidth || 400,
    H = cv.height || 200;
  cv.width = W;
  cv.height = H;
  const ctx = cv.getContext("2d");
  ctx.clearRect(0, 0, W, H);

  const pad = { t: 20, b: 30, l: 30, r: 10 };
  const cW = W - pad.l - pad.r,
    cH = H - pad.t - pad.b;
  const maxVal = Math.max(...freqData, 4); // Cột cao nhất dựa trên data thật (thấp nhất là 4)

  // Vẽ đường mục tiêu (4 buổi/tuần)
  const targetY = pad.t + cH - (4 / maxVal) * cH;
  ctx.strokeStyle = "rgba(77,168,255,0.4)";
  ctx.setLineDash([5, 5]);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(pad.l, targetY);
  ctx.lineTo(W - pad.r, targetY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Vẽ cột
  const barW = (cW / freqData.length) * 0.5;
  const gap = cW / freqData.length;

  freqData.forEach((val, i) => {
    const h = (val / maxVal) * cH;
    const x = pad.l + i * gap + (gap - barW) / 2;
    const y = pad.t + cH - h;

    const grd = ctx.createLinearGradient(0, y, 0, y + h);
    grd.addColorStop(0, "#4da8ff");
    grd.addColorStop(1, "rgba(77,168,255,0.2)");

    ctx.fillStyle = grd;
    ctx.beginPath();
    ctx.roundRect(x, y, barW, h, [4, 4, 0, 0]);
    ctx.fill();

    ctx.fillStyle = "#888";
    ctx.font = "10px Inter";
    ctx.textAlign = "center";
    ctx.fillText(`T${i + 1}`, x + barW / 2, H - 10);
  });
}

// ── 3. Vẽ Radar Phân bổ Cơ bắp ──
// muscleData là mảng tỷ lệ % tương ứng: [Ngực, Lưng, Chân, Vai, Tay, Bụng] -> Ví dụ: [80, 65, 90, 60, 75, 45]
function drawRadarChart(muscleData) {
  const cv = document.getElementById("radarChart");
  if (!cv) return;
  if (!muscleData || muscleData.length !== 6) muscleData = [0, 0, 0, 0, 0, 0];

  const ctx = cv.getContext("2d");
  const W = cv.width,
    H = cv.height;
  const cx = W / 2,
    cy = H / 2,
    R = 80;

  ctx.clearRect(0, 0, W, H);

  const labels = ["Ngực", "Lưng", "Chân", "Vai", "Tay", "Bụng"];
  const sides = labels.length;

  // Lưới
  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 1;
  for (let level = 1; level <= 4; level++) {
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
      const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
      const r = R * (level / 4);
      const x = cx + Math.cos(angle) * r,
        y = cy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();
  }

  // Nhãn
  ctx.fillStyle = "#aaa";
  ctx.font = "bold 11px Inter";
  ctx.textAlign = "center";
  for (let i = 0; i < sides; i++) {
    const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * R, cy + Math.sin(angle) * R);
    ctx.stroke();

    let offsetX = Math.cos(angle) * (R + 25);
    let offsetY = Math.sin(angle) * (R + 20) + 4;
    ctx.fillText(labels[i], cx + offsetX, cy + offsetY);
  }

  // Dữ liệu thật
  ctx.beginPath();
  for (let i = 0; i < sides; i++) {
    const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
    const r = R * (muscleData[i] / 100);
    const x = cx + Math.cos(angle) * r,
      y = cy + Math.sin(angle) * r;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(232, 255, 71, 0.35)";
  ctx.fill();
  ctx.strokeStyle = "#e8ff47";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Dấu chấm
  for (let i = 0; i < sides; i++) {
    const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
    const r = R * (muscleData[i] / 100);
    const x = cx + Math.cos(angle) * r,
      y = cy + Math.sin(angle) * r;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#e8ff47";
    ctx.fill();
  }
}

// ── 4. Render Mục tiêu Tiến độ ──
// goalsData là mảng: [{name: "Giảm mỡ", pct: 60, color: "#4da8ff"}, ...]
function renderGoals(goalsData) {
  const list = document.getElementById("goalsList");
  if (!list) return;

  if (!goalsData || goalsData.length === 0) {
    list.innerHTML = `<div style="padding:16px 0;color:var(--text-muted);font-size:13px;text-align:center;">Chưa có mục tiêu.</div>`;
    return;
  }

  let html = "";
  goalsData.forEach((g) => {
    html += `
            <div style="margin-bottom: 16px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:13px; font-weight:600;">
                    <span style="color:var(--text-main);">${g.name}</span>
                    <span style="color:${g.color || "#e8ff47"}">${g.pct}%</span>
                </div>
                <div style="height:6px; background:var(--border); border-radius:3px; overflow:hidden;">
                    <div style="height:100%; width:${g.pct}%; background:${g.color || "#e8ff47"}; border-radius:3px; transition: width 0.5s;"></div>
                </div>
            </div>
        `;
  });
  list.innerHTML = html;
}
const _style = document.createElement("style");
_style.textContent = `
/* ── Card lộ trình active ── */
#activePlanWrap {
    background: var(--bg-card, #161616);
    border: 1px solid var(--border, #2a2a2a);
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 28px;
}

.active-plan-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
}
.active-plan-name {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-primary, #f0f0f0);
    margin-bottom: 4px;
}
.active-plan-meta {
    font-size: 11px;
    color: var(--text-muted, #555);
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.btn-view-plan {
    font-size: 11px;
    font-weight: 700;
    color: var(--accent, #e8ff47);
    text-decoration: none;
    letter-spacing: 0.5px;
    white-space: nowrap;
}
.active-progress-wrap { margin-bottom: 16px; }
.active-progress-top {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-secondary, #888);
    margin-bottom: 8px;
}

/* ── Dots ngày tập ── */
.active-days-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
}
.day-dot {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid var(--border, #2a2a2a);
    background: var(--bg-secondary, #111);
    color: var(--text-muted, #555);
    cursor: default;
}
.day-dot.done {
    background: rgba(78,205,196,0.12);
    border-color: rgba(78,205,196,0.4);
    color: #4ecdc4;
}
.day-dot.rest {
    background: rgba(255,255,255,0.03);
    color: var(--text-muted, #555);
    font-size: 10px;
}

/* ── Danh sách lộ trình đã xong ── */
.routine-item-tcn {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--border, #2a2a2a);
}
.routine-item-tcn:last-child { border-bottom: none; }
.ri-icon { font-size: 20px; }
.ri-info { flex: 1; }
.ri-name { font-size: 14px; font-weight: 600; color: var(--text-primary, #f0f0f0); margin-bottom: 3px; }
.ri-meta { font-size: 11px; color: var(--text-muted, #555); }
.ri-badge {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--accent, #e8ff47);
    background: rgba(232,255,71,0.08);
    padding: 4px 10px;
    border-radius: 4px;
}
`;
document.head.appendChild(_style);
