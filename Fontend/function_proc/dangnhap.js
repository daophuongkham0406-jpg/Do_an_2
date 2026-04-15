const container = document.getElementById("container");
const registerBtn = document.getElementById("register");
const loginBtn = document.getElementById("login");

// Chuyển sang form Đăng ký
registerBtn.addEventListener("click", () => container.classList.add("active"));

// Chuyển về form Đăng nhập
loginBtn.addEventListener("click", () => container.classList.remove("active"));

// ============================================================================
// TÍNH NĂNG ẨN/HIỆN MẬT KHẨU (FORM CHÍNH)
// ============================================================================
const eyeButtons = document.querySelectorAll(".eye-btn");
eyeButtons.forEach((btn) => {
  btn.addEventListener("click", function () {
    const input = this.previousElementSibling;
    if (input.type === "password") {
      input.type = "text";
      this.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
    } else {
      input.type = "password";
      this.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
    }
  });
});

// ============================================================================
// HÀM HIỂN THỊ THÔNG BÁO (TOAST)
// ============================================================================
function showToast(msg, type = "info") {
  const wrap = document.getElementById("toastWrap");
  if (!wrap) return;
  const t = document.createElement("div");
  t.className = `toast ${type}`;

  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "error") icon = "❌";

  t.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
  wrap.appendChild(t);

  requestAnimationFrame(() =>
    requestAnimationFrame(() => t.classList.add("show")),
  );

  setTimeout(() => {
    t.classList.remove("show");
    setTimeout(() => t.remove(), 400);
  }, 2500);
}

// ============================================================================
// XỬ LÝ ĐĂNG KÝ
// ============================================================================
async function handleRegister(e) {
  e.preventDefault();

  const name = document.getElementById("reg-name").value.trim();
  const age = parseInt(document.getElementById("reg-age").value);
  const username = document.getElementById("reg-username").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const pass = document.getElementById("reg-pass").value;
  const confirm = document.getElementById("reg-confirm").value;
  const gender = document.querySelector('input[name="gender"]:checked');

  // Kiểm tra mật khẩu mạnh bằng Regex
  const passRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
  if (!passRegex.test(pass)) {
    return showToast(
      "⚠️ Mật khẩu phải từ 8 ký tự, gồm ít nhất 1 chữ hoa, 1 chữ thường và 1 số!",
      "error",
    );
  }

  if (pass !== confirm) {
    return showToast("Mật khẩu xác nhận không khớp!", "error");
  }

  try {
    const response = await fetch("http://127.0.0.1:5000/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fullName: name,
        age: age,
        gender: gender ? gender.value : "khac",
        username: username,
        email: email,
        password: pass,
      }),
    });

    const result = await response.json();

    if (response.ok) {
      showToast("Đang gửi mã OTP đến email...", "info");
      window.tempRegEmail = email;
      document.getElementById("verify-email-display").innerText = email;
      document.getElementById("otp-modal").classList.add("show");
      startCountdown("reg-countdown", "resend-reg-otp");
    } else {
      if (response.status === 400 || response.status === 409) {
        showToast("⚠️ Thông tin đã tồn tại: " + result.message, "error");
      } else {
        showToast(
          "❌ Lỗi: " + (result.message || "Vui lòng liên hệ Admin."),
          "error",
        );
      }
    }
  } catch (error) {
    showToast(
      "🔌 Không thể kết nối tới server. Vui lòng bật Backend!",
      "error",
    );
  }
}

// ============================================================================
// XỬ LÝ ĐĂNG NHẬP
// ============================================================================
async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const pass = document.getElementById("login-pass").value;

  try {
    const response = await fetch("http://127.0.0.1:5000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: pass }),
    });

    const result = await response.json();

    if (response.ok) {
      showToast("🎉 Đăng nhập thành công!", "success");
      if (result.token) localStorage.setItem("token", result.token);
      if (result.user)
        localStorage.setItem("loggedInUser", JSON.stringify(result.user));
      if (result.user)
        localStorage.setItem("userId", result.user._id || result.user.id);

      setTimeout(() => {
        if (result.user && result.user.role === "admin") {
          window.location.href = "admin.html";
        } else {
          window.location.href = "index.html";
        }
      }, 1500);
    } else {
      showToast(
        "⚠️ Đăng nhập thất bại: " + (result.message || "Sai thông tin"),
        "error",
      );
    }
  } catch (error) {
    showToast(
      "❌ Lỗi kết nối khi đăng nhập. Vui lòng kiểm tra lại Backend!",
      "error",
    );
  }
}

document
  .getElementById("register-form")
  .addEventListener("submit", handleRegister);
document.getElementById("login-form").addEventListener("submit", handleLogin);

// ============================================================================
// HỆ THỐNG XỬ LÝ OTP (ĐĂNG KÝ & QUÊN MẬT KHẨU)
// ============================================================================

function startCountdown(timerId, btnId) {
  let timeLeft = 60;
  const timerSpan = document.getElementById(timerId);
  const resendBtn = document.getElementById(btnId);
  resendBtn.classList.remove("active");

  const interval = setInterval(() => {
    timeLeft--;
    timerSpan.innerText = timeLeft;
    if (timeLeft <= 0) {
      clearInterval(interval);
      timerSpan.innerText = "0";
      resendBtn.classList.add("active");
    }
  }, 1000);
}

// --- LUỒNG 1: XÁC THỰC OTP ĐĂNG KÝ ---
const otpModal = document.getElementById("otp-modal");
document
  .getElementById("close-otp")
  .addEventListener("click", () => otpModal.classList.remove("show"));

document
  .getElementById("btn-verify-reg")
  .addEventListener("click", async () => {
    const otpCode = document.getElementById("reg-otp-input").value.trim();
    if (otpCode.length !== 6)
      return showToast("⚠️ Vui lòng nhập đủ 6 số OTP", "error");

    try {
      const res = await fetch(
        "http://127.0.0.1:5000/api/auth/verify-registration",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: window.tempRegEmail, otp: otpCode }),
        },
      );

      if (res.ok) {
        showToast("🎉 Xác thực thành công! Bạn có thể đăng nhập.", "success");
        otpModal.classList.remove("show");
        document.getElementById("register-form").reset();
        container.classList.remove("active");
      } else {
        showToast("❌ Mã OTP không đúng hoặc đã hết hạn!", "error");
      }
    } catch (err) {
      showToast("Lỗi kết nối máy chủ!", "error");
    }
  });

// --- LUỒNG 2: QUÊN MẬT KHẨU (2 BƯỚC) ---
const forgotModal = document.getElementById("forgot-modal");
document.getElementById("forgot-link").addEventListener("click", (e) => {
  e.preventDefault();
  forgotModal.classList.add("show");
  document.getElementById("forgot-step-1").style.display = "block";
  document.getElementById("forgot-step-2").style.display = "none";
});
document
  .getElementById("close-forgot")
  .addEventListener("click", () => forgotModal.classList.remove("show"));

// BƯỚC 1: GỬI YÊU CẦU LẤY OTP
document
  .getElementById("btn-send-reset")
  .addEventListener("click", async () => {
    const email = document.getElementById("forgot-email").value.trim();
    if (!email) return showToast("⚠️ Nhập email của bạn!", "error");

    const btn = document.getElementById("btn-send-reset");
    btn.innerText = "Đang gửi...";
    btn.disabled = true;

    try {
      const res = await fetch(
        "http://127.0.0.1:5000/api/auth/forgot-password",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email }),
        },
      );

      if (res.ok) {
        window.tempResetEmail = email;
        showToast("✅ Đã gửi mã OTP. Vui lòng kiểm tra email!", "success");
        document.getElementById("forgot-step-1").style.display = "none";
        document.getElementById("forgot-step-2").style.display = "block";
      } else {
        showToast("⚠️ Email không tồn tại trong hệ thống!", "error");
      }
    } catch (err) {
      showToast("❌ Lỗi mạng!", "error");
    } finally {
      btn.innerText = "Gửi mã OTP";
      btn.disabled = false;
    }
  });

// BƯỚC 2: CẬP NHẬT MẬT KHẨU MỚI BẰNG OTP
document
  .getElementById("btn-confirm-reset")
  .addEventListener("click", async () => {
    const otpCode = document.getElementById("reset-otp").value.trim();
    const newPass = document.getElementById("reset-new-pass").value;
    const confirmPass = document.getElementById("reset-confirm-pass").value;

    if (otpCode.length !== 6)
      return showToast("⚠️ Mã OTP phải gồm 6 số!", "error");

    // Kiểm tra mật khẩu mạnh bằng Regex
    const passRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
    if (!passRegex.test(newPass)) {
      return showToast(
        "⚠️ Mật khẩu phải từ 8 ký tự, gồm ít nhất 1 chữ hoa, 1 chữ thường và 1 số!",
        "error",
      );
    }

    if (newPass !== confirmPass)
      return showToast("⚠️ Mật khẩu xác nhận không khớp!", "error");

    try {
      const res = await fetch("http://127.0.0.1:5000/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: window.tempResetEmail,
          otp: otpCode,
          newPassword: newPass,
        }),
      });

      if (res.ok) {
        showToast(
          "🎉 Đổi mật khẩu thành công! Vui lòng đăng nhập lại.",
          "success",
        );
        forgotModal.classList.remove("show");
        document.getElementById("forgot-email").value = "";
        document.getElementById("reset-otp").value = "";
        document.getElementById("reset-new-pass").value = "";
        document.getElementById("reset-confirm-pass").value = "";
      } else {
        showToast("❌ Mã OTP sai hoặc hết hạn!", "error");
      }
    } catch (err) {
      showToast("❌ Lỗi mạng!", "error");
    }
  });

// THIẾT LẬP LẠI TÍNH NĂNG CON MẮT CHO MODAL THEO DOM
document.querySelector("#forgot-modal").addEventListener("click", function (e) {
  if (e.target.closest(".eye-btn")) {
    const btn = e.target.closest(".eye-btn");
    const input = btn.previousElementSibling;
    if (input.type === "password") {
      input.type = "text";
      btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
    } else {
      input.type = "password";
      btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
    }
  }
});
