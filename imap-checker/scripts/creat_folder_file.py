import os
from pathlib import Path

# ---------- TỰ ĐỘNG XÁC ĐỊNH ĐƯỜNG DẪN ----------
HOME = Path.home()
BASE_DIR = HOME / "MAC_WIN_PY" / "imap-checker"
PY_CMD = "python" if os.name == "nt" else "python3"

# ---------- HÀM TẠO THƯ MỤC ----------
def smart_mkdir(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        print(f"[+] Folder OK: {path}")
    except Exception as e:
        print(f"[x] Lỗi tạo folder {path}: {e}")

# ---------- HÀM TẠO FILE ----------
def smart_touch(file_path: Path):
    try:
        if not file_path.exists():
            # ❌ file_path.touch(encoding="utf-8")  (Python không hỗ trợ encoding)
            file_path.touch()   # ✅ chỉ bỏ encoding, giữ nguyên logic
            print(f"[+] File OK: {file_path.name}")
        else:
            print(f"[!] File đã tồn tại: {file_path.name}")
    except Exception as e:
        print(f"[x] Lỗi tạo file {file_path}: {e}")

# ---------- KIỂM TRA HỆ THỐNG ----------
print("\n--- ĐANG KIỂM TRA CẤU TRÚC HỆ THỐNG ---")

# Folders
ACCOUNT_DIR = BASE_DIR / "account"
LOG_DIR = BASE_DIR / "LOG"
SEND_MAIL_DIR = BASE_DIR / "SEND_MAIL"

for folder in [ACCOUNT_DIR, LOG_DIR, SEND_MAIL_DIR]:
    smart_mkdir(folder)

# Files trong account
account_files = [
    "account.txt",
    "accounts_gm_clean",
    "accounts_gm_err",
    "accounts_gm_ok",
    "accounts_gm_test",
    "accounts_gm_all",
    "accounts_gm_wait",
]

for name in account_files:
    smart_touch(ACCOUNT_DIR / name)

# Files trong SEND_MAIL
send_mail_files = [
    "mail_account.conf",
]

for name in send_mail_files:
    smart_touch(SEND_MAIL_DIR / name)

print("\n--- ✅ HOÀN TẤT KIỂM TRA ---")
