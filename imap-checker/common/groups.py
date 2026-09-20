#!/usr/bin/env python3
"""Danh sách gốc (một file account DUY NHẤT) + các NHÓM mail (subset chọn từ gốc).

Nguyên tắc: trên đĩa CHỈ tồn tại một file danh sách account (danh sách gốc).
Nhóm KHÔNG sinh ra file nào — chỉ là một lựa chọn email lưu trong
``context/groups.json``. Khi chạy job, truyền tên nhóm qua biến môi trường
``IMAP_GROUP`` (hoặc danh sách email ad-hoc qua ``IMAP_EMAILS``) để script tự
lọc account đọc từ danh sách gốc — kể cả khi launchd chạy lúc app đã tắt.
"""
import json
import os

from common.paths import CONTEXT_DIR
from common.accounts import read_account_lines

GROUPS_PATH = CONTEXT_DIR / "groups.json"

# Tên biến môi trường để chọn nhóm / danh sách email khi chạy script.
ENV_GROUP = "IMAP_GROUP"
ENV_EMAILS = "IMAP_EMAILS"


def load_groups():
    """Trả về dict {'master_file': str, 'groups': [{'name','emails'}]}."""
    if not GROUPS_PATH.exists():
        return {"master_file": "", "groups": []}
    try:
        data = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"master_file": "", "groups": []}
    data.setdefault("master_file", "")
    data.setdefault("groups", [])
    return data


def save_groups(data):
    GROUPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GROUPS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_master_file():
    return load_groups().get("master_file", "")


def set_master_file(path):
    data = load_groups()
    data["master_file"] = str(path)
    save_groups(data)


def list_groups():
    return load_groups().get("groups", [])


def master_accounts():
    """dict {email: password} từ danh sách gốc. Chưa chọn/không có → {}."""
    mf = get_master_file()
    if not mf:
        return {}
    result = {}
    for email_addr, pwd in read_account_lines(mf):
        result[email_addr] = pwd
    return result


def group_emails(name):
    """Danh sách email của một nhóm (theo groups.json). Không có → []."""
    g = next((g for g in list_groups() if g.get("name") == name), None)
    return list((g or {}).get("emails", []))


def accounts_for(group_name=None, emails=None):
    """Trả về list[(email, password)] từ danh sách gốc, lọc theo:
      - ``emails`` (danh sách email ad-hoc) nếu có; hoặc
      - ``group_name`` (một nhóm đã lưu) nếu có; hoặc
      - toàn bộ danh sách gốc nếu cả hai đều rỗng.
    Email không có trong gốc bị bỏ qua (không có mật khẩu để dùng).
    """
    master = master_accounts()
    if emails:
        want = list(emails)
    elif group_name:
        want = group_emails(group_name)
    else:
        return list(master.items())
    return [(e, master[e]) for e in want if e in master]


def accounts_from_env():
    """Đọc bộ lọc từ biến môi trường (dùng trong script CLI / launchd).
    IMAP_EMAILS='a@x,b@y' ưu tiên; nếu không có thì IMAP_GROUP='Tên nhóm'.
    Không set gì → None (nghĩa là dùng toàn bộ file như cũ)."""
    raw_emails = (os.environ.get(ENV_EMAILS) or "").strip()
    if raw_emails:
        emails = [e.strip() for e in raw_emails.split(",") if e.strip()]
        return accounts_for(emails=emails)
    grp = (os.environ.get(ENV_GROUP) or "").strip()
    if grp:
        return accounts_for(group_name=grp)
    return None
