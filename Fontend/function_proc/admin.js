// ═══════════════════════════════════════════════════════
// ██  API LAYER — KẾT NỐI TRỰC TIẾP MONGODB
// ═══════════════════════════════════════════════════════
const API_URL = 'http://127.0.0.1:5000/api/exercises'; 

function getHeaders(){
    return {'Content-Type': 'application/json'};
}

async function apiGet() {
    try {
        const r = await fetch(API_URL, { headers: getHeaders() });
        if (!r.ok) throw new Error(r.status);
        return await r.json();
    } catch(e) { 
        showToast('Lỗi kết nối Backend. Hãy kiểm tra python app.py!', 'error'); 
        return []; 
    }
}

async function apiPost(data) {
    try {
        const r = await fetch(API_URL, { method: 'POST', headers: getHeaders(), body: JSON.stringify(data) });
        if (!r.ok) throw new Error(r.status);
        return await r.json();
    } catch(e) { showToast('Lỗi khi Thêm bài tập', 'error'); throw e; }
}

async function apiPut(id, data) {
    try {
        const r = await fetch(`${API_URL}/${id}`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify(data) });
        if (!r.ok) throw new Error(r.status);
        return await r.json();
    } catch(e) { showToast('Lỗi khi Sửa bài tập', 'error'); throw e; }
}

async function apiDelete(id) {
    try {
        const r = await fetch(`${API_URL}/${id}`, { method: 'DELETE', headers: getHeaders() });
        if (!r.ok) throw new Error(r.status);
        return true;
    } catch(e) { showToast('Lỗi khi Xóa bài tập', 'error'); throw e; }
}

// ═══════════════════════════════════════════════════════
// ██  STATE & INIT (CÓ BẢO MẬT)
// ═══════════════════════════════════════════════════════
let exercises = [];
let editingId = null;
let deleteId = null;

async function init() {
    // 1. BẢO MẬT: KIỂM TRA QUYỀN ADMIN
    const userStr = localStorage.getItem('loggedInUser');
    if (!userStr) {
        window.location.href = 'dangnhap.html'; // Chưa đăng nhập -> Đuổi
        return;
    }
    const user = JSON.parse(userStr);
    if (user.role !== 'admin') {
        alert('⛔ Bạn không có quyền truy cập trang Quản trị!');
        window.location.href = 'index.html'; // User thường -> Đuổi
        return;
    }

    // Hiển thị tên Admin trên Topbar
    const adminNameEl = document.getElementById('adminName');
    if(adminNameEl) adminNameEl.textContent = `Xin chào, ${user.fullName}`;

    // 2. TẢI DỮ LIỆU
    exercises = await apiGet();
    
    document.getElementById('statusDot').className = 'status-dot connected';
    document.getElementById('statusText').textContent = 'Đã kết nối MongoDB';
    
    renderStats();
    renderTable();
}

function renderStats(){
    const t = exercises.length;
    document.getElementById('statTotal').textContent = t;
    document.getElementById('statBeginner').textContent = exercises.filter(e=>e.diff==='B').length;
    document.getElementById('statInter').textContent = exercises.filter(e=>e.diff==='I').length;
    document.getElementById('statAdv').textContent = exercises.filter(e=>e.diff==='A').length;
    document.getElementById('exCountBadge').textContent = t;
}

// ═══════════════════════════════════════════════════════
// ██  TABLE RENDER
// ═══════════════════════════════════════════════════════
const diffLabel={B:'Người mới',I:'Trung bình',A:'Nâng cao'};

function renderTable(){
    const q=document.getElementById('adminSearch').value.toLowerCase();
    const m=document.getElementById('filterMuscle').value;
    const d=document.getElementById('filterDiff').value;
    
    let data=[...exercises];
    if(q) data=data.filter(e=>e.name.toLowerCase().includes(q));
    if(m) data=data.filter(e=>e.muscle===m);
    if(d) data=data.filter(e=>e.diff===d);
    
    const tbody=document.getElementById('tableBody');
    if(!data.length){tbody.innerHTML='<div class="empty-row">Không tìm thấy bài tập nào.</div>';return;}
    
    tbody.innerHTML=data.map(e=>`
        <div class="tr" onclick="openEdit('${e.id}')">
            <div class="td icon-cell">${e.icon||'❓'}</div>
            <div class="td id-cell">${String(e.id).slice(-6)}</div>
            <div class="td name">${e.name}</div>
            <div class="td equip">${e.muscle}</div>
            <div class="td equip">${e.equip}</div>
            <div class="td"><span class="badge badge-${e.diff}">${diffLabel[e.diff]||e.diff}</span></div>
            <div class="td actions" onclick="event.stopPropagation()">
                <button class="icon-btn edit" onclick="openEdit('${e.id}')" title="Sửa">✏️</button>
                <button class="icon-btn del" onclick="askDelete('${e.id}')" title="Xóa">🗑️</button>
            </div>
        </div>
    `).join('');
}

// ═══════════════════════════════════════════════════════
// ██  FORM — ADD / EDIT
// ═══════════════════════════════════════════════════════
function openAdd(){
    editingId=null;
    document.getElementById('formTitle').textContent='THÊM BÀI TẬP MỚI';
    clearForm();
    addStep(); addStep(); 
    addTip(); 
    document.getElementById('formOverlay').classList.add('open');
    document.body.style.overflow='hidden';
}

function openEdit(id){
    const ex=exercises.find(e=>e.id===id);
    if(!ex) return;
    editingId=id;
    document.getElementById('formTitle').textContent='SỬA BÀI TẬP';
    clearForm();
    document.getElementById('f_name').value=ex.name||'';
    document.getElementById('f_muscle').value=ex.muscle||'';
    document.getElementById('f_icon').value=ex.icon||'';
    document.getElementById('f_diff').value=ex.diff||'';
    document.getElementById('f_equip').value=ex.equip||'';
    document.getElementById('f_sets').value=ex.sets||'';
    document.getElementById('f_reps').value=ex.reps||'';
    document.getElementById('f_rest').value=ex.rest||'';
    (ex.sec||[]).forEach(s=>addSec(s));
    (ex.steps||[]).forEach(s=>addStep(s.t,s.d));
    (ex.tips||[]).forEach(t=>addTip(t));
    document.getElementById('formOverlay').classList.add('open');
    document.body.style.overflow='hidden';
}

function clearForm(){
    ['f_name','f_muscle','f_icon','f_diff','f_equip','f_sets','f_reps','f_rest'].forEach(id=>{
        const el=document.getElementById(id);
        if(el) el.value='';
    });
    ['secList','stepList','tipList'].forEach(id=>document.getElementById(id).innerHTML='');
}

function closeForm(){
    document.getElementById('formOverlay').classList.remove('open');
    document.body.style.overflow='';
}

// ── Dynamic rows ──
function addSec(val=''){
    const div=document.createElement('div');
    div.className='dynamic-item';
    div.innerHTML=`<input type="text" placeholder="VD: Vai trước" value="${val}"><button class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('secList').appendChild(div);
}
let stepCount=0;
function addStep(t='',d=''){
    stepCount++;
    const n=document.getElementById('stepList').children.length+1;
    const div=document.createElement('div');
    div.className='dynamic-item';
    div.style.cssText='display:grid;grid-template-columns:28px 1fr 1.5fr auto;gap:8px;align-items:start;';
    div.innerHTML=`
        <span style="font-family:'Bebas Neue';font-size:26px;color:var(--border2);line-height:1.4;">${String(n).padStart(2,'0')}</span>
        <input type="text" placeholder="Tiêu đề bước…" value="${escHtml(t)}">
        <textarea placeholder="Mô tả chi tiết bước…" rows="2">${escHtml(d)}</textarea>
        <button class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('stepList').appendChild(div);
}
function addTip(val=''){
    const div=document.createElement('div');
    div.className='dynamic-item';
    div.innerHTML=`<input type="text" placeholder="VD: ⚡ Không nhấc mông khỏi bench" value="${escHtml(val)}"><button class="remove-btn" onclick="this.parentElement.remove()">✕</button>`;
    document.getElementById('tipList').appendChild(div);
}

function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

// ── SUBMIT ──
async function submitForm(){
    const name=document.getElementById('f_name').value.trim();
    const muscle=document.getElementById('f_muscle').value;
    const icon=document.getElementById('f_icon').value.trim();
    const diff=document.getElementById('f_diff').value;
    const equip=document.getElementById('f_equip').value;
    if(!name||!muscle||!icon||!diff||!equip){
        showToast('Vui lòng điền đầy đủ các trường bắt buộc (*)','error');return;
    }
    const sec=[...document.querySelectorAll('#secList .dynamic-item input')].map(i=>i.value.trim()).filter(Boolean);
    const steps=[...document.querySelectorAll('#stepList .dynamic-item')].map(row=>{
        const inputs=row.querySelectorAll('input,textarea');
        return{t:(inputs[0]||{}).value||'',d:(inputs[1]||{}).value||''};
    }).filter(s=>s.t||s.d);
    const tips=[...document.querySelectorAll('#tipList .dynamic-item input')].map(i=>i.value.trim()).filter(Boolean);
    
    const payload={name,muscle,icon,diff,equip,sets:document.getElementById('f_sets').value.trim(),reps:document.getElementById('f_reps').value.trim(),rest:document.getElementById('f_rest').value.trim(),sec,steps,tips};
    
    if(editingId){
        const updated=await apiPut(editingId,payload);
        exercises=exercises.map(e=>e.id===editingId?{...e,...updated}:e);
        showToast('✅ Đã cập nhật bài tập','success');
    }else{
        const created=await apiPost(payload);
        exercises.push(created);
        showToast('✅ Đã thêm bài tập mới','success');
    }
    closeForm();
    renderStats();
    renderTable();
}

// ═══════════════════════════════════════════════════════
// ██  DELETE
// ═══════════════════════════════════════════════════════
function askDelete(id){
    deleteId=id;
    const ex=exercises.find(e=>e.id===id);
    document.getElementById('confirmName').textContent=ex?`"${ex.name}"`:'bài tập này';
    document.getElementById('confirmOverlay').classList.add('open');
    document.body.style.overflow='hidden';
}
function closeConfirm(){
    document.getElementById('confirmOverlay').classList.remove('open');
    document.body.style.overflow='';
    deleteId=null;
}
async function confirmDelete(){
    if(!deleteId) return;
    await apiDelete(deleteId);
    exercises=exercises.filter(e=>e.id!==deleteId);
    showToast('🗑️ Đã xóa bài tập','info');
    closeConfirm();
    renderStats();
    renderTable();
}

// ═══════════════════════════════════════════════════════
// ██  TOAST & EVENTS
// ═══════════════════════════════════════════════════════
function showToast(msg,type='info'){
    const wrap=document.getElementById('toastWrap');
    const t=document.createElement('div');
    t.className=`toast ${type}`;
    t.textContent=msg;
    wrap.appendChild(t);
    requestAnimationFrame(()=>requestAnimationFrame(()=>t.classList.add('show')));
    setTimeout(()=>{t.classList.remove('show');setTimeout(()=>t.remove(),400);},3000);
}

document.getElementById('formOverlay').addEventListener('click',e=>{if(e.target===e.currentTarget)closeForm();});
document.getElementById('confirmOverlay').addEventListener('click',e=>{if(e.target===e.currentTarget)closeConfirm();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeForm();closeConfirm();}});

// Khởi chạy khi load trang
init();