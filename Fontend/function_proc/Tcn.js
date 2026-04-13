// ============================================================================
// KHAI BÁO BIẾN TOÀN CỤC
// ============================================================================
const API_SERVER = 'http://127.0.0.1:5000'; // Đổi chung về cổng 5000
let userProfile = {};
let userHistory = [];
let allWorkoutsHistory = []; // Lưu lại để dùng cho Modal

// Lấy ID người dùng từ LocalStorage
const userStr = localStorage.getItem('loggedInUser');
const localUser = userStr ? JSON.parse(userStr) : {};
const CURRENT_UID = localUser.id || localUser._id || "guest";

// ============================================================================
// KHỞI CHẠY KHI TẢI TRANG
// ============================================================================
document.addEventListener("DOMContentLoaded", async () => {
    if (!userStr || CURRENT_UID === "guest") {
        toast("❌ Lỗi: Không tìm thấy tài khoản! Vui lòng đăng nhập lại.", "err");
        return;
    }

    // 1. Tải thông tin cá nhân cũ (Dùng cho Modal Chỉnh sửa / Nhật ký)
    await fetchOldProfile();

    // 2. Tải Lộ trình đang tập
    fetchActivePlan(CURRENT_UID);

    // 3. Tải Dữ liệu phân tích mới (Tổng quan, Radar, Cân nặng)
    fetchTcnOverview();
    fetchRadarChart();
    fetchWeightChart();
    fetchWeightsData(); 
});

// Lấy Profile cho Modal Edit
async function fetchOldProfile() {
    try {
        const res = await fetch(`${API_SERVER}/api/profile/get/${CURRENT_UID}`);
        const data = await res.json();
        if (res.ok) {
            userProfile = data.profile || {};
            userHistory = data.history || [];
            
            // Nếu là người mới, tạo mốc lịch sử đầu tiên
            if(userHistory.length === 0 && userProfile.weight) {
                userHistory.push({ date: new Date().toISOString().split('T')[0], weight: userProfile.weight });
            }
        }
    } catch (e) { console.error("Lỗi lấy Profile:", e); }
}

// ============================================================================
// 1. QUẢN LÝ LỘ TRÌNH LUYỆN TẬP (AI PLAN)
// ============================================================================
async function fetchActivePlan(userId) {
    const wrap = document.getElementById('activePlanWrap');
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
    const wrap = document.getElementById('activePlanWrap');
    const cardTitle = wrap.parentElement.querySelector('.card-title');
    if(cardTitle) cardTitle.textContent = plan.plan_name || "Lộ trình AI";

    let daysHtml = '';
    const progress = plan.daily_progress || [];

    progress.forEach((dayData, index) => {
        const isDone = dayData.completed ? 'checked' : '';
        const textStyle = dayData.completed ? 'text-decoration: line-through; opacity: 0.5;' : '';
        const dayLabel = dayData.day_name || `Ngày ${index + 1}`;

        daysHtml += `
            <div style="display:flex; align-items:center; justify-content:space-between; padding: 12px 15px; border-bottom: 1px solid var(--border); background: var(--bg-input); border-radius: 8px; margin-bottom: 8px; transition: 0.3s;">
                <div style="display:flex; align-items:center; gap: 12px;">
                    <input type="checkbox" style="width: 18px; height: 18px; accent-color: #e8ff47; cursor:pointer;" 
                           ${isDone} 
                           onchange="updatePlanDay('${plan.id}', ${index}, this.checked)">
                    <div style="font-size: 14px; font-weight: 600; color: var(--text-main); ${textStyle}">${dayLabel}</div>
                </div>
                <button style="background:transparent; border:1px solid var(--border); color:var(--text-muted); padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor:pointer;" onmouseover="this.style.color='#e8ff47'; this.style.borderColor='#e8ff47'" onmouseout="this.style.color='var(--text-muted)'; this.style.borderColor='var(--border)'">Xem bài</button>
            </div>
        `;
    });
    wrap.innerHTML = daysHtml;
}

async function updatePlanDay(planId, dayIndex, isCompleted) {
    try {
        const response = await fetch(`${API_SERVER}/api/plans/update_progress/${planId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ day_index: dayIndex, is_completed: isCompleted })
        });

        if (response.ok) {
            toast(isCompleted ? "✅ Đã hoàn thành ngày tập!" : "⏳ Đã hủy hoàn thành", "ok");
            fetchActivePlan(CURRENT_UID); // Tải lại lộ trình
            fetchTcnOverview();           // Tải lại điểm thành tích
            fetchRadarChart();            // Tải lại biểu đồ
        } else {
            toast("❌ Lỗi khi lưu tiến độ!", "err");
        }
    } catch (error) { toast("🔌 Lỗi mạng!", "err"); }
}

// ============================================================================
// 2. KÉO DỮ LIỆU TỪ API THỐNG KÊ (OVERVIEW, RADAR, WEIGHT)
// ============================================================================
async function fetchTcnOverview() {
    try {
        const res = await fetch(`${API_SERVER}/api/tcn/overview?userId=${CURRENT_UID}`).then(r => r.json());
        if (res.success) {
            const d = res.data;
            document.getElementById("profileName").textContent = d.fullName.toUpperCase();
            document.getElementById("avatarEl").textContent = d.fullName.charAt(0).toUpperCase();
            
            document.getElementById("metaAge").textContent = d.age;
            document.getElementById("metaWeight").textContent = d.weight;
            document.getElementById("metaHeight").textContent = d.height;
            document.getElementById("metaBMI").textContent = `BMI ${d.bmi}`;
            
            document.getElementById("pWorkouts").textContent = d.workoutsCompleted;
            document.getElementById("pRoutines").textContent = d.routinesCompleted;
            document.getElementById("pWeightChange").textContent = d.weightChange;
            document.getElementById("metaWorkouts").textContent = d.workoutsCompleted;

            document.getElementById("sv-w").textContent = `${d.weight} kg`;
            document.getElementById("sv-h").textContent = `${d.height} cm`;
            document.getElementById("sv-bmi").textContent = d.bmi;
            
            // Render số lượng lộ trình xong
            document.getElementById('routineCount').textContent = d.routinesCompleted;
            if(d.routinesCompleted > 0) {
                document.getElementById('routineList').innerHTML = `<p style='color:var(--accent); font-size:14px; padding: 10px 0;'>🏆 Đã hoàn thành ${d.routinesCompleted} lộ trình!</p>`;
            } else {
                document.getElementById('routineList').innerHTML = `<p style='color:#888; font-size:13px; padding: 10px 0;'>Bạn chưa hoàn thành lộ trình nào.</p>`;
            }
            
            document.getElementById("sv-w").textContent = `${d.weight} kg`;
            document.getElementById("sv-h").textContent = `${d.height} cm`;
            document.getElementById("sv-bmi").textContent = d.bmi;
            
            // DÒNG MỚI THÊM: Đổ dữ liệu Tỷ lệ cơ ra ô giao diện
            const muscleEl = document.getElementById("sv-m");
            if(muscleEl) {
                muscleEl.textContent = d.musclePct > 0 ? `${d.musclePct}%` : "--";
            }

            renderRecentWorkouts(d.recentWorkouts);
            // Lưu lại tất cả buổi tập để mở Modal
            allWorkoutsHistory = d.allWorkouts;
            // Vẽ biểu đồ cột Tần suất
            drawFreqChart(d.freqData);
            updateBMIScale(d.bmi);
        }
    } catch (e) { console.error("Lỗi tải Overview:", e); }
}

async function fetchRadarChart() {
    try {
        const res = await fetch(`${API_SERVER}/api/tcn/radar?userId=${CURRENT_UID}`).then(r => r.json());
        if (res.success) drawRadarChart(res.data);
    } catch (e) { console.error("Lỗi vẽ Radar:", e); }
}

async function fetchWeightChart() {
    try {
        const res = await fetch(`${API_SERVER}/api/tcn/weight-chart?userId=${CURRENT_UID}`).then(r => r.json());
        if (res.success && res.data.labels.length > 0) {
            drawRealWeightChart(res.data.labels, res.data.weights, res.data.goal_weight);
        }
    } catch (e) { console.error("Lỗi tải biểu đồ cân nặng:", e); }
}

// ============================================================================
// 3. CÁC HÀM VẼ BIỂU ĐỒ & GIAO DIỆN
// ============================================================================
function renderRecentWorkouts(workoutsData) {
    const list = document.getElementById("wlogList");
    if (!list) return;
    if (!workoutsData || workoutsData.length === 0) {
        list.innerHTML = `<div style="padding:16px 0;color:var(--text-muted);font-size:13px;">Chưa có lịch sử tập luyện.</div>`;
        return;
    }
    let html = "";
    workoutsData.forEach(log => {
        html += `
            <div style="display:flex; justify-content:space-between; align-items:center; padding: 12px 0; border-bottom: 1px solid var(--border);">
                <div>
                    <div style="font-size:14px; font-weight:600; color:var(--text-main); margin-bottom:4px;">${log.name}</div>
                    <div style="font-size:11px; color:var(--text-muted);">🕒 ${log.time} · 🏋️ ${log.vol}</div>
                </div>
                <div style="font-size:12px; color:var(--accent); font-weight:500;">${log.date}</div>
            </div>`;
    });
    list.innerHTML = html;
}

let wChartInstance = null;
function drawRealWeightChart(labels, data, goalWeight) {
    const cv = document.getElementById("weightChart");
    if(!cv) return;
    const ctx = cv.getContext("2d");
    const goalData = Array(labels.length).fill(goalWeight);

    if (wChartInstance) wChartInstance.destroy();
    wChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Cân nặng (kg)', data: data, borderColor: '#e8ff47', backgroundColor: 'rgba(232, 255, 71, 0.1)', borderWidth: 2, pointBackgroundColor: '#161616', pointBorderColor: '#e8ff47', pointBorderWidth: 2, pointRadius: 4, fill: true, tension: 0.4 },
                { label: 'Mục tiêu', data: goalData, borderColor: 'rgba(77, 168, 255, 0.5)', borderWidth: 1.5, borderDash: [5, 5], pointRadius: 0, fill: false }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
            scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } }, x: { grid: { display: false }, ticks: { color: '#888', maxTicksLimit: 5 } } }
        }
    });
}

function drawRadarChart(muscleData) {
    const cv = document.getElementById("radarChart");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    const cx = W / 2, cy = H / 2, R = 80;
    ctx.clearRect(0, 0, W, H);

    const labels = ["Ngực", "Lưng", "Chân", "Vai", "Tay", "Bụng"];
    const sides = labels.length;

    // --- TỰ ĐỘNG CÂN CHỈNH TỶ LỆ (SCALE) ---
    // Mốc 10đ là thay đổi rõ rệt. Đặt giới hạn lưới gốc là 20 để 10đ nằm ở Vòng số 2.
    // Nếu người dùng cày quá kinh khủng (>20), biểu đồ sẽ tự nới rộng ra.
    const currentMax = Math.max(...muscleData);
    const MAX_SCORE = Math.max(20, currentMax); 

    // Lưới nền (Có 4 vòng. Vòng 1=5đ, Vòng 2=10đ (Rõ rệt), Vòng 3=15đ, Vòng 4=20đ)
    ctx.strokeStyle = "rgba(255,255,255,0.1)"; ctx.lineWidth = 1;
    for (let level = 1; level <= 4; level++) {
        ctx.beginPath();
        for (let i = 0; i < sides; i++) {
            const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
            const r = R * (level / 4);
            const x = cx + Math.cos(angle) * r, y = cy + Math.sin(angle) * r;
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.closePath(); ctx.stroke();
    }

    // Gắn Nhãn + Điểm số (Màu trắng mờ)
    ctx.fillStyle = "#aaa"; ctx.font = "bold 11px Inter"; ctx.textAlign = "center";
    for (let i = 0; i < sides; i++) {
        const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(angle) * R, cy + Math.sin(angle) * R); ctx.stroke();
        let offsetX = Math.cos(angle) * (R + 25), offsetY = Math.sin(angle) * (R + 20) + 4;
        
        let labelText = `${labels[i]} ${muscleData[i]}`;
        ctx.fillText(labelText, cx + offsetX, cy + offsetY);
    }

    // Vẽ Vùng dữ liệu vàng chanh
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
        const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
        const r = R * (muscleData[i] / MAX_SCORE); // Tính độ dài theo Max_Score
        const x = cx + Math.cos(angle) * r, y = cy + Math.sin(angle) * r;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = "rgba(232, 255, 71, 0.35)"; ctx.fill();
    ctx.strokeStyle = "#e8ff47"; ctx.lineWidth = 2; ctx.stroke();

    // Vẽ Chấm vàng ở đỉnh
    for (let i = 0; i < sides; i++) {
        const angle = ((Math.PI * 2) / sides) * i - Math.PI / 2;
        const r = R * (muscleData[i] / MAX_SCORE);
        const x = cx + Math.cos(angle) * r, y = cy + Math.sin(angle) * r;
        ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fillStyle = "#e8ff47"; ctx.fill();
    }
}
function updateBMIScale(bmi) {
    const needle = document.getElementById("bmiNeedle");
    const chip = document.getElementById("bmiCatChip");
    if(!needle || !chip) return;
    let pct = 0;
    if(bmi < 18.5) { pct = (bmi/18.5)*25; chip.textContent="Thiếu cân"; chip.style.color="#4da8ff"; }
    else if(bmi < 25) { pct = 25 + ((bmi-18.5)/6.5)*38; chip.textContent="Bình thường"; chip.style.color="#4dff91"; }
    else if(bmi < 30) { pct = 63 + ((bmi-25)/5)*25; chip.textContent="Thừa cân"; chip.style.color="#e8ff47"; }
    else { pct = 88 + ((bmi-30)/10)*12; pct = pct>100?100:pct; chip.textContent="Béo phì"; chip.style.color="#ff6060"; }
    needle.style.left = `${pct}%`;
}

// ============================================================================
// 4. CHỈNH SỬA HỒ SƠ & CẬP NHẬT NHẬT KÝ (GIỮ NGUYÊN CỦA BẠN)
// ============================================================================
async function saveProfile() {
    const name = document.getElementById('f_name').value.trim();
    const age = parseInt(document.getElementById('f_age').value);
    const w = parseFloat(document.getElementById('f_weight').value);
    const h = parseFloat(document.getElementById('f_height').value);
    const gw = parseFloat(document.getElementById('f_gw').value);

    if (!name || age < 10 || w < 20 || h < 80) return toast("Vui lòng điền thông tin hợp lệ", "err");

    const updateData = { fullName: name, age: age, weight: w, height: h, goalWeight: gw, gender: document.getElementById('f_gender').value, level: document.getElementById('f_level').value, goalType: document.getElementById('f_gtype').value };

    try {
        const res = await fetch(`${API_SERVER}/api/profile/update/${userProfile._id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updateData)
        });
        if (res.ok) {
            localUser.fullName = name; localStorage.setItem('loggedInUser', JSON.stringify(localUser));
            fetchTcnOverview(); closeEdit(); toast("✅ Cập nhật hồ sơ thành công", "ok");
        }
    } catch (e) { toast("Lỗi hệ thống", "err"); }
}

async function saveLog() {
    const w = parseFloat(document.getElementById('l_w').value);
    const fat = parseFloat(document.getElementById('l_f').value);
    const waist = parseFloat(document.getElementById('l_waist').value);
    const note = document.getElementById('l_note').value;

    if (!w || w < 20 || w > 300) return toast("Cân nặng không hợp lý", "err");
    const logData = { weight: w, fat: fat, waist: waist, note: note };

    try {
        const res = await fetch(`${API_SERVER}/api/profile/log/${userProfile._id}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(logData)
        });
        if (res.ok) {
            fetchTcnOverview(); fetchWeightChart(); closeLog(); toast('📊 Đã lưu nhật ký!', 'ok');
        }
    } catch (e) { toast("Lỗi hệ thống", "err"); }
}

function openEdit() {
    document.getElementById('f_name').value = userProfile.fullName || "";
    document.getElementById('f_age').value = userProfile.age || "";
    document.getElementById('f_weight').value = userProfile.weight || "";
    document.getElementById('f_height').value = userProfile.height || "";
    document.getElementById('f_gw').value = userProfile.goalWeight || "";
    document.getElementById('editOverlay').classList.add('open');
}
function closeEdit() { document.getElementById('editOverlay').classList.remove('open'); }
function openLog() { document.getElementById('logDateChip').textContent = `📅 Hôm nay`; document.getElementById('logOverlay').classList.add('open'); }
function closeLog() { document.getElementById('logOverlay').classList.remove('open'); }
function toast(msg, type='inf'){
    const el=document.createElement('div'); el.className=`toast ${type}`;el.textContent=msg;
    document.getElementById('toastWrap').appendChild(el);
    setTimeout(()=>{el.classList.add('show');}, 10);
    setTimeout(()=>{el.classList.remove('show');setTimeout(()=>el.remove(),400);},3000);
}
// =====================================
// XỬ LÝ MODAL "XEM TẤT CẢ LỊCH SỬ"
// =====================================
function openHistoryModal() {
    const tbody = document.getElementById('historyTableBody');
    if(allWorkoutsHistory.length === 0) {
        tbody.innerHTML = '<div class="empty-row">Chưa có lịch sử tập luyện nào.</div>';
    } else {
        tbody.innerHTML = allWorkoutsHistory.map(log => `
            <div class="tr hist-grid">
                <div class="td" style="font-weight:600; color:var(--text-main);">${log.name}</div>
                <div class="td" style="color:var(--accent); font-size:12px;">🏋️ ${log.vol}</div>
                <div class="td" style="color:var(--text-muted); font-size:12px;">${log.date}</div>
            </div>
        `).join('');
    }
    document.getElementById('historyModalOverlay').classList.add('open');
}

function closeHistoryModal() {
    document.getElementById('historyModalOverlay').classList.remove('open');
}

//=====================================
// cột tần suất luyện tập (buổi/tuần)
// =====================================
let fChartInstance = null;
function drawFreqChart(data) {
    const cv = document.getElementById("freqChart");
    if(!cv) return;
    const ctx = cv.getContext("2d");

    if (fChartInstance) fChartInstance.destroy();
    fChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['7 tuần trước', '6 tuần trước', '5 tuần trước', '4 tuần trước', '3 tuần trước', '2 tuần trước', '1 tuần trước', 'Tuần hiện tại'],
            datasets: [{
                label: 'Số buổi tập',
                data: data,
                backgroundColor: '#4da8ff',
                borderRadius: 4,
                barPercentage: 0.5
            }]
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, max: 7, ticks: { stepSize: 1, color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { ticks: { color: '#888' }, grid: { display: false } }
            }
        }
    });
}
// ============================================================================
// XỬ LÝ GIAO DIỆN "MỨC TẠ CỦA BẠN"
// ============================================================================
async function fetchWeightsData() {
    try {
        const res = await fetch(`${API_SERVER}/api/tcn/weights?userId=${CURRENT_UID}`).then(r => r.json());
        if (res.success) {
            renderWeightsList(res.data);
        }
    } catch (e) {
        console.error("Lỗi tải mức tạ:", e);
    }
}

function renderWeightsList(weightsData) {
    const list = document.getElementById('weightsList');
    if (!list) return;

    list.innerHTML = weightsData.map(w => `
        <div class="w-row">
            <div class="w-name">${w.muscle}</div>
            <div class="w-ctrl">
                <button class="w-btn" onclick="adjustWeight('${w.muscle}', -1, this)">-</button>
                <div class="w-val"><span>${w.weight}</span>kg</div>
                <button class="w-btn" onclick="adjustWeight('${w.muscle}', 1, this)">+</button>
            </div>
            <div class="w-cmt ${w.is_upgrade ? 'upgrade' : ''}">${w.comment}</div>
        </div>
    `).join('');
}

// Hàm tăng giảm tạ cục bộ và gọi API lưu ngầm
let weightTimer;
function adjustWeight(muscle, amount, btnEl) {
    // 1. Cập nhật số trên giao diện ngay lập tức
    const valContainer = btnEl.parentElement.querySelector('.w-val span');
    let currentWeight = parseFloat(valContainer.textContent);
    let newWeight = Math.max(1, currentWeight + amount); // Không cho giảm dưới 1kg
    valContainer.textContent = newWeight;

    // 2. Chờ người dùng bấm xong (Debounce 800ms) rồi mới gọi API lưu vào Database
    clearTimeout(weightTimer);
    weightTimer = setTimeout(async () => {
        try {
            await fetch(`${API_SERVER}/api/tcn/weights/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: CURRENT_UID, muscle: muscle, weight: newWeight })
            });
            toast(`Đã lưu mức tạ ${muscle}: ${newWeight}kg`, 'ok');
        } catch (e) {
            toast('Lỗi lưu mức tạ', 'err');
        }
    }, 800);
}