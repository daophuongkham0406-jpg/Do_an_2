from ketnoidb import db

def seed_exercises():
    # 1. Xóa dữ liệu cũ (nếu có) để tránh bị trùng lặp khi chạy nhiều lần
    db.exercise.delete_many({})

    # 2. Tạo danh sách bài tập bám sát 100% sơ đồ UML của bạn
    danh_sach_bai_tap = [
        {
            "name": "Barbell Bench Press",
            "muscleGroup": "Ngực",
            "equipmentType": "Barbell",
            "imageUrl": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=500",
            "isBodyweight": False
        },
        {
            "name": "Push-Up",
            "muscleGroup": "Ngực",
            "equipmentType": "Bodyweight",
            "imageUrl": "https://images.unsplash.com/photo-1598971639058-fab3c3109a00?w=500",
            "isBodyweight": True
        },
        {
            "name": "Pull-Up",
            "muscleGroup": "Lưng",
            "equipmentType": "Bodyweight",
            "imageUrl": "https://images.unsplash.com/photo-1598971484999-6934b3e81395?w=500",
            "isBodyweight": True
        },
        {
            "name": "Dumbbell Lateral Raise",
            "muscleGroup": "Vai",
            "equipmentType": "Dumbbell",
            "imageUrl": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=500",
            "isBodyweight": False
        },
        {
            "name": "Squat",
            "muscleGroup": "Chân",
            "equipmentType": "Barbell",
            "imageUrl": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=500",
            "isBodyweight": False
        }
    ]

    # 3. Bơm vào MongoDB
    db.exercise.insert_many(danh_sach_bai_tap)
    print(f"✅ Đã tạo thành công {len(danh_sach_bai_tap)} bài tập trong Database!")

if __name__ == "__main__":
    seed_exercises()