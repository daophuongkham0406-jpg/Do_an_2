document.addEventListener("DOMContentLoaded", () => {
  // 1. TỰ ĐỘNG IN ĐẬM MENU ĐANG CHỌN
  let path = window.location.pathname;
  let page = path.split("/").pop();
  if (page === "" || page === "TrangChu.html") page = "index.html";

  document.querySelectorAll(".nav-menu ul li a").forEach((link) => {
    if (link.getAttribute("href") === page) {
      link.classList.add("active-menu");
    }
  });

  // 2. NÚT BẤM ĐỔI MÀU SÁNG/TỐI
  const toggleBtn = document.getElementById("themeToggle");
  if (toggleBtn) {
    if (localStorage.getItem("theme") === "light") {
      document.body.classList.add("light-mode");
      toggleBtn.textContent = "☀️";
    } else {
      document.body.classList.remove("light-mode");
      toggleBtn.textContent = "🌙";
    }

    toggleBtn.addEventListener("click", () => {
      document.body.classList.toggle("light-mode");
      if (document.body.classList.contains("light-mode")) {
        toggleBtn.textContent = "☀️";
        localStorage.setItem("theme", "light");
      } else {
        toggleBtn.textContent = "🌙";
        localStorage.setItem("theme", "dark");
      }
    });
  }
});
