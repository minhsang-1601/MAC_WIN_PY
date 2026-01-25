import sqlite3
import os

def bulk_insert_gmails(file_path, db_path):
    # 1. Kết nối Database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tạo bảng nếu chưa có (khớp với cấu trúc của bạn)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            pass_web01 TEXT NOT NULL,
            pass_gm01 TEXT NOT NULL,
            proxy TEXT,
            cookies TEXT,
            user_agent TEXT,
            last_login TEXT,
            status TEXT DEFAULT 'new'
        )
    ''')
    
    accounts_to_import = []
    
    print(f"Đang đọc file: {file_path}")
    
    try:
        # 2. Đọc file text
        if not os.path.exists(file_path):
            print(f"Lỗi: Không tìm thấy file tại {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    # Tách tất cả các phần ngăn cách bởi dấu phẩy
                    parts = line.split(',')
                    
                    # Kiểm tra xem dòng có đủ ít nhất 3 cột (email, pass_web, pass_gm)
                    if len(parts) >= 3:
                        email = parts[0].strip()
                        pass_web = parts[1].strip()
                        pass_gm = parts[2].strip()
                        
                        accounts_to_import.append((email, pass_web, pass_gm))
                    else:
                        print(f"Bỏ qua dòng sai định dạng: {line}")
        
        # 3. Câu lệnh SQL nạp vào 3 cột cụ thể
        query = "INSERT OR IGNORE INTO accounts (email, pass_web01, pass_gm01) VALUES (?, ?, ?)"
        
        if accounts_to_import:
            cursor.executemany(query, accounts_to_import)
            # 4. Xác nhận lưu
            conn.commit()
            print(f"--- THÀNH CÔNG ---")
            print(f"Đã nạp thành công {cursor.rowcount} tài khoản mới vào DB!")
        else:
            print("Không có dữ liệu hợp lệ để nạp.")

    except Exception as e:
        print(f"Lỗi hệ thống: {e}")
        conn.rollback()
    finally:
        conn.close()

# --- THỰC HIỆN CHẠY ---
# Đường dẫn file trên MacBook của bạn
txt_path = '/Users/minhsang1601/MAC_WIN_PY/imap-checker/context/account.txt'
db_path = 'pokemon_data.db'

bulk_insert_gmails(txt_path, db_path)
