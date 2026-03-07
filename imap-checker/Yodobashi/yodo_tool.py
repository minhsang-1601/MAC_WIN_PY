import asyncio
import sys
from playwright.async_api import async_playwright

async def auto_order(email, password, product_url):
    async with async_playwright() as p:
        user_data_dir = "./yodobashi_profile"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # SỬA LỖI TẠI ĐÂY: Lấy tab đầu tiên từ danh sách
        page = context.pages[0] if context.pages else await context.new_page()

        # --- BƯỚC 1: TRUY CẬP TRANG CHỦ VÀ BẤM LOGIN ---
        print("[*] Đang vào trang chủ...")
        await page.goto("https://www.yodobashi.com", wait_until="domcontentloaded")
        
        try:
            # Tìm chữ 'ログイン' trên menu để sang trang nhập ID/Pass
            login_link = page.locator("a:has-text('ログイン')").first
            await login_link.wait_for(state="visible", timeout=10000)
            await login_link.click()
            print("=> Đã bấm chuyển sang trang đăng nhập.")
            
            # --- BƯỚC 2: ĐIỀN THÔNG TIN VÀ NHẤN ENTER ---
            await page.wait_for_selector("input[name='memberId']", timeout=10000)
            await page.fill("input[name='memberId']", email)
            await page.fill("input[name='password']", password)
            
            print("=> Đang thực hiện đăng nhập bằng phím ENTER...")
            await asyncio.sleep(1) # Chờ 1s cho web nhận diện chữ đã điền
            await page.keyboard.press("Enter")
            
            # Đợi 5 giây xem có nhảy trang thành công không
            await asyncio.sleep(5)
            if "login" in page.url:
                print("(!) Vẫn ở trang Login. Vui lòng tự lấy chuột nhấn nút đỏ hoặc giải CAPTCHA!")
                while "login" in page.url:
                    await asyncio.sleep(2)
            
            print("==> ĐĂNG NHẬP XONG!")
        except Exception as e:
            print(f"[-] Đã login sẵn hoặc gặp lỗi: {e}")

        # --- BƯỚC 3: QUÉT SẢN PHẨM ---
        print(f"[*] Đang quét hàng: {product_url}")
        while True:
            try:
                await page.goto(product_url, wait_until="domcontentloaded")
                add_btn = page.locator("#JS_addToCartBtn")
                
                if await add_btn.is_visible() and await add_btn.is_enabled():
                    print("!!! CÓ HÀNG - CLICK MUA !!!")
                    await add_btn.click(force=True)
                    
                    await asyncio.sleep(1)
                    await page.goto("https://secure.yodobashi.com")
                    
                    next_btn = page.locator(".p-cart_nextBtn")
                    await next_btn.wait_for(state="visible", timeout=10000)
                    await next_btn.click()
                    
                    print("==> Đã đến bước xác nhận cuối cùng!")
                    break 
                else:
                    print("[-] Chưa có hàng... F5")
                    await asyncio.sleep(1.5)
            except:
                await asyncio.sleep(2)

        await asyncio.sleep(600)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Gõ: python yodo_tool.py <Email> <Pass> <URL>")
        sys.exit(1)
        
    asyncio.run(auto_order(sys.argv[1], sys.argv[2], sys.argv[3]))
