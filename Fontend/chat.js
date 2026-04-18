const CHAT_API_URL = "http://127.0.0.1:5002/api/chat";

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
                <p>Chào bạn! Mình là AI HLV của FIT ME. Hôm nay bạn cần tư vấn bài tập hay chế độ ăn uống gì không?</p>
            </li>
        </ul>

        <div class="chat-suggestions">
            <button class="suggestion-btn">Lên lộ trình Clean Bulk</button>
            <button class="suggestion-btn">Mục tiêu tăng 3kg cơ</button>
            <button class="suggestion-btn">Bài tập ngực hôm nay</button>
        </div>

        <div class="chat-input">
            <input type="text" placeholder="Nhập câu hỏi..." required>
            <span id="send-btn" style="cursor: pointer;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="var(--accent, #e8ff47)"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"></path></svg>
            </span>
        </div>
    </div>
`;

document.body.insertAdjacentHTML("beforeend", chatbotHTML);

const chatbotToggler = document.querySelector(".chatbot-toggler");
const closeBtn = document.querySelector(".close-btn");
const chatbox = document.querySelector(".chatbox");
const chatInput = document.querySelector(".chat-input input");
const sendChatBtn = document.querySelector("#send-btn");
const suggestionBtns = document.querySelectorAll(".suggestion-btn");

chatbotToggler.addEventListener("click", () =>
  document.body.classList.toggle("show-chatbot"),
);
closeBtn.addEventListener("click", () =>
  document.body.classList.remove("show-chatbot"),
);

const formatAIResponse = (text) => {
  return text
    .replace(
      /^### (.*$)/gim,
      '<b style="display:block; margin:10px 0 5px; font-size:1.1em; color:var(--accent, #e8ff47)">$1</b>',
    )
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(
      /^\* (.*$)/gim,
      '<div style="margin-left:10px; margin-bottom:3px;">• $1</div>',
    )
    .replace(/\n/g, "<br>");
};

const createChatLi = (message, className) => {
  const chatLi = document.createElement("li");
  chatLi.classList.add("chat", className);
  const pTag = document.createElement("p");
  pTag.textContent = message;
  chatLi.appendChild(pTag);
  return chatLi;
};

const generateResponse = async (incomingChatLi, userMessage) => {
  const messageElement = incomingChatLi.querySelector("p");

  try {
    const response = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
    });

    const data = await response.json();

    if (response.ok) {
      messageElement.innerHTML = formatAIResponse(data.reply);
    } else {
      messageElement.textContent = `Lỗi: ${data.error || "Không thể lấy câu trả lời."}`;
    }
  } catch (error) {
    messageElement.textContent = "Lỗi kết nối máy chủ AI (Cổng 5002)!";
  } finally {
    chatbox.scrollTo(0, chatbox.scrollHeight);
  }
};

const handleChat = (message) => {
  if (!message) return;
  chatInput.value = "";

  chatbox.appendChild(createChatLi(message, "outgoing"));
  chatbox.scrollTo(0, chatbox.scrollHeight);

  const suggestionsContainer = document.querySelector(".chat-suggestions");
  if (suggestionsContainer) suggestionsContainer.style.display = "none";

  setTimeout(() => {
    const incomingChatLi = createChatLi("HLV đang suy nghĩ...", "incoming");
    chatbox.appendChild(incomingChatLi);
    chatbox.scrollTo(0, chatbox.scrollHeight);
    generateResponse(incomingChatLi, message);
  }, 400);
};

suggestionBtns.forEach((btn) => {
  btn.addEventListener("click", (e) => handleChat(e.target.textContent));
});

sendChatBtn.addEventListener("click", () => handleChat(chatInput.value.trim()));

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleChat(chatInput.value.trim());
  }
});
