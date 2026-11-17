import os
import re
import time
from typing import Callable, Optional
from curl_cffi import requests
import requests as std_requests

class FileDownloader:
    """
    Downloads media streams with real-time speed, ETA, and progress calculation.
    """

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Removes illegal filesystem characters."""
        clean = re.sub(r'[\\/*?:"<>|]', "", name)
        clean = clean.replace("\n", " ").replace("\r", "").strip()
        return clean or "Episode"

    @staticmethod
    def format_bytes(num_bytes: int) -> str:
        """Formats bytes into human readable string (e.g. 15.4 MB)."""
        if num_bytes < 1024:
            return f"{num_bytes} B"
        elif num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.1f} KB"
        elif num_bytes < 1024 * 1024 * 1024:
            return f"{num_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def format_speed(bps: float) -> str:
        """Formats speed into MB/s or KB/s."""
        if bps < 1024:
            return f"{bps:.0f} B/s"
        elif bps < 1024 * 1024:
            return f"{bps / 1024:.1f} KB/s"
        else:
            return f"{bps / (1024 * 1024):.2f} MB/s"

    def download_file(
        self,
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
        check_cancelled: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Streams download to dest_path.
        progress_callback(downloaded_bytes, total_bytes, percent, speed_bps)
        Returns True if successful, False otherwise.
        """
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        part_path = dest_path + ".part"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://ssstik.io/'
        }

        # Try with curl_cffi first, then standard requests as fallback
        for method in ['curl_cffi', 'std_requests']:
            resp = None
            try:
                if method == 'curl_cffi':
                    resp = requests.get(url, headers=headers, impersonate='chrome120', stream=True, timeout=25)
                else:
                    resp = std_requests.get(url, headers=headers, stream=True, timeout=25)

                if resp.status_code not in (200, 206):
                    print(f"[Downloader] HTTP error {resp.status_code} using {method}")
                    if resp:
                        resp.close()
                    continue

                total_size = int(resp.headers.get('content-length', 0))
                downloaded = 0
                start_time = time.time()
                last_update_time = start_time
                last_downloaded = 0

                with open(part_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=64 * 1024):
                        if check_cancelled and check_cancelled():
                            print("[Downloader] Download cancelled by user.")
                            f.close()
                            resp.close()
                            if os.path.exists(part_path):
                                try:
                                    os.remove(part_path)
                                except Exception:
                                    pass
                            return False

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            now = time.time()
                            elapsed = now - last_update_time
                            if elapsed >= 0.2:  # Update progress 5 times a sec
                                speed = (downloaded - last_downloaded) / elapsed if elapsed > 0 else 0
                                percent = (downloaded / total_size * 100.0) if total_size > 0 else 0.0
                                
                                if progress_callback:
                                    progress_callback(downloaded, total_size, percent, speed)

                                last_update_time = now
                                last_downloaded = downloaded

                resp.close()

                # Verify file was downloaded and non-empty
                if os.path.exists(part_path) and os.path.getsize(part_path) > 1024:
                    if progress_callback:
                        progress_callback(downloaded, total_size, 100.0, 0.0)

                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    os.rename(part_path, dest_path)
                    return True
                else:
                    print(f"[Downloader] Downloaded file was empty or missing using {method}")

            except Exception as e:
                print(f"[Downloader] Error with {method}: {e}")
                if resp:
                    try:
                        resp.close()
                    except Exception:
                        pass
                if os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except Exception:
                        pass

        return False
