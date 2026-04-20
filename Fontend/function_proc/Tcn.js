// ============================================================================
// KHAI BÁO BIẾN TOÀN CỤC
// ============================================================================
const API_SERVER = "http://127.0.0.1:5000";
let userProfile = {};
let userHistory = [];
let allWorkoutsHistory = [];

let wChartInstance = null;
let fChartInstance = null;

let USER_ID = "guest";
try {
  const userStr = localStorage.getItem("loggedInUser");
  if (userStr) {
    const userObj = JSON.parse(userStr);
    USER_ID = userObj._id || userObj.id || userObj.user_id || "guest";
  }
} catch (e) {
  console.error("Lỗi đọc user:", e);
}

const userStr = localStorage.getItem("loggedInUser");
const localUser = userStr ? JSON.parse(userStr) : {};
const CURRENT_UID = localUser.id || localUser._id || "guest";

if (typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels);
} else {
    console.warn("⚠️ Chưa tải được ChartDataLabels.");
}

// ============================================================================
// KHỞI CHẠY KHI TẢI TRANG
// ============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  if (!userStr || CURRENT_UID === "guest") {
    toast("❌ Lỗi: Không tìm thấy tài khoản! Vui lòng đăng nhập lại.", "err");
    return;
  }

  await fetchOldProfile();
  fetchActivePlan(CURRENT_UID);
  fetchTcnOverview();
  fetchRadarChart();
  fetchWeightChart();
  fetchWeightsData();

  // Kiểm tra trạng thái VIP và cập nhật nút
  await checkAndUpdateVipButton();
});

// ============================================================================
// KIỂM TRA VIP VÀ CẬP NHẬT NÚT
// ============================================================================
async function checkAndUpdateVipButton() {
  const btn = document.getElementById("btnUpgradeVip");
  if (!btn) return;

  try {
    const res  = await fetch(`${API_SERVER}/api/payment/status/${CURRENT_UID}`);
    const data = await res.json();

    if (data.isPremium) {
      // Cập nhật localStorage
      try {
        const uStr = localStorage.getItem("loggedInUser");
        if (uStr) {
          const uObj = JSON.parse(uStr);
          uObj.isPremium   = true;
          uObj.premiumPlan = data.plan;
          localStorage.setItem("loggedInUser", JSON.stringify(uObj));
        }
      } catch(e) {}

      renderVipActiveButton(btn, data);
    } else {
      renderVipUpgradeButton(btn);
    }
  } catch (e) {
    console.warn("Không kiểm tra được VIP status:", e);
    renderVipUpgradeButton(btn);
  }
}

// Nút khi CHƯA VIP
function renderVipUpgradeButton(btn) {
  btn.innerHTML = "👑 Nâng cấp VIP (50.000đ)";
  btn.style.background = "linear-gradient(90deg, #ffd700, #ffa500)";
  btn.style.color = "#000";
  btn.style.cursor = "pointer";
  btn.onclick = () => openPaymentModal();
}

// Nút khi ĐÃ VIP — hiển thị đếm ngược
function renderVipActiveButton(btn, data) {
  const planLabel = data.plan === "vip_3month" ? "3 Tháng" : "1 Tháng";
  const expireDate = data.expireDate || "";

  // Tính số ngày còn lại
  let daysLeft = 0;
  if (expireDate) {
    const parts = expireDate.split('/');
    if (parts.length === 3) {
      const expire = new Date(parts[2], parts[1] - 1, parts[0]);
      const today  = new Date();
      today.setHours(0, 0, 0, 0);
      daysLeft = Math.max(0, Math.ceil((expire - today) / (1000 * 60 * 60 * 24)));
    }
  }

  btn.innerHTML = `
    <span style="font-size:14px;">👑 VIP ${planLabel} · còn ${daysLeft} ngày</span>
    <span style="display:block;font-size:10px;opacity:0.8;margin-top:2px;">
      Hết hạn: ${expireDate}
    </span>
  `;
  btn.style.background = "linear-gradient(90deg, #4ade80, #22c55e)";
  btn.style.color = "#000";
  btn.style.cursor = "default";
  btn.style.padding = "12px 20px";
  btn.onclick = null;

  // Đếm ngược realtime nếu còn thời gian
  if (daysLeft > 0) startVipCountdown(btn, data);
}

// Đếm ngược theo giây (nếu < 1 ngày thì hiện giờ:phút:giây)
function startVipCountdown(btn, data) {
  const expireDate = data.expireDate || "";
  if (!expireDate) return;

  const parts = expireDate.split('/');
  if (parts.length !== 3) return;

  // Hết hạn vào cuối ngày (23:59:59)
  const expireMs = new Date(
    parseInt(parts[2]),
    parseInt(parts[1]) - 1,
    parseInt(parts[0]),
    23, 59, 59
  ).getTime();

  const planLabel = data.plan === "vip_3month" ? "3 Tháng" : "1 Tháng";

  const tick = () => {
    const now      = Date.now();
    const diffMs   = expireMs - now;

    if (diffMs <= 0) {
      btn.innerHTML = "👑 VIP đã hết hạn";
      btn.style.background = "#334155";
      btn.style.color = "#94a3b8";
      btn.onclick = () => openPaymentModal();
      return;
    }

    const totalSecs = Math.floor(diffMs / 1000);
    const days      = Math.floor(totalSecs / 86400);
    const hours     = Math.floor((totalSecs % 86400) / 3600);
    const mins      = Math.floor((totalSecs % 3600) / 60);
    const secs      = totalSecs % 60;

    let countdownText = "";
    if (days > 0) {
      countdownText = `${days} ngày ${String(hours).padStart(2,'0')}:${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;
    } else {
      countdownText = `${String(hours).padStart(2,'0')}:${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;
    }

    btn.innerHTML = `
      <span style="font-size:13px;">👑 VIP ${planLabel} · còn ${countdownText}</span>
      <span style="display:block;font-size:10px;opacity:0.8;margin-top:2px;">Hết hạn: ${expireDate}</span>
    `;

    setTimeout(tick, 1000);
  };

  tick();
}

// ============================================================================
// XỬ LÝ THANH TOÁN SEPAY
// ============================================================================
function openPaymentModal() {
  if (!CURRENT_UID || CURRENT_UID === "guest") {
    alert("Vui lòng đăng nhập để nâng cấp VIP!");
    return;
  }

  const oldModal = document.getElementById("paymentModal");
  if (oldModal) oldModal.remove();

  const modal = document.createElement("div");
  modal.id = "paymentModal";
  modal.style.cssText = `
    position:fixed; inset:0; background:rgba(0,0,0,0.85);
    backdrop-filter:blur(8px); z-index:99999;
    display:flex; align-items:center; justify-content:center; padding:20px;
  `;

  modal.innerHTML = `
    <div style="
      background:#1a1a2e; border:1px solid #334155;
      border-radius:20px; padding:36px 32px;
      max-width:480px; width:100%; position:relative;
    ">
      <button onclick="cancelPayment()" style="
        position:absolute; top:16px; right:16px;
        background:transparent; border:1px solid #334155;
        color:#888; width:32px; height:32px; border-radius:50%;
        cursor:pointer; font-size:16px;
      ">✕</button>

      <div style="text-align:center; margin-bottom:28px;">
        <div style="font-size:36px; margin-bottom:8px;">👑</div>
        <h2 style="color:#f8fafc; font-size:22px; font-weight:700; margin-bottom:8px;">
          Nâng cấp VIP
        </h2>
        <p style="color:#64748b; font-size:13px;">
          Mở khóa lộ trình 21 ngày & 30 ngày cá nhân hóa bằng AI
        </p>
      </div>

      <div style="display:flex; flex-direction:column; gap:14px; margin-bottom:28px;">

        <!-- Gói 1 tháng -->
        <div class="plan-option" data-plan="vip_1month" data-amount="50000"
          onclick="selectPlan(this)"
          style="border:2px solid #334155; border-radius:14px; padding:20px; cursor:pointer; transition:all 0.2s; position:relative;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="color:#f8fafc; font-weight:700; font-size:16px;">🗓️ Gói 1 Tháng</div>
              <div style="color:#64748b; font-size:12px; margin-top:4px;">
                Lộ trình 21-30 ngày · Dinh dưỡng AI · Check-in hàng ngày
              </div>
            </div>
            <div style="text-align:right;">
              <div style="color:#38bdf8; font-size:22px; font-weight:800;">50.000đ</div>
              <div style="color:#64748b; font-size:11px;">/ tháng</div>
            </div>
          </div>
        </div>

        <!-- Gói 3 tháng -->
        <div class="plan-option" data-plan="vip_3month" data-amount="120000"
          onclick="selectPlan(this)"
          style="border:2px solid #334155; border-radius:14px; padding:20px; cursor:pointer; transition:all 0.2s; position:relative;">
          <div style="
            position:absolute; top:-10px; left:20px;
            background:linear-gradient(90deg,#ffd700,#ffa500);
            color:#000; font-size:10px; font-weight:800;
            padding:3px 12px; border-radius:20px; letter-spacing:1px;
          ">TIẾT KIỆM 20%</div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="color:#f8fafc; font-weight:700; font-size:16px;">🚀 Gói 3 Tháng</div>
              <div style="color:#64748b; font-size:12px; margin-top:4px;">
                Toàn bộ tính năng Premium · Ưu tiên AI
              </div>
            </div>
            <div style="text-align:right;">
              <div style="color:#ffd700; font-size:22px; font-weight:800;">120.000đ</div>
              <div style="color:#64748b; font-size:11px; text-decoration:line-through;">150.000đ</div>
            </div>
          </div>
        </div>
      </div>

      <button id="btnConfirmPlan" onclick="proceedToPayment()" disabled
        style="
          width:100%; padding:15px; border:none; border-radius:10px;
          background:#334155; color:#64748b;
          font-size:15px; font-weight:700; cursor:not-allowed;
          transition:all 0.3s;
        ">
        Chọn gói để tiếp tục →
      </button>
    </div>
  `;

  document.body.appendChild(modal);
}

let selectedPlan = null;
function selectPlan(el) {
  document.querySelectorAll(".plan-option").forEach(p => {
    p.style.border = "2px solid #334155";
    p.style.background = "transparent";
  });
  el.style.border = "2px solid #38bdf8";
  el.style.background = "rgba(56,189,248,0.06)";
  selectedPlan = { type: el.dataset.plan, amount: parseInt(el.dataset.amount) };

  const confirmBtn = document.getElementById("btnConfirmPlan");
  confirmBtn.disabled = false;
  confirmBtn.style.background = "linear-gradient(135deg,#38bdf8,#0ea5e9)";
  confirmBtn.style.color = "#fff";
  confirmBtn.style.cursor = "pointer";
  confirmBtn.textContent = `Thanh toán ${selectedPlan.amount.toLocaleString('vi-VN')}đ →`;
}

async function proceedToPayment() {
  if (!selectedPlan) return;
  const confirmBtn = document.getElementById("btnConfirmPlan");
  confirmBtn.disabled = true;
  confirmBtn.textContent = "⏳ Đang tạo đơn hàng...";

  try {
    const res = await fetch(`${API_SERVER}/api/payment/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: CURRENT_UID, planType: selectedPlan.type })
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error);
    showQRScreen(data);
  } catch (e) {
    alert("Lỗi tạo đơn hàng: " + e.message);
    confirmBtn.disabled = false;
    confirmBtn.textContent = "Thử lại";
  }
}

let pollingInterval = null;
function showQRScreen(paymentData) {
  const modal = document.getElementById("paymentModal");
  if (!modal) return;
  const planLabel = paymentData.plan_type === "vip_3month" ? "Gói 3 Tháng" : "Gói 1 Tháng";

  modal.querySelector("div").innerHTML = `
    <button onclick="cancelPayment()" style="
      position:absolute; top:16px; right:16px;
      background:transparent; border:1px solid #334155;
      color:#888; width:32px; height:32px; border-radius:50%;
      cursor:pointer; font-size:16px;
    ">✕</button>

    <div style="text-align:center;">
      <div style="font-size:13px; color:#64748b; margin-bottom:4px;">THANH TOÁN ${planLabel.toUpperCase()}</div>
      <div style="font-size:28px; font-weight:800; color:#38bdf8; margin-bottom:20px;">
        ${paymentData.amount.toLocaleString('vi-VN')}đ
      </div>

      <div style="background:#fff; border-radius:16px; padding:16px; display:inline-block; margin-bottom:20px;">
        <img src="${paymentData.qr_url}" alt="QR Thanh toán"
          style="width:200px; height:200px; display:block;"
          onerror="this.src='https://via.placeholder.com/200x200?text=QR+Error'" />
      </div>

      <div style="background:#0f172a; border:1px solid #334155; border-radius:12px; padding:16px; margin-bottom:20px; text-align:left;">
        <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #334155;">
          <span style="color:#64748b; font-size:12px;">Ngân hàng</span>
          <span style="color:#f8fafc; font-weight:600;">${paymentData.bank_code}</span>
        </div>
        <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #334155;">
          <span style="color:#64748b; font-size:12px;">Số tài khoản</span>
          <span style="color:#38bdf8; font-weight:700;">${paymentData.account_number}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #334155;">
          <span style="color:#64748b; font-size:12px;">Nội dung CK</span>
          <span style="color:#ffd700; font-weight:800; background:rgba(255,215,0,0.1); padding:4px 10px; border-radius:6px; cursor:pointer;"
            onclick="copyContent('${paymentData.transfer_content}')" title="Click để sao chép">
            ${paymentData.transfer_content} 📋
          </span>
        </div>
        <div style="display:flex; justify-content:space-between; padding:8px 0;">
          <span style="color:#64748b; font-size:12px;">Số tiền</span>
          <span style="color:#4ade80; font-weight:700;">${paymentData.amount.toLocaleString('vi-VN')} VNĐ</span>
        </div>
      </div>

      <div style="background:rgba(255,215,0,0.08); border:1px solid rgba(255,215,0,0.2); border-radius:10px; padding:12px; margin-bottom:16px; font-size:12px; color:#ffd700; text-align:left;">
        ⚠️ <strong>QUAN TRỌNG:</strong> Nhập đúng nội dung chuyển khoản
        <strong>${paymentData.transfer_content}</strong> để hệ thống tự động xác nhận!
      </div>

      <div id="paymentStatus" style="display:flex; align-items:center; justify-content:center; gap:10px; color:#64748b; font-size:13px; margin-bottom:16px;">
        <div style="width:12px; height:12px; border-radius:50%; border:2px solid #38bdf8; border-top-color:transparent; animation:spin 1s linear infinite;"></div>
        Đang chờ thanh toán... (tự động kiểm tra)
      </div>

      <p style="color:#475569; font-size:11px;">Hết hạn sau 15 phút · Liên hệ hỗ trợ nếu cần</p>
    </div>
  `;

  startPolling(paymentData.transfer_content);
}

function copyContent(text) {
  navigator.clipboard.writeText(text).then(() => {
    toast("📋 Đã sao chép: " + text, "ok");
  });
}

function startPolling(transferContent) {
  let attempts = 0;
  const maxAttempts = 300;

  pollingInterval = setInterval(async () => {
    attempts++;
    if (attempts > maxAttempts) {
      clearInterval(pollingInterval);
      const statusEl = document.getElementById("paymentStatus");
      if (statusEl) statusEl.innerHTML = `<span style="color:#fb7185">⏰ Hết thời gian. Vui lòng thử lại.</span>`;
      return;
    }

    try {
      const res  = await fetch(`${API_SERVER}/api/payment/check?transfer_content=${transferContent}&userId=${CURRENT_UID}`);
      const data = await res.json();
      if (data.status === "paid") {
        clearInterval(pollingInterval);
        onPaymentSuccess(data);
      }
    } catch (e) {}
  }, 3000);
}

function onPaymentSuccess(data) {
  try {
    const uStr = localStorage.getItem("loggedInUser");
    if (uStr) {
      const uObj = JSON.parse(uStr);
      uObj.isPremium   = true;
      uObj.premiumPlan = data.plan_type;
      localStorage.setItem("loggedInUser", JSON.stringify(uObj));
    }
  } catch (e) {}

  const modal = document.getElementById("paymentModal");
  if (modal) {
    modal.querySelector("div").innerHTML = `
      <div style="text-align:center; padding:20px 0;">
        <div style="font-size:60px; margin-bottom:16px;">🎉</div>
        <h2 style="color:#4ade80; font-size:24px; font-weight:800; margin-bottom:10px;">
          Thanh toán thành công!
        </h2>
        <p style="color:#94a3b8; font-size:14px; margin-bottom:8px;">
          Tài khoản của bạn đã được nâng cấp VIP
        </p>
        <div style="background:rgba(74,222,128,0.1); border:1px solid rgba(74,222,128,0.2); border-radius:10px; padding:14px; margin:20px 0; color:#4ade80; font-weight:600; font-size:14px;">
          👑 ${data.plan_type === "vip_3month" ? "Gói 3 Tháng" : "Gói 1 Tháng"}
          ${data.expire ? `· Hết hạn: ${data.expire}` : ""}
        </div>
        <button onclick="window.location.reload()" style="
          width:100%; padding:14px; border:none; border-radius:10px;
          background:linear-gradient(135deg,#4ade80,#22c55e);
          color:#000; font-size:15px; font-weight:800; cursor:pointer;
        ">
          ✨ Bắt đầu tạo lộ trình Premium!
        </button>
      </div>
    `;
  }
}

function cancelPayment() {
  if (pollingInterval) clearInterval(pollingInterval);
  selectedPlan = null;
  const modal = document.getElementById("paymentModal");
  if (modal) modal.remove();
}

// ============================================================================
// LẤY PROFILE CŨ
// ============================================================================
async function fetchOldProfile() {
  try {
    const res  = await fetch(`${API_SERVER}/api/profile/get/${CURRENT_UID}`);
    const data = await res.json();
    if (res.ok) {
      userProfile = data.profile || {};
      userHistory = data.history || [];
      if (userHistory.length === 0 && userProfile.weight) {
        userHistory.push({ date: new Date().toISOString().split("T")[0], weight: userProfile.weight });
      }
    }
  } catch (e) {
    console.error("Lỗi lấy Profile:", e);
  }
}

// ============================================================================
// QUẢN LÝ LỘ TRÌNH
// ============================================================================
async function fetchActivePlan(userId) {
  const wrap = document.getElementById("activePlanWrap");
  if (!wrap) return;

  try {
    const response = await fetch(`${API_SERVER}/api/plans/active/${userId}`);
    if (!response.ok) {
      wrap.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;background:var(--bg3);border-radius:12px;">Bạn chưa có lộ trình nào.<br>Hãy sang trang Lộ Trình để tạo ngay!</div>`;
      return;
    }
    const plan = await response.json();
    renderPlanUI(plan);
  } catch (error) {
    wrap.innerHTML = `<div style="padding:20px;text-align:center;color:#ff4d4d;font-size:13px;">Lỗi kết nối máy chủ khi tải lộ trình.</div>`;
  }
}

function renderPlanUI(plan) {
  const wrap = document.getElementById("activePlanWrap");
  if (!wrap) return;

  const cardTitle = wrap.parentElement.querySelector(".card-title");
  if (cardTitle) cardTitle.textContent = plan.plan_name || "Lộ trình AI";

  let daysHtml = "";
  const progress = plan.daily_progress || [];

  progress.forEach((dayData, index) => {
    const isDone    = dayData.is_locked || dayData.day_done;
    const textStyle = isDone ? "text-decoration: line-through; opacity: 0.5;" : "";
    const dayLabel  = dayData.day_name || `Ngày ${dayData.day_number || index + 1}`;
    const exDataStr = encodeURIComponent(JSON.stringify(dayData.exercises || []));
    const isRestStr = dayData.is_rest ? "true" : "false";

    daysHtml += `
      <div style="display:flex; align-items:center; justify-content:space-between; padding:12px 15px; border-bottom:1px solid var(--border); background:var(--bg-input); border-radius:8px; margin-bottom:8px; transition:0.3s;">
        <div style="display:flex; align-items:center; gap:12px;">
          <div style="width:18px; height:18px; border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:bold; border:2px solid ${isDone ? "#4ecdc4" : "var(--border)"}; background:${isDone ? "#4ecdc4" : "transparent"}; color:${isDone ? "#111" : "transparent"}; transition:all 0.3s;">
            ${isDone ? "✓" : ""}
          </div>
          <div style="font-size:14px; font-weight:600; color:var(--text-main); ${textStyle}">${dayLabel}</div>
        </div>
        <button onclick="openDayDetailModal('${dayLabel}', '${isRestStr}', '${exDataStr}')"
          style="background:transparent; border:1px solid var(--border); color:var(--text-muted); padding:4px 10px; border-radius:4px; font-size:11px; cursor:pointer;"
          onmouseover="this.style.color='#e8ff47'; this.style.borderColor='#e8ff47'"
          onmouseout="this.style.color='var(--text-muted)'; this.style.borderColor='var(--border)'">Xem bài</button>
      </div>`;
  });
  wrap.innerHTML = daysHtml;
}

// ============================================================================
// MODAL XEM CHI TIẾT BÀI TẬP
// ============================================================================
function openDayDetailModal(dayName, isRest, exDataStr) {
  const titleEl   = document.getElementById("dayDetailTitle");
  const contentEl = document.getElementById("dayDetailContent");
  if (!titleEl || !contentEl) return;

  titleEl.textContent = `Chi tiết ${dayName}`;

  if (isRest === "true") {
    contentEl.innerHTML = `<div style="text-align:center; padding:30px 20px; color:var(--text-muted); background:var(--bg-secondary); border-radius:12px;">🛌<br><br>Hôm nay là ngày nghỉ ngơi phục hồi.</div>`;
  } else {
    try {
      const exercises = JSON.parse(decodeURIComponent(exDataStr));
      if (exercises.length === 0) {
        contentEl.innerHTML = `<div style="color:var(--text-muted);">Không có bài tập nào.</div>`;
      } else {
        contentEl.innerHTML = exercises.map((ex, i) => `
          <div style="background:var(--bg-secondary); padding:14px; border-radius:10px; border:1px solid var(--border); display:flex; align-items:center; gap:12px; margin-bottom:8px;">
            <div style="font-family:'Bebas Neue'; font-size:24px; color:var(--border2); width:30px;">0${i + 1}</div>
            <div>
              <div style="font-weight:600; color:var(--text-main); margin-bottom:4px; font-size:15px;">${ex.name}</div>
              <div style="font-size:12px; color:var(--accent); font-weight:600;">
                ${ex.sets} Sets × ${ex.reps} Reps
                <span style="color:var(--text-muted); font-weight:400; margin-left:8px;">⏱ Nghỉ: ${ex.rest}s</span>
              </div>
            </div>
          </div>`).join("");
      }
    } catch (e) {
      contentEl.innerHTML = `<div style="color:#ff6060;">Lỗi hiển thị bài tập.</div>`;
    }
  }
  document.getElementById("dayDetailModalOverlay").classList.add("open");
}

function closeDayDetailModal() {
  const modal = document.getElementById("dayDetailModalOverlay");
  if (modal) modal.classList.remove("open");
}

function safeSetText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ============================================================================
// API THỐNG KÊ
// ============================================================================
async function fetchTcnOverview() {
  try {
    const res = await fetch(`${API_SERVER}/api/tcn/overview?userId=${CURRENT_UID}`).then(r => r.json());
    if (res.success) {
      const d = res.data;
      safeSetText("profileName", d.fullName.toUpperCase());
      safeSetText("avatarEl", d.fullName.charAt(0).toUpperCase());
      safeSetText("metaAge", d.age);
      safeSetText("metaWeight", d.weight);
      safeSetText("metaHeight", d.height);
      safeSetText("metaBMI", `BMI ${d.bmi}`);
      safeSetText("pWorkouts", d.workoutsCompleted);
      safeSetText("pRoutines", d.routinesCompleted);
      safeSetText("pWeightChange", d.weightChange);
      safeSetText("pStreak", d.currentStreak);
      safeSetText("routineCount", d.routinesCompleted);
      safeSetText("metaWorkouts", d.workoutsCompleted);
      safeSetText("sv-w", `${d.weight} kg`);
      safeSetText("sv-h", `${d.height} cm`);
      safeSetText("sv-bmi", d.bmi);
      safeSetText("sv-m", d.musclePct > 0 ? `${d.musclePct}%` : "--");

      const routineList = document.getElementById("routineList");
      if (routineList) {
        routineList.innerHTML = d.routinesCompleted > 0
          ? `<p style='color:var(--accent); font-size:14px; padding:10px 0;'>🏆 Đã hoàn thành ${d.routinesCompleted} lộ trình!</p>`
          : `<p style='color:#888; font-size:13px; padding:10px 0;'>Bạn chưa hoàn thành lộ trình nào.</p>`;
      }

      const streakBadge = document.getElementById("streakBadge");
      if (streakBadge) {
        streakBadge.textContent = `🔥 Streak ${d.currentStreak}`;
        if (d.currentStreak > 3) streakBadge.style.color = "#ff6060";
      }

      renderRecentWorkouts(d.recentWorkouts);
      allWorkoutsHistory = d.allWorkouts;
      drawFreqChart(d.freqData);
      updateBMIScale(d.bmi);
    }
  } catch (e) {
    console.error("Lỗi tải Overview:", e);
  }
}

async function fetchRadarChart() {
  try {
    const res = await fetch(`${API_SERVER}/api/tcn/radar?userId=${CURRENT_UID}`).then(r => r.json());
    if (res.success) drawRadarChart(res.data);
  } catch (e) {}
}

async function fetchWeightChart() {
  try {
    const res = await fetch(`${API_SERVER}/api/tcn/weight-chart?userId=${CURRENT_UID}`).then(r => r.json());
    if (res.success && res.data.labels.length > 0) {
      drawRealWeightChart(res.data.labels, res.data.weights, res.data.goal_weight);
    }
  } catch (e) {}
}

// ============================================================================
// VẼ BIỂU ĐỒ
// ============================================================================
function renderRecentWorkouts(workoutsData) {
  const list = document.getElementById("wlogList");
  if (!list) return;
  if (!workoutsData || workoutsData.length === 0) {
    list.innerHTML = `<div style="padding:16px 0;color:var(--text-muted);font-size:13px;">Chưa có lịch sử tập luyện.</div>`;
    return;
  }
  list.innerHTML = workoutsData.map(log => `
    <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--border);">
      <div>
        <div style="font-size:14px; font-weight:600; color:var(--text-main); margin-bottom:4px;">${log.name}</div>
        <div style="font-size:11px; color:var(--text-muted);">🕒 ${log.time} · 🏋️ ${log.vol}</div>
      </div>
      <div style="font-size:12px; color:var(--accent); font-weight:500;">${log.date}</div>
    </div>`).join("");
}

function drawRealWeightChart(labels, data, goalWeight) {
  const cv = document.getElementById("weightChart");
  if (!cv) return;
  const ctx      = cv.getContext("2d");
  const goalData = Array(labels.length).fill(goalWeight);
  if (wChartInstance) wChartInstance.destroy();

  const pluginsArray = typeof ChartDataLabels !== 'undefined' ? [ChartDataLabels] : [];

  wChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Cân nặng (kg)",
          data,
          borderColor: "#e8ff47",
          backgroundColor: "rgba(232,255,71,0.1)",
          borderWidth: 2,
          pointBackgroundColor: "#161616",
          pointBorderColor: "#e8ff47",
          pointBorderWidth: 2,
          pointRadius: 4,
          fill: true,
          tension: 0.4,
        },
        {
          label: "Mục tiêu",
          data: goalData,
          borderColor: "rgba(77,168,255,0.5)",
          borderWidth: 1.5,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    plugins: pluginsArray,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        datalabels: {
          display: ctx => ctx.datasetIndex === 0,
          align: 'top', anchor: 'end', offset: 5,
          color: '#e8ff47',
          font: { family: 'Barlow, sans-serif', weight: 'bold', size: 12 },
          formatter: v => v + 'kg'
        },
        legend: { display: false }
      },
      scales: {
        y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#888" } },
        x: { grid: { display: false }, ticks: { color: "#888", maxTicksLimit: 5 } },
      },
    },
  });
}

function drawRadarChart(muscleData) {
  const cv = document.getElementById("radarChart");
  if (!cv) return;
  const ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height, cx = W/2, cy = H/2, R = 80;
  ctx.clearRect(0, 0, W, H);

  const labels  = ["Ngực", "Lưng", "Chân", "Vai", "Tay", "Bụng"];
  const sides   = labels.length;
  const MAX_SCORE = Math.max(20, Math.max(...muscleData));

  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 1;
  for (let level = 1; level <= 4; level++) {
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
      const angle = ((Math.PI*2)/sides)*i - Math.PI/2;
      const r = R*(level/4);
      const x = cx + Math.cos(angle)*r, y = cy + Math.sin(angle)*r;
      i === 0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
    }
    ctx.closePath(); ctx.stroke();
  }

  ctx.fillStyle = "#aaa";
  ctx.font = "bold 11px Inter";
  ctx.textAlign = "center";
  for (let i = 0; i < sides; i++) {
    const angle = ((Math.PI*2)/sides)*i - Math.PI/2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle)*R, cy + Math.sin(angle)*R);
    ctx.stroke();
    ctx.fillText(`${labels[i]} ${muscleData[i]}`, cx + Math.cos(angle)*(R+25), cy + Math.sin(angle)*(R+20)+4);
  }

  ctx.beginPath();
  for (let i = 0; i < sides; i++) {
    const angle = ((Math.PI*2)/sides)*i - Math.PI/2;
    const r = R*(muscleData[i]/MAX_SCORE);
    const x = cx + Math.cos(angle)*r, y = cy + Math.sin(angle)*r;
    i === 0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
  }
  ctx.closePath();
  ctx.fillStyle = "rgba(232,255,71,0.35)"; ctx.fill();
  ctx.strokeStyle = "#e8ff47"; ctx.lineWidth = 2; ctx.stroke();

  for (let i = 0; i < sides; i++) {
    const angle = ((Math.PI*2)/sides)*i - Math.PI/2;
    const r = R*(muscleData[i]/MAX_SCORE);
    ctx.beginPath();
    ctx.arc(cx + Math.cos(angle)*r, cy + Math.sin(angle)*r, 4, 0, Math.PI*2);
    ctx.fillStyle = "#e8ff47"; ctx.fill();
  }
}

function updateBMIScale(bmi) {
  const needle = document.getElementById("bmiNeedle");
  const chip   = document.getElementById("bmiCatChip");
  if (!needle || !chip) return;
  let pct = 0;
  if (bmi < 18.5)      { pct = (bmi/18.5)*25; chip.textContent = "Thiếu cân"; chip.style.color = "#4da8ff"; }
  else if (bmi < 25)   { pct = 25+((bmi-18.5)/6.5)*38; chip.textContent = "Bình thường"; chip.style.color = "#4dff91"; }
  else if (bmi < 30)   { pct = 63+((bmi-25)/5)*25; chip.textContent = "Thừa cân"; chip.style.color = "#e8ff47"; }
  else                 { pct = Math.min(100, 88+((bmi-30)/10)*12); chip.textContent = "Béo phì"; chip.style.color = "#ff6060"; }
  needle.style.left = `${pct}%`;
}

// ============================================================================
// CHỈNH SỬA HỒ SƠ & CẬP NHẬT NHẬT KÝ
// ============================================================================
async function saveProfile() {
  const name = document.getElementById("f_name").value.trim();
  const age  = parseInt(document.getElementById("f_age").value);
  const w    = parseFloat(document.getElementById("f_weight").value);
  const h    = parseFloat(document.getElementById("f_height").value);
  const gw   = parseFloat(document.getElementById("f_gw").value);
  if (!name || age < 10 || w < 20 || h < 80) return toast("Vui lòng điền thông tin hợp lệ", "err");

  const updateData = {
    fullName: name, age, weight: w, height: h, goalWeight: gw,
    gender:   document.getElementById("f_gender").value,
    level:    document.getElementById("f_level").value,
    goalType: document.getElementById("f_gtype").value,
  };
  try {
    const res = await fetch(`${API_SERVER}/api/profile/update/${userProfile._id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updateData),
    });
    if (res.ok) {
      localUser.fullName = name;
      localStorage.setItem("loggedInUser", JSON.stringify(localUser));
      fetchTcnOverview();
      closeEdit();
      toast("✅ Cập nhật hồ sơ thành công", "ok");
    }
  } catch (e) { toast("Lỗi hệ thống", "err"); }
}

async function saveLog() {
  const w    = parseFloat(document.getElementById("l_w").value);
  const note = document.getElementById("l_note").value;
  if (!w || w < 20 || w > 300) return toast("Cân nặng không hợp lý", "err");

  try {
    const res = await fetch(`${API_SERVER}/api/profile/log/${userProfile._id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ weight: w, note }),
    });
    if (res.ok) {
      fetchTcnOverview();
      fetchWeightChart();
      closeLog();
      toast("📊 Đã lưu nhật ký!", "ok");
    }
  } catch (e) { toast("Lỗi hệ thống", "err"); }
}

function openEdit() {
  document.getElementById("f_name").value   = userProfile.fullName || "";
  document.getElementById("f_age").value    = userProfile.age || "";
  document.getElementById("f_weight").value = userProfile.weight || "";
  document.getElementById("f_height").value = userProfile.height || "";
  document.getElementById("f_gw").value     = userProfile.goalWeight || "";
  document.getElementById("editOverlay").classList.add("open");
}
function closeEdit() { document.getElementById("editOverlay").classList.remove("open"); }
function openLog() {
  document.getElementById("logDateChip").textContent = `📅 Hôm nay`;
  document.getElementById("logOverlay").classList.add("open");
}
function closeLog() { document.getElementById("logOverlay").classList.remove("open"); }

function toast(msg, type = "inf") {
  const wrap = document.getElementById("toastWrap");
  if (!wrap) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => el.classList.add("show"), 10);
  setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 400); }, 3000);
}

// ============================================================================
// MODAL LỊCH SỬ
// ============================================================================
function openHistoryModal() {
  const tbody = document.getElementById("historyTableBody");
  if (!tbody) return;
  tbody.innerHTML = allWorkoutsHistory.length === 0
    ? '<div class="empty-row">Chưa có lịch sử tập luyện nào.</div>'
    : allWorkoutsHistory.map(log => `
      <div class="tr hist-grid">
        <div class="td" style="font-weight:600; color:var(--text-main);">${log.name}</div>
        <div class="td" style="color:var(--accent); font-size:12px;">🏋️ ${log.vol}</div>
        <div class="td" style="color:var(--text-muted); font-size:12px;">${log.date}</div>
      </div>`).join("");
  document.getElementById("historyModalOverlay").classList.add("open");
}
function closeHistoryModal() {
  const modal = document.getElementById("historyModalOverlay");
  if (modal) modal.classList.remove("open");
}

// ============================================================================
// BIỂU ĐỒ TẦN SUẤT
// ============================================================================
function drawFreqChart(data) {
  const cv = document.getElementById("freqChart");
  if (!cv) return;
  const ctx = cv.getContext("2d");
  if (fChartInstance) fChartInstance.destroy();
  fChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["7T trước","6T trước","5T trước","4T trước","3T trước","2T trước","Tuần trước","Tuần này"],
      datasets: [{ label: "Số buổi tập", data, backgroundColor: "#4da8ff", borderRadius: 4, barPercentage: 0.5 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 7, ticks: { stepSize: 1, color: "#888" }, grid: { color: "rgba(255,255,255,0.05)" } },
        x: { ticks: { color: "#888" }, grid: { display: false } },
      },
    },
  });
}

// ============================================================================
// MỨC TẠ
// ============================================================================
async function fetchWeightsData() {
  try {
    const res = await fetch(`${API_SERVER}/api/tcn/weights?userId=${CURRENT_UID}`).then(r => r.json());
    if (res.success) renderWeightsList(res.data);
  } catch (e) {}
}

function renderWeightsList(weightsData) {
  const list = document.getElementById("weightsList");
  if (!list) return;
  list.innerHTML = weightsData.map(w => `
    <div class="w-row">
      <div class="w-name">${w.muscle}</div>
      <div class="w-ctrl">
        <button class="w-btn" onclick="adjustWeight('${w.muscle}', -1, this)">-</button>
        <div class="w-val"><span>${w.weight}</span>kg</div>
        <button class="w-btn" onclick="adjustWeight('${w.muscle}', 1, this)">+</button>
      </div>
      <div class="w-cmt ${w.is_upgrade ? "upgrade" : ""}">${w.comment}</div>
    </div>`).join("");
}

let weightTimer;
function adjustWeight(muscle, amount, btnEl) {
  const valContainer = btnEl.parentElement.querySelector(".w-val span");
  let newWeight = Math.max(1, parseFloat(valContainer.textContent) + amount);
  valContainer.textContent = newWeight;
  clearTimeout(weightTimer);
  weightTimer = setTimeout(async () => {
    try {
      await fetch(`${API_SERVER}/api/tcn/weights/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: CURRENT_UID, muscle, weight: newWeight }),
      });
      toast(`Đã lưu mức tạ ${muscle}: ${newWeight}kg`, "ok");
    } catch (e) { toast("Lỗi lưu mức tạ", "err"); }
  }, 800);
}

// ============================================================================
// LỘ TRÌNH TRÊN TRANG CÁ NHÂN
// ============================================================================
async function loadProfileActivePlan() {
  const titleEl = document.getElementById("profile-plan-title");
  const listEl  = document.getElementById("profile-plan-list");
  if (!titleEl || !listEl) return;

  try {
    const serverUrl = typeof AI_SERVER_URL !== "undefined" ? AI_SERVER_URL : "http://localhost:5001";
    const res  = await fetch(`${serverUrl}/api/get-active-plan?userId=${USER_ID}`);
    const data = await res.json();

    if (data.plan && data.plan.plan_data) {
      const planData  = data.plan.plan_data;
      const daysDone  = data.plan.days_done || 0;
      const totalDays = planData.duration_days || planData.days.length;
      const pct       = Math.round((daysDone / totalDays) * 100) || 0;

      titleEl.textContent = planData.plan_name || `Lộ trình ${totalDays} ngày`;
      listEl.innerHTML = `
        <div style="margin-top:10px;">
          <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:8px;">
            <span>Tiến độ hoàn thành</span>
            <span><strong style="color:var(--accent,#e8ff47)">${daysDone}</strong> / ${totalDays} ngày</span>
          </div>
          <div style="width:100%; background:var(--border,#2a2a2a); height:8px; border-radius:4px; overflow:hidden;">
            <div style="width:${pct}%; background:var(--accent,#e8ff47); height:100%; border-radius:4px; transition:width 0.5s ease;"></div>
          </div>
        </div>`;
    } else {
      titleEl.textContent = "Chưa có lộ trình";
      listEl.innerHTML    = "Bạn chưa bắt đầu lộ trình nào.";
    }
  } catch (error) {
    titleEl.textContent = "Lỗi kết nối";
    listEl.innerHTML    = "Không thể lấy dữ liệu từ máy chủ.";
  }
}
loadProfileActivePlan();