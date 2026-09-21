#!/usr/bin/env python3
"""Đọc cấu hình mail gửi báo cáo (SEND_MAIL/mail_account.conf) + danh sách
email dùng được làm FROM/TO. Không phụ thuộc PyQt.
"""
from common.paths import MAIL_CONFIG_PATH
from common.providers import get_provider
from common.accounts import list_all_accounts


def _read_mail_conf():
    """Đọc file conf (Python exec) → dict. Không có/đọc lỗi → {}."""
    if not MAIL_CONFIG_PATH.exists():
        return {}
    try:
        cfg = {}
        exec(MAIL_CONFIG_PATH.read_text(encoding="utf-8"), {}, cfg)
        return cfg
    except Exception:
        return {}


def save_mail_config(sender, password, to_email):
    """Ghi SEND_MAIL/mail_account.conf (định dạng Python) làm FROM/TO mặc định
    khi gửi báo cáo. password là App Password của FROM (để SMTP đăng nhập)."""
    MAIL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# FROM/TO mặc định khi gửi mail báo cáo (KHÔNG commit).\n"
        f"SENDER_EMAIL = {sender!r}\n"
        f"APP_PASSWORD = {password!r}\n"
        f"TO_EMAILS = [{to_email!r}]\n"
    )
    MAIL_CONFIG_PATH.write_text(content, encoding="utf-8")


def get_mail_config_defaults():
    """(sender_email, to_email) mặc định từ mail_account.conf.

    Trả về (None, None) nếu chưa có file hoặc đọc lỗi.
    """
    cfg = _read_mail_conf()
    if not cfg:
        return None, None
    sender = cfg.get("SENDER_EMAIL")
    to_emails = cfg.get("TO_EMAILS") or []
    return sender, (to_emails[0] if to_emails else None)


def list_sendable_accounts():
    """Email đã biết + có mật khẩu + thuộc Gmail/Yahoo — dùng làm FROM khi gửi
    báo cáo (SMTP hỗ trợ cả Gmail lẫn Yahoo)."""
    accounts = list_all_accounts()
    return {e: p for e, p in accounts.items() if p and get_provider(e) is not None}


def list_accounts_with_password():
    """Mọi email đã biết có mật khẩu (không giới hạn provider) — dùng làm TO,
    vì người nhận không cần đăng nhập/xác thực gì cả."""
    accounts = list_all_accounts()
    return {e: p for e, p in accounts.items() if p}
