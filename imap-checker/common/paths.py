#!/usr/bin/env python3
"""Đường dẫn dùng chung cho TOÀN BỘ app (UI Qt + các script CLI + launchd).

Trước đây mỗi script tự dựng lại BASE_DIR/PY_CMD theo kiểu riêng (chỗ dùng
``pathlib.Path``, chỗ dùng ``os.path``) → dễ lệch nhau. Gom về một chỗ:
sửa đường dẫn chỉ sửa ở đây.

Mọi giá trị là ``pathlib.Path`` (trừ ``PY_CMD``). Script nào cần chuỗi thì
``str(...)`` tại chỗ.
"""
import os
from pathlib import Path

if os.name == "nt":  # Windows
    HOME = Path(os.path.expanduser("~"))
    PY_CMD = "python"
else:  # macOS / Linux
    HOME = Path.home()
    PY_CMD = "python3"

BASE_DIR = HOME / "MAC_WIN_PY" / "imap-checker"

SCRIPTS_DIR = BASE_DIR / "scripts"
ACCOUNT_DIR = BASE_DIR / "account"
LOG_DIR = BASE_DIR / "LOG"
CONTEXT_DIR = BASE_DIR / "context"

CONFIG_PATH = CONTEXT_DIR / "config.ini"
SCHEDULES_PATH = CONTEXT_DIR / "schedules.json"
MAIL_CONFIG_PATH = BASE_DIR / "SEND_MAIL" / "mail_account.conf"

# Các script CLI (dùng cho subprocess ở UI và cho launchd)
SCRIPT_CHECK_ALL = SCRIPTS_DIR / "check_mail_all_common.py"
SCRIPT_CHECK_ONE = SCRIPTS_DIR / "check_gmail_common.py"
SCRIPT_GETBODY = SCRIPTS_DIR / "getbody_mail_common.py"
SCRIPT_CLEAN = SCRIPTS_DIR / "clean_mail_common.py"
SCRIPT_SEND = SCRIPTS_DIR / "send_file_common.py"
