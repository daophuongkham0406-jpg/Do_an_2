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

// ════════════════════════════════════════
// CSS NỘI TUYẾN cho các element mới
// (Thêm vào TrangCaNhan.css hoặc để ở đây)
// ════════════════════════════════════════
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
