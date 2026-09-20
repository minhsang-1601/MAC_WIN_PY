#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.paths import PY_CMD, ACCOUNT_DIR as _ACCOUNT_DIR, LOG_DIR as _LOG_DIR, SCRIPT_CHECK_ALL

SCRIPT_PATH = str(SCRIPT_CHECK_ALL)
ACCOUNT_DIR = str(_ACCOUNT_DIR)
LOG_DIR = str(_LOG_DIR)
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- INPUT FILES ----------
INPUT_FILES = [
    "accounts_gm_check_1",
    "accounts_gm_check_2",
    "accounts_gm_check_3",
    "accounts_gm_check_4",
    "accounts_gm_check_5",
]

# ---------- THAM SỐ ----------
if len(sys.argv) < 2:
    print("❌ Thiếu SECTION")
    print("👉 Cách dùng: python run_multi.py Poke1")
    sys.exit(1)

SECTION = sys.argv[1]

# ---------- LOG ----------
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"run_multi_{SECTION}_{timestamp}.log")

def log(msg):
    msg = str(msg)
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

log("====================================")
log(f"LOG_FILE   : {LOG_FILE}")
log(f"SECTION    : {SECTION}")
log("====================================")

# ---------- Đếm số file có dữ liệu ----------
files_with_data = []
for fname in INPUT_FILES:
    path = os.path.join(ACCOUNT_DIR, fname)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        files_with_data.append(fname)

log(f"📊 Tổng số file có dữ liệu: {len(files_with_data)}")
log(f"📄 Danh sách file có dữ liệu: {files_with_data}")

# ---------- RUN LOOP ----------
for idx, fname in enumerate(INPUT_FILES):
    input_path = os.path.join(ACCOUNT_DIR, fname)

    # File không tồn tại hoặc rỗng → skip
    if not os.path.exists(input_path):
        log(f"⚠️ Không tìm thấy file input: {input_path}")
        continue
    if os.path.getsize(input_path) == 0:
        log(f"⏭️ File rỗng, bỏ qua: {input_path}")
        continue

    # Nếu tổng file có dữ liệu = 1 → chạy luôn
    if len(files_with_data) == 1:
        log(f"▶️ Chỉ có 1 file có dữ liệu, chạy ngay: {input_path}")
    else:
        # Nếu >1 file có dữ liệu → nghỉ 5 phút trước khi chạy (trừ file đầu tiên)
        if idx > 0:
            log(f"⏳ Có nhiều file có dữ liệu, nghỉ 5 phút trước khi chạy: {input_path}")
            time.sleep(300)
        else:
            log(f"▶️ File đầu tiên chạy ngay: {input_path}")

    # Chạy script
    log("\n------------------------------------")
    log(f"▶️ Đang chạy file: {input_path}")
    log("------------------------------------")
    cmd = [PY_CMD, SCRIPT_PATH, SECTION, input_path]

    try:
        ret = subprocess.call(cmd)
        log(f"✅ Process exit code: {ret}")
    except Exception as e:
        log(f"❌ Lỗi khi chạy process: {e}")

log("\n✅ Đã chạy xong toàn bộ input!")
