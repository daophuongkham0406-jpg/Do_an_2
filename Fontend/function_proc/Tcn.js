// =========================================================
// 1. LẤY DỮ LIỆU TỪ DATABASE KHI VÀO TRANG
// =========================================================
let userProfile = {};
let userHistory = [];

document.addEventListener("DOMContentLoaded", async () => {
    const userStr = localStorage.getItem('loggedInUser');
    if (!userStr) return; // check_login.js sẽ tự đá khách ra ngoài

    const localUser = JSON.parse(userStr);
    
    try {
        // Gọi API lấy dữ liệu thật từ Database
        const response = await fetch(`http://127.0.0.1:5000/api/profile/get/${localUser.id}`);
        const data = await response.json();

        if (response.ok) {
            userProfile = data.profile;
            userHistory = data.history;
            
            // Nếu là người mới tinh chưa có lịch sử, tạo 1 mốc dựa trên cân nặng đăng ký
            if(userHistory.length === 0 && userProfile.weight) {
                userHistory.push({ date: new Date().toISOString().split('T')[0], weight: userProfile.weight });
            }

            renderProfile();
            // Tạm thời ẩn các biểu đồ liên quan đến lịch tập (sẽ làm ở phần sau)
            document.getElementById('routineCount').textContent = "0";
            document.getElementById('routineList').innerHTML = "<p style='color:#888;font-size:13px;'>Bạn chưa hoàn thành lộ trình nào.</p>";
            document.getElementById('wlogList').innerHTML = "<p style='color:#888;font-size:13px;'>Hãy bắt đầu buổi tập đầu tiên!</p>";
            
            // Vẽ biểu đồ cân nặng
            setTimeout(() => drawWeight('3m'), 100);
        }
    } catch (error) {
        toast("Lỗi kết nối đến máy chủ", "err");
    }
});

// =========================================================
// 2. LOGIC TÍNH TOÁN & HIỂN THỊ
// =========================================================
function calcBMI(w, h) {
    if (!w || !h) return 0;
    return +(w / ((h / 100) ** 2)).toFixed(1);
}

function renderProfile() {
    const p = userProfile;
    const BMI = calcBMI(p.weight, p.height);

    // Điền tên to
    document.getElementById('profileName').textContent = (p.fullName || "Người dùng").toUpperCase();
    document.getElementById('avatarEl').textContent = (p.fullName || "N").charAt(0).toUpperCase();
    
    // Điền thông số cơ bản
    document.getElementById('metaAge').textContent = p.age || "--";
    document.getElementById('metaWeight').textContent = p.weight || "--";
    document.getElementById('metaHeight').textContent = p.height || "--";
    document.getElementById('metaBMI').textContent = `BMI ${BMI}`;
    
    // Khung thống kê
    document.getElementById('sv-w').textContent = `${p.weight || 0} kg`;
    document.getElementById('sv-h').textContent = `${p.height || 0} cm`;
    document.getElementById('sv-bmi').textContent = BMI;

    // Phân loại BMI
    let bmiLabel = "Chưa rõ", bmiCls = "bmi-normal", pct = 50;
    if (BMI > 0 && BMI < 18.5) { bmiLabel = 'Thiếu cân'; bmiCls = 'bmi-under'; pct = (BMI / 30) * 100; }
    else if (BMI < 25) { bmiLabel = 'Bình thường'; bmiCls = 'bmi-normal'; pct = ((BMI - 15) / 20) * 100; }
    else if (BMI < 30) { bmiLabel = 'Thừa cân'; bmiCls = 'bmi-over'; pct = ((BMI - 15) / 20) * 100; }
    else if (BMI >= 30) { bmiLabel = 'Béo phì'; bmiCls = 'bmi-obese'; pct = 90; }
    
    const chip = document.getElementById('bmiCatChip');
    chip.textContent = bmiLabel;
    chip.className = `bmi-cat ${bmiCls}`;
    document.getElementById('bmiNeedle').style.left = `${Math.min(95, Math.max(3, pct))}%`;
}

// =========================================================
// 3. CHỈNH SỬA THÔNG TIN (KIỂM TRA LOGIC CON NGƯỜI)
// =========================================================
async function saveProfile() {
    const name = document.getElementById('f_name').value.trim();
    const age = parseInt(document.getElementById('f_age').value);
    const w = parseFloat(document.getElementById('f_weight').value);
    const h = parseFloat(document.getElementById('f_height').value);
    const gw = parseFloat(document.getElementById('f_gw').value);

    // Logic kiểm tra con người
    if (!name) return toast("Tên không được để trống", "err");
    if (age < 10 || age > 100) return toast("Tuổi không hợp lý (10-100)", "err");
    if (w < 20 || w > 300) return toast("Cân nặng không hợp lý (20-300kg)", "err");
    if (h < 80 || h > 250) return toast("Chiều cao không hợp lý (80-250cm)", "err");
    if (gw && (gw < 20 || gw > 300)) return toast("Mục tiêu cân nặng sai", "err");

    const updateData = {
        fullName: name, age: age, weight: w, height: h, goalWeight: gw,
        gender: document.getElementById('f_gender').value,
        level: document.getElementById('f_level').value,
        goalType: document.getElementById('f_gtype').value
    };

    try {
        const res = await fetch(`http://127.0.0.1:5000/api/profile/update/${userProfile._id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });

        if (res.ok) {
            // Cập nhật lại UI
            Object.assign(userProfile, updateData);
            
            // Cập nhật tên trên Header
            const localUser = JSON.parse(localStorage.getItem('loggedInUser'));
            localUser.fullName = name;
            localStorage.setItem('loggedInUser', JSON.stringify(localUser));
            document.getElementById('profile-link').innerHTML = `👋 Xin chào, ${name}`;

            renderProfile();
            closeEdit();
            toast("✅ Cập nhật hồ sơ thành công", "ok");
        }
    } catch (e) { toast("Lỗi hệ thống", "err"); }
}

// =========================================================
// 4. CẬP NHẬT CHỈ SỐ HÀNG NGÀY
// =========================================================
async function saveLog() {
    const w = parseFloat(document.getElementById('l_w').value);
    const fat = parseFloat(document.getElementById('l_f').value);
    const waist = parseFloat(document.getElementById('l_waist').value);
    const note = document.getElementById('l_note').value;

    if (!w) return toast('Vui lòng nhập cân nặng hôm nay', 'err');
    if (w < 20 || w > 300) return toast("Cân nặng nhập vào không hợp lý", "err");
    if (fat && (fat < 3 || fat > 60)) return toast("Tỷ lệ mỡ (3% - 60%)", "err");

    const logData = { weight: w, fat: fat, waist: waist, note: note };

    try {
        const res = await fetch(`http://127.0.0.1:5000/api/profile/log/${userProfile._id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(logData)
        });

        if (res.ok) {
            userProfile.weight = w;
            // Xóa log cũ của ngày hôm nay nếu có, thêm log mới
            const today = new Date().toISOString().split('T')[0];
            userHistory = userHistory.filter(h => h.date !== today);
            userHistory.push({ date: today, weight: w });
            
            renderProfile();
            drawWeight('3m'); // Vẽ lại biểu đồ
            closeLog();
            toast('📊 Đã lưu nhật ký!', 'ok');
        }
    } catch (e) { toast("Lỗi hệ thống", "err"); }
}

// =========================================================
// Các hàm tiện ích đóng mở Modal, Toast và vẽ biểu đồ giữ nguyên
// (Copy phần hàm openEdit, closeEdit, openLog, closeLog, toast, và drawWeight từ file cũ của bạn xuống đây)
// =========================================================

function openEdit() {
    document.getElementById('f_name').value = userProfile.fullName || "";
    document.getElementById('f_age').value = userProfile.age || "";
    document.getElementById('f_weight').value = userProfile.weight || "";
    document.getElementById('f_height').value = userProfile.height || "";
    document.getElementById('f_gw').value = userProfile.goalWeight || "";
    document.getElementById('editOverlay').classList.add('open');
}
function closeEdit() { document.getElementById('editOverlay').classList.remove('open'); }
function openLog() {
    document.getElementById('logDateChip').textContent = `📅 Hôm nay`;
    document.getElementById('logOverlay').classList.add('open');
}
function closeLog() { document.getElementById('logOverlay').classList.remove('open'); }
function toast(msg, type='inf'){
    const el=document.createElement('div');
    el.className=`toast ${type}`;el.textContent=msg;
    document.getElementById('toastWrap').appendChild(el);
    setTimeout(()=>{el.classList.add('show');}, 10);
    setTimeout(()=>{el.classList.remove('show');setTimeout(()=>el.remove(),400);},3000);
}

// Hàm vẽ biểu đồ Cân nặng đơn giản hóa
function drawWeight(period='3m'){
    const cv=document.getElementById('weightChart');
    if(!cv) return;
    const W=cv.offsetWidth||580, H=230;
    cv.width=W; cv.height=H;
    const ctx=cv.getContext('2d');
    ctx.clearRect(0,0,W,H);

    if(userHistory.length < 1) return; // Không có dữ liệu thì thôi
    
    // ... Dán ruột hàm drawWeight() cũ của bạn vào đây ...
}