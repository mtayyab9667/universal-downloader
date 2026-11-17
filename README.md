---
title: Universal Video Downloader
emoji: 🎬
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Universal Video & Drama Downloader

A universal social media video & drama downloader supporting **YouTube, TikTok (Videos & Drama Series), Instagram Reels, Facebook, X (Twitter), Reddit, and Pinterest**.

## 🎨 Aesthetic
- **Muted Sage Grey** (`#A5A79B`)
- **Warm Cream Beige** (`#E8D2B5`)
- Purely typographic design with zero icons.

---

## 🚀 Running Locally

### Desktop GUI
Double-click `run.bat` or run:
```bash
python main.py
```

### Web Dashboard
Double-click `run_web.bat` or run:
```bash
cd backend
python app.py
```
Open your browser at `http://localhost:8000`.

---

## 🌐 100% Free Cloud Deployment (Hugging Face Spaces)

This repository includes a production-ready `Dockerfile` that packages **Python 3.11**, **FFmpeg**, and the **FastAPI backend**.

1. Create a free account at [huggingface.co](https://huggingface.co).
2. Click **New Space**:
   - Space Name: e.g. `universal-downloader`
   - License: `mit`
   - Select **Docker** -> **Blank**
   - Visibility: **Public**
3. Upload the project files (`Dockerfile`, `README.md`, `requirements.txt`, `backend/`, `downloader/`).
4. Hugging Face will automatically build and launch your app with a permanent, free HTTPS URL:
   `https://<your-username>-universal-downloader.hf.space`
