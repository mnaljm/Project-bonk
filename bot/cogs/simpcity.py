import os
import io
import logging
import json
import re
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

class MediaPuller(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        # SimpCity
        self.simpcity_username = os.getenv("SIMPCITY_USERNAME")
        self.simpcity_password = os.getenv("SIMPCITY_PASSWORD")
        # SocialMediaGirls
        self.smg_username = os.getenv("SMG_USERNAME")
        self.smg_password = os.getenv("SMG_PASSWORD")
        self.history_file = os.path.join("data", "simpcity_history.json")
        if not os.path.exists("data"):
            os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w") as f:
                json.dump([], f)
        
    @app_commands.command(name="link", description="Extract images from a forum thread (SimpCity or SocialMediaGirls)")
    @app_commands.describe(url="The URL of the thread")
    async def link(self, interaction: discord.Interaction, url: str):
        url_lower = url.lower()
        if "simpcity" not in url_lower and "socialmediagirls" not in url_lower:
            await interaction.response.send_message("Please provide a valid SimpCity or SocialMediaGirls URL.", ephemeral=True)
            return

        await interaction.response.defer()
        
        try:
            async with async_playwright() as p:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=os.path.abspath("playwright_data"),
                    headless=True,
                    viewport={"width": 1280, "height": 720}
                )
                try:
                    page = await context.new_page()
                    all_media_urls, cookies, user_agent = await self._do_scrape(page, url)
                    
                    if not all_media_urls:
                        await interaction.followup.send("No images or videos found on the page or extraction failed.")
                        return

                    with open(self.history_file, "r") as f:
                        history = set(json.load(f))
                        
                    normalized_urls = []
                    for m in all_media_urls:
                        if m.split("?")[0].lower().endswith(".ico"):
                            continue
                        if m.startswith("/"):
                            if "simpcity" in url_lower: m = "https://simpcity.cr" + m
                            elif "socialmediagirls" in url_lower: m = "https://socialmediagirls.com" + m
                        normalized_urls.append(m)
                    
                    media_urls = [m for m in normalized_urls if m not in history]
                    
                    if not media_urls:
                        await interaction.followup.send("No *new* images or videos found (all previously sent).")
                        return
                    
                    await interaction.followup.send(f"Found {len(media_urls)} new media files. Downloading and uploading...")
                    
                    files = []
                    embed_links = []
                    new_history = []
                    batch_count = 1
                    current_batch_size = 0
                    MAX_BATCH_SIZE = 22 * 1024 * 1024  # 22 MB safe limit
                    
                    async def send_current_batch():
                        nonlocal files, batch_count, current_batch_size, new_history, history
                        if files:
                            await interaction.followup.send(content=f"Batch {batch_count}:", files=files)
                            batch_count += 1
                            files.clear()
                            current_batch_size = 0
                            
                        if new_history:
                            history.update(new_history)
                            with open(self.history_file, "w") as f:
                                json.dump(list(history), f)
                            new_history.clear()

                    for idx, img_url in enumerate(media_urls):
                        try:
                            resp = await context.request.get(img_url, headers={"Referer": url})
                            if resp.status == 200:
                                content_type = resp.headers.get("content-type", "")
                                if "text/html" in content_type:
                                    embed_links.append(img_url)
                                    new_history.append(img_url)
                                else:
                                    data = await resp.body()
                                    file_size = len(data)
                                    
                                    if file_size == 0:
                                        self.logger.warning(f"0-byte file detected, skipping: {img_url}")
                                        continue
                                        
                                    if file_size > MAX_BATCH_SIZE:
                                        self.logger.warning(f"Skipping extremely large file: {img_url}")
                                        continue
                                        
                                    if current_batch_size + file_size > MAX_BATCH_SIZE or len(files) >= 10:
                                        await send_current_batch()
                                        
                                    filename = img_url.split("/")[-1].split("?")[0]
                                    if not filename or len(filename) > 50:
                                        ext = ".bin"
                                        if "image/jpeg" in content_type: ext = ".jpg"
                                        elif "image/png" in content_type: ext = ".png"
                                        elif "video/mp4" in content_type: ext = ".mp4"
                                        filename = f"media_file_{idx}{ext}"
                                        
                                    files.append(discord.File(fp=io.BytesIO(data), filename=filename))
                                    current_batch_size += file_size
                                    new_history.append(img_url)
                        except Exception as e:
                            self.logger.error(f"Failed to download media {img_url}: {e}")
                    
                    await send_current_batch()
                    
                    if embed_links:
                        for chunk in [embed_links[i:i + 5] for i in range(0, len(embed_links), 5)]:
                            await interaction.followup.send(content="Embedded Links:\n" + "\n".join(chunk))
                        history.update(embed_links)
                        with open(self.history_file, "w") as f:
                            json.dump(list(history), f)
                    
                    if batch_count == 1 and not embed_links:
                        await interaction.followup.send("Failed to download or upload any media files (they might have been too large or 0 bytes).")
                finally:
                    await context.close()
                    
        except Exception as e:
            self.logger.error(f"Error processing {url}: {e}")
            error_msg = f"An error occurred: {str(e)}"
            await interaction.followup.send(error_msg[:1990] + "..." if len(error_msg) > 1990 else error_msg)

    async def _do_scrape(self, page, base_url: str) -> tuple[List[str], List[dict], str]:
        self.logger.info(f"Navigating to {base_url}")
        
        is_simpcity = "simpcity" in base_url.lower()
        is_smg = "socialmediagirls" in base_url.lower()
        
        username = self.simpcity_username if is_simpcity else self.smg_username
        password = self.simpcity_password if is_simpcity else self.smg_password

        # Login process
        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            self.logger.warning(f"Initial navigation warning for {base_url}: {e}")
        await page.wait_for_timeout(3000)
        
        needs_login = await page.locator("a[href*='/login/']").count() > 0
        if needs_login and username and password:
            self.logger.info(f"Logging into {'SimpCity' if is_simpcity else 'SocialMediaGirls'}...")
            await page.locator("a[href*='/login/']").first.click()
            await page.wait_for_load_state("domcontentloaded")
            
            await page.fill('input[name="login"]', username)
            await page.fill('input[name="password"]', password)
            await page.click('button.button--icon--login')
            
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

        current_url = base_url
        if base_url not in page.url:
            current_url = page.url
            
        all_images = []
        all_videos = []
        all_external = []
        
        while current_url:
            self.logger.info(f"Scraping page: {current_url}")
            if page.url != current_url:
                try:
                    await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                except Exception as e:
                    self.logger.warning(f"Navigation warning for {current_url}: {e}")
                await page.wait_for_timeout(3000)
                
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            login_required_text = "Login or Register to view"
            if login_required_text in content:
                self.logger.warning(f"Detection of '{login_required_text}' on {current_url}")

            content_areas = soup.find_all("div", class_=["message-userContent", "bbWrapper", "message-body"])
            
            for area in content_areas:
                for img in area.find_all("img"):
                    if img.find_parent("a", class_="js-lbImage"): continue
                    src = img.get("src") or img.get("data-src")
                    if src and not src.startswith("data:") and "smilies" not in src.lower() and "emoji" not in src.lower():
                        all_images.append(src)
                
                for lb_img in area.find_all("a", class_="js-lbImage"):
                    src = lb_img.get("href") or lb_img.get("data-src")
                    if src and not src.startswith("data:"):
                        all_images.append(src)

                for video in area.find_all("video"):
                    src = video.get("src") or (video.find("source").get("src") if video.find("source") else None)
                    if src: all_videos.append(src)
                
                for iframe in area.find_all("iframe"):
                    src = iframe.get("src") or iframe.get("data-s9e-mediaembed-src")
                    if src: all_videos.append(src)
                        
                text_content = area.get_text()
                urls = re.findall(r'(https?://(?:www\.)?(?:gofile\.(?:io|com)|imgur\.com)[^\s\'"<>]+)', text_content)
                all_external.extend(urls)
                
                for a in area.find_all("a", href=True):
                    href = a["href"]
                    if "gofile.io" in href or "imgur.com" in href:
                        all_external.append(href)
                        
            # Check pagination
            next_btn = soup.find("a", class_="pageNav-jump--next")
            if next_btn and next_btn.get("href"):
                next_href = next_btn["href"]
                domain = "https://simpcity.cr" if is_simpcity else "https://forums.socialmediagirls.com"
                current_url = domain + next_href if next_href.startswith("/") else next_href
            else:
                current_url = None

        seen_ext = set()
        cleaned_external = [link for link in all_external if not (link in seen_ext or seen_ext.add(link))]
        
        if cleaned_external:
            self.logger.info(f"Identified {len(cleaned_external)} external links across all pages.")
            
        for ext_url in cleaned_external:
            try:
                self.logger.info(f"Navigating to external link: {ext_url}")
                gofile_api_links = []
                async def handle_response(response):
                    try:
                        url_str = response.url
                        if "gofile.io" in url_str and response.request.method != "OPTIONS":
                            text = await response.text()
                            extracted = re.findall(r'(https?(?:\\?/){2}srv-[a-zA-Z0-9-]+\.gofile\.io[^\s\'"<>,\}]+)', text)
                            gofile_api_links.extend(extracted)
                    except Exception:
                        pass
                        
                page.on("response", handle_response)
                try:
                    await page.goto(ext_url, wait_until="networkidle", timeout=60000)
                except Exception as e:
                    self.logger.warning(f"Navigation warning for external link {ext_url}: {e}")
                await page.wait_for_timeout(6000) 
                
                page.remove_listener("response", handle_response)
                
                ext_content = await page.content()
                ext_soup = BeautifulSoup(ext_content, "html.parser")
                
                try:
                    dom_links = await page.evaluate('''() => Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h.includes('srv-store'))''')
                    gofile_api_links.extend(dom_links)
                except Exception:
                    pass
                
                if gofile_api_links:
                    cleaned_gofile = [u.replace('\\', '') for u in gofile_api_links]
                    all_images.extend(cleaned_gofile)
                    self.logger.info(f"Intercepted {len(cleaned_gofile)} CDN API links from Gofile.")
                    
                if "imgur.com" in ext_url:
                    imgur_deep_links = re.findall(r'(https?://i\.imgur\.com/[a-zA-Z0-9]+\.(?:jpg|jpeg|png|gif|mp4))', ext_content)
                    all_images.extend(imgur_deep_links)
                    
                direct_cdn_links = re.findall(r'(https?://srv-[a-zA-Z0-9-]+\.gofile\.io/[^\s\'"<>]+)', ext_content)
                all_images.extend(direct_cdn_links)
                
                for img in ext_soup.find_all("img"):
                    src = img.get("src") or img.get("data-src")
                    if src and not src.startswith("data:") and "favicon" not in src.lower() and "logo" not in src.lower():
                        if "gofile.io/dist/" not in src:
                            all_images.append(src)
                            
                for video in ext_soup.find_all("video"):
                    src = video.get("src") or (video.find("source").get("src") if video.find("source") else None)
                    if src and not src.startswith("blob:"):
                        all_videos.append(src)
                        
                for a in ext_soup.find_all("a", href=True):
                    href = a["href"]
                    if href.lower().endswith((".mp4", ".jpg", ".jpeg", ".png", ".gif", ".m4v", ".webm")):
                        all_images.append(href)
                        
            except Exception as e:
                self.logger.error(f"Failed to scrape external link {ext_url}: {e}")

        seen_imgs = set()
        cleaned_images = [img for img in all_images if not (img in seen_imgs or seen_imgs.add(img))]
        seen_vids = set()
        cleaned_videos = [vid for vid in all_videos if not (vid in seen_vids or seen_vids.add(vid))]
        
        site_name = 'SimpCity' if is_simpcity else 'SocialMediaGirls'
        self.logger.info(f"Successfully scraped {len(cleaned_images)} images and {len(cleaned_videos)} videos from {site_name}")
        
        cookies = await page.context.cookies()
        user_agent = await page.evaluate("navigator.userAgent")
        return cleaned_images + cleaned_videos, cookies, user_agent

async def setup(bot):
    await bot.add_cog(MediaPuller(bot))
