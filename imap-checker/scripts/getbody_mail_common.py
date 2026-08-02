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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.providers import resolve_imap_host

# ============ CAU HINH TU DONG (CHAY DUOC CA MAC & WIN) ============
MAILBOX = "INBOX"

home = Path.home()
# Đảm bảo đường dẫn này chính xác trên máy của bạn
CONFIG_PATH = str(home / "MAC_WIN_PY" / "imap-checker" / "context" / "config.ini")
# ===================================================================

def decode_mime_words(s):
    if not s: return ""
    parts = decode_header(s)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            decoded.append(part)
    return ''.join(decoded)

def get_text_from_message(msg):
    """Lấy nội dung văn bản thuần túy từ email"""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))
            if content_type == "text/plain" and 'attachment' not in content_disposition:
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
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ Khong tim thay file config tai: {CONFIG_PATH}")
        sys.exit(1)
        
    config.read(CONFIG_PATH, encoding='utf-8')
    if not config.sections():
        print(f"❌ File config trong hoặc sai định dạng.")
        sys.exit(1)
        
    if section_name is None:
        section_name = config.sections()[0]
    if section_name not in config:
        print(f"❌ Section [{section_name}] khong ton tai.")
        sys.exit(1)

    section = config[section_name]
    return (
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

    subject_title, keywords, recent_minutes, max_results = load_config(section_name)

    try:
        # Tham khảo tài liệu IMAP tại: https://docs.python.org
        host, port = resolve_imap_host(email_user)
        imap = imaplib.IMAP4_SSL(host, port)
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

    # Duyệt ngược từ mail mới nhất
    for uid in reversed(uids[-500:]):
        uid_str = uid.decode()
        try:
            typ, msg_data = imap.uid('fetch', uid_str, '(RFC822)')
            if typ != 'OK': continue
            raw = next((p[1] for p in msg_data if isinstance(p, tuple)), None)
            if not raw: continue

            msg = email.message_from_bytes(raw)
            msg_dt = parsedate_to_datetime(msg.get('Date'))
            if msg_dt.tzinfo is None: msg_dt = msg_dt.replace(tzinfo=timezone.utc)

            # Nếu mail cũ hơn thời gian quy định thì dừng
            if msg_dt < cutoff: break 

            subject = decode_mime_words(msg.get('Subject', ''))
            
            # Kiểm tra tiêu đề
            if subject_title and subject_title not in subject: 
                continue

            body = get_text_from_message(msg)
            
            # Kiểm tra từ khóa trong Body
            found_match = False
            if keywords:
                if any(k in body for k in keywords):
                    found_match = True
            else:
                found_match = True

            if found_match:
                results_found += 1
                print(f"==> Email {results_found} (UID {uid_str})")
                print(f"Subject: {subject}")
                print(f"Thời gian: {msg_dt}")
                
                print("*" * 15 + "***************" + "*" * 15)
                print("-" * 15 + " NỘI DUNG BODY " + "-" * 15)
                print("*" * 15 + "***************" + "*" * 15)
                print(body.strip())
                print("-" * 45)

            if results_found >= max_results: break
        except Exception as e:
            print(f"⚠️ Lỗi xử lý Email UID {uid_str}: {e}")
            continue

    if results_found == 0:
        print(f"🚫 Khong tim thay mail nao khop dieu kien trong {recent_minutes} phut qua.")

    imap.logout()
    print(f"------------------> DA CHECK XONG MAIL. <------------------")
    sys.exit(0)

if __name__ == "__main__":
    main()
