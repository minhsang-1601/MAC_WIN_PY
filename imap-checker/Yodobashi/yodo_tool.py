import asyncio
import sys
from playwright.async_api import async_playwright

async def auto_order(email, password, product_url):
    async with async_playwright() as p:
        user_data_dir = "./yodo_profile_final"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-http2", 
                "--disable-quic",
                "--no-sandbox"
            ],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        page.set_default_timeout(60000)

        print("[*] Đang kết nối tới Yodobashi...")
        try:
            await page.goto("https://www.yodobashi.com/", wait_until="commit")
            
            # --- KIỂM TRA VÀ ĐĂNG NHẬP (DÙNG CSS) ---
            login_link = page.locator("a:has-text('ログイン')").first
            # Nếu thấy chữ ログイン trong 5s thì mới làm bước đăng nhập
            if await login_link.is_visible(timeout=5000):
                print("=> Thấy nút Login, đang tiến hành...")
                await login_link.click()
                await page.wait_for_selector("input[name='memberId']", timeout=10000)
                await page.fill("input[name='memberId']", email)
                await page.fill("input[name='password']", password)
                await page.keyboard.press("Enter")
                await asyncio.sleep(5)
                print("==> ĐĂNG NHẬP XONG!")
            else:
                print("[-] Không thấy chữ Login, bỏ qua...")

        except Exception:
            print("[-] Đã đăng nhập hoặc lỗi tải trang, chuyển sang săn hàng...")

        # --- BƯỚC 3: QUÉT SẢN PHẨM & THANH TOÁN (DÙNG CSS) ---
        print(f"[*] Đang quét hàng: {product_url}")
        while True:
            try:
                await page.goto(product_url, wait_until="commit")
                # CSS Selector cho nút đỏ "Cho vào giỏ hàng"
                add_btn = page.locator("#JS_addToCartBtn")
                
                if await add_btn.is_visible() and await add_btn.is_enabled():
                    print("!!! THẤY NÚT ĐỎ - CLICK GIỎ HÀNG !!!")
                    await add_btn.click(force=True)
                    
                    await asyncio.sleep(1.5)
                    await page.goto("https://secure.yodobashi.com")
                    
                    # CSS Selector cho nút đỏ thanh toán trong giỏ
                    checkout_btn = page.locator(".p-cart_nextBtn")
                    await checkout_btn.wait_for(state="visible", timeout=10000)
                    await checkout_btn.click(force=True)
                    
                    print("==> THÀNH CÔNG! Đã đến trang cuối.")
                    break 
                else:
                    print("[-] Chưa có hàng... F5")
                    await asyncio.sleep(1.5)
            except:
                await asyncio.sleep(2)

        await asyncio.sleep(600)

if __name__ == "__main__":
    # Chạy: python yodo_tool.py <Email> <Pass> <URL>
    asyncio.run(auto_order(sys.argv[1], sys.argv[2], sys.argv[3]))
