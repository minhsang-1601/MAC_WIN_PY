#!/usr/bin/env python3
import secrets
import string
import sys
import io

# Tối ưu hóa hiển thị cho Windows (tránh lỗi font ký tự đặc biệt)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def gen_secure_password(length=12):
    specials = "!@#$%"
    # Gom nhóm các loại ký tự
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    all_chars = upper + lower + digits + specials

    # Đảm bảo có ít nhất 1 ký tự từ mỗi nhóm để đạt độ phức tạp tối đa
    pwd = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(specials),
    ]

    # Lấp đầy độ dài còn lại bằng cách chọn ngẫu nhiên an toàn
    pwd += [secrets.choice(all_chars) for _ in range(length - 4)]

    # Trộn danh sách ký tự một cách an toàn
    # Vì secrets không có hàm shuffle trực tiếp, ta dùng SystemRandom
    secrets.SystemRandom().shuffle(pwd)
    
    return "".join(pwd)

def main():
    length = 12
    count = 100
    
    try:
        for _ in range(count):
            print(gen_secure_password(length))
    except BrokenPipeError:
        # Tránh lỗi khi pipe dữ liệu trên Mac/Linux (ví dụ: | head)
        dev_null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(dev_null, sys.stdout.fileno())
        sys.exit(0)

if __name__ == "__main__":
    main()
