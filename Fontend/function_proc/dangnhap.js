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

    // 3. Gửi yêu cầu lên Backend
   // --- GỬI DỮ LIỆU VÀO DATABASE VÀ BẮT LỖI HỆ THỐNG ---
    try {
        const response = await fetch('http://127.0.0.1:5000/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fullName: name,
                age: age,
                gender: gender.value,
                username: username,
                email: email,
                password: pass
            })
        });

        // Xử lý dữ liệu trả về từ backend
        const result = await response.json();

        if (response.ok) { 
            alert("🎉 Đăng nhập thành công! Đang chuyển hướng...");
            
            // Lưu thông tin user vào bộ nhớ
            localStorage.setItem("loggedInUser", JSON.stringify(result.user));
            if(result.token) localStorage.setItem('token', result.token);
            
            // LẼ TẺ: KIỂM TRA ROLE ĐỂ CHUYỂN TRANG
            if (result.user.role === 'admin') {
                window.location.href = "admin.html"; // Sếp về trang quản lý
            } else {
                window.location.href = "index.html"; // Khách về trang chủ
            }
            
        } else {
            // TÁCH RIÊNG CÁC LỖI TỪ DATABASE / BACKEND
            if (response.status === 400 || response.status === 409) {
                // Lỗi 400/409: Thường do Backend báo về khi bị trùng Username hoặc Email trong Database
                alert("⚠️ Thông tin đã tồn tại: " + result.message);
                
            } else if (response.status === 500) {
                // Lỗi 500: Database bị sập, sai tài khoản MongoDB, hoặc lỗi code Python
                alert("❌ Lỗi Hệ Thống Database: Server không thể xử lý yêu cầu lúc này. Vui lòng thử lại sau!");
                console.error("Chi tiết lỗi Server (500):", result);
                
            } else {
                // Các lỗi từ chối khác (401, 403, 404...)
                alert("❌ Lỗi không xác định: " + (result.message || "Vui lòng liên hệ Admin."));
            }
        }
        
    } catch (error) {
        console.error("Chi tiết lỗi Network/Connection:", error);

        // 1. LỖI MẤT KẾT NỐI INTERNET CỦA NGƯỜI DÙNG
        if (!navigator.onLine) {
            alert("🌐 Lỗi mạng: Thiết bị của bạn đang ngoại tuyến. Vui lòng kiểm tra lại kết nối Wi-Fi/4G!");
            return false;
        }

        // 2. LỖI KHÔNG TÌM THẤY MÁY CHỦ (SERVER TẮT HOẶC SAI ĐỊA CHỈ)
        // Thường xuất hiện dưới dạng TypeError: Failed to fetch
        if (error.name === 'TypeError') {
    alert(`🔌 Lỗi kết nối mạng!
            Nguyên nhân:
            - Không kết nối được tới server
            - Server chưa chạy (python app.py)
            - Sai IP hoặc cổng
            `);
                return false;
            }

if (error.message && error.message.includes('Failed to fetch')) {
    alert(`🚫 Request đã gửi nhưng bị thất bại!
        Nguyên nhân:
        - Bị chặn CORS
        - API không tồn tại
        - HTTPS gọi HTTP bị block
        `);
            return false;
        }
                // 3. LỖI QUÁ THỜI GIAN (TIMEOUT)
        // Xảy ra nếu sau này bạn dùng AbortController để giới hạn thời gian request
        if (error.name === 'AbortError') {
            alert("⏳ Quá thời gian kết nối! Máy chủ phản hồi quá chậm, vui lòng thử lại sau.");
            return false;
        }

        // 4. CÁC LỖI NGOẠI LỆ KHÁC
        alert("⚠️ Đã xảy ra sự cố không xác định khi kết nối: " + error.message);
    }
}

/* ── Xử lý Đăng nhập ── */
async function handleLogin(e) {
    e.preventDefault();
    
    // 1. SỬA LẠI ID: Trỏ đúng vào id="login-email" của file HTML
    const email = document.getElementById('login-email').value.trim();
    const pass = document.getElementById('login-pass').value;
    
    try {
        const response = await fetch('http://127.0.0.1:5000/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // 2. SỬA LẠI DỮ LIỆU GỬI ĐI: Gửi 'email' thay vì 'username'
            body: JSON.stringify({ email: email, password: pass }) 
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert("🎉 Đăng nhập thành công!");
            
            // Lưu dữ liệu vào localStorage (Bạn có thể lưu token hoặc thông tin user)
            // Lát nữa trang index.html sẽ đọc cái này để biết ai đang đăng nhập
            if(result.token) localStorage.setItem('token', result.token);
            if(result.user) localStorage.setItem('loggedInUser', JSON.stringify(result.user));
            
            // 3. LỆNH NHẢY TRANG CHỦ
            window.location.href = 'index.html';
            
        } else {
            alert("⚠️ Đăng nhập thất bại: " + (result.message || "Sai thông tin"));
        }
    } catch (error) {
        console.error("Chi tiết lỗi Đăng nhập:", error);
        alert("❌ Lỗi kết nối khi đăng nhập. Vui lòng thử lại sau!");
    }
}

// Gắn sự kiện cho form Đăng ký và Đăng nhập
document
  .getElementById('register-form')
  .addEventListener('submit', function(e) {
    e.preventDefault();
    handleRegister(e);
  });

document
  .getElementById('login-form')
  .addEventListener('submit', function(e) {
    e.preventDefault();
    handleLogin(e);
  });