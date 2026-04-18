// ============================================================================
// NÚT QUAY LẠI TRANG QUẢN TRỊ (HIỂN THỊ MỌI TRANG, BÊN PHẢI NÚT SÁNG/TỐI)
// ============================================================================
document.addEventListener("DOMContentLoaded", () => {
    try {
        const userStr = localStorage.getItem("loggedInUser");
        if (userStr) {
            const userObj = JSON.parse(userStr);
            
            // Kiểm tra xem có phải là Admin không
            if (userObj.role === "admin") {
                
                // Kiểm tra xem nút đã được tạo chưa (chống tạo trùng lặp)
                if (document.getElementById("btnBackToAdmin")) return;
                
                // 1. Tạo nút
                const adminBtn = document.createElement("button");
                adminBtn.innerHTML = "🛡️ Quản Trị";
                adminBtn.id = "btnBackToAdmin";
                adminBtn.className = "admin-btn";
                
                // Chú ý sửa lại link này cho đúng file quản trị của bạn nhé
                adminBtn.onclick = () => {
                    window.location.href = "admin.html"; 
                };

                // 2. Trang trí CSS cho nút
                Object.assign(adminBtn.style, {
                    padding: "6px 14px", 
                    background: "transparent",          // đổi từ đỏ -> trong suốt
                    color: "var(--accent)",             // màu chữ theo accent
                    border: "1px solid var(--accent)",  // viền theo accent
                    borderRadius: "6px", 
                    fontFamily: "inherit",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: "pointer",
                    marginLeft: "12px",
                    transition: "0.3s",                 // dùng luôn của dưới
                    display: "flex",
                    alignItems: "center",
                    gap: "6px"
                });
                // Hiệu ứng di chuột
                adminBtn.onmouseover = () => { 
                    adminBtn.style.backgroundColor = "#5a79e7"; 
                    adminBtn.style.color = "#324792"; 
                };
                

                // 3. Tìm nút Sáng/Tối và chèn vào BÊN PHẢI
                const themeBtn = document.getElementById("themeToggle");
                
                if (themeBtn) {
                    // Dùng 'afterend' để chèn nút Admin vào NGAY SAU nút Mặt trăng
                    themeBtn.insertAdjacentElement('afterend', adminBtn);
                } else {
                    console.warn("Không tìm thấy nút Sáng/Tối");
                }
            }
        }
    } catch (e) {
        console.error("Lỗi hiển thị nút Admin:", e);
    }
});