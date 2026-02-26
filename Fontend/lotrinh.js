const dbExercises = [
    { name: "Barbell Squat", muscle: "Chân", equipment: "Barbell", img: "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=400&q=80" },
    { name: "Push Up", muscle: "Ngực", equipment: "Bodyweight", img: "https://images.unsplash.com/photo-1598971639058-fab3c3109a00?w=400&q=80" },
    { name: "Pull Up", muscle: "Lưng", equipment: "Bodyweight", img: "https://images.unsplash.com/photo-1598971484999-6934b4553bce?w=400&q=80" },
    { name: "Dumbbell Curl", muscle: "Tay", equipment: "Dumbbell", img: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80" },
    { name: "Bench Press", muscle: "Ngực", equipment: "Barbell", img: "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&q=80" },
    { name: "Lunges", muscle: "Chân", equipment: "Bodyweight", img: "https://images.unsplash.com/photo-1434682881908-b43d0467b798?w=400&q=80" },
    { name: "Dumbbell Row", muscle: "Lưng", equipment: "Dumbbell", img: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80" }
];

const btnGenerate = document.getElementById('btn-generate');

if (btnGenerate) {
    btnGenerate.addEventListener('click', () => {
        const goal = document.getElementById('goal').value;
        const level = document.getElementById('level').value;
        const equipment = document.getElementById('equipment').value;
        
        document.getElementById('plan-title').innerText = `Lộ trình ${goal} - ${level}`;
        
        const validEx = dbExercises.filter(ex => equipment === 'All' || ex.equipment === equipment);
        
        const schedule = [
            { day: "Thứ 2", focus: "Thân trên", req: ["Ngực", "Lưng", "Tay"] },
            { day: "Thứ 3", focus: "Thân dưới", req: ["Chân"] },
            { day: "Thứ 4", focus: "Phục hồi", req: [] },
            { day: "Thứ 5", focus: "Thân trên", req: ["Ngực", "Lưng", "Tay"] },
            { day: "Thứ 6", focus: "Thân dưới", req: ["Chân"] },
            { day: "Cuối tuần", focus: "Nghỉ ngơi", req: [] }
        ];

        document.getElementById('plan-container').innerHTML = schedule.map(d => {
            const exToday = d.req.length ? validEx.filter(ex => d.req.includes(ex.muscle)).slice(0, 4) : [];
            
            const bodyHtml = exToday.length ? `
                <div class="day-body">
                    ${exToday.map(ex => `
                        <div class="exercise-item">
                            <img src="${ex.img}" class="card-img">
                            <div class="exercise-info">
                                <div style="font-weight: 800; margin-bottom: 8px;">${ex.name}</div>
                                <span class="tag-muscle">${ex.muscle}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : `<div class="rest-day">Nghỉ ngơi hoặc giãn cơ nhẹ nhàng.</div>`;

            return `
                <div class="day-card">
                    <div class="day-header">
                        <span>${d.day}</span>
                        <span style="color: #6b7280; font-size: 0.9rem;">${d.focus}</span>
                    </div>
                    ${bodyHtml}
                </div>
            `;
        }).join('');
    });
}