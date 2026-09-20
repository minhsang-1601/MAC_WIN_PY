#!/usr/bin/env python3
"""Giải mã tiêu đề + lấy body text của email — dùng chung cho mọi script check mail.

Trước đây 3 script tự chép lại các hàm này với vài dị bản khác nhau. Gom về
một bản duy nhất:

- ``decode_mime_words``: bản ``make_header`` + chuẩn hoá Unicode NFC (bản vốn
  dùng ở check_mail_all_common — tốt nhất cho tiếng Nhật/Việt).
- ``get_email_body``: lấy phần text/plain đầu tiên, ``errors="replace"`` để
  không nuốt mất ký tự.
"""
import unicodedata
from email.header import decode_header, make_header


def decode_mime_words(s):
    """Giải mã header MIME (Subject/From...) về str, chuẩn hoá NFC.

    Lỗi giải mã → trả nguyên chuỗi vào (không làm hỏng luồng).
    """
    if not s:
        return ""
    try:
        decoded = str(make_header(decode_header(s)))
        return unicodedata.normalize("NFC", decoded)
    except Exception:
        return s


def get_email_body(msg):
    """Trả về nội dung text/plain của email (str). Không có thì trả "".

    Multipart: lấy part text/plain đầu tiên không phải attachment.
    """
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    return ""
