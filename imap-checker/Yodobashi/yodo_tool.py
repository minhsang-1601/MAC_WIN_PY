import asyncio
import sys
from playwright.async_api import async_playwright

async def auto_order(email, password, product_url):
    async with async_playwright() as p:
        user_data_dir = "./yodo_profile_final"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            # CẤU HÌNH QUAN TRỌNG: Ép tắt HTTP/2 và giả lập người dùng thật
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-http2",        # Sửa lỗi ERR_HTTP2_PROTOCOL_ERROR
                "--disable-quic",         # Sửa lỗi ERR_QUIC_PROTOCOL_ERROR
                "--no-sandbox",
                "--disable-extensions"
            ],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        # Tăng thời gian chờ lên 60s để vượt qua các bước kiểm tra của Web
        page.set_default_timeout(60000)

        print("[*] Đang kết nối tới Yodobashi...")
        try:
            # Dùng wait_until="commit" để thao tác ngay khi web phản hồi
            await page.goto("https://www.yodobashi.com/", wait_until="commit")
            
            # --- DÙNG CSS ĐỂ VÀO TRANG LOGIN ---
            print("=> Đang dùng CSS để nhấn nút Login...")
            login_link = page.locator("a:has-text('ログイン')").first
            await login_link.wait_for(state="visible", timeout=20000)
            await login_link.click()
            
            # --- ĐIỀN THÔNG TIN ---
            await page.wait_for_selector("input[name='memberId']", timeout=20000)
            await page.fill("input[name='memberId']", email)
            await page.fill("input[name='password']", password)
            await page.keyboard.press("Enter")
            
            print("==> ĐĂNG NHẬP THÀNH CÔNG!")
            await asyncio.sleep(5)

        except Exception as e:
            print(f"[!] Lỗi: {e}")
            # Nếu vẫn lỗi, bạn hãy tự tay F5 trình duyệt 1 lần xem có vào được không
            await asyncio.sleep(60)

        # (Các bước quét sản phẩm giữ nguyên như cũ...)
        # ...

if __name__ == "__main__":
    asyncio.run(auto_order(sys.argv[1], sys.argv[2], sys.argv[3]))
