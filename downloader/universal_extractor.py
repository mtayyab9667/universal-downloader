import os
import re
import tempfile
from typing import Dict, Any, List, Optional
import yt_dlp

from .detector import PlatformDetector, Platform
from .api import TikTokDramaAPI


def get_cookie_file() -> Optional[str]:
    """
    Retrieves YouTube cookies from environment variable (e.g. Render.com)
    or from a local cookies.txt file to bypass YouTube's datacenter bot checks.
    """
    raw_cookies = os.environ.get("YOUTUBE_COOKIES")
    if raw_cookies:
        cookie_path = os.path.join(tempfile.gettempdir(), "render_yt_cookies.txt")
        try:
            cleaned = raw_cookies.replace('\\n', '\n').strip()
            if not cleaned.startswith('# Netscape'):
                cleaned = "# Netscape HTTP Cookie File\n" + cleaned
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write(cleaned + "\n")
            return cookie_path
        except Exception:
            pass

    for p in [
        os.path.join(os.getcwd(), "cookies.txt"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt"),
    ]:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return None

class UniversalExtractor:
    """
    Unified extraction engine supporting YouTube, Instagram, TikTok, Facebook,
    X (Twitter), Reddit, Pinterest, and 1000+ video sites.
    """

    def __init__(self):
        self.tiktok_drama_api = TikTokDramaAPI()

    def extract(self, url: str) -> Dict[str, Any]:
        """
        Extracts metadata and format options from any video link.
        """
        url = url.strip()
        detection = PlatformDetector.detect(url)
        platform = detection["platform"]

        # Case 1: TikTok Short Drama Series (Specialized 1-Click Multi-Episode Engine)
        if platform == Platform.TIKTOK and detection["is_shortdrama"]:
            drama_id, _ = self.tiktok_drama_api.parse_drama_id_and_episode(url)
            if drama_id:
                drama_data = self.tiktok_drama_api.fetch_drama_episodes(drama_id)
                return {
                    "success": True,
                    "platform": platform,
                    "detection": detection,
                    "is_drama_series": True,
                    "is_playlist": True,
                    "id": drama_id,
                    "title": drama_data["dramaInfo"].get("dramaName", "TikTok Short Drama"),
                    "author": drama_data["dramaInfo"].get("author", "TikTok Creator"),
                    "thumbnail": drama_data["dramaInfo"].get("cover", ""),
                    "total_episodes": drama_data["totalEpisodes"],
                    "episodes": drama_data["episodes"],
                    "raw_data": drama_data
                }

        # Case 2: General / Universal Social Media Extraction via yt-dlp
        cookie_file = get_cookie_file()
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': 'in_playlist',
            'no_color': True,
        }
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file

        info = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as first_err:
            err_msg = str(first_err)
            if "confirm you’re not a bot" in err_msg.lower() or "confirm you're not a bot" in err_msg.lower():
                clean_err = (
                    "YouTube Bot Protection (Cloud Hosting IP): YouTube restricts video extraction on cloud servers like Render. "
                    "To enable YouTube on this live website: Add YOUTUBE_COOKIES in Render Dashboard -> Environment. "
                    "Alternatively, run the desktop app locally on your PC where YouTube works with zero restrictions! "
                    "(Note: TikTok, Instagram, Facebook, and X work 100% on this cloud site without any cookies.)"
                )
            else:
                clean_err = err_msg

            return {
                "success": False,
                "platform": platform,
                "detection": detection,
                "error": clean_err
            }

        try:
            if not info:
                return {
                    "success": False,
                    "error": "Could not extract video information from this link."
                }

            # Check if it's a playlist or single video
            is_playlist = 'entries' in info and bool(info['entries'])

            if is_playlist:
                entries = []
                for entry in info.get('entries', []):
                    if entry:
                        entries.append({
                            'id': entry.get('id', ''),
                            'title': entry.get('title', 'Unknown Title'),
                            'url': entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                            'duration': entry.get('duration', 0),
                            'thumbnail': entry.get('thumbnail', '')
                        })

                return {
                    "success": True,
                    "platform": platform,
                    "detection": detection,
                    "is_drama_series": False,
                    "is_playlist": True,
                    "id": info.get('id', ''),
                    "title": info.get('title', 'Playlist'),
                    "author": info.get('uploader') or info.get('channel', 'Creator'),
                    "thumbnail": info.get('thumbnail') or (entries[0]['thumbnail'] if entries else ""),
                    "total_episodes": len(entries),
                    "episodes": entries,
                    "raw_data": info
                }

            # Single Video Extraction
            formats = self._parse_available_formats(info, platform)

            return {
                "success": True,
                "platform": platform,
                "detection": detection,
                "is_drama_series": False,
                "is_playlist": False,
                "id": info.get('id', ''),
                "title": info.get('title', 'Untitled Video'),
                "author": info.get('uploader') or info.get('channel') or info.get('creator', 'Creator'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration', 0),
                "duration_str": self._format_duration(info.get('duration', 0)),
                "view_count": info.get('view_count', 0),
                "formats": formats,
                "raw_data": info
            }

        except Exception as e:
            return {
                "success": False,
                "platform": platform,
                "detection": detection,
                "error": str(e)
            }

    def _parse_available_formats(self, info: Dict[str, Any], platform: Platform) -> List[Dict[str, Any]]:
        """
        Synthesizes raw yt-dlp format streams into clean, consumer-friendly options:
        - 4K / 1440p / 1080p / 720p / 480p / 360p MP4
        - MP3 Audio Only (Highest Quality)
        - M4A Audio Only
        """
        raw_formats = info.get('formats', [])
        available_resolutions = set()
        has_video = False
        has_audio = False

        for f in raw_formats:
            h = f.get('height')
            if h and isinstance(h, int):
                available_resolutions.add(h)
                has_video = True
            if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                has_audio = True

        formats_list = []

        # Target standard resolutions in descending order
        target_res = [
            (2160, "4K (2160p) Ultra HD"),
            (1440, "2K (1440p) Quad HD"),
            (1080, "1080p Full HD"),
            (720, "720p HD"),
            (480, "480p Standard"),
            (360, "360p Low Quality"),
        ]

        if available_resolutions:
            for height, label in target_res:
                # Check if this resolution or higher is available
                matching = [h for h in available_resolutions if abs(h - height) <= 30 or (height == 1080 and h >= 1000)]
                if matching:
                    formats_list.append({
                        "format_id": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best",
                        "label": label,
                        "type": "video",
                        "ext": "mp4",
                        "height": height
                    })

        # If no specific heights detected, provide Best Video
        if not formats_list:
            formats_list.append({
                "format_id": "bestvideo+bestaudio/best",
                "label": "Best Video Quality (No Watermark MP4)",
                "type": "video",
                "ext": "mp4",
                "height": 1080
            })

        # Audio Only Options
        formats_list.append({
            "format_id": "bestaudio/best",
            "label": "Audio Only — MP3 (Highest Quality 320kbps)",
            "type": "audio",
            "ext": "mp3",
            "height": 0
        })

        formats_list.append({
            "format_id": "bestaudio/best",
            "label": "Audio Only — M4A (Original Stream)",
            "type": "audio",
            "ext": "m4a",
            "height": 0
        })

        return formats_list

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if not seconds:
            return ""
        sec = int(round(seconds))
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        if h > 0:
            return f"{h}h {m:02d}m {s:02d}s"
        else:
            return f"{m}m {s:02d}s"
