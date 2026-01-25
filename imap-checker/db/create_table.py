import sqlite3

def create_database():
    conn = sqlite3.connect('pokemon_data.db')
    cursor = conn.cursor()
    
    # Tạo bảng với các cột cần thiết
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        pass_web01 TEXT NOT NULL,
        pass_gm01 TEXT NOT NULL,
        proxy TEXT,            -- Lưu IP proxy riêng cho mỗi nick
        cookies TEXT,          -- Lưu chuỗi Cookie sau khi login thành công
        user_agent TEXT,       -- Lưu thông tin trình duyệt để tránh bị lộ
        last_login TEXT,       -- Lưu ngày giờ đăng nhập gần nhất
        status TEXT DEFAULT 'new' -- Trạng thái: new, active, banned
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Đã khởi tạo bảng dữ liệu thành công.")

create_database()
