
    const AI_SERVER_URL = 'http://localhost:5001';
    // ── Lấy userId từ localStorage (do check_login.js lưu) ──
    const USER_ID = localStorage.getItem('userId') || 'guest';

    let selectedDays  = 7;
    let currentPlanData = null;  // JSON plan hiện tại
    let currentPlanId   = null;  // _id sau khi lưu

    // ── Theme toggle ──
    const toggleBtn = document.getElementById("themeToggle");
    toggleBtn.addEventListener("click", () => {
        document.body.classList.toggle("light-mode");
        const isLight = document.body.classList.contains("light-mode");
        toggleBtn.textContent = isLight ? "☀️" : "🌙";
        localStorage.setItem("theme", isLight ? "light" : "dark");
    });
    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light-mode");
        toggleBtn.textContent = "☀️";
    }

    // ── Chọn độ dài lộ trình ──
    function selectDur(el, days) {
        if (el.classList.contains('disabled')) return;
        document.querySelectorAll('.dur-btn').forEach(b => b.classList.remove('active'));
        el.classList.add('active');
        selectedDays = days;
    }

    // ── Mở khóa gói dài (gọi khi là tài khoản Premium) ──
    function unlockLongPlans() {
        document.querySelectorAll('.dur-btn.disabled').forEach(b => {
            b.classList.remove('disabled');
            const lock = b.querySelector('.lock');
            if (lock) lock.remove();
            const days = parseInt(b.dataset.days);
            b.onclick = () => selectDur(b, days);
        });
        document.getElementById('durationHint').innerHTML = '✅ <span style="color:var(--accent);font-weight:bold;">Tài khoản Premium</span>. Bạn có thể sử dụng mọi tính năng!';
    }

    // ── KIỂM TRA QUYỀN PREMIUM (MỚI) ──
    function checkPremiumStatus() {
        const userStr = localStorage.getItem('loggedInUser');
        if (!userStr) return;
        
        const localUser = JSON.parse(userStr);
        
        // GIẢ SỬ: Dữ liệu user của bạn có thuộc tính isPremium hoặc role là 'vip'
        // Bạn có thể chỉnh sửa điều kiện này tùy theo cách bạn lưu trong Database
        const isPremium = localUser.isPremium === true || localUser.role === 'premium';
        
        if (isPremium) {
            unlockLongPlans(); // Nếu là VIP thì mở khóa ngay và luôn!
        }
    }
    
    // Gọi hàm kiểm tra lúc vừa load trang
    checkPremiumStatus();

    // ═══════════════════════════════════════
    // TẠO LỘ TRÌNH
    // ═══════════════════════════════════════
    document.getElementById('btn-generate').addEventListener('click', async () => {
        const goal      = document.getElementById('goal').value;
        const level     = document.getElementById('level').value;
        const equipment = document.getElementById('equipment').value;
        const userInfo  = document.getElementById('userInfo').value;
        const height    = document.getElementById('height').value;
        const weight    = document.getElementById('weight').value;
        const age       = document.getElementById('age').value;

        document.getElementById('plan-title').innerText = `LỘ TRÌNH ${goal.toUpperCase()} — ${selectedDays} NGÀY`;
        document.getElementById('plan-sub').innerText   = `${level} · ${height}cm · ${weight}kg · ${age} tuổi`;

        const container = document.getElementById('plan-container');
        container.innerHTML = `
            <div class="empty-state">
                <div class="loading-spinner"></div>
                <p>AI đang phân tích và tạo lộ trình ${selectedDays} ngày cho bạn...</p>
                <p style="font-size:12px;margin-top:6px;opacity:0.5">${goal} · ${level} · ${height}cm · ${weight}kg</p>
            </div>`;

        const btn = document.getElementById('btn-generate');
        btn.disabled = true;
        btn.innerText = 'Đang tạo...';

        // Ẩn progress bar
        document.getElementById('progressWrap').classList.remove('show');
        currentPlanData = null;
        currentPlanId   = null;

        try {
            const response = await fetch(`${AI_SERVER_URL}/api/generate-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal, level, equipment, userInfo, height, weight, age, duration: selectedDays })
            });

            const data = await response.json();

            if (data.plan_data) {
                currentPlanData = data.plan_data;
                renderPlan(data.plan_data, container);
                appendPlanActions(container, data.plan_data);
            } else if (data.error) {
                const is429 = data.error.includes('429') || data.error.includes('Quota');
                container.innerHTML = `<div class="empty-state" style="color:${is429 ? 'var(--accent)' : '#e74c3c'}">
                    ${is429 ? '⏳ AI đang bận, vui lòng chờ 15 giây rồi thử lại.' : '❌ Lỗi AI: ' + data.error}
                </div>`;
            }

        } catch (err) {
            container.innerHTML = `
                <div class="empty-state" style="color:#e74c3c">
                    <p>❌ Không thể kết nối máy chủ AI.</p>
                    <p style="font-size:12px;margin-top:8px;opacity:0.6">Hãy chạy: <code>python ai_server.py</code> tại cổng 5001</p>
                </div>`;
        } finally {
            btn.disabled = false;
            btn.innerText = '⚡ Tạo Lộ Trình Bằng AI';
        }
    });

    function renderPlan(planData, container, progress = null) {
    container.innerHTML = '';
    let totalDays = planData.days.length;
    let completedDaysCount = 0;

    planData.days.forEach((day, index) => {
        const dayCard = document.createElement('div');
        dayCard.className = `day-card ${index === 0 ? 'open' : ''}`;
        dayCard.dataset.dayNumber = day.day_number;

        // Ép Ngày 4 và Ngày 7 thành ngày nghỉ nếu cần
        if (day.day_number === 4 || day.day_number === 7) {
            day.is_rest = true; 
        }

        let dayDone = false;
        let exProgress = {};
        if (progress) {
            const pd = progress.find(p => p.day_number === day.day_number);
            if (pd) {
                dayDone = pd.day_done;
                pd.exercises.forEach(e => { exProgress[e.name] = e.completed; });
            }
        }
        if (dayDone) {
            dayCard.classList.add('day-done-card');
        }

        dayCard.innerHTML = `
            <div class="day-header" onclick="this.parentElement.classList.toggle('open')">
                <div class="day-header-left">
                    <span class="day-num-badge">Ngày ${day.day_number}</span>
                    <span class="day-name">${day.day_name || ''}</span>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <span class="day-focus">${day.is_rest ? 'NGHỈ NGƠI' : (day.focus || '')}</span>
                    <span class="day-check-badge ${dayDone ? 'show' : ''}">✓ Hoàn thành</span>
                    <span class="day-toggle-icon">▼</span>
                </div>
            </div>
            <div class="day-body" id="day-body-${day.day_number}"></div>`;

        container.appendChild(dayCard);
        const body = document.getElementById(`day-body-${day.day_number}`);

        if (day.is_rest) {
            // TẠO Ô TICK CHO NGÀY NGHỈ
            body.innerHTML = `
                <div class="rest-check-box ${dayDone ? 'completed' : ''}" id="rest-btn-${day.day_number}">
                    <div class="ex-checkbox">${dayDone ? '✓' : ''}</div>
                    <span style="font-weight:600;">Xác nhận đã nghỉ ngơi & phục hồi</span>
                </div>`;

            const restBtn = document.getElementById(`rest-btn-${day.day_number}`);
            restBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isDone = !restBtn.classList.contains('completed');
                checkinExercise(currentPlanId, day.day_number, 'RestDay', isDone, restBtn, dayCard, true);
            });
        } else {
            // RENDER BÀI TẬP NHƯ CŨ
            day.exercises.forEach(ex => {
                const done = exProgress[ex.name] || false;
                const exEl = document.createElement('div');
                exEl.className = `routine-item${done ? ' completed' : ''}`;
                exEl.innerHTML = `
                    <div class="ex-checkbox">${done ? '✓' : ''}</div>
                    <div class="routine-item-info">
                        <h4>${ex.name}</h4>
                        <div class="tags">
                            <span class="tag tag-muscle">${ex.muscle_group}</span>
                            <span class="tag tag-sets">${ex.sets} sets × ${ex.reps} reps</span>
                        </div>
                    </div>`;
                exEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const isDone = !exEl.classList.contains('completed');
                    checkinExercise(currentPlanId, day.day_number, ex.name, isDone, exEl, dayCard, false);
                });
                body.appendChild(exEl);
            });
        }
    });

    // Cập nhật lại thanh tiến độ dựa trên số lượng .day-done-card thực tế
    const actualDone = document.querySelectorAll('.day-done-card').length;
    updateProgressBar(actualDone, totalDays);
}
    // ═══════════════════════════════════════
    // NÚT ÁP DỤNG / TẠO LẠI
    // ═══════════════════════════════════════
    function appendPlanActions(container, planData) {
        const wrap = document.createElement('div');
        wrap.className = 'plan-actions';
        wrap.id = 'plan-action-buttons'; // Thêm ID để dễ gọi
        wrap.innerHTML = `
            <button class="btn-apply" id="btn-apply">💾 Áp dụng lộ trình này</button>
            <button class="btn-retry" id="btn-retry">🔄 Tạo lại</button>
        `;
        container.appendChild(wrap);

        // Nút hủy (nằm dưới cùng)
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn-danger';
        cancelBtn.id = 'btn-cancel-plan';
        cancelBtn.innerHTML = '🗑️ HỦY LỘ TRÌNH ĐANG TẬP';
        container.appendChild(cancelBtn);

        document.getElementById('btn-apply').addEventListener('click', () => savePlan(planData));
        document.getElementById('btn-retry').addEventListener('click', () => {
            document.getElementById('btn-generate').click();
        });
        document.getElementById('btn-cancel-plan').addEventListener('click', cancelPlan);
    }

    // ═══════════════════════════════════════
    // LƯU LỘ TRÌNH VÀO MONGODB
    // ═══════════════════════════════════════
    async function savePlan(planData) {
        const height = document.getElementById('height').value;
        const weight = document.getElementById('weight').value;
        const age    = document.getElementById('age').value;
        const btn    = document.getElementById('btn-apply');
        if (btn) { btn.disabled = true; btn.innerText = 'Đang lưu...'; }

        try {
            const res  = await fetch(`${AI_SERVER_URL}/api/save-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plan_data: planData,
                    plan_html: document.getElementById('plan-container').innerHTML,
                    userId:    USER_ID,
                    height, weight, age
                })
            });
            const result = await res.json();

            if (result.success) {
                currentPlanId = result.plan_id;
                showToast('✅ Lộ trình đã kích hoạt! Bắt đầu tập thôi!', 'success');

                // 1. Cập nhật progress bar
                updateProgressBar(0, planData.duration_days || selectedDays);

                // 2. Ẩn nút "Áp dụng" và "Tạo lại"
                document.getElementById('plan-action-buttons').style.display = 'none';

                // 3. Hiện nút "Hủy lộ trình"
                document.getElementById('btn-cancel-plan').classList.add('show');
                
                // 4. Khóa cái form bên trái lại không cho người dùng bấm lung tung nữa
                document.getElementById('btn-generate').disabled = true;
                document.getElementById('btn-generate').innerText = 'LỘ TRÌNH ĐANG CHẠY';
                document.getElementById('btn-generate').style.opacity = '0.5';
            } else {
                showToast('❌ Lỗi lưu: ' + result.error, 'error');
            }
        } catch(e) {
            showToast('❌ Không kết nối được server', 'error');
        } finally {
            if (btn && btn.style.display !== 'none') {
                btn.disabled = false;
                btn.innerText = '💾 Áp dụng lộ trình này';
            }
        }
        
    }

    // ═══════════════════════════════════════
    // CHECK-IN BÀI TẬP (BẢN PRO - CẬP NHẬT TỨC THỜI)
    // ═══════════════════════════════════════
    async function checkinExercise(planId, dayNumber, exName, completed, exEl, dayCard, isRest = false) {
        
        // 🌟 BƯỚC 1: ĐỔI MÀU GIAO DIỆN NGAY LẬP TỨC (Không chờ Server)
        if (isRest) {
            if (completed) {
                exEl.classList.add('completed');
                exEl.querySelector('.ex-checkbox').textContent = '✓';
                exEl.style.borderColor = '#4ecdc4';
                exEl.style.background = 'rgba(78,205,196,0.05)';
                
                dayCard.classList.add('day-done-card');
                const badge = dayCard.querySelector('.day-check-badge');
                if(badge) { badge.textContent = '✓ Hoàn thành'; badge.classList.add('show'); }
            } else {
                exEl.classList.remove('completed');
                exEl.querySelector('.ex-checkbox').textContent = '';
                exEl.style.borderColor = 'var(--border-hover)';
                exEl.style.background = 'rgba(255,255,255,0.03)';
                
                dayCard.classList.remove('day-done-card');
                const badge = dayCard.querySelector('.day-check-badge');
                if(badge) badge.classList.remove('show');
            }
        } 
        else {
            if (completed) {
                exEl.classList.add('completed');
                exEl.querySelector('.ex-checkbox').textContent = '✓';
            } else {
                exEl.classList.remove('completed');
                exEl.querySelector('.ex-checkbox').textContent = '';
            }

            // Kiểm tra xem đã tick hết sạch bài tập trong ngày chưa?
            const body = document.getElementById(`day-body-${dayNumber}`);
            const allItems = body.querySelectorAll('.routine-item');
            const allDone = [...allItems].every(el => el.classList.contains('completed'));
            
            const badge = dayCard.querySelector('.day-check-badge');
            if (allDone) {
                dayCard.classList.add('day-done-card');
                if(badge) { badge.textContent = '✓ Hoàn thành'; badge.classList.add('show'); }
            } else {
                dayCard.classList.remove('day-done-card');
                if(badge) badge.classList.remove('show');
            }
        }

        // 🌟 BƯỚC 2: ĐẾM LẠI VÀ CHẠY THANH TIẾN ĐỘ NGAY LẬP TỨC
        const totalDaysCount = document.querySelectorAll('.day-card').length;
        const completedDaysCount = document.querySelectorAll('.day-done-card').length;
        
        updateProgressBar(completedDaysCount, totalDaysCount);

        if (completedDaysCount === totalDaysCount && totalDaysCount > 0) {
            showToast('🎉 Tuyệt vời! Bạn đã hoàn thành toàn bộ lộ trình!', 'success');
            // XÓA HOẶC COMMENT DÒNG BÊN DƯỚI LẠI
            // if(typeof unlockLongPlans === 'function') unlockLongPlans(); 
        }

        // 🌟 BƯỚC 3: GỬI BÁO CÁO CHO SERVER NGẦM PHÍA SAU
        try {
            fetch(`${AI_SERVER_URL}/api/checkin-exercise`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ planId, dayNumber, exerciseName: exName, completed })
            }).then(res => {
                if(!res.ok) console.warn("Lưu tiến độ lên server thất bại!");
            });
        } catch (e) {
            console.error("Lỗi mạng khi lưu ngầm:", e);
        }
    }

    // ═══════════════════════════════════════
    // CẬP NHẬT THANH TIẾN ĐỘ
    // ═══════════════════════════════════════
    function updateProgressBar(done, total) {
        const pct = total > 0 ? Math.round(done / total * 100) : 0;
        document.getElementById('progressWrap').classList.add('show');
        document.getElementById('progressPct').textContent  = pct + '%';
        document.getElementById('progressBar').style.width  = pct + '%';
        document.getElementById('progressDays').textContent = `${done} / ${total} ngày hoàn thành`;
    }

    // ═══════════════════════════════════════
    // TOAST NOTIFICATION
    // ═══════════════════════════════════════
    function showToast(msg, type = 'success') {
        const t = document.createElement('div');
        t.className = `toast ${type}`;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 3500);
    }
    // ═══════════════════════════════════════
    // HỦY LỘ TRÌNH
    // ═══════════════════════════════════════
    async function cancelPlan() {
        if (!confirm("⚠️ Bạn có chắc chắn muốn hủy bỏ lộ trình đang tập không? Mọi tiến độ của lộ trình này sẽ bị xóa sạch!")) return;

        try {
            const res = await fetch(`${AI_SERVER_URL}/api/cancel-plan/${USER_ID}`, {
                method: 'DELETE'
            });
            const result = await res.json();

            if (result.success) {
                showToast('Đã hủy lộ trình.', 'success');
                
                // Reset lại toàn bộ giao diện về trạng thái ban đầu
                currentPlanId = null;
                currentPlanData = null;
                
                // Ẩn thanh tiến độ
                document.getElementById('progressWrap').classList.remove('show');
                
                // Đưa bảng chính về rỗng
                document.getElementById('plan-container').innerHTML = `
                    <div class="empty-state">
                        <p>Đã hủy lộ trình. Hãy tạo lộ trình mới ở bảng bên trái.</p>
                    </div>`;
                    
                // Mở khóa lại nút Tạo lộ trình bên sidebar
                const btnGen = document.getElementById('btn-generate');
                btnGen.disabled = false;
                btnGen.innerText = '⚡ Tạo Lộ Trình Bằng AI';
                btnGen.style.opacity = '1';
                
            } else {
                showToast('Lỗi: ' + result.message, 'error');
            }
        } catch (e) {
            showToast('Lỗi kết nối máy chủ.', 'error');
        }
    }
    // Kiểm tra lúc vừa vào trang xem có Plan active không
    async function checkActivePlanOnLoad() {
        try {
            const res = await fetch(`${AI_SERVER_URL}/api/get-active-plan?userId=${USER_ID}`);
            const data = await res.json();

            if (data.plan) {
                // Đã có lộ trình đang chạy!
                currentPlanId = data.plan._id || data.plan.id;
                currentPlanData = data.plan.plan_data;
                
                document.getElementById('plan-title').innerText = "LỘ TRÌNH ĐANG THỰC HIỆN";
                
                // Vẽ lại giao diện từ JSON
                const container = document.getElementById('plan-container');
                renderPlan(currentPlanData, container, data.plan.daily_progress);
                appendPlanActions(container, currentPlanData);
                
                // Kích hoạt trạng thái Active (giống hệt lúc vừa bấm nút save)
                updateProgressBar(data.plan.days_done || 0, currentPlanData.duration_days);
                document.getElementById('plan-action-buttons').style.display = 'none';
                document.getElementById('btn-cancel-plan').classList.add('show');
                
                const btnGen = document.getElementById('btn-generate');
                btnGen.disabled = true;
                btnGen.innerText = 'LỘ TRÌNH ĐANG CHẠY';
                btnGen.style.opacity = '0.5';
            }
        } catch (e) {
            console.log("Không có lộ trình active hoặc server tắt");
        }
    }
    
    // Gọi hàm này khi load trang
    checkActivePlanOnLoad();
