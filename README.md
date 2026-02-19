# TikDown: Hyper-Speed TikTok Downloader

Zero-latency, high-reliability TikTok downloader with support for Videos (No Watermark) and Photo Slideshows.

## 📁 Project Structure
- `/client`: Next.js Frontend (React, Tailwind, Framer Motion)
- `/server`: Python FastAPI Backend (Async aiohttp racing, Selenium Fallback)

## 🚀 Key Features
- **Async API Racing**: Fires 12+ API requests simultaneously to find the fastest download link.
- **Photo Slideshows**: Automatically detects and extracts high-res image collections.
- **Smart Caching**: In-memory TTL cache for instant repeated downloads.
- **CDN Proxy**: Built-in streaming proxy to bypass regional blocks and improve buffer speeds.

## 🛠 Tech Stack
- **Backend**: Python 3.11, FastAPI, aiohttp, Selenium (Fallback)
- **Frontend**: Next.js 16, TypeScript, Lucide Icons

## 📦 Local Setup

### Backend (Server)
1. `cd server`
2. `pip install -r requirements.txt`
3. `python app.py` (Starts on port 8000)

### Frontend (Client)
1. `cd client`
2. `npm install`
3. `npm run dev` (Starts on port 3000)

## 🐳 Docker Deployment
```bash
docker-compose up --build
```
