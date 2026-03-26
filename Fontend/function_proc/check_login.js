document.addEventListener("DOMContentLoaded", () => {
    // 1. KIỂM TRA TRẠNG THÁI ĐĂNG NHẬP
    const userStr = localStorage.getItem('loggedInUser'); // Dữ liệu ta đã lưu lúc đăng nhập thành công
    const loginBtn = document.querySelector('.btn-signup'); // Tìm nút Đăng nhập/Đăng ký

    if (userStr && loginBtn) {
        // NẾU ĐÃ ĐĂNG NHẬP: Biến đổi chuỗi JSON thành Object
        const user = JSON.parse(userStr);

        // Tạo một vùng chứa mới gồm Tên và Nút Đăng xuất
        const userMenu = document.createElement('div');
        userMenu.style.display = 'flex';
        userMenu.style.alignItems = 'center';
        userMenu.style.gap = '15px';

        // Lấy fullName từ dữ liệu Database hiện lên
        userMenu.innerHTML = `
            <span style="color: #c6ff00; font-weight: 600; font-size: 15px;"> ${user.fullName}</span>
            <button id="logout-btn" style="background: transparent; border: 1px solid #fff; color: #fff; padding: 8px 16px; border-radius: 6px; cursor: pointer; transition: 0.3s;">
                Đăng xuất
            </button>
        `;

        // Đổi chỗ: Xóa nút Đăng nhập cũ, nhét vùng userMenu mới vào
        loginBtn.parentNode.replaceChild(userMenu, loginBtn);

        // Hiệu ứng hover cho nút đăng xuất (cho đẹp)
        const logoutBtn = document.getElementById('logout-btn');
        logoutBtn.addEventListener('mouseover', () => logoutBtn.style.background = 'rgba(255,255,255,0.1)');
        logoutBtn.addEventListener('mouseout', () => logoutBtn.style.background = 'transparent');

        // BẮT SỰ KIỆN ĐĂNG XUẤT
        logoutBtn.addEventListener('click', () => {
            if(confirm("Bạn có chắc chắn muốn đăng xuất?")) {
                localStorage.removeItem('loggedInUser'); // Xóa trí nhớ trình duyệt
                localStorage.removeItem('token');
                window.location.href = 'index.html'; // Tải lại trang chủ (sẽ quay về dạng Khách)
            }
        });
    }

    // 2. CHẶN TÀI KHOẢN KHÁCH NHẤN VÀO CÁC TRANG KHÁC
    // Tìm tất cả các link trong menu điều hướng
    const navLinks = document.querySelectorAll('.nav-menu a');
    
    navLinks.forEach(link => {
        // Bỏ qua trang chủ, chỉ bắt lỗi các trang khác (Bài tập, Lộ trình...)
        if (!link.href.includes('index.html')) {
            link.addEventListener('click', (e) => {
                // Nếu chưa đăng nhập (không có dữ liệu trong localStorage)
                if (!localStorage.getItem('loggedInUser')) {
                    e.preventDefault(); // Chặn không cho nhảy trang
                    
                    alert('🔒 Vui lòng đăng nhập để sử dụng tính năng này!');
                    // Tự động đẩy khách sang trang đăng nhập
                    window.location.href = 'dangnhap.html'; 
                }
            });
        }
    });
});