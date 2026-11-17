import re
from enum import Enum
from typing import Dict, Any, Optional

class Platform(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X_TWITTER = "twitter"
    REDDIT = "reddit"
    PINTEREST = "pinterest"
    GENERIC = "generic"

class PlatformDetector:
    """
    Intelligently analyzes URLs to detect social media platform and content type.
    Purely typographic metadata with no icons.
    """

    PLATFORM_METADATA = {
        Platform.YOUTUBE: {
            "name": "YouTube",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["Videos", "Shorts", "Playlists", "Audio (MP3)"]
        },
        Platform.TIKTOK: {
            "name": "TikTok",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["No-WM Video", "Short Dramas (1-90+ eps)", "Audio"]
        },
        Platform.INSTAGRAM: {
            "name": "Instagram",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["Reels", "Posts", "Stories", "Carousels"]
        },
        Platform.FACEBOOK: {
            "name": "Facebook",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["Reels", "Watch Videos", "HD & SD MP4"]
        },
        Platform.X_TWITTER: {
            "name": "X / Twitter",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["Video Posts", "GIFs", "Threads"]
        },
        Platform.REDDIT: {
            "name": "Reddit",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["Reddit Videos (A/V Muxed)"]
        },
        Platform.PINTEREST: {
            "name": "Pinterest",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["Pins", "Idea Pins"]
        },
        Platform.GENERIC: {
            "name": "Universal Video",
            "icon": "",
            "color": "#415048",
            "badge_color": "#323E38",
            "supported_types": ["Direct Stream", "Any supported site"]
        }
    }

    @classmethod
    def detect(cls, url: str) -> Dict[str, Any]:
        url = url.strip()
        if not url:
            return cls._make_result(Platform.GENERIC, is_empty=True)

        # YouTube Detection
        if re.search(r'(?:youtube\.com|youtu\.be)', url, re.IGNORECASE):
            is_playlist = "list=" in url and not ("watch?v=" in url and "index=" not in url)
            is_shorts = "/shorts/" in url
            return cls._make_result(
                Platform.YOUTUBE,
                is_playlist=is_playlist,
                content_hint="Shorts" if is_shorts else ("Playlist" if is_playlist else "Video")
            )

        # TikTok Detection
        if re.search(r'(?:tiktok\.com|douyin\.com)', url, re.IGNORECASE):
            is_shortdrama = "/shortdrama/episode/" in url or "/series/" in url
            return cls._make_result(
                Platform.TIKTOK,
                is_shortdrama=is_shortdrama,
                content_hint="Short Drama (Series)" if is_shortdrama else "Video / Reel"
            )

        # Instagram Detection
        if re.search(r'(?:instagram\.com|instagr\.am)', url, re.IGNORECASE):
            is_reel = "/reel/" in url or "/reels/" in url
            is_story = "/stories/" in url
            return cls._make_result(
                Platform.INSTAGRAM,
                content_hint="Story" if is_story else ("Reel" if is_reel else "Post / Carousel")
            )

        # Facebook Detection
        if re.search(r'(?:facebook\.com|fb\.watch|fb\.com)', url, re.IGNORECASE):
            is_reel = "/reel/" in url or "/reels/" in url
            return cls._make_result(
                Platform.FACEBOOK,
                content_hint="Reel" if is_reel else "Watch Video"
            )

        # X / Twitter Detection
        if re.search(r'(?:twitter\.com|x\.com)', url, re.IGNORECASE):
            return cls._make_result(Platform.X_TWITTER, content_hint="Tweet / Video")

        # Reddit Detection
        if re.search(r'reddit\.com', url, re.IGNORECASE):
            return cls._make_result(Platform.REDDIT, content_hint="Reddit Video")

        # Pinterest Detection
        if re.search(r'(?:pinterest\.com|pin\.it)', url, re.IGNORECASE):
            return cls._make_result(Platform.PINTEREST, content_hint="Pinterest Pin")

        # Generic / Other
        return cls._make_result(Platform.GENERIC, content_hint="Universal Stream")

    @classmethod
    def _make_result(cls, platform: Platform, is_empty: bool = False, **kwargs) -> Dict[str, Any]:
        meta = cls.PLATFORM_METADATA.get(platform, cls.PLATFORM_METADATA[Platform.GENERIC])
        result = {
            "platform": platform,
            "name": meta["name"],
            "icon": meta.get("icon", ""),
            "color": meta["color"],
            "badge_color": meta["badge_color"],
            "supported_types": meta["supported_types"],
            "is_empty": is_empty,
            "is_shortdrama": kwargs.get("is_shortdrama", False),
            "is_playlist": kwargs.get("is_playlist", False),
            "content_hint": kwargs.get("content_hint", "Video")
        }
        return result
