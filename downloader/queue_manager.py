import os
import re
import time
import threading
import traceback
from typing import List, Dict, Any, Callable, Optional
from .resolver import VideoResolver
from .downloader import FileDownloader

class QueueManager:
    """
    Manages the batch download queue in a background thread.
    Supports pause, cancel, resumability, and rate-limiting delays.
    """

    def __init__(self):
        self.resolver = VideoResolver()
        self.downloader = FileDownloader()

        self.queue: List[Dict[str, Any]] = []
        self.dest_folder: str = "Downloads"
        self.delay_between_downloads: float = 1.5
        
        self.is_running: bool = False
        self.is_paused: bool = False
        self.stop_requested: bool = False
        
        self._thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_episode_start: Optional[Callable[[Dict[str, Any], int, int], None]] = None
        self.on_episode_progress: Optional[Callable[[int, int, float, float], None]] = None
        self.on_episode_complete: Optional[Callable[[Dict[str, Any], int, str, str], None]] = None
        self.on_overall_progress: Optional[Callable[[int, int, float], None]] = None
        self.on_all_finished: Optional[Callable[[int, int, int], None]] = None

    def log(self, msg: str):
        print(f"[Queue] {msg}")
        if self.on_log:
            self.on_log(msg)

    def set_queue(self, episodes: List[Dict[str, Any]], dest_folder: str, delay: float = 1.5):
        self.queue = list(episodes)
        self.dest_folder = dest_folder
        self.delay_between_downloads = delay

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self.stop_requested = False
        self._thread = threading.Thread(target=self._run_queue, daemon=True)
        self._thread.start()

    def pause(self):
        self.is_paused = True
        self.log("Batch download paused.")

    def resume(self):
        self.is_paused = False
        self.log("Batch download resumed.")

    def stop(self):
        self.stop_requested = True
        self.is_paused = False
        self.log("Stopping batch download...")

    def _check_cancelled(self) -> bool:
        return self.stop_requested

    def _run_queue(self):
        total = len(self.queue)
        success_count = 0
        skipped_count = 0
        failed_count = 0

        self.log(f"Starting batch queue: {total} episodes queued.")
        
        try:
            os.makedirs(self.dest_folder, exist_ok=True)

            for index, ep in enumerate(self.queue):
                if self.stop_requested:
                    self.log("Batch processing stopped by user.")
                    break

                # Handle pause
                while self.is_paused and not self.stop_requested:
                    time.sleep(0.5)

                if self.stop_requested:
                    break

                ep_num = ep.get('episodeNumber', index + 1)
                raw_title = ep.get('title', f"Episode_{ep_num}")
                clean_title = self.downloader.sanitize_filename(raw_title)
                # Remove any trailing .mp4 if already present in title
                clean_title = re.sub(r'\.mp4$', '', clean_title, flags=re.IGNORECASE).strip()
                
                # Form clean filename: e.g. "EP 01 - The Twin Scorpio Girls' Reversal-EP1.mp4"
                filename = f"EP {ep_num:02d} - {clean_title}.mp4"
                dest_file = os.path.join(self.dest_folder, filename)

                # Check if file already exists and is non-empty (Resumability)
                if os.path.exists(dest_file) and os.path.getsize(dest_file) > 1024 * 100:
                    self.log(f"Skipping [Ep {ep_num}] - Already downloaded: {filename}")
                    skipped_count += 1
                    if self.on_episode_complete:
                        self.on_episode_complete(ep, index, "SKIPPED", "Already exists")
                    if self.on_overall_progress:
                        self.on_overall_progress(index + 1, total, ((index + 1) / total) * 100.0)
                    continue

                # Start downloading episode
                if self.on_episode_start:
                    self.on_episode_start(ep, index, total)

                self.log(f"Resolving download link for [Ep {ep_num}] (ID: {ep.get('id')})...")
                
                # Resolve clean stream URL
                video_url = self.resolver.resolve_video_url(
                    video_id=ep.get('id', ''),
                    author_unique_id=ep.get('author', 'tiktok')
                )

                if not video_url:
                    self.log(f"Failed to resolve download link for [Ep {ep_num}].")
                    failed_count += 1
                    if self.on_episode_complete:
                        self.on_episode_complete(ep, index, "FAILED", "Could not resolve stream URL")
                    if self.on_overall_progress:
                        self.on_overall_progress(index + 1, total, ((index + 1) / total) * 100.0)
                    continue

                self.log(f"Downloading [Ep {ep_num}] -> {filename}...")
                
                # Progress forwarder
                def ep_progress(dl, tot, pct, spd):
                    if self.on_episode_progress:
                        self.on_episode_progress(dl, tot, pct, spd)

                ok = self.downloader.download_file(
                    url=video_url,
                    dest_path=dest_file,
                    progress_callback=ep_progress,
                    check_cancelled=self._check_cancelled
                )

                if ok:
                    self.log(f"Successfully finished [Ep {ep_num}].")
                    success_count += 1
                    if self.on_episode_complete:
                        self.on_episode_complete(ep, index, "COMPLETED", "Success")
                else:
                    if self.stop_requested:
                        self.log(f"Download of [Ep {ep_num}] was cancelled.")
                        break
                    else:
                        self.log(f"Error downloading [Ep {ep_num}].")
                        failed_count += 1
                        if self.on_episode_complete:
                            self.on_episode_complete(ep, index, "FAILED", "Download error")

                # Update overall progress
                if self.on_overall_progress:
                    self.on_overall_progress(index + 1, total, ((index + 1) / total) * 100.0)

                # Anti-rate-limit polite delay before next video
                if index < total - 1 and not self.stop_requested and self.delay_between_downloads > 0:
                    time.sleep(self.delay_between_downloads)

        except Exception as e:
            self.log(f"Fatal error in queue processing: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False
            self.log(f"Queue complete! {success_count} downloaded, {skipped_count} skipped, {failed_count} failed.")
            if self.on_all_finished:
                self.on_all_finished(success_count, skipped_count, failed_count)
