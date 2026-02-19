import requests
import re
import json
import os
import time

def get_tiktok_no_watermark(tiktok_url):
    print(f"[*] Reverse Engineering TikTok URL: {tiktok_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    session = requests.Session()
    session.headers.update(headers)

    # 1. Expand the URL if it's a short link (vm.tiktok.com)
    res = session.get(tiktok_url, allow_redirects=True)
    final_url = res.url
    print(f"[*] Final URL: {final_url}")

    # 2. Extract Video ID
    video_id_match = re.search(r'video/(\d+)', final_url)
    if not video_id_match:
        print("[!] Could not find Video ID.")
        return
    video_id = video_id_match.group(1)
    print(f"[*] Video ID: {video_id}")

    # 3. Method A: API 16 (Mobile API)
    # This is the gold standard for reverse engineering
    api_url = f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/feed/?aweme_id={video_id}"
    mobile_headers = {
        "User-Agent": "com.zhiliaoapp.musically/2022405040 (Linux; U; Android 10; en_US; Pixel 4; Build/QQ3A.200805.001; Cronet/58.0.2991.0)"
    }
    
    try:
        api_res = requests.get(api_url, headers=mobile_headers)
        if api_res.status_code == 200:
            data = api_res.json()
            if "aweme_list" in data and len(data["aweme_list"]) > 0:
                video_data = data["aweme_list"][0]["video"]
                
                # The 'play_addr' in the mobile API often contains the no-watermark link
                # or you can find a specific type
                play_addr_data = video_data.get("play_addr", {})
                url_list = play_addr_data.get("url_list", [])
                
                if url_list:
                    download_url = url_list[0]
                    print(f"[*] Found Direct URL via Mobile API: {download_url[:60]}...")
                    # Note: Sometimes you need to replace 'playwm' with 'play'
                    download_url = download_url.replace("playwm", "play")
                    return download_url
    except Exception as e:
        print(f"[!] Mobile API failed: {e}")

    # 4. Method B: Extracting from Web Proxy Script Tag
    # Look for SIGI_STATE or __UNIVERSAL_DATA_FOR_REHYDRATION__
    html = res.text
    # We'll look for the playAddr in the JSON
    play_addr_match = re.search(r'"playAddr":"([^"]+)"', html)
    if play_addr_match:
        play_addr = play_addr_match.group(1).replace("\\u002F", "/")
        print(f"[*] Found playAddr in Web Page: {play_addr[:60]}...")
        # Web URLs often have watermark. We can try to strip it or find the 'hidden' no-wm link.
        # However, the mobile API is usually the one without watermark.
        return play_addr

    print("[!] Failed to find a direct video link.")
    return None

def download_video(url, filename):
    if not url:
        return
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/"
    }
    
    print(f"[*] Downloading video from: {url[:50]}...")
    res = requests.get(url, headers=headers, stream=True)
    if res.status_code == 200:
        with open(filename, 'wb') as f:
            for chunk in res.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
        print(f"[+] Download complete: {filename}")
    else:
        print(f"[!] Failed to download. Status: {res.status_code}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.tiktok.com/@drifting.ashes8/video/7584077374749265174"
    video_url = get_tiktok_no_watermark(url)
    if video_url:
        download_video(video_url, f"reversed_tiktok_{int(time.time())}.mp4")
