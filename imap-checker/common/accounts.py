#!/usr/bin/env python3
"""Đọc/ghi/gộp file account ``email,password`` — dùng chung cho UI lẫn script.

Trước đây logic này nằm trong ``ui_qt/helpers.py`` (đọc bởi UI) VÀ chép lại
trong ``scripts/check_mail_all_common.py`` (``read_accounts``). Gom về một chỗ,
không phụ thuộc PyQt.
"""
from pathlib import Path

from common.paths import ACCOUNT_DIR


def parse_account_line(line):
    """Tách 1 dòng account → (email, password), hoặc None nếu dòng bỏ qua.

    Chấp nhận ``email,password`` hoặc ``email password`` (khoảng trắng).
    Dòng rỗng / bắt đầu bằng ``#`` → None.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "," in line:
        email_addr, pwd = [x.strip() for x in line.split(",", 1)]
        return email_addr, pwd
    parts = line.split()
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def read_account_lines(path):
    """Đọc file account → list[(email, password)]. File không tồn tại → []."""
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            parsed = parse_account_line(ln)
            if parsed:
                rows.append(parsed)
    return rows


def write_account_lines(path, rows):
    """Ghi list[(email, password)] ra file, mỗi dòng ``email,password``."""
    with open(path, "w", encoding="utf-8") as f:
        for email_addr, pwd in rows:
            if email_addr:
                f.write(f"{email_addr},{pwd}\n")


def list_account_files():
    """Mọi file trong thư mục account/ (đã sort). Thư mục chưa có → []."""
    if not ACCOUNT_DIR.exists():
        return []
    return sorted(p for p in ACCOUNT_DIR.iterdir() if p.is_file())


def list_all_accounts():
    """Gộp email+password từ MỌI file account → dict {email: password}.

    Email trùng ở nhiều file thì file đọc sau (theo thứ tự list_account_files)
    thắng.
    """
    result = {}
    for path in list_account_files():
        for email_addr, pwd in read_account_lines(path):
            result[email_addr] = pwd
    return result
