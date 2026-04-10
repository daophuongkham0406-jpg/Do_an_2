const container   = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn    = document.getElementById('login');

// Chuyển sang form Đăng ký
registerBtn.addEventListener('click', () => container.classList.add('active'));

// Chuyển về form Đăng nhập
loginBtn.addEventListener('click', () => container.classList.remove('active'));

// ============================================================================
// HÀM HIỂN THỊ THÔNG BÁO (TOAST) THAY THẾ ALERT
// ============================================================================
function showToast(msg, type = 'info') {
    const wrap = document.getElementById('toastWrap');
    if (!wrap) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    
    let icon = 'ℹ️';
    if(type === 'success') icon = '✅';
    if(type === 'error') icon = '❌';

    t.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
    wrap.appendChild(t);
    
    requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('show')));
    
    // Tự động tắt sau 3 giây
    setTimeout(() => { 
        t.classList.remove('show'); 
        setTimeout(() => t.remove(), 400); 
    }, 2000);
}


// ============================================================================
// XỬ LÝ ĐĂNG KÝ
// ============================================================================
async function handleRegister(e) {
    e.preventDefault();

    const name = document.getElementById('reg-name').value.trim();
    const age = parseInt(document.getElementById('reg-age').value);
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim(); 
    const pass = document.getElementById('reg-pass').value;
    const confirm = document.getElementById('reg-confirm').value;
    const gender = document.querySelector('input[name="gender"]:checked');

    if(pass !== confirm) {
        showToast("Mật khẩu xác nhận không khớp!", "error");
        return false;
    }

    try {
        const response = await fetch('http://127.0.0.1:5000/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                fullName: name,
                age: age,
                gender: gender ? gender.value : 'khac',
                username: username,
                email: email,
                password: pass
            })
        });

        const result = await response.json();

        if (response.ok) { 
            // Báo thành công và quay về form đăng nhập
            showToast("🎉 Đăng ký thành công! Vui lòng đăng nhập.", "success");
            e.target.reset(); 
            container.classList.remove('active'); 
        } else {
            if (response.status === 400 || response.status === 409) {
                showToast("⚠️ Thông tin đã tồn tại: " + result.message, "error");
            } else if (response.status === 500) {
                showToast("❌ Lỗi Hệ Thống Database!", "error");
            } else {
                showToast("❌ Lỗi: " + (result.message || "Vui lòng liên hệ Admin."), "error");
            }
        }
    } catch (error) {
        console.error("Lỗi Network:", error);
        if (!navigator.onLine) {
            showToast("🌐 Lỗi mạng: Đang ngoại tuyến!", "error");
        } else {
            showToast("🔌 Không thể kết nối tới server. Vui lòng bật Backend (app.py)!", "error");
        }
    }
}


// ============================================================================
// XỬ LÝ ĐĂNG NHẬP
// ============================================================================
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value.trim();
    const pass = document.getElementById('login-pass').value;
    
    try {
        const response = await fetch('http://127.0.0.1:5000/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: pass }) 
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast("🎉 Đăng nhập thành công!", "success");
            
            // Lưu dữ liệu
            if(result.token) localStorage.setItem('token', result.token);
            if(result.user) localStorage.setItem('loggedInUser', JSON.stringify(result.user));
            
            // TRÌ HOÃN 1.5 GIÂY ĐỂ HIỆN THÔNG BÁO RỒI MỚI CHUYỂN TRANG
            setTimeout(() => {
                if (result.user && result.user.role === 'admin') {
                    window.location.href = 'admin.html'; // Admin về trang quản lý
                } else {
                    window.location.href = 'index.html'; // User về trang chủ
                }
            }, 1500);
            
        } else {
            showToast("⚠️ Đăng nhập thất bại: " + (result.message || "Sai thông tin"), "error");
        }
    } catch (error) {
        console.error("Chi tiết lỗi Đăng nhập:", error);
        showToast("❌ Lỗi kết nối khi đăng nhập. Vui lòng kiểm tra lại Backend!", "error");
    }
}

// Gắn sự kiện
document.getElementById('register-form').addEventListener('submit', handleRegister);
document.getElementById('login-form').addEventListener('submit', handleLogin);