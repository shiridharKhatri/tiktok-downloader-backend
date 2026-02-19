from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import uvicorn
import os
import re
import time
import requests
import tempfile
import random
import aiohttp
from typing import Optional

# Import our reverse engineered engine logic
from tiktok_downloader import TikTokDownloader, USER_AGENTS

app = FastAPI(
    title="TikDown Production API",
    description="High-performance TikTok Video Downloader (No Watermark)",
    version="1.0.0"
)

# Initialize downloader
downloader = TikTokDownloader(headless=True)

# Allow CORS for static frontend hosting (Nginx)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Metrics for Monitoring
stats = {
    "total_requests": 0,
    "success_count": 0,
    "fail_count": 0,
    "proxy_requests": 0,
    "start_time": time.time()
}

@app.get("/proxy")
async def proxy_media(url: str, filename: Optional[str] = "video.mp4", request: Request = None):
    """
    STABLE Async Media Proxy.
    Handles slow connections and large files without timing out.
    """
    stats["proxy_requests"] += 1
    
    # Forward headers from client (especially Range)
    client_headers = {}
    if request:
        range_header = request.headers.get("range")
        if range_header: client_headers["Range"] = range_header
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.tiktok.com/",
        **client_headers
    }
    
    # Use a generous timeout for the whole transaction but keep read timeouts decent
    timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_read=60)
    
    try:
        async def stream_generator():
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    # Stream in smaller chunks for better interactivity
                    async for chunk in resp.content.iter_chunked(256 * 1024):
                        yield chunk

        # Get initial response info
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as head_resp:
                exclude = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'access-control-allow-origin']
                resp_headers = {n: v for (n, v) in head_resp.headers.items() if n.lower() not in exclude}
                
                # Critical headers for browsers and production
                resp_headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                resp_headers['Access-Control-Allow-Origin'] = '*'
                resp_headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range'
                resp_headers['Accept-Ranges'] = 'bytes' # Support seeking
                
                # Check for content length
                content_length = head_resp.headers.get('content-length')
                if content_length: resp_headers['Content-Length'] = content_length

                return StreamingResponse(stream_generator(), headers=resp_headers, status_code=head_resp.status)
    except Exception as e:
        print(f"[!] Proxy streaming error: {e}")
        raise HTTPException(status_code=500, detail="Media stream timed out or failed.")

@app.get("/")
def read_root():
    uptime = int(time.time() - stats["start_time"])
    return {
        "status": "online",
        "uptime_seconds": uptime,
        "metrics": stats,
        "message": "TikDown API is running. Point your static frontend here.",
        "documentation": "/docs"
    }

@app.get("/status")
def get_status():
    """Returns the current health and success rate of the API."""
    success_rate = (stats["success_count"] / stats["total_requests"] * 100) if stats["total_requests"] > 0 else 100
    return {
        "is_healthy": success_rate > 50,
        "success_rate": f"{success_rate:.2f}%",
        "total": stats["total_requests"],
        "success": stats["success_count"],
        "failed": stats["fail_count"],
        "proxy": stats["proxy_requests"]
    }

@app.get("/info")
async def get_video_info(url: str = Query(..., description="The TikTok video URL")):
    stats["total_requests"] += 1
    info, _ = await downloader.get_media_info(url)
    
    if info:
        stats["success_count"] += 1
        return {
            "success": True,
            "data": info,
            "original_url": url,
            "timestamp": int(time.time())
        }
    
    stats["fail_count"] += 1
    raise HTTPException(status_code=404, detail="Could not retrieve media info.")

@app.get("/download")
async def download_video(url: str = Query(..., description="The TikTok video URL")):
    stats["total_requests"] += 1
    info, referer = await downloader.get_media_info(url)
    video_url = info.get("play") if info else None
    
    if not video_url:
        stats["fail_count"] += 1
        raise HTTPException(status_code=404, detail="Video not found or all engines failed.")

    temp_dir = tempfile.gettempdir()
    match = re.search(r'video/(\d+)', url)
    video_id = match.group(1) if match else int(time.time())
    file_path = os.path.join(temp_dir, f"tiktok_{video_id}.mp4")

    success = await downloader.download_to_path(url, file_path)
    
    if success:
        stats["success_count"] += 1
        return FileResponse(
            path=file_path,
            filename=f"video_{video_id}.mp4",
            media_type="video/mp4"
        )
    
    stats["fail_count"] += 1
    raise HTTPException(status_code=500, detail="Failed to process video download.")

if __name__ == "__main__":
    # Start the production server
    # 0.0.0.0 makes it accessible on the internet (your VPS IP)
    print("[*] TikDown API starting on http://0.0.0.0:8087")
    uvicorn.run(app, host="0.0.0.0", port=8087)
