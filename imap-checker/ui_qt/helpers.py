#!/usr/bin/env python3
"""Đường dẫn + logic đọc/ghi file dùng chung cho toàn bộ app Qt.

Port từ ui/app.py (Streamlit) sang thuần Python, không phụ thuộc UI framework.
"""
import configparser
import os
import sys
from pathlib import Path

if os.name == "nt":
    HOME = Path(os.path.expanduser("~"))
    PY_CMD = "python"
else:
    HOME = Path.home()
    PY_CMD = "python3"

BASE_DIR = HOME / "MAC_WIN_PY" / "imap-checker"
SCRIPTS_DIR = BASE_DIR / "scripts"
ACCOUNT_DIR = BASE_DIR / "account"
LOG_DIR = BASE_DIR / "LOG"
CONFIG_PATH = BASE_DIR / "context" / "config.ini"

sys.path.insert(0, str(BASE_DIR))
from common.providers import get_provider  # noqa: E402

PROVIDER_LABELS = {"gmail": "🟢 Gmail", "yahoo": "🟣 Yahoo"}

SCRIPT_CHECK_ALL = SCRIPTS_DIR / "check_mail_all_common.py"
SCRIPT_CHECK_ONE = SCRIPTS_DIR / "check_gmail_common.py"
SCRIPT_GETBODY = SCRIPTS_DIR / "getbody_mail_common.py"
SCRIPT_CLEAN = SCRIPTS_DIR / "clean_mail_common.py"

CONFIG_FIELDS = ["from", "subject_title", "keywords", "recent_minutes", "max_results", "keywords_count"]

CONFIG_FIELD_LABELS = {
    "from": "Người gửi (from)",
    "subject_title": "Tiêu đề chứa",
    "keywords": "Từ khoá trong nội dung",
    "recent_minutes": "Trong bao nhiêu phút gần đây",
    "max_results": "Số kết quả tối đa",
    "keywords_count": "Từ khoá để đếm",
}


def provider_label(email_addr):
    if not email_addr:
        return ""
    p = get_provider(email_addr)
    return PROVIDER_LABELS.get(p, "⚠️ Không hỗ trợ")


def read_account_lines(path: Path):
    """Đọc file account 'email,password' mỗi dòng -> list[(email, pwd)]."""
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if "," in ln:
                email_addr, pwd = [x.strip() for x in ln.split(",", 1)]
            else:
                parts = ln.split()
                if len(parts) < 2:
                    continue
                email_addr, pwd = parts[0], parts[1]
            rows.append((email_addr, pwd))
    return rows


def write_account_lines(path: Path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for email_addr, pwd in rows:
            if email_addr:
                f.write(f"{email_addr},{pwd}\n")


def list_account_files():
    if not ACCOUNT_DIR.exists():
        return []
    return sorted(p for p in ACCOUNT_DIR.iterdir() if p.is_file())


def load_ini():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")
    return cfg


def save_ini(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)


def job_sections(cfg):
    """Chỉ trả về section job thật — bỏ section chú thích/hướng dẫn không có key chuẩn."""
    return [s for s in cfg.sections() if "recent_minutes" in cfg[s]]
