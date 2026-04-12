document.addEventListener("DOMContentLoaded", function() {
    // 1. Nhìn lên thanh địa chỉ (URL) để lấy tên file hiện tại
    let path = window.location.pathname;
    let page = path.split("/").pop();
    
    // Nếu người dùng vào thẳng trang chủ (không có đuôi file)
    if (page === "" || page === "TrangChu.html") {
        page = "index.html";
    }

    // 2. Tìm tất cả các link trong thanh menu của bạn
    // (Đảm bảo HTML của bạn đang dùng class .nav-menu cho thanh điều hướng nhé)
    let menuLinks = document.querySelectorAll(".nav-menu ul li a");

    // 3. Quét từng link một
    menuLinks.forEach(function(link) {
        // Lấy đường dẫn của link đó (ví dụ: "bt.html", "lotrinh.html")
        let linkHref = link.getAttribute("href");

        // Nếu đường dẫn của link TRÙNG khớp với trang hiện tại
        if (linkHref === page) {
            // Thì nhét thêm class 'active-menu' vào để nó in đậm và gạch chân
            link.classList.add("active-menu");
        }
    });
});