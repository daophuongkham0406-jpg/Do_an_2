const dbExercises = [
    { name: "Barbell Squat", muscle: "Chân", equipment: "Barbell", img: "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=400&q=80" },
    { name: "Push Up", muscle: "Ngực", equipment: "Bodyweight", img: "https://images.unsplash.com/photo-1598971639058-fab3c3109a00?w=400&q=80" },
    { name: "Pull Up", muscle: "Lưng", equipment: "Bodyweight", img: "https://images.unsplash.com/photo-1598971484999-6934b4553bce?w=400&q=80" },
    { name: "Dumbbell Curl", muscle: "Tay", equipment: "Dumbbell", img: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80" },
    { name: "Bench Press", muscle: "Ngực", equipment: "Barbell", img: "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&q=80" },
    { name: "Lunges", muscle: "Chân", equipment: "Bodyweight", img: "https://images.unsplash.com/photo-1434682881908-b43d0467b798?w=400&q=80" },
    { name: "Dumbbell Row", muscle: "Lưng", equipment: "Dumbbell", img: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80" }
];

function renderExercises(data) {
    const grid = document.getElementById('exercise-grid');
    if (!grid) return;
    grid.innerHTML = data.length ? data.map(ex => `
        <div class="card">
            <img src="${ex.img}" class="card-img" alt="${ex.name}">
            <div class="card-body">
                <div class="card-title">${ex.name}</div>
                <div class="card-tags">
                    <span class="tag tag-muscle">${ex.muscle}</span>
                    <span class="tag tag-equip">${ex.equipment}</span>
                </div>
            </div>
        </div>
    `).join('') : '<div class="empty-state">Không tìm thấy bài tập phù hợp.</div>';
}

document.querySelectorAll('.filter-cb').forEach(cb => {
    cb.addEventListener('change', () => {
        const checked = Array.from(document.querySelectorAll('.filter-cb:checked')).map(el => el.value);
        if (!checked.length) return renderExercises(dbExercises);
        
        const filtered = dbExercises.filter(ex => checked.includes(ex.muscle) || checked.includes(ex.equipment));
        renderExercises(filtered);
    });
});

// Chạy lần đầu
renderExercises(dbExercises);