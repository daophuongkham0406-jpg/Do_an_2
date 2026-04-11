// ==========================================
// File: chat.js - Giao diện Chatbot AI PUMPD
// Kết nối với cổng 5002 (chat_ai.py)
// ==========================================

const CHAT_API_URL = "http://127.0.0.1:5002/api/chat";

// 1. MÃ HTML CỦA CHATBOT TÍCH HỢP
const chatbotHTML = `
    <button class="chatbot-toggler">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
    </button>

    <div class="chatbot-box">
        <header>
            <h2>AI Huấn Luyện Viên</h2>
            <span class="close-btn" style="cursor: pointer;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </span>
        </header>
        
        <ul class="chatbox">
            <li class="chat incoming">
                <p>Chào bạn! Mình là AI HLV cá nhân của PUMPD. Bạn muốn tìm bài tập nào, hay cần tư vấn lộ trình tập luyện hôm nay?</p>
            </li>
        </ul>

        <div class="chat-suggestions">
            <button class="suggestion-btn">Lên lộ trình Clean Bulk</button>
            <button class="suggestion-btn">Mục tiêu tăng 3kg cơ nạc</button>
            <button class="suggestion-btn">Gợi ý bài tập ngực hôm nay</button>
        </div>

        <div class="chat-input">
            <input type="text" placeholder="Nhập câu hỏi..." required>
            <span id="send-btn" style="cursor: pointer;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="var(--accent, #e8ff47)"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"></path></svg>
            </span>
        </div>
    </div>
`;

// 2. CHÈN TỰ ĐỘNG CHATBOT VÀO CUỐI TRANG WEB
document.body.insertAdjacentHTML("beforeend", chatbotHTML);

// 3. KHỞI TẠO CÁC BIẾN DOM
const chatbotToggler = document.querySelector(".chatbot-toggler");
const closeBtn = document.querySelector(".close-btn");
const chatbox = document.querySelector(".chatbox");
const chatInput = document.querySelector(".chat-input input");
const sendChatBtn = document.querySelector("#send-btn");
const suggestionBtns = document.querySelectorAll(".suggestion-btn");

// 4. CÁC HÀM XỬ LÝ
// Mở & Đóng khung chat
chatbotToggler.addEventListener("click", () => document.body.classList.toggle("show-chatbot"));
closeBtn.addEventListener("click", () => document.body.classList.remove("show-chatbot"));

// Hàm tạo thẻ chứa tin nhắn
const createChatLi = (message, className) => {
    const chatLi = document.createElement("li");
    chatLi.classList.add("chat", className);
    // Dùng textContent để an toàn, chống lỗi (XSS)
    const pTag = document.createElement("p");
    pTag.textContent = message; 
    chatLi.appendChild(pTag);
    return chatLi;
};

// Hàm kết nối với Server Python và trả lời
const generateResponse = async (incomingChatLi, userMessage) => {
    const messageElement = incomingChatLi.querySelector("p");
    
    try {
        const response = await fetch(CHAT_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: userMessage })
        });

        const data = await response.json();
        
        if (response.ok) {
            // Thay thế chữ "Đang suy nghĩ..." bằng câu trả lời của AI
            messageElement.textContent = data.reply;
        } else {
            messageElement.textContent = `Lỗi: ${data.error || "Không thể lấy câu trả lời từ AI."}`;
        }
    } catch (error) {
        messageElement.textContent = "Oops! Lỗi kết nối đến máy chủ AI. Hãy chắc chắn rằng bạn đang chạy file chat_ai.py ở cổng 5002!";
    } finally {
        // Đảm bảo khung chat luôn cuộn xuống dòng mới nhất
        chatbox.scrollTo(0, chatbox.scrollHeight);
    }
};

// Hàm xử lý chính khi người dùng gửi tin nhắn
const handleChat = (message) => {
    if(!message) return;
    
    chatInput.value = ""; // Xóa trắng ô nhập liệu
    
    // Hiển thị tin nhắn người dùng
    chatbox.appendChild(createChatLi(message, "outgoing"));
    chatbox.scrollTo(0, chatbox.scrollHeight); 

    // Ẩn danh sách gợi ý khi đã bắt đầu chat
    const suggestionsContainer = document.querySelector('.chat-suggestions');
    if(suggestionsContainer) suggestionsContainer.style.display = 'none';

    // Hiển thị trạng thái chờ
    setTimeout(() => {
        const incomingChatLi = createChatLi("HLV đang phân tích dữ liệu...", "incoming");
        chatbox.appendChild(incomingChatLi);
        chatbox.scrollTo(0, chatbox.scrollHeight);
        
        // Gọi API sang server AI
        generateResponse(incomingChatLi, message);
    }, 400); // Đợi 0.4s để tạo hiệu ứng giống người thật
};

// 5. GẮN SỰ KIỆN LẮNG NGHE CHO CÁC NÚT BẤM
suggestionBtns.forEach(btn => {
    btn.addEventListener("click", (e) => handleChat(e.target.textContent));
});

sendChatBtn.addEventListener("click", () => handleChat(chatInput.value.trim()));

chatInput.addEventListener("keydown", (e) => {
    if(e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleChat(chatInput.value.trim());
    }
});