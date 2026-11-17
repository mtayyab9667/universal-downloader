import re
import time
from typing import Optional, Dict
from curl_cffi import requests

class VideoResolver:
    """
    Resolves clean, watermark-free HD video download links for TikTok episodes.
    Features automatic rate-limit detection and exponential backoff retries.
    """
    
    def __init__(self):
        self.session = requests.Session(impersonate='chrome120')
        self.ssstik_token: Optional[str] = None
        self.last_token_time: float = 0

    def _get_ssstik_token(self) -> str:
        """Gets or refreshes the SSSTik CSRF / verification token."""
        now = time.time()
        if self.ssstik_token and (now - self.last_token_time) < 300:
            return self.ssstik_token

        try:
            r = self.session.get("https://ssstik.io/en-1", timeout=12)
            if r.status_code == 200:
                m = re.search(r'(?:s_tt|s_v)\s*=\s*[\'"]([^\'"]+)[\'"]', r.text)
                if m:
                    self.ssstik_token = m.group(1)
                    self.last_token_time = now
                    return self.ssstik_token
        except Exception as e:
            print(f"[Resolver] Warning: Could not fetch SSSTik token: {e}")
        
        return ""

    def resolve_ssstik(self, video_url: str) -> Optional[str]:
        """
        Attempts to resolve clean video URL via SSSTik.
        Includes automatic retry with progressive backoff if rate limited (empty response).
        """
        retry_delays = [0, 3, 5, 7]

        for attempt, delay in enumerate(retry_delays):
            if delay > 0:
                print(f"[Resolver] Rate limit detected (attempt {attempt+1}/4). Backing off {delay}s...")
                time.sleep(delay)
                # Create a fresh session on retry
                self.session = requests.Session(impersonate='chrome120')
                self.ssstik_token = None

            token = self._get_ssstik_token()
            post_data = {'id': video_url, 'locale': 'en', 'tt': token}
            headers = {
                'HX-Request': 'true',
                'HX-Current-URL': 'https://ssstik.io/en-1',
                'Referer': 'https://ssstik.io/en-1'
            }

            try:
                r = self.session.post("https://ssstik.io/abc?url=dl", data=post_data, headers=headers, timeout=12)
                
                # If rate limited, SSSTik returns empty response (len == 0)
                if r.status_code == 200 and len(r.text) == 0:
                    continue

                if r.status_code == 200:
                    # Method 1: Look for any direct tikcdn.io video link (excluding avatars /a/)
                    tikcdn_links = [
                        h for h in re.findall(r'href=[\'"](https?://tikcdn\.io/ssstik/[^\'"]+)[\'"]', r.text)
                        if '/a/' not in h
                    ]
                    if tikcdn_links:
                        return tikcdn_links[0]

                    # Method 2: Look for <a> tags mentioning 'without watermark' (ignoring inner tags & whitespace)
                    for m in re.finditer(r'<a\s+[^>]*href=[\'"](https?://[^\'"]+)[\'"][^>]*>(.*?)</a>', r.text, re.DOTALL | re.IGNORECASE):
                        href, text = m.group(1), m.group(2)
                        if 'without' in text.lower() and 'watermark' in text.lower():
                            return href

            except Exception as e:
                print(f"[Resolver] SSSTik request error (attempt {attempt+1}): {e}")

        return None

    def resolve_tikwm(self, video_url: str) -> Optional[str]:
        """Fallback resolver using TikWM."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.tikwm.com/'
        }
        try:
            r = self.session.post("https://www.tikwm.com/api/", data={'url': video_url}, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('code') == 0 and data.get('data'):
                    return data['data'].get('hdplay') or data['data'].get('play')
        except Exception as e:
            print(f"[Resolver] TikWM error for {video_url}: {e}")
        return None

    def resolve_video_url(self, video_id: str, author_unique_id: str = "tiktok") -> Optional[str]:
        """
        Main entry point: Resolves direct no-watermark MP4 download URL for an episode.
        """
        video_url = f"https://www.tiktok.com/@{author_unique_id}/video/{video_id}"
        
        # 1. Try Primary Resolver with auto-backoff (SSSTik)
        url = self.resolve_ssstik(video_url)
        if url:
            return url

        # 2. Try Fallback Resolver (TikWM)
        url = self.resolve_tikwm(video_url)
        if url:
            return url

        return None
