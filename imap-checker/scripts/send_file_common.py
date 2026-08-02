#!/usr/bin/env python3
"""
send_file_common.py

- Gửi nhiều file được truyền từ tham số đầu vào.
- File đầu tiên dùng để lấy ngày giờ từ tên file (YYYYMMDD_HHMMSS).
- Sử dụng Gmail SMTP (App Password)
"""

import os
import sys
import re
import smtplib
from email.message import EmailMessage
from datetime import datetime

# ---------- TỰ ĐỘNG XÁC ĐỊNH ĐƯỜNG DẪN ----------
if os.name == 'nt':  # Windows
    HOME = os.path.expanduser("~")
    BASE_DIR = os.path.join(HOME, "MAC_WIN_PY", "imap-checker")
    PY_CMD = "python"
else:  # macOS / Linux
    HOME = os.path.expanduser("~")
    BASE_DIR = os.path.join(HOME, "MAC_WIN_PY", "imap-checker")
    PY_CMD = "python3"

sys.path.insert(0, BASE_DIR)
from common.providers import resolve_smtp_host

# File cấu hình mail (KHÔNG COMMIT)
MAIL_CONFIG_PATH = os.path.join(
    BASE_DIR,
    "SEND_MAIL",
    "mail_account.conf"
)

MAIL_SUBJECT = "[AUTO] Ket qua check mail"
MAIL_BODY = "File ket qua check mail duoc gui tu dong.\n\n-- Python Script"

# ============================


# ✅ MỚI: Load mail account từ file config (format Python)
def load_mail_config():
    # Cho phép UI ghi đè FROM/TO theo từng lần chạy qua biến môi trường —
    # không set thì giữ nguyên hành vi cũ (đọc mail_account.conf).
    from_override = os.environ.get("MAIL_FROM_OVERRIDE")
    pwd_override = os.environ.get("MAIL_FROM_PASSWORD_OVERRIDE")
    to_override = os.environ.get("MAIL_TO_OVERRIDE")
    if from_override and pwd_override and to_override:
        return from_override, pwd_override, [to_override]

    if not os.path.exists(MAIL_CONFIG_PATH):
        print(f"❌ Không tìm thấy file config: {MAIL_CONFIG_PATH}")
        sys.exit(1)

    cfg = {}

    try:
        with open(MAIL_CONFIG_PATH, "r", encoding="utf-8") as f:
            code = f.read()

        # Execute file config như python code
        exec(code, {}, cfg)

        sender = cfg.get("SENDER_EMAIL")
        password = cfg.get("APP_PASSWORD")
        to_emails = cfg.get("TO_EMAILS")

        if not sender or not password or not to_emails:
            raise ValueError("Thiếu SENDER_EMAIL / APP_PASSWORD / TO_EMAILS")

        if not isinstance(to_emails, list):
            raise ValueError("TO_EMAILS phải là list")

        return sender, password, to_emails

    except Exception as e:
        print(f"❌ Lỗi đọc mail_account.conf: {e}")
        sys.exit(1)


def extract_datetime_from_filename(filepath):
    """
    Bắt pattern YYYYMMDD_HHMMSS ở bất kỳ đâu trong tên file
    """
    filename = os.path.basename(filepath)
    m = re.search(r"(\d{8})_(\d{6})", filename)
    if not m:
        return "UNKNOWN_TIME"

    try:
        dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "UNKNOWN_TIME"


def attach_file_to_mail(msg, file_path):
    """
    Đính kèm 1 file vào email
    """
    if not os.path.exists(file_path):
        print(f"❌ File không tồn tại: {file_path}")
        return False

    try:
        with open(file_path, "rb") as f:
            data = f.read()
            filename = os.path.basename(file_path)

        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=filename
        )
        print(f"📎 Đã attach: {filename}")
        return True
    except Exception as e:
        print(f"❌ Lỗi attach file {file_path}: {e}")
        return False


def send_mail(file_list):
    """
    file_list: list đường dẫn file cần gửi
    """

    # ✅ Load mail account từ file config
    SENDER_EMAIL, APP_PASSWORD, TO_EMAILS = load_mail_config()

    if not file_list:
        print("❌ Không có file nào để gửi.")
        sys.exit(1)

    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(TO_EMAILS)

    # Lấy thời gian từ file đầu tiên (CSV)
    check_time = extract_datetime_from_filename(file_list[0])
    msg["Subject"] = f"{MAIL_SUBJECT} - {check_time}"
    msg.set_content(MAIL_BODY)

    # Attach từng file
    attached_count = 0
    for fpath in file_list:
        if attach_file_to_mail(msg, fpath):
            attached_count += 1

    if attached_count == 0:
        print("❌ Không attach được file nào. Hủy gửi mail.")
        sys.exit(1)

    try:
        smtp_server, smtp_port = resolve_smtp_host(SENDER_EMAIL)
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)

        print(f"✅ Đã gửi mail thành công ({attached_count} file).")

    except Exception as e:
        print(f"❌ Lỗi khi gửi mail: {e}")
        sys.exit(1)


def main():
    # Nhận danh sách file từ tham số dòng lệnh (GIỮ NGUYÊN)
    if len(sys.argv) < 2:
        print("❌ Thiếu tham số file.")
        print("Ví dụ:")
        print("  python send_file_common.py file1.csv file2.txt")
        sys.exit(1)

    file_list = sys.argv[1:]

    print("📄 Danh sách file sẽ gửi:")
    for f in file_list:
        print("   -", f)

    send_mail(file_list)


if __name__ == "__main__":
    main()
