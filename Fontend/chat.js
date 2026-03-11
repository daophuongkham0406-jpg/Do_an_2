// 1. CHUẨN BỊ MÃ HTML CỦA CHATBOT TÍCH HỢP
const chatbotHTML = `
    <button class="chatbot-toggler">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
    </button>

    <div class="chatbot-box">
        <header>
            <h2>AI Huấn Luyện Viên</h2>
            <span class="close-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </span>
        </header>
        
        <ul class="chatbox">
            <li class="chat incoming">
                <p>Chào bạn! Mình là AI HLV cá nhân. Hãy cho mình biết chiều cao, cân nặng, độ tuổi hoặc mục tiêu thể hình của bạn để mình hỗ trợ nhé!</p>
            </li>
        </ul>

        <div class="chat-suggestions">
            <button class="suggestion-btn">Lên lộ trình Clean Bulk</button>
            <button class="suggestion-btn">Mục tiêu tăng 3kg cơ nạc</button>
            <button class="suggestion-btn">Gợi ý bài tập ngực hôm nay</button>
        </div>

        <div class="chat-input">
            <input type="text" placeholder="Nhập chỉ số hoặc câu hỏi..." required>
            <span id="send-btn">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="#512da8"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"></path></svg>
            </span>
        </div>
    </div>
`;

// 2. CHÈN TỰ ĐỘNG CHATBOT VÀO CUỐI TRANG WEB
document.body.insertAdjacentHTML("beforeend", chatbotHTML);

// 3. XỬ LÝ SỰ KIỆN LOGIC (ĐÓNG/MỞ, NHẮN TIN, CHỌN GỢI Ý)
const chatbotToggler = document.querySelector(".chatbot-toggler");
const closeBtn = document.querySelector(".close-btn");
const chatbox = document.querySelector(".chatbox");
const chatInput = document.querySelector(".chat-input input");
const sendChatBtn = document.querySelector("#send-btn");
const suggestionBtns = document.querySelectorAll(".suggestion-btn");

// Mở & Đóng khung chat
chatbotToggler.addEventListener("click", () => document.body.classList.toggle("show-chatbot"));
closeBtn.addEventListener("click", () => document.body.classList.remove("show-chatbot"));

// Hàm tạo thẻ chứa tin nhắn
const createChatLi = (message, className) => {
    const chatLi = document.createElement("li");
    chatLi.classList.add("chat", className);
    chatLi.innerHTML = `<p>${message}</p>`;
    return chatLi;
}

// Hàm xử lý khi gửi tin nhắn hoặc bấm vào nút gợi ý
const handleChat = (message) => {
    if(!message) return;
    
    chatInput.value = ""; // Xóa trắng ô nhập liệu
    
    // 3.1 Hiển thị tin nhắn của người dùng lên màn hình
    chatbox.appendChild(createChatLi(message, "outgoing"));
    chatbox.scrollTo(0, chatbox.scrollHeight); // Cuộn xuống cuối

    // 3.2 Ẩn danh sách câu hỏi gợi ý khi đã bắt đầu chat
    const suggestionsContainer = document.querySelector('.chat-suggestions');
    if(suggestionsContainer) suggestionsContainer.style.display = 'none';

    // 3.3 Giả lập AI suy nghĩ và trả lời (sau này sẽ thay bằng gọi API Node.js)
    setTimeout(() => {
        let aiResponse = "";
        let lowerMsg = message.toLowerCase();
        
        if(lowerMsg.includes("clean bulk") || lowerMsg.includes("tăng") || lowerMsg.includes("cơ")) {
            aiResponse = "Tuyệt vời! Để xây dựng lộ trình tăng cơ nạc (Clean Bulk), hệ thống đang phân tích các bài tập Compound phù hợp với bạn. Vui lòng đợi trong giây lát...";
        } else if (lowerMsg.includes("ngực") || lowerMsg.includes("bài tập")) {
            aiResponse = "Với bài tập ngực, bạn nên ưu tiên Bench Press, Incline Dumbbell Press và Cable Crossover. Bạn muốn tập trung vào phần ngực trên hay ngực dưới?";
        } else {
            aiResponse = "Hệ thống đang tiếp nhận chỉ số của bạn. Danh sách các bài tập sẽ được khởi tạo dựa trên dữ liệu Class Diagram trong hệ thống.";
        }

        // Hiển thị phản hồi của AI
        chatbox.appendChild(createChatLi(aiResponse, "incoming"));
        chatbox.scrollTo(0, chatbox.scrollHeight);
    }, 800);
}

// Lắng nghe sự kiện click vào các nút gợi ý
suggestionBtns.forEach(btn => {
    btn.addEventListener("click", (e) => handleChat(e.target.textContent));
});

// Lắng nghe sự kiện gửi tin nhắn qua nút Send
sendChatBtn.addEventListener("click", () => handleChat(chatInput.value.trim()));

// Lắng nghe sự kiện nhấn phím Enter để gửi
chatInput.addEventListener("keydown", (e) => {
    if(e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleChat(chatInput.value.trim());
    }
});