#!/usr/bin/env python3
import email
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
import csv
import os
import sys
import subprocess
import time
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.paths import BASE_DIR, PY_CMD, CONFIG_PATH, LOG_DIR, SCRIPT_SEND
from common.config_ini import load_ini
from common.imap_util import open_imap
from common.mailparse import decode_mime_words, get_email_body
from common.accounts import read_account_lines
from common.groups import accounts_from_env

# Chuỗi hoá để phần code cũ (dùng os.path.join) khỏi phải đổi.
BASE_DIR = str(BASE_DIR)
CONFIG_PATH = str(CONFIG_PATH)
ACCOUNTS_PATH_DEFAULT = os.path.join(BASE_DIR, "account", "accounts_gm.txt")
RESULTS_DIR = str(LOG_DIR)
SEND_SCRIPT = str(SCRIPT_SEND)


def parse_args():
    if len(sys.argv) < 2:
        print("Sử dụng: python check_mail_all_common.py <SECTION> [ACCOUNTS_FILE] [SEND_FLAG (0/1)]")
        sys.exit(1)
    
    section = sys.argv[1]
    accounts_file = ACCOUNTS_PATH_DEFAULT
    send_flag = "1"

    if len(sys.argv) == 3:
        if sys.argv[2] in ["0", "1"]:
            send_flag = sys.argv[2]
        else:
            accounts_file = sys.argv[2]
    elif len(sys.argv) >= 4:
        accounts_file = sys.argv[2]
        send_flag = sys.argv[3]

    return section, accounts_file, send_flag


def read_accounts(path):
    if not os.path.exists(path):
        print(f"Không tìm thấy file accounts: {path}")
        sys.exit(1)
    return read_account_lines(path)


def safe_int(val, default):
    val = (val or "").strip()
    return int(val) if val.isdigit() else default


# =================== SEARCH + FILTER ===================

def search_and_collect(imap, account_email, section_cfg):
    # ===== FROM FILTER =====
    raw_from = (section_cfg.get("from") or "").strip()
    from_list = [f.strip().lower() for f in raw_from.split(",") if f.strip()]

    # ===== KEYWORDS =====
    raw_keywords = (section_cfg.get("keywords") or "").strip()
    keywords_list = [k.strip() for k in raw_keywords.split(",") if k.strip()]
    keywords_lower = [k.lower() for k in keywords_list]

    recent_minutes = safe_int(section_cfg.get("recent_minutes"), 0)
    max_results = safe_int(section_cfg.get("max_results"), 10)

    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=recent_minutes)

    imap.select("INBOX")
    status, data = imap.search(None, "ALL")
    if status != "OK":
        return results

    ids = data[0].split()
    for mid in reversed(ids):
        if len(results) >= max_results:
            break
        try:
            status, msg_data = imap.fetch(mid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            # ===== FILTER FROM (ƯU TIÊN ĐẦU TIÊN) =====
            from_header = decode_mime_words(msg.get("From", "")).lower()
            if from_list:
                matched_from = False
                for f in from_list:
                    if f in from_header:
                        matched_from = True
                        break
                if not matched_from:
                    continue   # ❌ Không đúng người gửi → skip

            # ===== FILTER TIME =====
            try:
                dt = parsedate_to_datetime(msg.get("Date"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)

            if recent_minutes > 0 and dt < cutoff:
                continue

            body = get_email_body(msg)
            subject = decode_mime_words(msg.get("Subject", ""))

            match_found = False
            kw_hit_map = {k: "" for k in keywords_list}
            lines = body.splitlines()

            # ===== OR LOGIC KEYWORD =====
            if keywords_list:
                for line in lines:
                    line_lower = line.lower()
                    for idx, kw in enumerate(keywords_lower):
                        if kw in line_lower:
                            match_found = True
                            original_kw = keywords_list[idx]
                            if not kw_hit_map[original_kw]:
                                kw_hit_map[original_kw] = line.strip()
            else:
                match_found = True

            if not match_found:
                continue

            row = {
                "gmail": account_email,
                "nguoi gui": decode_mime_words(msg.get("From", "")),
                "ngay gio gui": dt.isoformat(),
                "tieu de mail": subject,
                "ghi chu": ""
            }

            for kw in keywords_list:
                col_name = f"kw_{kw}"
                row[col_name] = kw_hit_map.get(kw, "")

            results.append(row)

        except Exception:
            pass

    return results


def rename_result_file(path):
    new_path = path.replace(".csv", "_check_xong.csv")
    try:
        os.rename(path, new_path)
        print(f"✅ Đã đổi tên file: {new_path}")
        return new_path
    except Exception:
        return None


# =================== THỐNG KÊ ===================

def count_keywords_in_subject(rows, keywords_csv):
    result = {}
    if not keywords_csv:
        return result

    keywords = [k.strip() for k in keywords_csv.split(",") if k.strip()]
    for kw in keywords:
        result[kw] = 0

    for row in rows:
        subject_val = (row.get("tieu de mail") or "").lower()
        for kw in keywords:
            result[kw] += subject_val.count(kw.lower())

    return result


def write_summary_txt(base_csv_path, section, section_cfg,
                      acc_name_no_ext, total_acc, error_count,
                      empty_success_count,
                      all_data_rows,
                      accounts_path):  # ✅ thêm accounts_path

    base_dir = os.path.dirname(base_csv_path)
    base_name = os.path.splitext(os.path.basename(base_csv_path))[0]
    txt_name = f"{base_name}_TongKet.txt"
    txt_path = os.path.join(base_dir, txt_name)

    subject_title   = section_cfg.get("subject_title", "")
    keywords         = section_cfg.get("keywords", "")
    recent_minutes   = section_cfg.get("recent_minutes", "")
    max_results      = section_cfg.get("max_results", "")
    keywords_count   = section_cfg.get("keywords_count", "")

    total_rows = len(all_data_rows)
    error_rows = error_count
    success = total_acc - error_rows

    kw_counter = count_keywords_in_subject(all_data_rows, keywords_count)

    lines = []
    lines.append("========== THÔNG TIN SECTION ==========")
    lines.append(f"SECTION             : {section}")
    lines.append(f"File input account  : {os.path.basename(accounts_path)}")  # ✅ thêm dòng này
    lines.append(f"subject_title       : {subject_title}")
    lines.append(f"keywords            : {keywords}")
    lines.append(f"recent_minutes      : {recent_minutes}")
    lines.append(f"max_results         : {max_results}")
    lines.append(f"keywords_count      : {keywords_count}")
    lines.append("")
    
    lines.append("========== KẾT QUẢ ==========")
    lines.append(f"Tổng số account                 : {total_acc}")
    lines.append(f"Số account login lỗi            : {error_rows}/{total_acc}")
    lines.append(f"Số account login thành công     : {success}/{total_acc}")
    lines.append(f"Số account không có mail        : {empty_success_count}")
    lines.append(f"Số mail tìm thấy                : {total_rows - error_rows - empty_success_count}")
    lines.append("")

    lines.append("========== ĐẾM KEYWORDS_COUNT ==========")
    if kw_counter:
        for kw, cnt in kw_counter.items():
            lines.append(f"{kw} : {cnt}")
    else:
        lines.append("Không cấu hình keywords_count")

    lines.append("")
    lines.append(f"Thời gian tạo : {datetime.now().isoformat()}")
    lines.append("=" * 50)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"📝 Đã tạo file tổng kết: {txt_path}")
    return txt_path


# =================== GỬI MAIL ===================

def call_send_script(result_file, summary_file):
    if not os.path.exists(SEND_SCRIPT):
        print(f"⚠️ Không tìm thấy script gửi: {SEND_SCRIPT}")
        return
    try:
        subprocess.run(
            [PY_CMD, SEND_SCRIPT, result_file, summary_file],
            check=True
        )
        print("📤 Đã gọi script gửi (CSV + TXT).")
    except Exception as e:
        print(f"❌ Lỗi khi gửi: {e}")


# =================== MAIN ===================

def main():
    section, accounts_path, send_flag = parse_args()
    acc_basename = os.path.basename(accounts_path)
    acc_name_no_ext = os.path.splitext(acc_basename)[0]

    if not os.path.isabs(accounts_path):
        accounts_path = os.path.join(BASE_DIR, "account", accounts_path)

    cfg = load_ini()
    if section not in cfg:
        print(f"Không thấy section [{section}] trong config.ini")
        sys.exit(1)

    raw_keywords = (cfg[section].get("keywords") or "").strip()
    keywords_list = [k.strip() for k in raw_keywords.split(",") if k.strip()]
    keyword_columns = [f"kw_{k}" for k in keywords_list]

    error_count = 0
    empty_success_count = 0
    # Ưu tiên bộ lọc nhóm/email qua biến môi trường (IMAP_GROUP/IMAP_EMAILS):
    # chạy đúng subset của danh sách gốc, KHÔNG cần file account riêng.
    # Không set gì → đọc file account như cũ (tương thích ngược).
    accounts = accounts_from_env()
    if accounts is None:
        accounts = read_accounts(accounts_path)
    all_data_rows = []
    stt = 1
    total_acc = len(accounts)

    for idx, (email_addr, pwd) in enumerate(accounts, 1):
        print(f"Processing {idx}/{total_acc}: {email_addr}", end="", flush=True)
        try:
            imap = open_imap(email_addr, pwd)
            matches = search_and_collect(imap, email_addr, cfg[section])
            print(f"\n[{email_addr}] -> Tìm thấy {len(matches)} mail.")

            if not matches:
                empty_success_count += 1

                empty_row = {
                    "stt": stt,
                    "gmail": email_addr,
                    "nguoi gui": "",
                    "ngay gio gui": "",
                    "tieu de mail": "",
                    "ghi chu": "Không thấy mail"
                }
                for col in keyword_columns:
                    empty_row[col] = ""
                all_data_rows.append(empty_row)
                stt += 1
            else:
                for m in matches:
                    m["stt"] = stt
                    all_data_rows.append(m)
                    stt += 1

            imap.logout()

        except Exception as e:
            error_count += 1
            print(f" -> err ({e})")
            error_row = {
                "stt": stt,
                "gmail": email_addr,
                "nguoi gui": "",
                "ngay gio gui": "",
                "tieu de mail": "",
                "ghi chu": str(e)
            }
            for col in keyword_columns:
                error_row[col] = "LOGIN ERROR"
            all_data_rows.append(error_row)
            stt += 1

        if idx < total_acc:
            wait_time = random.randint(5, 15)
            for i in range(wait_time, 0, -1):
                print(f"\r   ⏳ Chờ {i} giây...", end="", flush=True)
                time.sleep(1)
            print("\r" + " " * 30 + "\r", end="", flush=True)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{section}_{acc_name_no_ext}_{ts}.csv"
    out_path = os.path.join(RESULTS_DIR, out_name)

    fieldnames = ["stt", "gmail"] + keyword_columns + [
        "nguoi gui",
        "ngay gio gui",
        "tieu de mail",
        "ghi chu"
    ]

    try:
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            dict_writer = csv.DictWriter(f, fieldnames=fieldnames)
            dict_writer.writerows(all_data_rows)

        print(f"📄 Kết quả lưu tại: {out_path}")

        final_file = rename_result_file(out_path)

        summary_file = None
        if final_file:
            summary_file = write_summary_txt(
                final_file,
                section,
                cfg[section],
                acc_name_no_ext,
                total_acc,
                error_count,
                empty_success_count,
                all_data_rows,
                accounts_path  # ✅ thêm accounts_path
            )

        if final_file and summary_file and send_flag == "1":
            call_send_script(final_file, summary_file)
        else:
            print("⏭️ Skip gửi mail (Flag = 0).")

    except Exception as e:
        print(f"❌ Lỗi ghi file: {e}")


if __name__ == "__main__":
    main()
