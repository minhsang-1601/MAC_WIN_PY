import imaplib
import sys
import os
import datetime
from pathlib import Path

# ============ CAU HINH TU DONG (MAC & WIN) ============
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
MAILBOX = "INBOX" 

home = Path.home()
BASE_DIR = home / "MAC_WIN_PY" / "imap-checker"
LOG_DIR = BASE_DIR / "LOG"
CONTEXT_DIR = BASE_DIR / "account"

LOG_DIR.mkdir(parents=True, exist_ok=True)
# Ngày hiện tại hiển thị: 2026-01-15
current_date = datetime.date.today().strftime("%Y-%m-%d")
PROCESS_LOG_FILE = LOG_DIR / f"Clean_mail_{current_date}.log"
# ======================================================

def xoa_gmail(email, app_password, months_to_keep):
    mail = None
    try:
        print(f"==> Dang dang nhap: {email}...")
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        
        typ, data = mail.login(email, app_password)
        if typ != 'OK':
            print(f"    [!] That bai: Dang nhap khong thanh cong.")
            return

        status, data = mail.select(MAILBOX)
        if status != 'OK':
            status, data = mail.select('"[Gmail]/All Mail"')
            if status != 'OK':
                print("    [!] That bai: Khong truy cap duoc hop thu.")
                return

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
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {email} | {msg}\n")
        
    except Exception as e:
        print(f"    [!] LOI: {e}")
    finally:
        if mail:
            try:
                mail.logout()
            except:
                pass

def main():
    print(f"\n--- GMAIL CLEANER 2026 | Ngay: {current_date} ---")
    
    if len(sys.argv) < 3:
        print("Su dung: python3 clean_mail.py <file_txt> <so_thang>")
        return

    file_name = sys.argv[1]
    months = int(sys.argv[2])
    file_path = CONTEXT_DIR / file_name
    
    if not file_path.exists():
        print(f"Loi: Khong tim thay file {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
        
    print(f"Doc file: {file_name} ({len(lines)} tai khoan)\n")

    for line in lines:
        if "," in line:
            acc, pwd = line.split(",", 1)
            xoa_gmail(acc.strip(), pwd.strip(), months)

    print("\n--- HOAN TAT ---")

if __name__ == "__main__":
    main()
