import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def main():
    if len(sys.argv) < 2:
        print("Usage: python setup_login.py [simpcity|smg]")
        return
        
    target = sys.argv[1].lower()
    if target == "simpcity":
        url = "https://simpcity.cr/login/"
    elif target == "smg":
        url = "https://forums.socialmediagirls.com/login/"
    else:
        print("Unknown target. Use 'simpcity' or 'smg'.")
        return

    print(f"Launching browser for {url}...")
    print("Please log in, solve any captchas, and then close the browser window when you are fully logged in and see the main forum page.")
    
    async with async_playwright() as p:
        # Launch headed browser so user can interact
        context = await p.chromium.launch_persistent_context(
            user_data_dir=os.path.abspath("playwright_data"),
            headless=False,  # Visible browser
            viewport={"width": 1280, "height": 720}
        )
        
        page = await context.new_page()
        await page.goto(url)
        
        print("\nWaiting for you to close the browser...")
        # Wait until the user closes the context/browser
        while context.pages:
            await asyncio.sleep(1)
            
        print("Browser closed. Session saved to 'playwright_data'.")

if __name__ == "__main__":
    asyncio.run(main())
