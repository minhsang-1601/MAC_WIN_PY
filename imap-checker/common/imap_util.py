#!/usr/bin/env python3
"""Kết nối IMAP dùng chung — mở SSL, đăng nhập, chọn hộp thư.

Gom lại đoạn ``IMAP4_SSL + login + select`` vốn lặp ở check_gmail / getbody /
clean / check_all. Host/port suy theo domain qua ``common.providers``.
"""
import imaplib

from common.providers import resolve_imap_host, get_provider

MAILBOX = "INBOX"


def open_imap(email_addr, password, readonly=False, mailbox=MAILBOX):
    """Mở kết nối IMAP đã đăng nhập + đã select hộp thư.

    - Suy host/port theo domain (Gmail/Yahoo) qua ``resolve_imap_host``.
    - Gmail: nếu select hộp mặc định lỗi thì thử ``[Gmail]/All Mail``
      (giữ đúng hành vi cũ của clean_mail).
    - Raise nguyên exception của imaplib/ValueError để nơi gọi tự xử/log.

    Trả về đối tượng ``imaplib.IMAP4_SSL`` đã sẵn sàng.
    """
    host, port = resolve_imap_host(email_addr)
    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(email_addr, password)

    status, _ = imap.select(mailbox, readonly=readonly)
    if status != "OK" and get_provider(email_addr) == "gmail":
        # Chỉ Gmail có hộp ảo "All Mail" để fallback.
        status, _ = imap.select('"[Gmail]/All Mail"', readonly=readonly)
    if status != "OK":
        raise RuntimeError(f"Không truy cập được hộp thư ({mailbox}).")
    return imap
