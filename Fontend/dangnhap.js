const container  = document.getElementById('container');
const registerBtn = document.getElementById('register');
const loginBtn    = document.getElementById('login');

// Chuyển sang form Đăng ký
registerBtn.addEventListener('click', () => container.classList.add('active'));

// Chuyển về form Đăng nhập
loginBtn.addEventListener('click', () => container.classList.remove('active'));

/* ── Hiện / Ẩn mật khẩu ── */
function togglePass(id, btn) {
    const input = document.getElementById(id);
    const isHidden = input.type === 'password';
    input.type = isHidden ? 'text' : 'password';
    btn.innerHTML = isHidden
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
               <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8
                        a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4
                        c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19
                        m-6.72-1.07a3 3 0 11-4.24-4.24"/>
               <line x1="1" y1="1" x2="23" y2="23"/>
           </svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
               <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
               <circle cx="12" cy="12" r="3"/>
           </svg>`;
}

/* ── Xử lý Đăng nhập ── */
function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const pass  = document.getElementById('login-pass').value;

    if (!email || !pass) {
        alert('Vui lòng nhập đầy đủ email và mật khẩu.');
        return false;
    }
    alert(`Đăng nhập thành công!\nEmail: ${email}`);
    return false;
}

/* ── Xử lý Đăng ký ── */
function handleRegister(e) {
    e.preventDefault();

    const name     = document.getElementById('reg-name').value.trim();
    const age      = parseInt(document.getElementById('reg-age').value);
    const username = document.getElementById('reg-username').value.trim();
    const pass     = document.getElementById('reg-pass').value;
    const confirm  = document.getElementById('reg-confirm').value;
    const gender   = document.querySelector('input[name="gender"]:checked');

    if (!name) {
        alert('Vui lòng nhập họ và tên.');
        return false;
    }
    if (!age || age < 1 || age > 120) {
        alert('Vui lòng nhập tuổi hợp lệ (1–120).');
        return false;
    }
    if (!gender) {
        alert('Vui lòng chọn giới tính.');
        return false;
    }
    if (!username) {
        alert('Vui lòng nhập tên tài khoản.');
        return false;
    }
    if (pass.length < 8) {
        alert('Mật khẩu phải có ít nhất 8 ký tự.');
        return false;
    }
    if (pass !== confirm) {
        alert('Mật khẩu xác nhận không khớp!');
        return false;
    }

    alert(`Đăng ký thành công!\nTên: ${name}\nTuổi: ${age}\nGiới tính: ${gender.value}\nTài khoản: ${username}`);

    // Quay về form đăng nhập sau khi đăng ký
    container.classList.remove('active');
    return false;
}