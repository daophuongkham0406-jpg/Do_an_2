document.addEventListener("DOMContentLoaded", () => {
  // ========================================================================
  // 0. TỰ ĐỘNG BƠM GIAO DIỆN THÔNG BÁO (TOAST) VÀO MỌI TRANG
  // ========================================================================
  if (!document.getElementById("global-toast-style")) {
    const style = document.createElement("style");
    style.id = "global-toast-style";
    style.innerHTML = `
            .toast-wrap { position: fixed; bottom: 30px; right: 30px; z-index: 99999; display: flex; flex-direction: column; gap: 12px; }
            .toast { background-color: #1d1e25; color: #ffffff; border-left: 4px solid #7241ff; padding: 16px 24px; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 12px; transform: translateX(120%); opacity: 0; transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55); }
            .toast.show { transform: translateX(0); opacity: 1; }
            .toast.success { border-left-color:var(--accent); }
            .toast.error { border-left-color: #ff4d4d; }
        `;
    document.head.appendChild(style);
  }

  if (!document.getElementById("toastWrap")) {
    const tw = document.createElement("div");
    tw.id = "toastWrap";
    tw.className = "toast-wrap";
    document.body.appendChild(tw);
  }

  function showToast(msg, type = "info") {
    const wrap = document.getElementById("toastWrap");
    const t = document.createElement("div");
    t.className = `toast ${type}`;
    let icon = "ℹ️";
    if (type === "error") icon = "❌";
    if (type === "success") icon = "✅";

    t.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
    wrap.appendChild(t);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => t.classList.add("show")),
    );
    setTimeout(() => {
      t.classList.remove("show");
      setTimeout(() => t.remove(), 400);
    }, 2000);
  }

  // ========================================================================
  // 1. KIỂM TRA TRẠNG THÁI ĐĂNG NHẬP VÀ ĐỔI MENU
  // ========================================================================
  const userStr = localStorage.getItem("loggedInUser");
  const loginBtn = document.querySelector(".btn-signup");

  if (userStr && loginBtn) {
    const user = JSON.parse(userStr);
    refreshLoggedInUser(user);

    const userMenu = document.createElement("div");
    userMenu.style.display = "flex";
    userMenu.style.alignItems = "center";
    userMenu.style.gap = "15px";

    // Lấy fullName, thiết kế nút đăng xuất màu Vàng Neon
    userMenu.innerHTML = `
            <a href="Tcn.html" id="profile-link" style="color: #ffffff; font-weight: 600; font-size: 14px; text-decoration: none; cursor: pointer; transition: 0.3s;">
                <span style="color:var(--accent)">${user.fullName}</span>
            </a>
            ${user.role === "admin" ? `
            <button id="admin-switch-btn" style="background: var(--accent); border: 1px solid var(--accent); color:#000; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 700; transition: all 0.3s;">
                Quản trị
            </button>` : ""}
            <button id="logout-btn" style="background: transparent; border: 1px solidvar(--accent); color:var(--accent); padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                Đăng xuất
            </button>
        `;

    // Thay nút Đăng nhập bằng Menu User
    loginBtn.parentNode.replaceChild(userMenu, loginBtn);

    // Hiệu ứng hover cho nút Đăng xuất
    const adminSwitchBtn = document.getElementById("admin-switch-btn");
    if (adminSwitchBtn) {
      adminSwitchBtn.addEventListener("click", () => {
        window.location.href = "admin.html";
      });
    }

    // Hiệu ứng hover cho nút Đăng xuất
    const logoutBtn = document.getElementById("logout-btn");
    logoutBtn.addEventListener("mouseover", () => {
      logoutBtn.style.background = "var(--accent)";
      logoutBtn.style.color = "#000";
    });
    logoutBtn.addEventListener("mouseout", () => {
      logoutBtn.style.background = "transparent";
      logoutBtn.style.color = "var(--accent)";
    });

    // BẮT SỰ KIỆN ĐĂNG XUẤT (Thay confirm bằng thông báo mượt mà)
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("loggedInUser");
      localStorage.removeItem("token");

      showToast("👋 Đã đăng xuất thành công!", "success");

      // Đợi 1 giây để người dùng thấy thông báo rồi mới f5
      setTimeout(() => {
        window.location.href = "index.html";
      }, 1000);
    });
  }

  async function refreshLoggedInUser(user) {
    const userId = user?.id || user?._id;
    if (!userId) return;
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/users/${userId}`, {
        headers: { "X-User-Id": userId },
      });
      if (!res.ok) return;
      const freshUser = await res.json();
      const mergedUser = { ...user, ...freshUser };
      localStorage.setItem("loggedInUser", JSON.stringify(mergedUser));
      if (mergedUser.role === "admin" && !document.getElementById("admin-switch-btn")) {
        location.reload();
      }
    } catch (e) {
      console.warn("Không làm mới được quyền tài khoản:", e);
    }
  }

  // ========================================================================
  // 2. CHẶN TÀI KHOẢN KHÁCH NHẤN VÀO TRANG CẤM
  // ========================================================================
  const navLinks = document.querySelectorAll(".nav-menu a");

  // Khai báo các trang mà Khách được phép vào (Trang chủ, Giới thiệu)
  const publicPages = ["index.html", "GioiThieuCauHoi.html"];

  navLinks.forEach((link) => {
    // Kiểm tra xem link này có nằm trong danh sách publicPages không
    const isPublic = publicPages.some((page) => link.href.includes(page));

    if (!isPublic && link.href !== "" && link.href !== "#") {
      link.addEventListener("click", (e) => {
        if (!localStorage.getItem("loggedInUser")) {
          e.preventDefault();

          showToast("🔒 Vui lòng đăng nhập để sử dụng tính năng này!", "error");

          setTimeout(() => {
            window.location.href = "dangnhap.html";
          }, 1500);
        }
      });
    }
  });
});
