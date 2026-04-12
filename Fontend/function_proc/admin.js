// ════════════════════════════════════════════════════════════════
// 1. CẤU HÌNH API & BIẾN TOÀN CỤC
// ════════════════════════════════════════════════════════════════
const API_URL = 'http://127.0.0.1:5000/api/exercises/';
const USER_API_URL = 'http://127.0.0.1:5000/api/users/';
const API_TIPS = 'http://127.0.0.1:5000/api/tips';
const API_WORKOUTS = 'http://127.0.0.1:5000/api/sample-workouts';
const API_FEATURED = 'http://127.0.0.1:5000/api/featured';
const API_MUSCLES = 'http://127.0.0.1:5000/api/muscles-info';
const API_FAQ = 'http://127.0.0.1:5000/api/faq';
const API_ABOUT = 'http://127.0.0.1:5000/api/about-features';
const API_CONTACTS = 'http://127.0.0.1:5000/api/contacts';

let exercises = [];
let usersList = []; 
let editingId = null;
let deleteId = null;
let deleteType = null; 

function getHeaders() {
    return { 'Content-Type': 'application/json' };
}

// ════════════════════════════════════════════════════════════════
// 2. HÀM XỬ LÝ LỖI CHUNG
// ════════════════════════════════════════════════════════════════
async function checkResponse(response) {
    if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        if (response.status === 404) throw new Error("404: Sai duong dan API. Kiem tra lai app.py!");
        else if (response.status === 500) throw new Error("500: Server Python bi loi code (Crash)!");
        else throw new Error(errData.message || `Loi khong xac dinh: ${response.status}`);
    }
    return response.json();
}

function showErrorToast(error, actionName) {
    console.error(`[Loi ${actionName}]:`, error);
    if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
        showToast("Máy chủ đang tắt! Hãy chạy 'python app.py'", 'error');
    } else {
        showToast(error.message, 'error');
    }
}

// ════════════════════════════════════════════════════════════════
// 3. API BÀI TẬP (EXERCISES)
// ════════════════════════════════════════════════════════════════
async function apiGet() {
    try {
        const r = await fetch(API_URL, { headers: getHeaders() });
        return await checkResponse(r);
    } catch (e) {
        showErrorToast(e, 'Tai danh sach bai tap');
        return [];
    }
}

async function apiPost(data) {
    try {
        const r = await fetch(API_URL, { method: 'POST', headers: getHeaders(), body: JSON.stringify(data) });
        return await checkResponse(r);
    } catch (e) {
        showErrorToast(e, 'Them bai tap');
        throw e;
    }
}

async function apiPut(id, data) {
    try {
        const r = await fetch(`${API_URL}${id}`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify(data) });
        return await checkResponse(r);
    } catch (e) {
        showErrorToast(e, 'Sua bai tap');
        throw e;
    }
}

async function apiDelete(id) {
    try {
        const r = await fetch(`${API_URL}${id}`, { method: 'DELETE', headers: getHeaders() });
        if (!r.ok) await checkResponse(r);
        return true;
    } catch (e) {
        showErrorToast(e, 'Xoa bai tap');
        throw e;
    }
}

// ════════════════════════════════════════════════════════════════
// 4. API NGƯỜI DÙNG (USERS)
// ════════════════════════════════════════════════════════════════
async function fetchUsers() {
    try {
        const r = await fetch(USER_API_URL, { headers: getHeaders() });
        usersList = await checkResponse(r);
        document.getElementById('userCountBadge').textContent = usersList.length;
        renderUserTable();
    } catch (e) {
        showErrorToast(e, 'Tai danh sach Nguoi dung');
        document.getElementById('userTableBody').innerHTML = '<div class="empty-row" style="color: var(--red);">❌ Loi tai du lieu. Hay kiem tra Backend!</div>';
    }
}

// ════════════════════════════════════════════════════════════════
// 5. KHỞI TẠO & ĐIỀU HƯỚNG MÀN HÌNH
// ════════════════════════════════════════════════════════════════
async function init() {
    const userStr = localStorage.getItem('loggedInUser');
    if (!userStr) {
        window.location.href = 'dangnhap.html';
        return;
    }
    const user = JSON.parse(userStr);
    
    // Đã sửa thành showToast thay vì alert
    if (user.role !== 'admin') {
        showToast('⛔ Bạn không có quyền truy cập trang Quản trị!', 'error');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1500);
        return;
    }

    const adminNameEl = document.getElementById('adminName');
    if (adminNameEl) adminNameEl.textContent = `${user.fullName}`;

    exercises = await apiGet();

    document.getElementById('statusDot').className = 'status-dot connected';
    document.getElementById('statusText').textContent = 'Da ket noi MongoDB';

    renderStats();
    renderTable();
}

// ════════════════════════════════════════════════════════════════
// ĐÃ SỬA: HÀM ĐIỀU HƯỚNG MÀN HÌNH (HỖ TRỢ THÊM TAB TIPS)
// ════════════════════════════════════════════════════════════════
function switchSection(sectionId) {
    // 1. Gỡ bỏ trạng thái sáng (active) của tất cả các menu bên trái
    document.querySelectorAll('.sidebar .s-item').forEach(el => el.classList.remove('active'));
    
    // 2. Làm sáng cái menu vừa được click
    const navItem = document.getElementById('nav-' + sectionId);
    if(navItem) navItem.classList.add('active');

    // 3. Ẩn TẤT CẢ các vùng nội dung bên phải
    document.getElementById('section-exercises').style.display = 'none';
    document.getElementById('section-users').style.display = 'none';
    
    const sectionTips = document.getElementById('section-tips');
    if (sectionTips) sectionTips.style.display = 'none'; // Ẩn tab tips

    const sectionWorkouts = document.getElementById('section-workouts');
    if (sectionWorkouts) sectionWorkouts.style.display = 'none';

    const sectionFeatured = document.getElementById('section-featured');
    if (sectionFeatured) sectionFeatured.style.display = 'none';

    const sectionMuscles = document.getElementById('section-muscles');
    if (sectionMuscles) sectionMuscles.style.display = 'none';

    const sectionFaq = document.getElementById('section-faq');
    if (sectionFaq) sectionFaq.style.display = 'none';

    const sectionAbout = document.getElementById('section-about');
    if (sectionAbout) sectionAbout.style.display = 'none';

    const sectionContacts = document.getElementById('section-contacts');
    if (sectionContacts) sectionContacts.style.display = 'none';

    // 4. Kích hoạt (Hiện) vùng nội dung tương ứng với menu vừa bấm
    const activeSection = document.getElementById('section-' + sectionId);
    if (activeSection) activeSection.style.display = 'block';

    // 5. Tự động tải dữ liệu nếu cần thiết
    if (sectionId === 'users' && usersList.length === 0) {
        fetchUsers();
    } else if (sectionId === 'tips') {
        loadAdminTips(); // Tự động gọi API lấy danh sách mẹo khi chuyển sang tab này
    } else if (sectionId === 'workouts') {
        loadAdminWorkouts(); // Tự động gọi API lấy danh sách bài tập mẫu khi chuyển sang tab này
    } else if (sectionId === 'featured') {
        loadAdminFeatured();
    } else if (sectionId === 'muscles') {
        loadAdminMuscles();
    } else if (sectionId === 'faq') {
        loadAdminFaq();
    } else if (sectionId === 'about') {
        loadAdminAbout();
    }else if (sectionId === 'contacts') {
        loadAdminContacts();
    }
}

// ════════════════════════════════════════════════════════════════
// 6. RENDER GIAO DIỆN (BÀI TẬP & USER)
// ════════════════════════════════════════════════════════════════
function renderStats() {
    const t = exercises.length;
    document.getElementById('statTotal').textContent = t;
    document.getElementById('statBeginner').textContent = exercises.filter(e => e.diff === 'B').length;
    document.getElementById('statInter').textContent = exercises.filter(e => e.diff === 'I').length;
    document.getElementById('statAdv').textContent = exercises.filter(e => e.diff === 'A').length;
    document.getElementById('exCountBadge').textContent = t;
}

const diffLabel = { B: 'Nguoi moi', I: 'Trung binh', A: 'Nang cao' };

function renderTable() {
    const q = document.getElementById('adminSearch').value.toLowerCase();
    const m = document.getElementById('filterMuscle').value;
    const d = document.getElementById('filterDiff').value;

    let data = [...exercises];
    if (q) data = data.filter(e => e.name.toLowerCase().includes(q));
    if (m) data = data.filter(e => e.muscle === m);
    if (d) data = data.filter(e => e.diff === d);

    const tbody = document.getElementById('tableBody');
    if (!data.length) { tbody.innerHTML = '<div class="empty-row">Khong tim thay bai tap nao.</div>'; return; }

    tbody.innerHTML = data.map(e => `
        <div class="tr" style="cursor:pointer;" onclick="openEdit('${e.id}')">
            <div class="td icon-cell">${e.icon || '❓'}</div>
            <div class="td id-cell">${String(e.id).slice(-6)}</div>
            <div class="td name">${e.name}</div>
            <div class="td equip">${e.muscle}</div>
            <div class="td equip">${e.equip}</div>
            <div class="td"><span class="badge badge-${e.diff}">${diffLabel[e.diff] || e.diff}</span></div>
            <div class="td actions" onclick="event.stopPropagation()">
                <button class="icon-btn edit" onclick="openEdit('${e.id}')" title="Sua">✏️</button>
                <button class="icon-btn del" onclick="askDelete('${e.id}')" title="Xoa">🗑️</button>
            </div>
        </div>
    `).join('');
}

function renderUserTable() {
    const q = document.getElementById('userSearch').value.toLowerCase();
    const r = document.getElementById('filterRole').value;

    let data = [...usersList];

    if (q) {
        data = data.filter(u =>
            (u.fullName && u.fullName.toLowerCase().includes(q)) ||
            (u.email && u.email.toLowerCase().includes(q)) ||
            (u.username && u.username.toLowerCase().includes(q))
        );
    }
    if (r) data = data.filter(u => u.role === r);

    const tbody = document.getElementById('userTableBody');
    if (!data.length) {
        tbody.innerHTML = '<div class="empty-row">Khong tim thay nguoi dung nao.</div>';
        return;
    }

    tbody.innerHTML = data.map(u => `
        <div class="tr user-grid" style="cursor:pointer;" onclick="openUserModal('${u.id}')">
            <div class="td id-cell" title="${u.id}">${String(u.id).slice(-6)}</div>
            <div class="td name">${u.fullName || 'Chua cap nhat'}</div>
            <div class="td" style="color:var(--text2)">${u.email || ''}</div>
            <div class="td" style="color:var(--text3)">@${u.username}</div>
            <div class="td"><span class="badge ${u.role === 'admin' ? 'badge-admin' : 'badge-user'}">${u.role.toUpperCase()}</span></div>
            <div class="td actions" onclick="event.stopPropagation()">
                ${u.role !== 'admin' ? `<button class="icon-btn del" onclick="askDeleteUser('${u.id}')" title="Xoa User">🗑️</button>` : ''}
            </div>
        </div>
    `).join('');
}

// ════════════════════════════════════════════════════════════════
// 7. XỬ LÝ FORM THÊM/SỬA BÀI TẬP
// ════════════════════════════════════════════════════════════════
function openAdd() {
    editingId = null;
    document.getElementById('formTitle').textContent = 'THEM BAI TAP MOI';
    clearForm();
    addStep(); addStep();
    addTip();
    document.getElementById('formOverlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function openEdit(id) {
    const ex = exercises.find(e => e.id === id);
    if (!ex) return;
    editingId = id;
    document.getElementById('formTitle').textContent = 'SUA BAI TAP';
    clearForm();
    document.getElementById('f_name').value = ex.name || '';
    document.getElementById('f_muscle').value = ex.muscle || '';
    document.getElementById('f_icon').value = ex.icon || '';
    document.getElementById('f_diff').value = ex.diff || '';
    document.getElementById('f_equip').value = ex.equip || '';
    document.getElementById('f_sets').value = ex.sets || '';
    document.getElementById('f_reps').value = ex.reps || '';
    document.getElementById('f_rest').value = ex.rest || '';
    (ex.sec || []).forEach(s => addSec(s));
    (ex.steps || []).forEach(s => addStep(s.t, s.d));
    (ex.tips || []).forEach(t => addTip(t));
    document.getElementById('formOverlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function clearForm() {
    ['f_name', 'f_muscle', 'f_icon', 'f_diff', 'f_equip', 'f_sets', 'f_reps', 'f_rest'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    ['secList', 'stepList', 'tipList'].forEach(id => document.getElementById(id).innerHTML = '');
}

function closeForm() {
    document.getElementById('formOverlay').classList.remove('open');
    document.body.style.overflow = '';
}

function addSec(val = '') {
    const div = document.createElement('div');
    div.className = 'dynamic-item';
    div.innerHTML = `<input type="text" placeholder="VD: Vai truoc" value="${val}"><button class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('secList').appendChild(div);
}

let stepCount = 0;
function addStep(t = '', d = '') {
    stepCount++;
    const n = document.getElementById('stepList').children.length + 1;
    const div = document.createElement('div');
    div.className = 'dynamic-item';
    div.style.cssText = 'display:grid;grid-template-columns:28px 1fr 1.5fr auto;gap:8px;align-items:start;';
    div.innerHTML = `
        <span style="font-family:'Bebas Neue';font-size:26px;color:var(--border2);line-height:1.4;">${String(n).padStart(2, '0')}</span>
        <input type="text" placeholder="Tieu de buoc…" value="${escHtml(t)}">
        <textarea placeholder="Mo ta chi tiet buoc…" rows="2">${escHtml(d)}</textarea>
        <button class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('stepList').appendChild(div);
}

function addTip(val = '') {
    const div = document.createElement('div');
    div.className = 'dynamic-item';
    div.innerHTML = `<input type="text" placeholder="Lu y..." value="${escHtml(val)}"><button class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('tipList').appendChild(div);
}

function escHtml(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

async function submitForm() {
    try {
        const name = document.getElementById('f_name').value.trim();
        const muscle = document.getElementById('f_muscle').value;
        const icon = document.getElementById('f_icon').value.trim();
        const diff = document.getElementById('f_diff').value;
        const equip = document.getElementById('f_equip').value;

        if (!name || !muscle || !icon || !diff || !equip) {
            // Đã đổi sang showToast
            showToast('Vui lòng điền đầy đủ các trường bắt buộc (*)', 'error');
            return;
        }

        const sec = [...document.querySelectorAll('#secList .dynamic-item input')].map(i => i.value.trim()).filter(Boolean);
        const steps = [...document.querySelectorAll('#stepList .dynamic-item')].map(row => {
            const inputs = row.querySelectorAll('input,textarea');
            return { t: (inputs[0] || {}).value || '', d: (inputs[1] || {}).value || '' };
        }).filter(s => s.t || s.d);
        const tips = [...document.querySelectorAll('#tipList .dynamic-item input')].map(i => i.value.trim()).filter(Boolean);

        const payload = {
            name, muscle, icon, diff, equip,
            sets: document.getElementById('f_sets') ? document.getElementById('f_sets').value.trim() : '',
            reps: document.getElementById('f_reps') ? document.getElementById('f_reps').value.trim() : '',
            rest: document.getElementById('f_rest') ? document.getElementById('f_rest').value.trim() : '',
            sec, steps, tips
        };

        if (editingId) {
            const updated = await apiPut(editingId, payload);
            exercises = exercises.map(e => e.id === editingId ? { ...e, ...updated } : e);
            showToast('Cập nhật bài tập thành công', 'success');
        } else {
            const created = await apiPost(payload);
            exercises.push(created);
            showToast('Thêm bài tập mới thành công', 'success');
        }

        closeForm();
        renderStats();
        renderTable();

    } catch (error) {
        console.error("Loi:", error);
        showToast("Đã xảy ra lỗi khi lưu! Vui lòng xem Console (F12).", "error");
    }
}

// ════════════════════════════════════════════════════════════════
// 8. XỬ LÝ XÓA CHUNG (BÀI TẬP VÀ NGƯỜI DÙNG)
// ════════════════════════════════════════════════════════════════
function askDelete(id) {
    deleteType = 'exercise';
    deleteId = id;
    const ex = exercises.find(e => e.id === id);
    document.getElementById('confirmName').textContent = ex ? `Bai tap: "${ex.name}"` : 'bai tap nay';
    document.getElementById('confirmOverlay').classList.add('open');
}

function askDeleteUser(id) {
    deleteType = 'user';
    deleteId = id;
    const u = usersList.find(e => e.id === id);
    document.getElementById('confirmName').textContent = u ? `User: "${u.fullName}"` : 'nguoi dung nay';
    document.getElementById('confirmOverlay').classList.add('open');
}

function closeConfirm() {
    document.getElementById('confirmOverlay').classList.remove('open');
    document.body.style.overflow = '';
    deleteId = null;
    deleteType = null;
}

async function confirmDelete() {
    if (!deleteId) return;

    if (deleteType === 'exercise') {
        await apiDelete(deleteId);
        exercises = exercises.filter(e => e.id !== deleteId);
        showToast('Đã xóa bài tập', 'info');
        renderStats();
        renderTable();
    } 
    else if (deleteType === 'user') {
        try {
            const r = await fetch(`${USER_API_URL}${deleteId}`, { method: 'DELETE', headers: getHeaders() });
            await checkResponse(r);
            usersList = usersList.filter(u => u.id !== deleteId);
            showToast('Đã xóa người dùng', 'info');
            document.getElementById('userCountBadge').textContent = usersList.length;
            renderUserTable();
        } catch (e) {
            showErrorToast(e, 'Xóa người dùng');
        }
    }
    closeConfirm();
}

// ════════════════════════════════════════════════════════════════
// 9. TIỆN ÍCH THÔNG BÁO (TOAST ĐƯỢC NÂNG CẤP)
// ════════════════════════════════════════════════════════════════
function showToast(msg, type = 'info') {
    const wrap = document.getElementById('toastWrap');
    if (!wrap) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    
    // Gắn thêm icon cho xịn xò
    let icon = 'ℹ️';
    if(type === 'success') icon = '✅';
    if(type === 'error') icon = '❌';

    t.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
    wrap.appendChild(t);
    
    requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('show')));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 3000);
}

document.getElementById('formOverlay').addEventListener('click', e => { if (e.target === e.currentTarget) closeForm(); });
document.getElementById('confirmOverlay').addEventListener('click', e => { if (e.target === e.currentTarget) closeConfirm(); });

// ════════════════════════════════════════════════════════════════
// 10. XỬ LÝ MODAL THÔNG TIN USER
// ════════════════════════════════════════════════════════════════
function openUserModal(id) {
    const u = usersList.find(e => e.id === id);
    if (!u) return;

    // Đổ dữ liệu vào Modal
    document.getElementById('u_fullName').textContent = u.fullName || 'Chưa cập nhật';
    
    // Xử lý Badge quyền
    const roleBadge = document.getElementById('u_role');
    roleBadge.textContent = u.role.toUpperCase();
    roleBadge.className = `badge ${u.role === 'admin' ? 'badge-admin' : 'badge-user'}`;
    
    document.getElementById('u_username').value = '@' + (u.username || 'N/A');
    document.getElementById('u_email').value = u.email || 'N/A';
    document.getElementById('u_age').value = u.age || 'N/A';
    
    // Chuyển đổi giới tính
    let genderStr = 'N/A';
    if(u.gender === 'nam') genderStr = 'Nam';
    else if(u.gender === 'nu') genderStr = 'Nữ';
    else if(u.gender === 'khac') genderStr = 'Khác';
    document.getElementById('u_gender').value = genderStr;
    
    // Xử lý ngày giờ đẹp mắt
    let dateStr = 'Chưa rõ';
    if (u.createdAt) {
        const d = new Date(u.createdAt);
        // Format: DD/MM/YYYY lúc HH:MM
        dateStr = `${d.getDate().toString().padStart(2,'0')}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getFullYear()} lúc ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
    }
    document.getElementById('u_created').value = dateStr;

    // Hiển thị Modal với hiệu ứng
    document.getElementById('userModalOverlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeUserModal() {
    document.getElementById('userModalOverlay').classList.remove('open');
    document.body.style.overflow = '';
}

// Bấm ra ngoài vùng tối để đóng Modal User
document.getElementById('userModalOverlay').addEventListener('click', e => { 
    if (e.target === e.currentTarget) closeUserModal(); 
});

// Khởi chạy khi load trang
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeForm(); closeConfirm(); closeUserModal(); } });
init();
// --------------------------------------------------------------
// 1. TẢI DỮ LIỆU ĐỔ VÀO BẢNG
function loadAdminTips() {
    const tbody = document.getElementById('tipsTableBody');
    tbody.innerHTML = '<div class="empty-row">Đang tải dữ liệu…</div>';

    fetch(API_TIPS)
        .then(res => res.json())
        .then(res => {
            if (res.success && res.data.length > 0) {
                tbody.innerHTML = res.data.map(tip => `
                    <div class="tr tips-grid">
                        <div class="td">${tip.order}</div>
                        <div class="td" style="font-weight: 600;">${tip.title}</div>
                        <div class="td" style="color: var(--text-muted); font-size: 13px;">${tip.content.substring(0, 60)}...</div>
                        <div class="td" style="display:flex; gap:10px;">
                            <span style="cursor:pointer; color:var(--accent);" onclick='editTip(${JSON.stringify(tip)})'>✏️</span>
                            <span style="cursor:pointer; color:#ff6060;" onclick="deleteTip('${tip._id}', '${tip.title}')">🗑️</span>
                        </div>
                    </div>
                `).join('');
            } else {
                tbody.innerHTML = '<div class="empty-row">Chưa có mẹo nào.</div>';
            }
        });
}

// 2. MỞ VÀ ĐÓNG MODAL
function openTipModal() {
    document.getElementById('tipModalOverlay').classList.add('open');
}

function closeTipModal() {
    document.getElementById('tipModalOverlay').classList.remove('open');
    // Reset Form
    document.getElementById('tip_id').value = '';
    document.getElementById('tip_order').value = '1';
    document.getElementById('tip_title').value = '';
    document.getElementById('tip_content').value = '';
    document.getElementById('tipModalTitle').innerText = 'THÊM MẸO MỚI';
}

// 3. BẤM NÚT SỬA (Điền dữ liệu lên Form)
function editTip(tip) {
    document.getElementById('tip_id').value = tip._id;
    document.getElementById('tip_order').value = tip.order;
    document.getElementById('tip_title').value = tip.title;
    document.getElementById('tip_content').value = tip.content;
    document.getElementById('tipModalTitle').innerText = 'SỬA MẸO TẬP LUYỆN';
    openTipModal();
}

// 4. LƯU DỮ LIỆU (POST hoặc PUT)
function saveTip() {
    const id = document.getElementById('tip_id').value;
    const data = {
        order: parseInt(document.getElementById('tip_order').value),
        title: document.getElementById('tip_title').value,
        content: document.getElementById('tip_content').value
    };

    if(!data.title || !data.content) return alert("Vui lòng nhập đủ Tiêu đề và Nội dung!");

    const method = id ? 'PUT' : 'POST';
    const url = id ? `${API_TIPS}/${id}` : API_TIPS;

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(res => {
        if(res.success) {
            closeTipModal();
            loadAdminTips(); // Load lại bảng
        } else {
            alert("Lỗi: " + res.error);
        }
    });
}

// 5. XÓA DỮ LIỆU (DELETE)
function deleteTip(id, title) {
    if (confirm(`Bạn có chắc muốn xóa mẹo "${title}" không?`)) {
        fetch(`${API_TIPS}/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(res => {
            if(res.success) loadAdminTips();
        });
    }
}
// ==========================================
// QUẢN LÝ LỊCH TẬP MẪU
// ==========================================
const catNames = { split: "Push/Pull/Legs", fullbody: "Full Body", upperlower: "Upper/Lower" };

function loadAdminWorkouts() {
    const tbody = document.getElementById('workoutsTableBody');
    tbody.innerHTML = '<div class="empty-row">Đang tải dữ liệu…</div>';

    fetch(API_WORKOUTS).then(res => res.json()).then(res => {
        if (res.success && res.data.length > 0) {
            tbody.innerHTML = res.data.map(wo => `
                <div class="tr workouts-grid">
                    <div class="td"><span class="tab-badge">${catNames[wo.category] || wo.category}</span></div>
                    <div class="td">${wo.order}</div>
                    <div class="td" style="font-weight: 600;">${wo.title}</div>
                    <div class="td">${wo.is_rest_day ? '<span style="color:#4ecdc4;">Có</span>' : '<span style="color:var(--text-muted);">Không</span>'}</div>
                    <div class="td" style="display:flex; gap:10px;">
                        <span style="cursor:pointer; color:var(--accent);" onclick='editWorkout(${JSON.stringify(wo).replace(/'/g, "\\'")})'>✏️</span>
                        <span style="cursor:pointer; color:#ff6060;" onclick="deleteWorkout('${wo._id}', '${wo.title}')">🗑️</span>
                    </div>
                </div>
            `).join('');
        } else {
            tbody.innerHTML = '<div class="empty-row">Chưa có lịch tập mẫu nào.</div>';
        }
    });
}

function toggleWorkoutExercises() {
    const isRest = document.getElementById('wo_is_rest').checked;
    document.getElementById('wo_exercises_section').style.display = isRest ? 'none' : 'block';
}

function addWorkoutExercise(name = '', sets_reps = '') {
    const div = document.createElement('div');
    div.className = 'dynamic-item';
    div.style.cssText = 'display:grid; grid-template-columns: 1fr 1fr auto; gap:8px;';
    div.innerHTML = `
        <input type="text" placeholder="Tên bài (VD: Bench Press)" value="${name}">
        <input type="text" placeholder="Sets x Reps (VD: 4x8)" value="${sets_reps}">
        <button class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('wo_exerciseList').appendChild(div);
}

function openWorkoutModal() {
    document.getElementById('workoutModalOverlay').classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeWorkoutModal() {
    document.getElementById('workoutModalOverlay').classList.remove('open');
    document.body.style.overflow = '';
    // Reset form
    document.getElementById('wo_id').value = '';
    document.getElementById('wo_title').value = '';
    document.getElementById('wo_order').value = '1';
    document.getElementById('wo_is_rest').checked = false;
    document.getElementById('wo_exerciseList').innerHTML = '';
    toggleWorkoutExercises();
    document.getElementById('workoutModalTitle').innerText = 'THÊM NGÀY TẬP MỚI';
}

function editWorkout(wo) {
    document.getElementById('wo_id').value = wo._id;
    document.getElementById('wo_category').value = wo.category;
    document.getElementById('wo_order').value = wo.order || 1;
    document.getElementById('wo_title').value = wo.title;
    document.getElementById('wo_is_rest').checked = wo.is_rest_day || false;
    
    document.getElementById('wo_exerciseList').innerHTML = '';
    if(wo.exercises && wo.exercises.length > 0) {
        wo.exercises.forEach(ex => addWorkoutExercise(ex.name, ex.sets_reps));
    }
    
    toggleWorkoutExercises();
    document.getElementById('workoutModalTitle').innerText = 'SỬA NGÀY TẬP';
    openWorkoutModal();
}

function saveWorkout() {
    const id = document.getElementById('wo_id').value;
    const is_rest = document.getElementById('wo_is_rest').checked;
    
    // Thu thập danh sách bài tập từ các thẻ input
    const exercises = [];
    if(!is_rest) {
        document.querySelectorAll('#wo_exerciseList .dynamic-item').forEach(row => {
            const inputs = row.querySelectorAll('input');
            const name = inputs[0].value.trim();
            const sets_reps = inputs[1].value.trim();
            if(name) exercises.push({ name: name, sets_reps: sets_reps });
        });
    }

    const data = {
        category: document.getElementById('wo_category').value,
        order: parseInt(document.getElementById('wo_order').value),
        title: document.getElementById('wo_title').value,
        is_rest_day: is_rest,
        exercises: exercises
    };

    if(!data.title) return alert("Vui lòng nhập Tiêu đề Ngày!");

    fetch(id ? `${API_WORKOUTS}/${id}` : API_WORKOUTS, {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(res => {
        if(res.success) {
            closeWorkoutModal();
            loadAdminWorkouts();
        } else alert("Lỗi: " + res.error);
    });
}

function deleteWorkout(id, title) {
    if (confirm(`Bạn có chắc muốn xóa "${title}" không?`)) {
        fetch(`${API_WORKOUTS}/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(res => { if(res.success) loadAdminWorkouts(); });
    }
}
// ==========================================
// QUẢN LÝ NỘI DUNG NỔI BẬT
// ==========================================
function loadAdminFeatured() {
    const tbody = document.getElementById('featuredTableBody');
    tbody.innerHTML = '<div class="empty-row">Đang tải dữ liệu…</div>';

    fetch(API_FEATURED).then(res => res.json()).then(res => {
        if (res.success && res.data.length > 0) {
            tbody.innerHTML = res.data.map(feat => `
                <div class="tr featured-grid">
                    <div class="td">${feat.order || 1}</div>
                    <div class="td" style="font-size: 24px;">${feat.icon || '📌'}</div>
                    <div class="td" style="font-weight: 600;">${feat.title}</div>
                    <div class="td" style="color: var(--text-muted); font-size: 13px;">${(feat.description || '').substring(0, 60)}...</div>
                    <div class="td" style="display:flex; gap:10px;">
                        <span style="cursor:pointer; color:var(--accent);" onclick='editFeatured(${JSON.stringify(feat).replace(/'/g, "\\'")})'>✏️</span>
                        <span style="cursor:pointer; color:#ff6060;" onclick="deleteFeatured('${feat._id}', '${feat.title}')">🗑️</span>
                    </div>
                </div>
            `).join('');
        } else {
            tbody.innerHTML = '<div class="empty-row">Chưa có nội dung nổi bật nào.</div>';
        }
    });
}

function openFeaturedModal() {
    document.getElementById('featuredModalOverlay').classList.add('open');
}

function closeFeaturedModal() {
    document.getElementById('featuredModalOverlay').classList.remove('open');
    document.getElementById('feat_id').value = '';
    document.getElementById('feat_order').value = '1';
    document.getElementById('feat_icon').value = '';
    document.getElementById('feat_tag').value = '';
    document.getElementById('feat_title').value = '';
    document.getElementById('feat_desc').value = '';
    document.getElementById('featuredModalTitle').innerText = 'THÊM NỘI DUNG NỔI BẬT';
}

function editFeatured(feat) {
    document.getElementById('feat_id').value = feat._id;
    document.getElementById('feat_order').value = feat.order || 1;
    document.getElementById('feat_icon').value = feat.icon || '';
    document.getElementById('feat_tag').value = feat.tag || '';
    document.getElementById('feat_title').value = feat.title || '';
    document.getElementById('feat_desc').value = feat.description || '';
    document.getElementById('featuredModalTitle').innerText = 'SỬA NỘI DUNG';
    openFeaturedModal();
}

function saveFeatured() {
    const id = document.getElementById('feat_id').value;
    const data = {
        order: parseInt(document.getElementById('feat_order').value) || 1,
        icon: document.getElementById('feat_icon').value,
        tag: document.getElementById('feat_tag').value,
        title: document.getElementById('feat_title').value,
        description: document.getElementById('feat_desc').value
    };

    if(!data.title) return alert("Vui lòng nhập Tiêu đề!");

    fetch(id ? `${API_FEATURED}/${id}` : API_FEATURED, {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(res => res.json()).then(res => {
        if(res.success) {
            closeFeaturedModal();
            loadAdminFeatured();
        } else alert("Lỗi: " + res.error);
    });
}

function deleteFeatured(id, title) {
    if (confirm(`Bạn có chắc muốn xóa "${title}" không?`)) {
        fetch(`${API_FEATURED}/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(res => { if(res.success) loadAdminFeatured(); });
    }
}
// ==========================================
// QUẢN LÝ NHÓM CƠ & BÀI TẬP
// ==========================================
function loadAdminMuscles() {
    const tbody = document.getElementById('musclesTableBody');
    tbody.innerHTML = '<div class="empty-row">Đang tải dữ liệu…</div>';

    fetch(API_MUSCLES).then(res => res.json()).then(res => {
        if (res.success && res.data.length > 0) {
            tbody.innerHTML = res.data.map(mus => `
                <div class="tr muscles-grid">
                    <div class="td">${mus.order || 1}</div>
                    <div class="td" style="font-size: 24px;">${mus.icon || '💪'}</div>
                    <div class="td" style="font-weight: 600;">${mus.name}</div>
                    <div class="td" style="color: var(--text-muted);">${mus.exercise_count || ''}</div>
                    <div class="td" style="display:flex; gap:10px;">
                        <span style="cursor:pointer; color:var(--accent);" onclick='editMuscle(${JSON.stringify(mus).replace(/'/g, "\\'")})'>✏️</span>
                        <span style="cursor:pointer; color:#ff6060;" onclick="deleteMuscle('${mus._id}', '${mus.name}')">🗑️</span>
                    </div>
                </div>
            `).join('');
        } else {
            tbody.innerHTML = '<div class="empty-row">Chưa có nhóm cơ nào.</div>';
        }
    });
}

function openMuscleModal() {
    document.getElementById('muscleModalOverlay').classList.add('open');
}

function closeMuscleModal() {
    document.getElementById('muscleModalOverlay').classList.remove('open');
    document.getElementById('mus_id').value = '';
    document.getElementById('mus_order').value = '1';
    document.getElementById('mus_icon').value = '';
    document.getElementById('mus_name').value = '';
    document.getElementById('mus_count').value = '';
    document.getElementById('muscleModalTitle').innerText = 'THÊM NHÓM CƠ';
}

function editMuscle(mus) {
    document.getElementById('mus_id').value = mus._id;
    document.getElementById('mus_order').value = mus.order || 1;
    document.getElementById('mus_icon').value = mus.icon || '';
    document.getElementById('mus_name').value = mus.name || '';
    document.getElementById('mus_count').value = mus.exercise_count || '';
    document.getElementById('muscleModalTitle').innerText = 'SỬA NHÓM CƠ';
    openMuscleModal();
}

function saveMuscle() {
    const id = document.getElementById('mus_id').value;
    const data = {
        order: parseInt(document.getElementById('mus_order').value) || 1,
        icon: document.getElementById('mus_icon').value,
        name: document.getElementById('mus_name').value,
        exercise_count: document.getElementById('mus_count').value
    };

    if(!data.name || !data.icon) return alert("Vui lòng nhập Tên và Icon!");

    fetch(id ? `${API_MUSCLES}/${id}` : API_MUSCLES, {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(res => res.json()).then(res => {
        if(res.success) {
            closeMuscleModal();
            loadAdminMuscles();
        } else alert("Lỗi: " + res.error);
    });
}

function deleteMuscle(id, name) {
    if (confirm(`Bạn có chắc muốn xóa "${name}" không?`)) {
        fetch(`${API_MUSCLES}/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(res => { if(res.success) loadAdminMuscles(); });
    }
}
// ==========================================
// QUẢN LÝ CÂU HỎI THƯỜNG GẶP (FAQ)
// ==========================================
const faqCatNames = { account: "Tài khoản", plan: "Lộ trình", payment: "Dịch vụ", technical: "Kỹ thuật" };

function loadAdminFaq() {
    const tbody = document.getElementById('faqTableBody');
    tbody.innerHTML = '<div class="empty-row">Đang tải dữ liệu…</div>';

    fetch(API_FAQ).then(res => res.json()).then(res => {
        if (res.success && res.data.length > 0) {
            tbody.innerHTML = res.data.map(faq => `
                <div class="tr faq-grid">
                    <div class="td"><span class="faq-cat-badge">${faqCatNames[faq.cat] || faq.cat}</span></div>
                    <div class="td" style="font-weight: 600; color: var(--accent);">${faq.question}</div>
                    <div class="td" style="color: var(--text-muted); font-size: 13px;">${(faq.answer || '').substring(0, 70)}...</div>
                    <div class="td" style="display:flex; gap:10px;">
                        <span style="cursor:pointer; color:var(--accent);" onclick='editFaq(${JSON.stringify(faq).replace(/'/g, "\\'")})'>✏️</span>
                        <span style="cursor:pointer; color:#ff6060;" onclick="deleteFaq('${faq._id}', '${faq.question}')">🗑️</span>
                    </div>
                </div>
            `).join('');
        } else {
            tbody.innerHTML = '<div class="empty-row">Chưa có câu hỏi nào.</div>';
        }
    });
}

function openFaqModal() {
    document.getElementById('faqModalOverlay').classList.add('open');
}

function closeFaqModal() {
    document.getElementById('faqModalOverlay').classList.remove('open');
    document.getElementById('faq_id').value = '';
    document.getElementById('faq_cat').value = 'account';
    document.getElementById('faq_tag').value = '';
    document.getElementById('faq_question').value = '';
    document.getElementById('faq_answer').value = '';
    document.getElementById('faqModalTitle').innerText = 'THÊM CÂU HỎI MỚI';
}

function editFaq(faq) {
    document.getElementById('faq_id').value = faq._id;
    document.getElementById('faq_cat').value = faq.cat || 'account';
    document.getElementById('faq_tag').value = faq.tag || '';
    document.getElementById('faq_question').value = faq.question || '';
    document.getElementById('faq_answer').value = faq.answer || '';
    document.getElementById('faqModalTitle').innerText = 'SỬA CÂU HỎI';
    openFaqModal();
}

function saveFaq() {
    const id = document.getElementById('faq_id').value;
    const data = {
        cat: document.getElementById('faq_cat').value,
        tag: document.getElementById('faq_tag').value,
        question: document.getElementById('faq_question').value,
        answer: document.getElementById('faq_answer').value
    };

    if(!data.question || !data.answer) return alert("Vui lòng nhập đủ Câu hỏi và Câu trả lời!");

    fetch(id ? `${API_FAQ}/${id}` : API_FAQ, {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(res => res.json()).then(res => {
        if(res.success) {
            closeFaqModal();
            loadAdminFaq();
        } else alert("Lỗi: " + res.error);
    });
}

function deleteFaq(id, question) {
    if (confirm(`Bạn có chắc muốn xóa câu hỏi "${question}" không?`)) {
        fetch(`${API_FAQ}/${id}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(res => { if(res.success) loadAdminFaq(); });
    }
}
// ==========================================
// QUẢN LÝ VÌ SAO CHỌN FIT ME (ABOUT FEATURES)
// ==========================================
function loadAdminAbout() {
    const tbody = document.getElementById('aboutTableBody');
    tbody.innerHTML = '<div class="empty-row">Đang tải dữ liệu…</div>';

    fetch(API_ABOUT).then(res => res.json()).then(res => {
        if (res.success && res.data.length > 0) {
            tbody.innerHTML = res.data.map(abt => `
                <div class="tr about-grid">
                    <div class="td">${abt.order || 1}</div>
                    <div class="td" style="font-size: 24px;">${abt.icon || '📌'}</div>
                    <div class="td" style="font-weight: 600;">${abt.title}</div>
                    <div class="td" style="color: var(--text-muted); font-size: 13px;">${(abt.description || '').substring(0, 60)}...</div>
                    <div class="td" style="display:flex; gap:10px;">
                        <span style="cursor:pointer; color:var(--accent);" onclick='editAbout(${JSON.stringify(abt).replace(/'/g, "\\'")})'>✏️</span>
                        <span style="cursor:pointer; color:#ff6060;" onclick="deleteAbout('${abt._id}', '${abt.title}')">🗑️</span>
                    </div>
                </div>
            `).join('');
        } else {
            tbody.innerHTML = '<div class="empty-row">Chưa có dữ liệu nào.</div>';
        }
    });
}

function openAboutModal() { document.getElementById('aboutModalOverlay').classList.add('open'); }

function closeAboutModal() {
    document.getElementById('aboutModalOverlay').classList.remove('open');
    document.getElementById('abt_id').value = '';
    document.getElementById('abt_order').value = '1';
    document.getElementById('abt_icon').value = '';
    document.getElementById('abt_title').value = '';
    document.getElementById('abt_desc').value = '';
    document.getElementById('aboutModalTitle').innerText = 'THÊM ĐẶC ĐIỂM';
}

function editAbout(abt) {
    document.getElementById('abt_id').value = abt._id;
    document.getElementById('abt_order').value = abt.order || 1;
    document.getElementById('abt_icon').value = abt.icon || '';
    document.getElementById('abt_title').value = abt.title || '';
    document.getElementById('abt_desc').value = abt.description || '';
    document.getElementById('aboutModalTitle').innerText = 'SỬA ĐẶC ĐIỂM';
    openAboutModal();
}

function saveAbout() {
    const id = document.getElementById('abt_id').value;
    const data = {
        order: parseInt(document.getElementById('abt_order').value) || 1,
        icon: document.getElementById('abt_icon').value,
        title: document.getElementById('abt_title').value,
        description: document.getElementById('abt_desc').value
    };

    if(!data.title) return alert("Vui lòng nhập Tiêu đề!");

    fetch(id ? `${API_ABOUT}/${id}` : API_ABOUT, {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(res => res.json()).then(res => {
        if(res.success) { closeAboutModal(); loadAdminAbout(); } 
        else alert("Lỗi: " + res.error);
    });
}

function deleteAbout(id, title) {
    if (confirm(`Bạn có chắc muốn xóa "${title}" không?`)) {
        fetch(`${API_ABOUT}/${id}`, { method: 'DELETE' }).then(res => res.json()).then(res => { if(res.success) loadAdminAbout(); });
    }
}
// ==========================================
// QUẢN LÝ THÔNG TIN LIÊN HỆ (CONTACTS)
// ==========================================
function loadAdminContacts() {
    const tbody = document.getElementById('contactsTableBody');
    tbody.innerHTML = '<div class="empty-row">Đang tải dữ liệu…</div>';

    fetch(API_CONTACTS).then(res => res.json()).then(res => {
        if (res.success && res.data.length > 0) {
            tbody.innerHTML = res.data.map(cont => `
                <div class="tr contacts-grid">
                    <div class="td">${cont.order || 1}</div>
                    <div class="td" style="font-size: 24px;">${cont.icon || '📞'}</div>
                    <div class="td" style="font-weight: 600;">${cont.title}</div>
                    <div class="td" style="color: var(--text-muted); font-size: 13px;">${(cont.description || '').substring(0, 40)}...</div>
                    <div class="td" style="color: var(--accent);">${cont.link_text || ''}</div>
                    <div class="td" style="display:flex; gap:10px;">
                        <span style="cursor:pointer; color:var(--accent);" onclick='editContact(${JSON.stringify(cont).replace(/'/g, "\\'")})'>✏️</span>
                        <span style="cursor:pointer; color:#ff6060;" onclick="deleteContact('${cont._id}', '${cont.title}')">🗑️</span>
                    </div>
                </div>
            `).join('');
        } else {
            tbody.innerHTML = '<div class="empty-row">Chưa có dữ liệu liên hệ nào.</div>';
        }
    });
}

function openContactModal() { document.getElementById('contactModalOverlay').classList.add('open'); }

function closeContactModal() {
    document.getElementById('contactModalOverlay').classList.remove('open');
    document.getElementById('cont_id').value = '';
    document.getElementById('cont_order').value = '1';
    document.getElementById('cont_icon').value = '';
    document.getElementById('cont_title').value = '';
    document.getElementById('cont_link').value = '';
    document.getElementById('cont_desc').value = '';
    document.getElementById('contactModalTitle').innerText = 'THÊM LIÊN HỆ';
}

function editContact(cont) {
    document.getElementById('cont_id').value = cont._id;
    document.getElementById('cont_order').value = cont.order || 1;
    document.getElementById('cont_icon').value = cont.icon || '';
    document.getElementById('cont_title').value = cont.title || '';
    document.getElementById('cont_link').value = cont.link_text || '';
    document.getElementById('cont_desc').value = cont.description || '';
    document.getElementById('contactModalTitle').innerText = 'SỬA LIÊN HỆ';
    openContactModal();
}

function saveContact() {
    const id = document.getElementById('cont_id').value;
    const data = {
        order: parseInt(document.getElementById('cont_order').value) || 1,
        icon: document.getElementById('cont_icon').value,
        title: document.getElementById('cont_title').value,
        link_text: document.getElementById('cont_link').value,
        description: document.getElementById('cont_desc').value
    };

    if(!data.title) return alert("Vui lòng nhập Tiêu đề!");

    fetch(id ? `${API_CONTACTS}/${id}` : API_CONTACTS, {
        method: id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(res => res.json()).then(res => {
        if(res.success) { closeContactModal(); loadAdminContacts(); } 
        else alert("Lỗi: " + res.error);
    });
}

function deleteContact(id, title) {
    if (confirm(`Bạn có chắc muốn xóa "${title}" không?`)) {
        fetch(`${API_CONTACTS}/${id}`, { method: 'DELETE' }).then(res => res.json()).then(res => { if(res.success) loadAdminContacts(); });
    }
}