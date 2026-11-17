import os
import re
import threading
from typing import Callable, Optional, Dict, Any
import imageio_ffmpeg
import yt_dlp

class UniversalDownloader:
    """
    Downloads media streams across YouTube, Instagram, Facebook, X, TikTok, etc.
    with automatic A/V muxing via FFmpeg and MP3 conversion.
    """

    def __init__(self):
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.is_running: bool = False
        self.stop_requested: bool = False
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def get_cookie_file() -> Optional[str]:
        import tempfile
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

    @staticmethod
    def sanitize_filename(name: str) -> str:
        # Strip illegal characters for Windows and HTTP headers
        clean = re.sub(r'[\\/*?:"<>|]', "", name)
        clean = clean.replace("\n", " ").replace("\r", "").strip()
        return clean or "Video"

    def stop(self):
        self.stop_requested = True
        self.is_running = False

    def download_sync(
        self,
        url: str,
        dest_folder: str,
        format_id: str = "bestvideo*+bestaudio/best",
        target_ext: str = "mp4",
        progress_callback: Optional[Callable[[float, str, str, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Synchronously downloads media using yt-dlp & FFmpeg.
        Returns the absolute path of the downloaded file.
        """
        os.makedirs(dest_folder, exist_ok=True)
        out_template = os.path.join(dest_folder, "%(title)s.%(ext)s")
        downloaded_filepath = ""

        def hook(d):
            nonlocal downloaded_filepath
            if cancel_check and cancel_check():
                raise Exception("Download cancelled by user.")

            if d.get('status') == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0

                percent = (downloaded / total * 100.0) if total > 0 else 0.0
                dl_str = self._format_bytes(downloaded)
                tot_str = self._format_bytes(total) if total > 0 else "?"
                speed_str = f"{self._format_bytes(speed)}/s" if speed else ""
                eta_str = f"ETA: {int(eta)}s" if eta else ""

                if progress_callback:
                    progress_callback(percent, f"{dl_str} / {tot_str}", speed_str, eta_str)

            elif d.get('status') == 'finished':
                downloaded_filepath = d.get('filename', '')
                if progress_callback:
                    progress_callback(100.0, "Processing audio/video with FFmpeg...", "", "")

        cookie_file = self.get_cookie_file()
        ydl_opts: Dict[str, Any] = {
            'format': format_id,
            'outtmpl': out_template,
            'ffmpeg_location': self.ffmpeg_exe,
            'progress_hooks': [hook],
            'quiet': True,
            'no_warnings': True,
            'windowsfilenames': True,
            'writethumbnail': False,
        }
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file

        if target_ext.lower() == 'mp4':
            ydl_opts['merge_output_format'] = 'mp4'
        elif target_ext.lower() == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # Retrieve the exact finished file created in dest_folder
        downloaded_files = [
            os.path.join(dest_folder, f) for f in os.listdir(dest_folder)
            if not f.endswith('.part') and not f.endswith('.ytdl') and not f.endswith('.temp')
        ]
        if downloaded_files:
            return downloaded_files[0]

        final_name = ydl.prepare_filename(info)
        if target_ext.lower() == 'mp3':
            final_name = os.path.splitext(final_name)[0] + ".mp3"
        elif target_ext.lower() == 'mp4':
            final_name = os.path.splitext(final_name)[0] + ".mp4"

        return final_name

    def download(
        self,
        url: str,
        dest_folder: str,
        format_id: str = "bestvideo+bestaudio/best",
        target_ext: str = "mp4",
        progress_callback: Optional[Callable[[float, str, str, str], None]] = None,
        completion_callback: Optional[Callable[[bool, str, str], None]] = None
    ):
        """
        Runs download in a background thread for desktop GUI.
        """
        if self.is_running:
            return

        self.is_running = True
        self.stop_requested = False

        def _worker():
            try:
                final_name = self.download_sync(
                    url=url,
                    dest_folder=dest_folder,
                    format_id=format_id,
                    target_ext=target_ext,
                    progress_callback=progress_callback,
                    cancel_check=lambda: self.stop_requested
                )
                self.is_running = False
                if completion_callback:
                    completion_callback(True, "Download completed successfully!", final_name)
            except Exception as e:
                self.is_running = False
                msg = str(e)
                if "cancelled" in msg.lower():
                    msg = "Download cancelled."
                if completion_callback:
                    completion_callback(False, msg, "")

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    @staticmethod
    def _format_bytes(num_bytes: float) -> str:
        if num_bytes < 1024:
            return f"{num_bytes:.0f} B"
        elif num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.1f} KB"
        elif num_bytes < 1024 * 1024 * 1024:
            return f"{num_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
