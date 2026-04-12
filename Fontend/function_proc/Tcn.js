// ════════════════════════════════════════════════════════════════
// Đây là File Tcn.js
// ════════════════════════════════════════════════════════════════
let userProfile = {};
let userHistory = [];

document.addEventListener("DOMContentLoaded", async () => {
    const userStr = localStorage.getItem('loggedInUser');
    if (!userStr) return; 

    const localUser = JSON.parse(userStr);
    
    // Cực kỳ quan trọng: Bắt lỗi ID khác nhau giữa các phiên bản
    const userId = localUser.id || localUser._id; 
    
    if (!userId) {
        toast("❌ Lỗi: Không tìm thấy ID tài khoản!", "err");
        return;
    }

    // GỌI API LẤY LỘ TRÌNH ĐANG THỰC HIỆN CỦA USER
    fetchActivePlan(userId);

    // GỌI API LẤY THÔNG TIN CÁ NHÂN VÀ LỊCH SỬ
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/profile/get/${userId}`);
        const data = await response.json();

        if (response.ok) {
            userProfile = data.profile;
            userHistory = data.history;
            
            // Nếu là người mới, tạo mốc lịch sử đầu tiên
            if(userHistory.length === 0 && userProfile.weight) {
                userHistory.push({ date: new Date().toISOString().split('T')[0], weight: userProfile.weight });
            }

            renderProfile();
            
            // Xóa dữ liệu ảo của Lịch tập (Vì chưa có API bài tập)
            document.getElementById('metaWorkouts').textContent = "0";
            document.getElementById('pWorkouts').textContent = "0";
            document.getElementById('pStreak').textContent = "0";
            document.getElementById('pRoutines').textContent = "0";

            document.getElementById('routineCount').textContent = "0";
            document.getElementById('routineList').innerHTML = "<p style='color:#888; font-size:13px; padding: 10px 0;'>Bạn chưa hoàn thành lộ trình nào.</p>";
            document.getElementById('wlogList').innerHTML = "<p style='color:#888; font-size:13px; padding: 10px 0;'>Hãy bắt đầu buổi tập đầu tiên!</p>";
            
            setTimeout(() => drawWeight('3m'), 100);
        } else {
            toast("❌ Lỗi từ server: " + data.message, "err");
        }
    } catch (error) {
        console.error("Lỗi kết nối:", error);
        toast("🔌 Mất kết nối! Hãy kiểm tra xem file app.py đã chạy chưa.", "err");
        document.getElementById('profileName').textContent = "LỖI KẾT NỐI SERVER";
    }
});

// ============================================================================
// 1. QUẢN LÝ LỘ TRÌNH LUYỆN TẬP (AI PLAN) - MỚI THÊM
// ============================================================================

// Hàm gọi API lấy Plan đang active
async function fetchActivePlan(userId) {
    const wrap = document.getElementById('activePlanWrap');
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/plans/active/${userId}`);
        
        if (!response.ok) {
            wrap.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:13px;background:var(--bg3);border-radius:12px;">Bạn chưa có lộ trình nào.<br>Hãy sang trang Lộ Trình để tạo ngay!</div>`;
            return;
        }

        const plan = await response.json();
        renderPlanUI(plan);

    } catch (error) {
        console.error("Lỗi tải lộ trình:", error);
        wrap.innerHTML = `<div style="padding:20px;text-align:center;color:#ff4d4d;font-size:13px;">Lỗi kết nối máy chủ khi tải lộ trình.</div>`;
    }
}

// Vẽ giao diện Check-list ngày tập
function renderPlanUI(plan) {
    const wrap = document.getElementById('activePlanWrap');
    
    // Đổi tên lộ trình trên tiêu đề Card HTML (Tìm ngược lên thẻ cha)
    const cardTitle = wrap.parentElement.querySelector('.card-title');
    if(cardTitle) cardTitle.textContent = plan.plan_name || "Lộ trình AI";

    // Tạo danh sách các ngày tập
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
                <button style="background:transparent; border:1px solid var(--border); color:var(--text-muted); padding: 4px 10px; border-radius: 4px; font-size: 11px; cursor:pointer; transition: 0.2s;" onmouseover="this.style.color='#e8ff47'; this.style.borderColor='#e8ff47'" onmouseout="this.style.color='var(--text-muted)'; this.style.borderColor='var(--border)'">Xem bài</button>
            </div>
        `;
    });

    wrap.innerHTML = daysHtml;
}

// Cập nhật lên CSDL khi người dùng Tick/Bỏ Tick
async function updatePlanDay(planId, dayIndex, isCompleted) {
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/plans/update_progress/${planId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ day_index: dayIndex, is_completed: isCompleted })
        });

        if (response.ok) {
            toast(isCompleted ? "✅ Đã hoàn thành ngày tập!" : "⏳ Đã hủy hoàn thành", "ok");
            // Render lại để giao diện áp dụng dòng kẻ ngang (line-through)
            const userStr = localStorage.getItem('loggedInUser');
            if (userStr) {
                const localUser = JSON.parse(userStr);
                fetchActivePlan(localUser.id || localUser._id);
            }
        } else {
            toast("❌ Lỗi khi lưu tiến độ!", "err");
        }
    } catch (error) {
        console.error("Lỗi cập nhật tiến độ:", error);
        toast("🔌 Lỗi mạng khi cập nhật tiến độ!", "err");
    }
}

// ============================================================================
// 2. CÁC HÀM XỬ LÝ HỒ SƠ & BIỂU ĐỒ (CŨ GIỮ NGUYÊN)
// ============================================================================

function calcBMI(w, h) {
    if (!w || !h) return 0;
    return +(w / ((h / 100) ** 2)).toFixed(1);
}

function renderProfile() {
    const p = userProfile;
    const BMI = calcBMI(p.weight, p.height);

    document.getElementById('profileName').textContent = (p.fullName || "Khách").toUpperCase();
    document.getElementById('avatarEl').textContent = (p.fullName || "K").charAt(0).toUpperCase();
    
    // Trình độ
    let levelName = "Chưa rõ";
    if(p.level === 'B') levelName = "Người mới";
    if(p.level === 'I') levelName = "Trung bình";
    if(p.level === 'A') levelName = "Nâng cao";
    document.getElementById('levelLbl').textContent = levelName;

    // Chỉ số
    document.getElementById('metaAge').textContent = p.age || "--";
    document.getElementById('metaWeight').textContent = p.weight || "--";
    document.getElementById('metaHeight').textContent = p.height || "--";
    document.getElementById('metaBMI').textContent = `BMI ${BMI}`;
    
    document.getElementById('sv-w').textContent = `${p.weight || 0} kg`;
    document.getElementById('sv-h').textContent = `${p.height || 0} cm`;
    document.getElementById('sv-bmi').textContent = BMI;

    let bmiLabel = "Chưa rõ", bmiCls = "bmi-normal", pct = 50;
    if (BMI > 0 && BMI < 18.5) { bmiLabel = 'Thiếu cân'; bmiCls = 'bmi-under'; pct = (BMI / 30) * 100; }
    else if (BMI >= 18.5 && BMI < 25) { bmiLabel = 'Bình thường'; bmiCls = 'bmi-normal'; pct = ((BMI - 15) / 20) * 100; }
    else if (BMI >= 25 && BMI < 30) { bmiLabel = 'Thừa cân'; bmiCls = 'bmi-over'; pct = ((BMI - 15) / 20) * 100; }
    else if (BMI >= 30) { bmiLabel = 'Béo phì'; bmiCls = 'bmi-obese'; pct = 90; }
    
    const chip = document.getElementById('bmiCatChip');
    chip.textContent = bmiLabel;
    chip.className = `bmi-cat ${bmiCls}`;
    document.getElementById('bmiNeedle').style.left = `${Math.min(95, Math.max(3, pct))}%`;
}

async function saveProfile() {
    const name = document.getElementById('f_name').value.trim();
    const age = parseInt(document.getElementById('f_age').value);
    const w = parseFloat(document.getElementById('f_weight').value);
    const h = parseFloat(document.getElementById('f_height').value);
    const gw = parseFloat(document.getElementById('f_gw').value);

    if (!name) return toast("Tên không được để trống", "err");
    if (age < 10 || age > 100) return toast("Tuổi không hợp lý (10-100)", "err");
    if (w < 20 || w > 300) return toast("Cân nặng không hợp lý (20-300kg)", "err");
    if (h < 80 || h > 250) return toast("Chiều cao không hợp lý (80-250cm)", "err");

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
            Object.assign(userProfile, updateData);
            
            // Cập nhật lại tên trên thanh Navbar
            const localUser = JSON.parse(localStorage.getItem('loggedInUser'));
            localUser.fullName = name;
            localStorage.setItem('loggedInUser', JSON.stringify(localUser));
            const profileLink = document.getElementById('profile-link');
            if(profileLink) profileLink.innerHTML = `<span style="color:#e6ff00">${name}</span>`;

            renderProfile();
            closeEdit();
            toast("✅ Cập nhật hồ sơ thành công", "ok");
        }
    } catch (e) { toast("Lỗi hệ thống", "err"); }
}

async function saveLog() {
    const w = parseFloat(document.getElementById('l_w').value);
    const fat = parseFloat(document.getElementById('l_f').value);
    const waist = parseFloat(document.getElementById('l_waist').value);
    const note = document.getElementById('l_note').value;

    if (!w) return toast('Vui lòng nhập cân nặng', 'err');
    if (w < 20 || w > 300) return toast("Cân nặng không hợp lý", "err");

    const logData = { weight: w, fat: fat, waist: waist, note: note };

    try {
        const res = await fetch(`http://127.0.0.1:5000/api/profile/log/${userProfile._id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(logData)
        });

        if (res.ok) {
            userProfile.weight = w;
            const today = new Date().toISOString().split('T')[0];
            userHistory = userHistory.filter(h => h.date !== today);
            userHistory.push({ date: today, weight: w });
            
            renderProfile();
            drawWeight('3m'); 
            closeLog();
            toast('📊 Đã lưu nhật ký!', 'ok');
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

function drawWeight(period='3m'){
    const cv=document.getElementById('weightChart');
    if(!cv) return;
    const W=cv.offsetWidth||580, H=230;
    cv.width=W; cv.height=H;
    const ctx=cv.getContext('2d');
    ctx.clearRect(0,0,W,H);

    if(userHistory.length < 1) return;

    let data=[...userHistory];
    const PAD={t:24,r:24,b:40,l:52};
    const cW=W-PAD.l-PAD.r,cH=H-PAD.t-PAD.b;
    const vals=data.map(d=>d.weight);
    const gw=userProfile.goalWeight;
    const minV=Math.min(...vals,gw||999)-1.5;
    const maxV=Math.max(...vals)+1.5;
    const rng=maxV-minV || 10;
    const xOf=i=> data.length > 1 ? PAD.l+(i/(data.length-1))*cW : PAD.l + cW/2;
    const yOf=v=>PAD.t+cH-((v-minV)/rng)*cH;

    for(let i=0;i<=5;i++){
        const y=PAD.t+(cH/5)*i;
        ctx.strokeStyle='rgba(255,255,255,.04)';ctx.lineWidth=1;
        ctx.beginPath();ctx.moveTo(PAD.l,y);ctx.lineTo(PAD.l+cW,y);ctx.stroke();
    }

    if(gw&&gw>=minV&&gw<=maxV){
        const gy=yOf(gw);
        ctx.strokeStyle='rgba(232,255,71,.28)';ctx.lineWidth=1.5;ctx.setLineDash([7,5]);
        ctx.beginPath();ctx.moveTo(PAD.l,gy);ctx.lineTo(PAD.l+cW,gy);ctx.stroke();
        ctx.setLineDash([]);
    }

    ctx.strokeStyle='#e8ff47';ctx.lineWidth=2.5;ctx.lineJoin='round';
    ctx.beginPath();
    data.forEach((d,i)=>{
        const x=xOf(i), y=yOf(d.weight);
        if(i===0){ctx.moveTo(x,y);return;}
        const px=xOf(i-1), py=yOf(data[i-1].weight), mx=(px+x)/2;
        ctx.bezierCurveTo(mx,py,mx,y,x,y);
    });
    ctx.stroke();

    data.forEach((d,i)=>{
        const x=xOf(i), y=yOf(d.weight);
        ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fillStyle='#e8ff47';ctx.fill();
        ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fillStyle='#1a1a1f';ctx.fill();
        
        ctx.fillStyle='#e8ff47';ctx.font='bold 11px Barlow,sans-serif';ctx.textAlign='center';
        ctx.fillText(`${d.weight}`,x,y-11);
    });
}