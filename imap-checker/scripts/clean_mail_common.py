import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.paths import LOG_DIR, ACCOUNT_DIR
from common.imap_util import open_imap
from common.accounts import read_account_lines

LOG_DIR.mkdir(parents=True, exist_ok=True)
# Ngày hiện tại hiển thị: 2026-01-15
current_date = datetime.date.today().strftime("%Y-%m-%d")
PROCESS_LOG_FILE = LOG_DIR / f"Clean_mail_{current_date}.log"


def xoa_mail(email_addr, app_password, months_to_keep):
    mail = None
    try:
        print(f"==> Dang dang nhap: {email_addr}...")
        # open_imap: login + select INBOX (fallback [Gmail]/All Mail cho Gmail).
        mail = open_imap(email_addr, app_password)

        # LOGIC TINH TOAN THEO THANG & DINH DANG YYYY-MM-DD
        if months_to_keep == 0:
            search_query = "ALL"
            print(f"    Che do: Xoa TOAN BO email.")
        else:
            # Tinh ngay cat (cutoff date)
            days = months_to_keep * 30
            cutoff_dt = datetime.date.today() - datetime.timedelta(days=days)

            # Gmail IMAP bat buoc dung dinh dang DD-Mon-YYYY trong cau lenh query
            # Nhung chung ta se hien thi ra man hinh la YYYY-MM-DD
            search_date_imap = cutoff_dt.strftime("%d-%b-%Y")
            display_date = cutoff_dt.strftime("%Y-%m-%d")

            search_query = f'SENTBEFORE {search_date_imap}'
            print(f"    Che do: Xoa email truoc ngay: {display_date} (Cu hon {months_to_keep} thang)")

        status, messages = mail.search(None, search_query)

        if status == "OK":
            email_ids = messages[0].split()
            count = len(email_ids)

            if count > 0:
                print(f"    Tim thay {count} email. Dang xoa...")
                for num in email_ids:
                    mail.store(num, '+FLAGS', '\\Deleted')

                mail.expunge()
                msg = f"Thanh cong: Da xoa {count} email."
            else:
                msg = "Hop thu sach (khong co email thoa dieu kien)."

            print(f"    {msg}")
            with open(PROCESS_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {email_addr} | {msg}\n")

    except Exception as e:
        print(f"    [!] LOI: {e}")
    finally:
        if mail:
            try:
                mail.logout()
            except:
                pass

def main():
    print(f"\n--- MAIL CLEANER (Gmail/Yahoo) 2026 | Ngay: {current_date} ---")

    if len(sys.argv) < 3:
        print("Su dung: python3 clean_mail_common.py <file_txt> <so_thang>")
        return

    file_name = sys.argv[1]
    months = int(sys.argv[2])
    file_path = ACCOUNT_DIR / file_name

    if not file_path.exists():
        print(f"Loi: Khong tim thay file {file_path}")
        return

    accounts = read_account_lines(file_path)
    print(f"Doc file: {file_name} ({len(accounts)} tai khoan)\n")

    for acc, pwd in accounts:
        xoa_mail(acc, pwd, months)

    print("\n--- HOAN TAT ---")

if __name__ == "__main__":
    main()
