import os
import sys
import time
import subprocess
from datetime import datetime

# ---------- TỰ ĐỘNG XÁC ĐỊNH ĐƯỜNG DẪN ----------
if os.name == 'nt':  # Windows
    HOME = os.path.expanduser("~")
    BASE_DIR = os.path.join(HOME, "MAC_WIN_PY", "imap-checker")
    PY_CMD = "python"
else:  # macOS / Linux
    BASE_DIR = os.path.expanduser("~/MAC_WIN_PY/imap-checker")
    PY_CMD = "python3"

SCRIPT_PATH = os.path.join(BASE_DIR, "scripts", "check_mail_all_common.py")
ACCOUNT_DIR = os.path.join(BASE_DIR, "account")
LOG_DIR = os.path.join(BASE_DIR, "LOG")

os.makedirs(LOG_DIR, exist_ok=True)

# ---------- INPUT LIST ----------
INPUT_FILES = [
    "accounts_gm_check_1",
    "accounts_gm_check_2",
    "accounts_gm_check_3",
    "accounts_gm_check_X",
]

# ---------- PARAM ----------
if len(sys.argv) < 2:
    print("❌ Thiếu SECTION")
    print("👉 Cách dùng: python run_multi.py Poke1")
    sys.exit(1)

SECTION = sys.argv[1]

# ---------- LOG FILE ----------
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

# ---------- RUN LOOP ----------
for fname in INPUT_FILES:
    input_path = os.path.join(ACCOUNT_DIR, fname)

    # ❌ Không tồn tại file
    if not os.path.exists(input_path):
        log(f"⚠️ Không tìm thấy file input: {input_path}")
        continue

    # ✅ File rỗng → skip
    if os.path.getsize(input_path) == 0:
        log(f"⏭️ File rỗng, bỏ qua: {input_path}")
        continue

    log("\n------------------------------------")
    log("▶️ Đang chạy:")
    log(f"    SECTION : {SECTION}")
    log(f"    INPUT   : {input_path}")
    log("------------------------------------")

    cmd = [
        PY_CMD,
        SCRIPT_PATH,
        SECTION,
        input_path
    ]

    try:
        ret = subprocess.call(cmd)
        log(f"✅ Process exit code: {ret}")
    except Exception as e:
        log(f"❌ Lỗi khi chạy process: {e}")

    log("⏳ Nghỉ 5 phút trước lượt tiếp theo ...")
    time.sleep(300)

log("\n✅ Đã chạy xong toàn bộ input!")
