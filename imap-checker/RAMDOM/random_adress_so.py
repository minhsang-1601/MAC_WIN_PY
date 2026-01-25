import itertools
import os

# ---------- ĐƯỜNG DẪN FILE ----------
OUTPUT_FILE = "all_variants.txt"

# ---------- DANH SÁCH BIẾN THỂ ----------
variants = {
    "0": ["0", "０"],
    "1": ["1", "１"],
    "2": ["2", "２"],
    "3": ["3", "３"],
    "4": ["4", "４"],
    "5": ["5", "５"],
    "6": ["6", "６"],
    "7": ["7", "７"],
    "8": ["8", "８"],
    "9": ["9", "９"],
    "-": ["-", "−", "ー"],  # dấu trừ / dash / chōon
}

# Chuỗi gốc
s = "102"

# Tạo list các ký tự với biến thể
char_options = [variants.get(c, [c]) for c in s]

# Sinh tất cả tổ hợp
all_combinations = itertools.product(*char_options)

# Ghép thành chuỗi và loại trùng
all_variants = [''.join(t) for t in all_combinations]
all_variants = list(dict.fromkeys(all_variants))

# Lưu vào file
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for v in all_variants:
        f.write(v + "\n")

print(f"✅ Đã sinh {len(all_variants)} biến thể và lưu vào file: {os.path.abspath(OUTPUT_FILE)}")
