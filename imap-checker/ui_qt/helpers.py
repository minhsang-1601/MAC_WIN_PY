#!/usr/bin/env python3
"""Đường dẫn + logic đọc/ghi file dùng chung cho toàn bộ app Qt.

Port từ ui/app.py (Streamlit) sang thuần Python, không phụ thuộc UI framework.
"""
import configparser
import json
import os
import plistlib
import subprocess
import sys
import time
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
MAIL_CONFIG_PATH = BASE_DIR / "SEND_MAIL" / "mail_account.conf"

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


def list_all_accounts():
    """Gộp email+password từ MỌI file trong account/ thành 1 dict {email: password}.
    Email trùng ở nhiều file thì file đọc sau (theo thứ tự list_account_files) thắng."""
    result = {}
    for path in list_account_files():
        for email_addr, pwd in read_account_lines(path):
            result[email_addr] = pwd
    return result


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
    """Xoá file trong LOG_DIR cũ hơn `days` ngày (theo mtime). days<=0 = không xoá gì.
    Trả về list tên file đã xoá."""
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


# ============================================================
# Lên lịch chạy tự động bằng launchd (macOS) — chạy đúng giờ kể cả khi tắt app
# ============================================================

SCHEDULES_PATH = BASE_DIR / "context" / "schedules.json"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LAUNCHD_LABEL_PREFIX = "com.imapchecker.schedule."


def load_schedules():
    if not SCHEDULES_PATH.exists():
        return []
    try:
        return json.loads(SCHEDULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_schedules(schedules):
    SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULES_PATH.write_text(json.dumps(schedules, ensure_ascii=False, indent=2), encoding="utf-8")


def build_schedule_command(schedule):
    p = schedule["params"]
    if schedule["job_type"] == "check_all":
        return [PY_CMD, str(SCRIPT_CHECK_ALL), p["section"], p["file"], p["send_flag"]]
    if schedule["job_type"] == "clean":
        return [PY_CMD, str(SCRIPT_CLEAN), p["file"], str(p["months"])]
    raise ValueError(f"job_type không hỗ trợ: {schedule['job_type']}")


def _plist_path(schedule_id):
    return LAUNCH_AGENTS_DIR / f"{LAUNCHD_LABEL_PREFIX}{schedule_id}.plist"


def build_calendar_interval(schedule):
    """StartCalendarInterval của launchd theo kiểu lặp: hàng ngày / theo thứ / theo ngày trong tháng.
    launchd: Weekday 1=Thứ 2 ... 6=Thứ 7, 7=Chủ nhật (0 cũng là CN nhưng dùng 7 cho rõ ràng)."""
    hour, minute = schedule["time"].split(":")
    hour, minute = int(hour), int(minute)
    repeat = schedule.get("repeat", "daily")

    if repeat == "daily":
        return {"Hour": hour, "Minute": minute}
    if repeat == "weekly":
        weekdays = schedule.get("weekdays") or []
        if not weekdays:
            raise ValueError("Chưa chọn thứ nào trong tuần.")
        return [{"Hour": hour, "Minute": minute, "Weekday": wd} for wd in weekdays]
    if repeat == "monthly":
        days = schedule.get("days_of_month") or []
        if not days:
            raise ValueError("Chưa chọn ngày nào trong tháng.")
        return [{"Hour": hour, "Minute": minute, "Day": d} for d in days]
    raise ValueError(f"Kiểu lặp không hỗ trợ: {repeat}")


def install_schedule(schedule):
    """Tạo + nạp launchd LaunchAgent cho 1 lịch chạy."""
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    label = f"{LAUNCHD_LABEL_PREFIX}{schedule['id']}"
    plist_path = _plist_path(schedule["id"])

    plist = {
        "Label": label,
        "ProgramArguments": build_schedule_command(schedule),
        "StartCalendarInterval": build_calendar_interval(schedule),
        "StandardOutPath": str(LOG_DIR / f"schedule_{schedule['id']}.out.log"),
        "StandardErrorPath": str(LOG_DIR / f"schedule_{schedule['id']}.err.log"),
        "RunAtLoad": False,
    }
    if schedule.get("mail_from") and schedule.get("mail_from_password") and schedule.get("mail_to"):
        plist["EnvironmentVariables"] = {
            "MAIL_FROM_OVERRIDE": schedule["mail_from"],
            "MAIL_FROM_PASSWORD_OVERRIDE": schedule["mail_from_password"],
            "MAIL_TO_OVERRIDE": schedule["mail_to"],
        }
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)

    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
    result = subprocess.run(["launchctl", "load", "-w", str(plist_path)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "launchctl load thất bại")


def uninstall_schedule(schedule_id):
    plist_path = _plist_path(schedule_id)
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", "-w", str(plist_path)], capture_output=True)
        plist_path.unlink()


# ============================================================
# Chọn FROM/TO khi gửi mail báo cáo (mặc định lấy từ mail_account.conf)
# ============================================================

def get_mail_config_defaults():
    """Đọc SENDER_EMAIL / TO_EMAILS[0] hiện tại từ SEND_MAIL/mail_account.conf.
    Trả về (sender_email, to_email) — None nếu chưa có file hoặc đọc lỗi."""
    if not MAIL_CONFIG_PATH.exists():
        return None, None
    try:
        cfg = {}
        exec(MAIL_CONFIG_PATH.read_text(encoding="utf-8"), {}, cfg)
        sender = cfg.get("SENDER_EMAIL")
        to_emails = cfg.get("TO_EMAILS") or []
        return sender, (to_emails[0] if to_emails else None)
    except Exception:
        return None, None


def list_sendable_accounts():
    """Email đã biết (Gmail/Yahoo) và có App Password thật — dùng làm FROM khi gửi báo cáo
    (SMTP đã hỗ trợ cả Gmail và Yahoo, xem common/providers.resolve_smtp_host)."""
    accounts = list_all_accounts()
    return {e: p for e, p in accounts.items() if p and get_provider(e) is not None}


def list_accounts_with_password():
    """Mọi email đã biết có mật khẩu thật (không giới hạn provider) — dùng làm TO,
    vì người nhận không cần đăng nhập/xác thực gì cả."""
    accounts = list_all_accounts()
    return {e: p for e, p in accounts.items() if p}
