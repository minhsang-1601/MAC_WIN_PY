import sqlite3

try:
    # Kết nối tới file (nếu chưa có sẽ tự tạo mới)
    conn = sqlite3.connect('pokemon_data.db')
    print("Kết nối SQLite thành công! Phiên bản:", sqlite3.version)
    conn.close()
except sqlite3.Error as e:
    print(f"Lỗi kết nối: {e}")
