#!/usr/bin/env python3
"""Lên lịch chạy tự động bằng launchd (macOS) — chạy đúng giờ kể cả khi tắt app.

Rút khỏi ui_qt/helpers.py để logic launchd không dính PyQt (test được độc lập).
"""
import json
import plistlib
import subprocess
from pathlib import Path

from common.paths import (
    PY_CMD, LOG_DIR, SCHEDULES_PATH,
    SCRIPT_CHECK_ALL, SCRIPT_CLEAN,
)

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
    SCHEDULES_PATH.write_text(
        json.dumps(schedules, ensure_ascii=False, indent=2), encoding="utf-8")


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
    """StartCalendarInterval của launchd theo kiểu lặp: hàng ngày / theo thứ /
    theo ngày trong tháng.
    launchd: Weekday 1=Thứ 2 ... 6=Thứ 7, 7=Chủ nhật (0 cũng là CN nhưng dùng
    7 cho rõ ràng)."""
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
    env = {}
    if schedule.get("group"):
        # Nhóm: script tự lấy subset từ danh sách gốc, không cần file riêng.
        env["IMAP_GROUP"] = schedule["group"]
    if schedule.get("mail_from") and schedule.get("mail_from_password") and schedule.get("mail_to"):
        env["MAIL_FROM_OVERRIDE"] = schedule["mail_from"]
        env["MAIL_FROM_PASSWORD_OVERRIDE"] = schedule["mail_from_password"]
        env["MAIL_TO_OVERRIDE"] = schedule["mail_to"]
    if env:
        plist["EnvironmentVariables"] = env
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)

    subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
    result = subprocess.run(
        ["launchctl", "load", "-w", str(plist_path)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "launchctl load thất bại")


def uninstall_schedule(schedule_id):
    plist_path = _plist_path(schedule_id)
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", "-w", str(plist_path)], capture_output=True)
        plist_path.unlink()
