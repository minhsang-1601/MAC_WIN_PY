#!/usr/bin/env python3
"""Danh sách gốc (một file account) + các NHÓM mail (subset chọn từ gốc).

Nhóm KHÔNG phải file người dùng tạo — chỉ là một lựa chọn email từ danh sách
gốc, lưu trong ``context/groups.json``. Để launchd (chạy khi app đã tắt) vẫn
đọc được, app tự "vật chất hoá" mỗi nhóm thành một file ẩn trong
``account/_groups/<tên>.txt`` (email,password) mỗi khi lưu — người dùng không
thấy/không quản lý các file này.
"""
import json
import re

from common.paths import CONTEXT_DIR, ACCOUNT_DIR
from common.accounts import read_account_lines, write_account_lines

GROUPS_PATH = CONTEXT_DIR / "groups.json"
GROUPS_DIR = ACCOUNT_DIR / "_groups"


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


def _safe_name(name):
    return re.sub(r"[^0-9A-Za-z_.-]+", "_", name.strip()) or "nhom"


def group_file_path(name):
    return GROUPS_DIR / f"{_safe_name(name)}.txt"


def materialize_group(name):
    """Ghi file ẩn (email,password) cho nhóm ``name`` từ danh sách gốc.
    Trả về đường dẫn file (Path). Email không có trong gốc thì bỏ qua."""
    accounts = master_accounts()
    group = next((g for g in list_groups() if g.get("name") == name), None)
    emails = (group or {}).get("emails", [])
    rows = [(e, accounts[e]) for e in emails if e in accounts]
    GROUPS_DIR.mkdir(parents=True, exist_ok=True)
    path = group_file_path(name)
    write_account_lines(path, rows)
    return path


def materialize_all():
    """Sinh lại file ẩn cho MỌI nhóm (gọi sau khi lưu nhóm / lưu danh sách gốc)
    và dọn file ẩn của nhóm đã xoá."""
    GROUPS_DIR.mkdir(parents=True, exist_ok=True)
    wanted = set()
    for g in list_groups():
        wanted.add(group_file_path(g["name"]).name)
        materialize_group(g["name"])
    # Dọn file ẩn thừa (nhóm đã xoá)
    for p in GROUPS_DIR.iterdir():
        if p.is_file() and p.name not in wanted:
            try:
                p.unlink()
            except Exception:
                pass
