import os
import tempfile
import http.cookiejar
from typing import Optional


def normalize_cookie_text(text: str) -> str:
    """
    Normalizes pasted cookies into strict Netscape HTTP Cookie format with TAB delimiters.
    Handles space-separated lines caused by browser textareas or environment variable forms.
    """
    lines = []
    has_header = False

    for raw_line in text.replace('\\n', '\n').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#'):
            if 'Netscape' in line:
                has_header = True
            lines.append(line)
            continue

        # Check if already tab-separated
        parts = line.split('\t')
        if len(parts) >= 7:
            lines.append('\t'.join(parts[:7]))
        else:
            # Reconstruct tab separation from whitespace-split fields
            ws_parts = line.split(None, 6)
            if len(ws_parts) == 7:
                lines.append('\t'.join(ws_parts))
            elif len(ws_parts) == 6:
                lines.append('\t'.join(ws_parts) + '\t')
            else:
                lines.append(line)

    content = '\n'.join(lines)
    if not has_header:
        content = '# Netscape HTTP Cookie File\n' + content
    return content


def get_cookie_file() -> Optional[str]:
    """
    Retrieves YouTube cookies from environment variable (e.g. Render.com)
    or from a local cookies.txt file to bypass YouTube's datacenter bot checks.
    """
    raw_cookies = os.environ.get("YOUTUBE_COOKIES")
    if raw_cookies:
        cookie_path = os.path.join(tempfile.gettempdir(), "render_yt_cookies.txt")
        try:
            normalized = normalize_cookie_text(raw_cookies)
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write(normalized + "\n")
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


def count_valid_cookies() -> int:
    """Returns the number of valid parsed cookies from the active cookie file."""
    cf = get_cookie_file()
    if not cf or not os.path.exists(cf):
        return 0
    try:
        cj = http.cookiejar.MozillaCookieJar(cf)
        cj.load(ignore_discard=True, ignore_expires=True)
        return len(cj)
    except Exception:
        return 0
