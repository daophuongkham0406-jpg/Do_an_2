# Chuan hoa tieng Viet cho AI goi y bai tap

Module `vietnamese_normalizer.py` dung de tranh loi lech ngon ngu khi nguoi dung nhap tieng Viet, con file `exercises.csv` lai luu nhan noi bo bang tieng Anh.

## Muc tieu

- Nguoi dung co the nhap: `dau goi`, `dau lung duoi`, `co vai`, `dui truoc`, `tay sau`.
- He thong map ve nhan noi bo nhu: `knee`, `lower_back`, `shoulder`, `quadriceps`, `triceps_brachii`.
- Khi hien thi, he thong doi nhan noi bo thanh tieng Viet, vi du `pectoralis_major` -> `co nguc`.
- Luat an toan se tranh goi y bai tap tac dong vao bo phan/nhom co nguoi dung can tranh.

## Cac nhom du lieu duoc chuan hoa

- `body_part`
- `primary_muscles`
- `secondary_muscles`
- `goals`
- `category`
- `difficulty`
- mot so `tags` an toan: `knee_safe`, `lower_back_safe`, `shoulder_safe`

## Nguyen tac an toan

- Neu nguoi dung nhap dau/chan thuong mot nhom co cu the, he thong loai cac bai co nhom co do trong `primary_muscles`.
- Neu nhom co do nam trong `secondary_muscles`, he thong giam uu tien hoac loai bo tuy muc do nghiem trong.
- Neu nguoi dung nhap dau goi, dau lung duoi, dau vai, he thong chi uu tien bai co tag an toan tuong ung:
  - dau goi -> `knee_safe`
  - dau lung duoi -> `lower_back_safe`
  - dau vai -> `shoulder_safe`
- Khong dua `equipment` vao luat goi y theo yeu cau hien tai.

## Vi du

```python
from vietnamese_normalizer import normalize_avoid_terms, display_pipe_values

print(normalize_avoid_terms("dau goi, lung duoi, tay sau"))
# {'avoid_keys': ['knee', 'lower_back', 'triceps_brachii'], 'unknown_terms': []}

print(display_pipe_values("pectoralis_major|triceps_brachii"))
# co nguc, co tay sau
```
