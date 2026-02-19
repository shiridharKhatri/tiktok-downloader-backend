import concurrent.futures
import threading
import time
import os
import re
import requests
import json
import random
import asyncio
import aiohttp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# List of modern User Agents to rotate
USER_AGENTS = [
    "com.zhiliaoapp.musically/2022405040 (Linux; U; Android 10; en_US; Pixel 4)",
    "com.ss.android.ugc.trill/494 (Linux; U; Android 12; en_US; Pixel 6 Pro)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
]

class TikTokDownloader:
    def __init__(self, headless=True):
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.driver = None
        self.proxies = [] 
        self.session = requests.Session()
        self.cache = {} # Simple in-memory cache: {url: (video_url, referer, expiry)}
        self.cache_lock = threading.Lock()

    def _get_headers(self, is_mobile=True):
        ua = random.choice(USER_AGENTS)
        headers = {
            "User-Agent": ua,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if not is_mobile:
            headers["Referer"] = "https://www.tiktok.com/"
        return headers

    def _init_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.chrome_options)

    def _close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except: pass
            self.driver = None

    async def fetch_direct_api(self, session, api_root, video_id):
        params = {
            "aweme_id": video_id,
            "iid": "7318518857994389254",
            "device_id": str(random.randint(7318517321748022790, 7318517321748022999)),
            "channel": "googleplay",
            "app_name": "musically_go",
            "version_code": "300704",
            "device_platform": "android",
            "device_type": "pixel+4",
            "os_version": "12"
        }
        try:
            async with session.get(api_root, params=params, headers=self._get_headers(is_mobile=True), timeout=2) as res:
                data = await res.json()
                if "aweme_list" in data and data["aweme_list"]:
                    item = data["aweme_list"][0]
                    # Extract Metadata
                    info = {
                        "id": item.get("aweme_id"),
                        "title": item.get("desc"),
                        "cover": item.get("video", {}).get("cover", {}).get("url_list", [None])[0],
                        "author": {
                            "nickname": item.get("author", {}).get("nickname"),
                            "avatar": item.get("author", {}).get("avatar_thumb", {}).get("url_list", [None])[0]
                        }
                    }
                    
                    # Check for Images (Slideshow)
                    if "image_post_info" in item:
                        images = []
                        for img in item["image_post_info"].get("display_image_list", []):
                            url_list = img.get("display_image", {}).get("url_list", [])
                            if url_list: images.append(url_list[0])
                        info["images"] = images
                        return info, None

                    # Video Info
                    video = item.get("video", {})
                    play_addr = video.get("play_addr", {})
                    urls = play_addr.get("url_list", [])
                    if urls:
                        info["play"] = urls[0]
                        return info, None
        except: pass
        return None, None

    async def fetch_provider(self, session, provider_info, tiktok_url):
        api_url, param, key = provider_info
        try:
            if "lovetik" in api_url:
                async with session.post(api_url, data={param: tiktok_url}, timeout=3) as res:
                    data = await res.json()
                    if data.get("status") == "ok":
                        info = {
                            "id": data.get("vid"),
                            "title": data.get("desc"),
                            "cover": data.get("cover"),
                            "author": {"nickname": data.get("author"), "avatar": data.get("author_a")}
                        }
                        # Lovetik handles images by returning multiple links
                        images = [l.get("a") for l in data.get("links", []) if l.get("t") == "Photo"]
                        if images:
                            info["images"] = images
                        else:
                            play = next((l.get("a") for l in data.get("links", []) if "watermark" not in l.get("t", "").lower()), None)
                            info["play"] = play
                        return info, None
            else:
                async with session.post(api_url, data={param: tiktok_url}, timeout=3) as res:
                    data = await res.json()
                    if data.get("code") == 0:
                        d = data["data"]
                        info = {
                            "id": d.get("id"),
                            "title": d.get("title"),
                            "cover": d.get("cover"),
                            "author": d.get("author", {})
                        }
                        if d.get("images"):
                            info["images"] = d.get("images")
                        else:
                            play = d.get(key)
                            if play and play.startswith("/"): play = "https://www.tikwm.com" + play
                            info["play"] = play
                        return info, None
        except: pass
        return None, None

    def engine_ssstik(self, tiktok_url):
        """
        ENGINE 3: Scraper (Last Resort - Slow)
        """
        try:
            self._init_driver()
            self.driver.get("https://ssstik.io/en")
            wait = WebDriverWait(self.driver, 10)
            input_field = wait.until(EC.presence_of_element_located((By.ID, "main_page_text")))
            input_field.send_keys(tiktok_url)
            self.driver.find_element(By.ID, "submit").click()
            
            # Detect if slideshow
            try:
                images_elements = self.driver.find_elements(By.CSS_SELECTOR, "ul.splide__list img")
                if images_elements:
                    images = [img.get_attribute("src") for img in images_elements]
                    return {"images": images}, "https://ssstik.io/"
            except: pass

            result_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.without_watermark")))
            url = result_link.get_attribute("href")
            return {"play": url}, "https://ssstik.io/"
        except: return None, None
        finally: self._close_driver()

    async def get_media_info_async(self, tiktok_url):
        match = re.search(r'video/(\d+)', tiktok_url)
        video_id = match.group(1) if match else None
        
        if not video_id:
            try:
                res = requests.get(tiktok_url, headers=self._get_headers(is_mobile=False), allow_redirects=True, timeout=2)
                match = re.search(r'video/(\d+)', res.url)
                if match: video_id = match.group(1)
            except: pass

        async with aiohttp.ClientSession() as session:
            tasks = []
            if video_id:
                endpoints = ["https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/", "https://api22-normal-c-useast1a.tiktokv.com/aweme/v1/feed/"]
                for api in endpoints: tasks.append(self.fetch_direct_api(session, api, video_id))
            
            providers = [("https://lovetik.com/api/ajax/search", "query", "links"), ("https://www.tikwm.com/api/", "url", "play")]
            for p in providers: tasks.append(self.fetch_provider(session, p, tiktok_url))

            for completed in asyncio.as_completed(tasks, timeout=5):
                try:
                    info, referer = await completed
                    if info: return info, referer
                except: continue
        return None, None

    async def get_media_info(self, tiktok_url):
        # 1. Check Cache
        with self.cache_lock:
            if tiktok_url in self.cache:
                info, ref, expiry = self.cache[tiktok_url]
                if time.time() < expiry: return info, ref

        # 2. Try Async Race (API/Provider)
        try:
            info, referer = await self.get_media_info_async(tiktok_url)
        except:
            info, referer = None, None

        # 3. Fallback to Selenium (Sync)
        if not info:
            # We run the synchronous scraper in a thread to prevent blocking the event loop
            loop = asyncio.get_event_loop()
            info, referer = await loop.run_in_executor(None, self.engine_ssstik, tiktok_url)

        # 4. Save to Cache
        if info:
            if not info.get("id"): info["id"] = str(int(time.time()))
            with self.cache_lock:
                self.cache[tiktok_url] = (info, referer, time.time() + 600)
            return info, referer

        return None, None

    async def get_video_link(self, tiktok_url):
        # Compatibility wrapper
        info, ref = await self.get_media_info(tiktok_url)
        if info: return info.get("play"), ref
        return None, None

    async def download_to_path(self, tiktok_url, output_filename=None):
        info, referer = await self.get_media_info(tiktok_url)
        video_url = info.get("play") if info else None
        if video_url:
            headers = self._get_headers(is_mobile=False)
            if referer: headers["Referer"] = referer
            try:
                timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=120)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(video_url, headers=headers) as res:
                        if res.status == 200:
                            with open(output_filename or f"tiktok_{int(time.time())}.mp4", 'wb') as f:
                                while True:
                                    chunk = await res.content.read(256*1024)
                                    if not chunk: break
                                    f.write(chunk)
                            return True
            except: pass
        return False

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if url:
        dl = TikTokDownloader()
        print(dl.get_media_info(url))
