async function fetchPlan() {
    const goal = document.getElementById("goal").value;
    const level = document.getElementById("level").value;
    const equipment = document.getElementById("equipment").value;
    const container = document.getElementById("plan-container");
    const title = document.getElementById("plan-title");

    container.innerHTML = "<p>Đang tạo lộ trình...</p>";

    try {
        const response = await fetch("http://127.0.0.1:8000/api/generate-plan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ goal, level, equipment })
        });

        const data = await response.json();
        title.innerText = data.title;
        container.innerHTML = "";

        data.schedule.forEach(day => {
            const dayCard = document.createElement("div");
            dayCard.className = "day-card";
            
            let exercisesHTML = "";
            if (day.exercises.length === 0) {
                exercisesHTML = `<div class="rest-day">Phục hồi cơ bắp. Đi dạo nhẹ nhàng hoặc giãn cơ.</div>`;
            } else {
                let items = day.exercises.map(ex => `
                    <div class="exercise-item">
                        <img src="${ex.img}" class="exercise-img">
                        <div class="exercise-info">
                            <div class="exercise-title">${ex.name}</div>
                            <span class="exercise-tag">${ex.muscle}</span>
                        </div>
                    </div>
                `).join('');
                exercisesHTML = `<div class="day-body">${items}</div>`;
            }

            dayCard.innerHTML = `
                <div class="day-header">${day.day}</div>
                ${exercisesHTML}
            `;
            container.appendChild(dayCard);
        });

    } catch (error) {
        container.innerHTML = `<p style="color: red;">Lỗi kết nối đến Backend. Hãy đảm bảo server Python đang chạy.</p>`;
    }
}