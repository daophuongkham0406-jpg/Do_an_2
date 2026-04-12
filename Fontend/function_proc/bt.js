// ════════════════════════════════════════════════════════════════
// 1. DATA TỪ MONGODB & BIẾN TRẠNG THÁI (STATE)
// ════════════════════════════════════════════════════════════════
let EX = []; 
const state = { muscle: "all", diff: "all", equip: "all", search: "", sort: "default" };
const favs = new Set();
let currentEx = null;

const diffMap = { B: "Beginner", I: "Intermediate", A: "Advanced" };
const diffLabel = { B: "Người mới", I: "Trung bình", A: "Nâng cao" };
const diffCls = { B: "badge-b", I: "badge-i", A: "badge-a" };
const diffOrder = { B: 0, I: 1, A: 2 };

// ════════════════════════════════════════════════════════════════
// 2. GỌI API LẤY DỮ LIỆU TỪ MÁY CHỦ
// ════════════════════════════════════════════════════════════════
async function fetchExercises() {
    const grid = document.getElementById("exerciseGrid");
    grid.innerHTML = `<div class="no-results"><p>Đang tải dữ liệu từ máy chủ...</p></div>`;
    
    try {
        const response = await fetch('http://127.0.0.1:5000/api/exercises/');
        if (response.ok) {
            EX = await response.json();
            
            // SAU KHI CÓ DỮ LIỆU, TỰ ĐỘNG TẠO BỘ LỌC
            buildDynamicFilters();
            render(); 
        } else {
            grid.innerHTML = `<div class="no-results"><span class="nr-icon">⚠️</span><p>Lỗi máy chủ: Không thể tải bài tập.</p></div>`;
        }
    } catch (error) {
        console.error("Lỗi kết nối API:", error);
        grid.innerHTML = `<div class="no-results"><span class="nr-icon">🔌</span><p>Mất kết nối tới Backend. Hãy kiểm tra python app.py!</p></div>`;
    }
}

// ════════════════════════════════════════════════════════════════
// 3. TẠO BỘ LỌC ĐỘNG (DYNAMIC FILTERS) TỪ DỮ LIỆU THỰC TẾ
// ════════════════════════════════════════════════════════════════
function buildDynamicFilters() {
    // 1. Trích xuất các giá trị không trùng lặp (Unique) từ Data
    const uniqueMuscles = [...new Set(EX.map(e => e.muscle))].filter(Boolean);
    const uniqueDiffs = [...new Set(EX.map(e => e.diff))].filter(Boolean);
    const uniqueEquips = [...new Set(EX.map(e => e.equip))].filter(Boolean);

    // 2. Cập nhật 3 con số To bự ở trên cùng (Hero Pills)
    const pills = document.querySelectorAll('.hero-pill-num');
    if (pills.length >= 3) {
        pills[0].textContent = EX.length;         // Số bài tập
        pills[1].textContent = uniqueMuscles.length; // Số nhóm cơ thực tế
        pills[2].textContent = uniqueDiffs.length;   // Số cấp độ thực tế
    }

    // 3. In HTML mới cho Sidebar
    // --- Nhóm Cơ ---
    document.getElementById("muscleChips").innerHTML = 
        `<span class="chip ${state.muscle === 'all' ? 'on' : ''}" data-val="all">Tất cả</span>` +
        uniqueMuscles.map(m => `<span class="chip ${state.muscle === m ? 'on' : ''}" data-val="${m}">${m}</span>`).join('');

    // --- Độ Khó ---
    document.getElementById("diffList").innerHTML = 
        `<li class="${state.diff === 'all' ? 'on' : ''}" data-val="all"><span class="s-box">${state.diff === 'all' ? '✓' : ''}</span>Tất cả</li>` +
        uniqueDiffs.map(d => {
            let dots = '';
            if(d === 'B') dots = '<span class="diff-row"><span class="dd f"></span><span class="dd"></span><span class="dd"></span></span>';
            if(d === 'I') dots = '<span class="diff-row"><span class="dd f"></span><span class="dd f"></span><span class="dd"></span></span>';
            if(d === 'A') dots = '<span class="diff-row"><span class="dd f"></span><span class="dd f"></span><span class="dd f"></span></span>';
            return `<li class="${state.diff === d ? 'on' : ''}" data-val="${d}"><span class="s-box">${state.diff === d ? '✓' : ''}</span>${diffLabel[d] || d}${dots}</li>`;
        }).join('');

    // --- Thiết bị ---
    document.getElementById("equipList").innerHTML = 
        `<li class="${state.equip === 'all' ? 'on' : ''}" data-val="all"><span class="s-box">${state.equip === 'all' ? '✓' : ''}</span>Tất cả</li>` +
        uniqueEquips.map(e => `<li class="${state.equip === e ? 'on' : ''}" data-val="${e}"><span class="s-box">${state.equip === e ? '✓' : ''}</span>${e}</li>`).join('');

    // 4. Gắn lại sự kiện Click cho các nút vừa tạo
    document.querySelectorAll("#muscleChips .chip").forEach(c => {
        c.onclick = () => { state.muscle = c.dataset.val; syncUI(); render(); };
    });
    document.querySelectorAll("#diffList li").forEach(li => {
        li.onclick = () => { state.diff = li.dataset.val; syncUI(); render(); };
    });
    document.querySelectorAll("#equipList li").forEach(li => {
        li.onclick = () => { state.equip = li.dataset.val; syncUI(); render(); };
    });
}

// ════════════════════════════════════════════════════════════════
// 4. LOGIC LỌC VÀ SẮP XẾP DỮ LIỆU
// ════════════════════════════════════════════════════════════════
function getFiltered() {
    let d = [...EX];
    if (state.muscle !== "all") d = d.filter(e => e.muscle === state.muscle);
    if (state.diff !== "all") d = d.filter(e => e.diff === state.diff);
    if (state.equip !== "all") d = d.filter(e => e.equip === state.equip);
    if (state.search.trim()) d = d.filter(e => e.name.toLowerCase().includes(state.search.toLowerCase()));
    
    if (state.sort === "az") d.sort((a, b) => a.name.localeCompare(b.name));
    if (state.sort === "za") d.sort((a, b) => b.name.localeCompare(a.name));
    if (state.sort === "easy") d.sort((a, b) => diffOrder[a.diff] - diffOrder[b.diff]);
    if (state.sort === "hard") d.sort((a, b) => diffOrder[b.diff] - diffOrder[a.diff]);
    
    return d;
}

// ════════════════════════════════════════════════════════════════
// 5. VẼ GIAO DIỆN DƯỚI (RENDER)
// ════════════════════════════════════════════════════════════════
function render() {
    const data = getFiltered();
    document.getElementById("resNum").textContent = data.length;
    const g = document.getElementById("exerciseGrid");
    
    if (!data.length) {
        g.innerHTML = `<div class="no-results"><span class="nr-icon">🔍</span><p>Không tìm thấy bài tập nào phù hợp bộ lọc.</p></div>`;
        return;
    }
    
    g.innerHTML = data.map((e, i) => `
        <div class="ex-card" style="animation-delay:${i * 35}ms" onclick="openModal('${e.id}')">
            <div class="card-img">
                <div class="card-glow"></div>
                <span class="big-icon">${e.icon || '🏋️'}</span>
                <span class="card-badge ${diffCls[e.diff] || 'badge-i'}">${diffLabel[e.diff] || e.diff}</span>
                <span class="card-fav ${favs.has(e.id) ? 'on' : ''}" onclick="toggleFav(event,'${e.id}')">♡</span>
            </div>
            <div class="card-body">
                <div class="card-muscle">${e.muscle}</div>
                <div class="card-name">${e.name}</div>
                <div class="card-tags">
                    <span class="ctag">${e.equip}</span>
                    <span class="ctag">${e.sets}×${e.reps}</span>
                    <span class="ctag">${e.rest}</span>
                </div>
            </div>
            <div class="card-action-list"><span class="list-arr">›</span></div>
        </div>
    `).join("");
    
    renderActiveTags();
}

function renderActiveTags() {
    const div = document.getElementById("activeFilters");
    const tags = [];
    if (state.muscle !== "all") tags.push({ l: state.muscle, k: "muscle" });
    if (state.diff !== "all") tags.push({ l: diffLabel[state.diff], k: "diff" });
    if (state.equip !== "all") tags.push({ l: state.equip, k: "equip" });
    if (state.search.trim()) tags.push({ l: `"${state.search.trim()}"`, k: "search" });
    
    div.innerHTML = tags.map(t => `<span class="af-tag">${t.l}<button onclick="clearTag('${t.k}')">✕</button></span>`).join("");
}

function clearTag(k) {
    if (k === "search") { state.search = ""; document.getElementById("searchInput").value = ""; }
    else state[k] = "all";
    syncUI(); 
    render();
}

function syncUI() {
    document.querySelectorAll("#muscleChips .chip").forEach(c => c.classList.toggle("on", c.dataset.val === state.muscle));
    document.querySelectorAll("#diffList li").forEach(li => {
        const on = li.dataset.val === state.diff;
        li.classList.toggle("on", on);
        li.querySelector(".s-box").textContent = on ? "✓" : "";
    });
    document.querySelectorAll("#equipList li").forEach(li => {
        const on = li.dataset.val === state.equip;
        li.classList.toggle("on", on);
        li.querySelector(".s-box").textContent = on ? "✓" : "";
    });
}

// ════════════════════════════════════════════════════════════════
// 6. KHỞI CHẠY VÀ LẮNG NGHE SỰ KIỆN TĨNH
// ════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("searchInput").addEventListener("input", e => { state.search = e.target.value; render(); });
    document.getElementById("sortSel").addEventListener("change", e => { state.sort = e.target.value; render(); });
    
    document.getElementById("clearBtn").onclick = () => {
        state.muscle = "all"; state.diff = "all"; state.equip = "all"; state.search = ""; state.sort = "default";
        document.getElementById("searchInput").value = "";
        document.getElementById("sortSel").value = "default";
        syncUI(); render();
    };
    
    document.getElementById("gridBtn").onclick = () => {
        document.getElementById("exerciseGrid").classList.remove("list");
        document.getElementById("gridBtn").classList.add("on");
        document.getElementById("listBtn").classList.remove("on");
    };
    document.getElementById("listBtn").onclick = () => {
        document.getElementById("exerciseGrid").classList.add("list");
        document.getElementById("listBtn").classList.add("on");
        document.getElementById("gridBtn").classList.remove("on");
    };

    // Gọi API ngay khi mở trang
    fetchExercises();
});

// ════════════════════════════════════════════════════════════════
// 7. XỬ LÝ MODAL (POPUP CHI TIẾT BÀI TẬP)
// ════════════════════════════════════════════════════════════════
function toggleFav(e, id) {
    e.stopPropagation();
    favs.has(id) ? favs.delete(id) : favs.add(id);
    render();
    if (currentEx && currentEx.id === id)
        document.getElementById("mFavBtn").innerHTML = favs.has(id) ? "❤️  Đã yêu thích" : "♡  Yêu thích";
}

function openModal(id) {
    const ex = EX.find(e => e.id === id);
    if (!ex) return;
    currentEx = ex;

    document.getElementById("mIcon").textContent = ex.icon || '🏋️';
    document.getElementById("mMuscle").textContent = (ex.muscle || "").toUpperCase();
    document.getElementById("mName").textContent = ex.name;
    document.getElementById("mBadges").innerHTML = `
        <span class="card-badge ${diffCls[ex.diff] || 'badge-i'}">${diffLabel[ex.diff] || ex.diff}</span>
        <span class="card-badge" style="background:rgba(77,160,255,.12);color:#4da0ff;border:1px solid rgba(77,160,255,.25)">${ex.equip}</span>
    `;
    document.getElementById("mStats").innerHTML = `
        <div class="m-stat"><div class="m-stat-num">${ex.sets}</div><div class="m-stat-lbl">Sets</div></div>
        <div class="m-stat"><div class="m-stat-num">${ex.reps}</div><div class="m-stat-lbl">Reps</div></div>
        <div class="m-stat"><div class="m-stat-num">${ex.rest}</div><div class="m-stat-lbl">Nghỉ</div></div>
    `;

    // Xóa đoạn gọi s.t và s.d đi, chỉ gọi thẳng chữ s ra thôi!
    const stepsHtml = (ex.steps && ex.steps.length > 0) 
        ? ex.steps.map((s, i) => `<li class="step"><span class="step-num">0${i + 1}</span><div class="step-text">${s}</div></li>`).join("")
        : `<p style="color:var(--text3); font-size:14px;">Chưa có hướng dẫn.</p>`;
    document.getElementById("pane-steps").innerHTML = `<ol class="steps">${stepsHtml}</ol>`;

    const allM = [{ role: "Cơ chính", name: ex.muscle }];
    if(ex.sec) ex.sec.forEach(s => allM.push({ role: "Cơ phụ", name: s }));
    document.getElementById("pane-muscles").innerHTML = `<div class="muscle-groups">${
        allM.map(m => `<div class="mg-item"><div class="mg-role">${m.role}</div><div class="mg-name">${m.name}</div></div>`).join("")
    }</div>`;

    const tipsHtml = (ex.tips && ex.tips.length > 0)
        ? ex.tips.map(t => `<li class="tip-item"><span class="tip-icon">⚡</span><span class="tip-text">${t}</span></li>`).join("")
        : `<p style="color:var(--text3); font-size:14px;">Không có lưu ý.</p>`;
    document.getElementById("pane-tips").innerHTML = `<ul class="tips-list">${tipsHtml}</ul>`;

    document.getElementById("mFavBtn").innerHTML = favs.has(ex.id) ? "❤️  Đã yêu thích" : "♡  Yêu thích";

    document.querySelectorAll(".m-tab").forEach(t => t.classList.remove("on"));
    document.querySelectorAll(".tab-pane").forEach(t => t.classList.remove("on"));
    document.querySelector(".m-tab[data-t='steps']").classList.add("on");
    document.getElementById("pane-steps").classList.add("on");

    document.querySelector(".modal").scrollTop = 0;
    document.getElementById("modalOverlay").classList.add("open");
    document.body.style.overflow = "hidden";
}

document.getElementById("modalClose").onclick = closeModal;
document.getElementById("modalOverlay").onclick = e => { if (e.target === e.currentTarget) closeModal(); };
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

function closeModal() {
    document.getElementById("modalOverlay").classList.remove("open");
    document.body.style.overflow = "";
}

document.querySelectorAll(".m-tab").forEach(btn => {
    btn.onclick = () => {
        document.querySelectorAll(".m-tab").forEach(t => t.classList.remove("on"));
        document.querySelectorAll(".tab-pane").forEach(t => t.classList.remove("on"));
        btn.classList.add("on");
        document.getElementById("pane-" + btn.dataset.t).classList.add("on");
    };
});

document.getElementById("mFavBtn").onclick = () => {
    if (!currentEx) return;
    favs.has(currentEx.id) ? favs.delete(currentEx.id) : favs.add(currentEx.id);
    document.getElementById("mFavBtn").innerHTML = favs.has(currentEx.id) ? "❤️  Đã yêu thích" : "♡  Yêu thích";
    render();
};