<?php
// Cấu hình header để trả về JSON
header('Content-Type: application/json; charset=utf-8');

// 1. Lấy dữ liệu từ Frontend gửi lên
$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    echo json_encode(['error' => 'Không nhận được dữ liệu.']);
    exit;
}

$goal = $input['goal'] ?? '';
$level = $input['level'] ?? '';
$equipment = $input['equipment'] ?? '';
$userInfo = $input['userInfo'] ?? '';

// 2. Cấu hình Gemini API
$apiKey = 'AIzaSyBDC_PmCE7pcTtMdF2-P7oAiYOiPtWnPnk'; // THAY API KEY CỦA BẠN VÀO ĐÂY
$url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=' . $apiKey;

// 3. Xây dựng Prompt (Câu lệnh cho AI)
// Lệnh cho AI tạo mã HTML khớp đúng với CSS của bạn
$prompt = "Bạn là một huấn luyện viên thể hình chuyên nghiệp. Hãy tạo một lộ trình tập luyện trong 3 ngày dựa trên thông tin sau:
- Mục tiêu: $goal
- Kinh nghiệm: $level
- Thiết bị sẵn có: $equipment
- Tình trạng cá nhân / Lưu ý thêm: $userInfo

YÊU CẦU QUAN TRỌNG: Bạn CHỈ ĐƯỢC PHÉP trả về mã HTML (không dùng markdown ```html), không kèm bất kỳ câu chữ nào khác. Hãy dùng chính xác cấu trúc HTML sau cho mỗi ngày:

<div class='day-card'>
    <div class='day-header'><span>Thứ [X]</span><span>[Tên nhóm cơ / Phục hồi]</span></div>
    <div class='day-body'>
        <div class='routine-item'>
            <img src='[Tìm một link ảnh unsplash minh họa bài tập, ví dụ: [https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80](https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80)]' alt='[Tên bài]'>
            <div class='routine-item-info'>
                <h4>[Tên bài tập]</h4>
                <span class='tag tag-muscle'>[Nhóm cơ]</span>
            </div>
        </div>
        </div>
</div>

Nếu là ngày nghỉ, dùng cấu trúc:
<div class='day-card'>
    <div class='day-header'><span>Thứ [X]</span><span>Phục hồi</span></div>
    <div class='rest-day'>Nghỉ ngơi và bổ sung dinh dưỡng.</div>
</div>";

// 4. Chuẩn bị dữ liệu gửi đi (Payload)
$data = [
    "contents" => [
        [
            "parts" => [
                ["text" => $prompt]
            ]
        ]
    ]
];

// 5. Gửi Request bằng cURL
$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

// 6. Xử lý kết quả trả về
if ($httpCode == 200) {
    $responseData = json_decode($response, true);
    // Trích xuất đoạn text (mã HTML) AI sinh ra
    $aiHtml = $responseData['candidates'][0]['content']['parts'][0]['text'] ?? '<div class="empty-state">Lỗi xử lý kết quả từ AI.</div>';
    
    // Loại bỏ markdown (nếu AI ngoan cố thêm vào)
    $aiHtml = str_replace(['```html', '```'], '', $aiHtml);
    
    echo json_encode(['html' => trim($aiHtml)]);
} else {
    echo json_encode(['error' => 'Lỗi kết nối API: ' . $response]);
}
?>