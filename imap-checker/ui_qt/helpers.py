#!/usr/bin/env python3
"""Lớp mỏng cho UI Qt — logic thật đã dời sang gói ``common/`` (dùng chung với
các script CLI). File này chỉ:

- re-export các thứ ``common`` cung cấp để ``pages.py``/``main_window.py`` giữ
  nguyên cách gọi ``h.xxx``;
- giữ vài thứ CHỈ dùng cho UI: nhãn hiển thị field, nhãn provider, và cài đặt
  log-retention (đọc/ghi trong config.ini).
"""
import os
import sys
import time
from pathlib import Path

# ── Đưa BASE_DIR lên path để import được gói common khi chạy từ source ──
if os.name == "nt":
    _HOME = Path(os.path.expanduser("~"))
else:
    _HOME = Path.home()
sys.path.insert(0, str(_HOME / "MAC_WIN_PY" / "imap-checker"))

# ── Re-export từ common (nguồn sự thật duy nhất) ──
from common.paths import (  # noqa: E402,F401
    HOME, PY_CMD, BASE_DIR, SCRIPTS_DIR, ACCOUNT_DIR, LOG_DIR,
    CONFIG_PATH, MAIL_CONFIG_PATH,
    SCRIPT_CHECK_ALL, SCRIPT_CHECK_ONE, SCRIPT_GETBODY, SCRIPT_CLEAN, SCRIPT_SEND,
)
from common.providers import get_provider  # noqa: E402,F401
from common.accounts import (  # noqa: E402,F401
    read_account_lines, write_account_lines, list_account_files, list_all_accounts,
)
from common.config_ini import load_ini, save_ini, job_sections  # noqa: E402,F401
from common.mailcfg import (  # noqa: E402,F401
    get_mail_config_defaults, list_sendable_accounts, list_accounts_with_password,
)
from common.scheduler import (  # noqa: E402,F401
    LAUNCH_AGENTS_DIR, LAUNCHD_LABEL_PREFIX,
    load_schedules, save_schedules, build_schedule_command,
    build_calendar_interval, install_schedule, uninstall_schedule,
)
from common.paths import SCHEDULES_PATH  # noqa: E402,F401


# ============================================================
# Chỉ dùng cho UI — nhãn hiển thị
# ============================================================

PROVIDER_LABELS = {"gmail": "🟢 Gmail", "yahoo": "🟣 Yahoo"}

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


# ============================================================
# Cài đặt UI (lưu chung trong config.ini, section riêng không phải job)
# ============================================================

UI_SETTINGS_SECTION = "_UI_Settings"
DEFAULT_LOG_RETENTION_DAYS = 30


def get_log_retention_days():
    cfg = load_ini()
    if UI_SETTINGS_SECTION in cfg:
        try:
            return cfg[UI_SETTINGS_SECTION].getint(
                "log_retention_days", fallback=DEFAULT_LOG_RETENTION_DAYS
            )
        except ValueError:
            return DEFAULT_LOG_RETENTION_DAYS
    return DEFAULT_LOG_RETENTION_DAYS


def set_log_retention_days(days):
    cfg = load_ini()
    if UI_SETTINGS_SECTION not in cfg:
        cfg[UI_SETTINGS_SECTION] = {}
    cfg[UI_SETTINGS_SECTION]["log_retention_days"] = str(days)
    save_ini(cfg)


def cleanup_old_logs(days=None):
    """Xoá file trong LOG_DIR cũ hơn `days` ngày (theo mtime). days<=0 = không
    xoá gì. Trả về list tên file đã xoá."""
    if days is None:
        days = get_log_retention_days()
    if days <= 0 or not LOG_DIR.exists():
        return []
    cutoff = time.time() - days * 86400
    deleted = []
    for p in LOG_DIR.iterdir():
        if p.is_file() and p.stat().st_mtime < cutoff:
            p.unlink()
            deleted.append(p.name)
    return deleted
