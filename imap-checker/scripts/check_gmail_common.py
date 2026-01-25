#!/usr/bin/env python3
# check_gmail_dky.py

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
import sys
import os
import configparser
from pathlib import Path

# ============ CAU HINH TU DONG (CHAY DUOC CA MAC & WIN) ============
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
MAILBOX = "INBOX"

home = Path.home()
CONFIG_PATH = str(home / "MAC_WIN_PY" / "imap-checker" / "context" / "config.ini")
# ===================================================================

def decode_mime_words(s):
    if not s:
        return ""
    parts = decode_header(s)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            decoded.append(part)
    return ''.join(decoded)

def get_text_from_message(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and 'attachment' not in str(part.get('Content-Disposition')):
                payload = part.get_payload(decode=True) or b''
                charset = part.get_content_charset() or 'utf-8'
                return payload.decode(charset, errors='replace')
    else:
        payload = msg.get_payload(decode=True) or b''
        charset = msg.get_content_charset() or 'utf-8'
        return payload.decode(charset, errors='replace')
    return ""

def load_config(section_name=None):
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding='utf-8')

    if not config.sections():
        print(f"❌ Khong tim thay file config tai: {CONFIG_PATH}")
        sys.exit(1)

    if section_name is None:
        section_name = config.sections()[0]

    if section_name not in config:
        print(f"❌ Section [{section_name}] khong ton tai.")
        sys.exit(1)

    section = config[section_name]

    return (
        section.get("from", "").lower(),   # ✅ thêm FROM filter
        section.get("subject_title", ""),
        [k.strip() for k in section.get("keywords", "").split(",") if k.strip()],
        section.getint("recent_minutes", fallback=15),
        section.getint("max_results", fallback=1)
    )

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 check_gmail_dky.py <email> <password> [section]")
        sys.exit(2)

    email_user = sys.argv[1]
    password = sys.argv[2]
    section_name = sys.argv[3] if len(sys.argv) > 3 else None

    # ✅ nhận thêm from_filter
    from_filter, subject_title, keywords, recent_minutes, max_results = load_config(section_name)

    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(email_user, password)
        imap.select(MAILBOX, readonly=True)
    except Exception as e:
        print(f"❌ Loi IMAP: {e}")
        sys.exit(1)

    typ, data = imap.uid('search', None, 'ALL')
    uids = data[0].split()

    if not uids:
        print("📢 Hom thu (Mailbox) hien dang trong.")
        imap.logout()
        sys.exit(0)

    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(minutes=recent_minutes)
    results_found = 0

    # Duyệt ngược từ mail mới nhất (tối đa 500 mail gần đây)
    for uid in reversed(uids[-500:]):
        uid_str = uid.decode()
        try:
            typ, msg_data = imap.uid('fetch', uid_str, '(RFC822)')
            if typ != 'OK':
                continue

            raw = next((p[1] for p in msg_data if isinstance(p, tuple)), None)
            if not raw:
                continue

            msg = email.message_from_bytes(raw)
            msg_dt = parsedate_to_datetime(msg.get('Date'))
            if msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)

            # Nếu mail đã cũ hơn khoảng thời gian quy định thì dừng tìm kiếm
            if msg_dt < cutoff:
                break

            subject = decode_mime_words(msg.get('Subject', ''))
            from_addr = decode_mime_words(msg.get('From', '')).lower()

            # 1️⃣ Lọc theo FROM trước
            if from_filter and from_filter not in from_addr:
                continue

            # 2️⃣ Lọc theo SUBJECT
            if subject_title and subject_title not in subject:
                continue

            body = get_text_from_message(msg)
            found_keyword_in_mail = False
            lines_matched = []

            # 3️⃣ Lọc theo KEYWORDS trong BODY
            if keywords:
                for line in body.splitlines():
                    line = line.strip()
                    if any(k in line for k in keywords):
                        lines_matched.append(line)
                        found_keyword_in_mail = True
            else:
                found_keyword_in_mail = True

            if found_keyword_in_mail:
                results_found += 1
                print(f"==> Email {results_found} (UID {uid_str})")
                print(f"From   : {from_addr}")
                print(f"Subject: {subject}")
                for l in lines_matched:
                    print(f"Dòng tìm thấy: {l}")
                print("-" * 30)

            if results_found >= max_results:
                break

        except Exception as e:
            continue

    # Thông báo nếu không tìm thấy kết quả nào sau khi quét
    if results_found == 0:
        print(f"🚫 Khong tim thay mail nao khop dieu kien (trong {recent_minutes} phut qua).")

    imap.logout()
    print(f"------------------> DA CHECK XONG MAIL. <------------------")
    sys.exit(0)

if __name__ == "__main__":
    main()
