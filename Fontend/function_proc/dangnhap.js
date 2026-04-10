const container  = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn    = document.getElementById('login');

// Chuyển sang form Đăng ký
registerBtn.addEventListener('click', () => container.classList.add('active'));

// Chuyển về form Đăng nhập
loginBtn.addEventListener('click', () => container.classList.remove('active'));

/* ── Xử lý Đăng ký ── */
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
        alert("Mật khẩu xác nhận không khớp!");
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
            // ĐĂNG KÝ XONG THÌ BÁO THÀNH CÔNG VÀ QUAY VỀ FORM ĐĂNG NHẬP
            alert("🎉 Đăng ký thành công! Vui lòng đăng nhập.");
            e.target.reset(); 
            container.classList.remove('active'); 
        } else {
            if (response.status === 400 || response.status === 409) {
                alert("⚠️ Thông tin đã tồn tại: " + result.message);
            } else if (response.status === 500) {
                alert("❌ Lỗi Hệ Thống Database!");
            } else {
                alert("❌ Lỗi: " + (result.message || "Vui lòng liên hệ Admin."));
            }
        }
    } catch (error) {
        console.error("Lỗi Network:", error);
        if (!navigator.onLine) {
            alert("🌐 Lỗi mạng: Đang ngoại tuyến!");
        } else {
            alert("🔌 Không thể kết nối tới server. Vui lòng bật Backend (app.py)!");
        }
    }
}

/* ── Xử lý Đăng nhập ── */
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
            alert("🎉 Đăng nhập thành công!");
            
            // Lưu dữ liệu
            if(result.token) localStorage.setItem('token', result.token);
            if(result.user) localStorage.setItem('loggedInUser', JSON.stringify(result.user));
            
            // KIỂM TRA ROLE ĐỂ CHUYỂN TRANG (ĐẶT Ở ĐÂY MỚI ĐÚNG!)
            if (result.user && result.user.role === 'admin') {
                window.location.href = 'admin.html'; // Sếp về trang quản lý
            } else {
                window.location.href = 'index.html'; // Khách về trang chủ
            }
            
        } else {
            alert("⚠️ Đăng nhập thất bại: " + (result.message || "Sai thông tin"));
        }
    } catch (error) {
        console.error("Chi tiết lỗi Đăng nhập:", error);
        alert("❌ Lỗi kết nối khi đăng nhập. Vui lòng kiểm tra lại Backend!");
    }
}

// Gắn sự kiện
document.getElementById('register-form').addEventListener('submit', handleRegister);
document.getElementById('login-form').addEventListener('submit', handleLogin);