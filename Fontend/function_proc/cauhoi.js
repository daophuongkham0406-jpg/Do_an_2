const API_FAQ = 'http://127.0.0.1:5000/api/faq';
const API_ABOUT = 'http://127.0.0.1:5000/api/about-features';
const API_CONTACTS = 'http://127.0.0.1:5000/api/contacts';
let faqData = []; // Biến lưu trữ toàn bộ câu hỏi

document.addEventListener("DOMContentLoaded", () => {
    initScrollReveal();
    loadPageData(); 
    setupCategoryFilters();
});

// 1. KHỞI TẠO HIỆU ỨNG CUỘN (SCROLL REVEAL)
function initScrollReveal() {
    const reveals = document.querySelectorAll(".reveal");
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
            }
        });
    }, { threshold: 0.12 });
    reveals.forEach((el) => observer.observe(el));
}

// 2. GỌI CÙNG LÚC 3 API (ABOUT, CONTACTS VÀ FAQ)
async function loadPageData() {
    try {
        // --- TẢI DỮ LIỆU ĐẶC ĐIỂM NỔI BẬT ---
        const resAbout = await fetch(API_ABOUT).then(r => r.json()).catch(() => null);
        const aboutGrid = document.getElementById('about-features-grid');
        
        if (aboutGrid && resAbout && resAbout.success) {
            aboutGrid.innerHTML = resAbout.data.map((item, i) => `
                <div class="about-card reveal visible" style="animation-delay: ${(i % 3) * 0.1}s">
                    <span class="about-icon">${item.icon || '📌'}</span>
                    <h3>${item.title}</h3>
                    <p>${item.description}</p>
                </div>
            `).join('');
        }

        // --- TẢI DỮ LIỆU LIÊN HỆ (Đã được đưa vào đúng chỗ) ---
        const resContact = await fetch(API_CONTACTS).then(r => r.json()).catch(() => null);
        const contactGrid = document.getElementById('contact-grid');
        
        if (contactGrid && resContact && resContact.success) {
            contactGrid.innerHTML = resContact.data.map((item, i) => `
                <div class="contact-card reveal visible" style="animation-delay: ${i * 0.1}s">
                    <div class="contact-icon-wrap">${item.icon || '📞'}</div>
                    <div>
                        <h4>${item.title}</h4>
                        <p>${item.description}</p>
                        <span class="contact-link">${item.link_text || ''}</span>
                    </div>
                </div>
            `).join('');
        }

        // --- TẢI DỮ LIỆU CÂU HỎI (FAQ) ---
        const resFaq = await fetch(API_FAQ).then(r => r.json()).catch(() => null);
        if (resFaq && resFaq.success) {
            faqData = resFaq.data;
            renderFAQ('all'); // Mặc định hiển thị tất cả câu hỏi
        } else {
            document.getElementById('faqList').innerHTML = '<p style="color:var(--text-muted); padding: 20px;">Không thể tải câu hỏi lúc này.</p>';
        }
    } catch (e) {
        console.error("Lỗi khi tải dữ liệu:", e);
    }
}

// 3. VẼ DANH SÁCH CÂU HỎI RA MÀN HÌNH (CÓ LỌC THEO TAB)
function renderFAQ(category) {
    const list = document.getElementById('faqList');
    if (!list) return;

    // Lọc dữ liệu theo Category
    let filteredData = faqData;
    if (category !== 'all') {
        filteredData = faqData.filter(item => item.cat === category);
    }

    if (filteredData.length === 0) {
        list.innerHTML = '<p style="color:var(--text-muted); padding: 20px;">Chưa có câu hỏi nào trong danh mục này.</p>';
        return;
    }

    // Đổ HTML Câu hỏi
    list.innerHTML = filteredData.map((item, i) => `
        <div class="accordion-item reveal visible" style="animation-delay: ${i * 0.05}s">
            <button class="accordion-header">
                <div class="faq-q-header">
                    <span class="faq-tag">${item.tag || 'Chung'}</span>
                    ${item.question}
                </div>
                <span class="acc-icon">+</span>
            </button>
            <div class="accordion-content">
                <div class="acc-inner">
                    <p>${item.answer}</p>
                </div>
            </div>
        </div>
    `).join('');

    // Phải gán lại sự kiện Đóng/Mở sau khi vẽ xong HTML mới
    attachAccordionEvents();
}

// 4. XỬ LÝ SỰ KIỆN CLICK ĐÓNG/MỞ CÂU HỎI
function attachAccordionEvents() {
    const accordions = document.querySelectorAll(".accordion-header");
    accordions.forEach((acc) => {
        acc.onclick = function () {
            const item = this.parentElement;
            // Đóng các mục khác đang mở
            document.querySelectorAll(".accordion-item").forEach((otherItem) => {
                if (otherItem !== item) {
                    otherItem.classList.remove("open");
                }
            });
            // Bật/tắt mục hiện tại
            item.classList.toggle("open");
        };
    });
}

// 5. XỬ LÝ SỰ KIỆN CHUYỂN TAB DANH MỤC Ở SIDEBAR
function setupCategoryFilters() {
    const catButtons = document.querySelectorAll('.faq-cat');
    catButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Xóa class active ở tất cả các nút
            catButtons.forEach(b => b.classList.remove('active'));
            // Thêm class active cho nút vừa bấm
            this.classList.add('active');
            
            // Lấy ID danh mục và gọi hàm render lại
            const catId = this.getAttribute('data-cat');
            renderFAQ(catId);
        });
    });
}