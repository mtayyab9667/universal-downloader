import re
from typing import Dict, Any, List, Optional
from curl_cffi import requests

class TikTokDramaAPI:
    BASE_URL = "https://www.tiktok.com"
    ITEM_LIST_API = "https://www.tiktok.com/api/drama/episode/item_list/"
    DRAMA_DETAIL_API = "https://www.tiktok.com/api/drama/detail/"
    
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.tiktok.com/'
    }

    @staticmethod
    def parse_drama_id_and_episode(url: str) -> tuple[Optional[str], Optional[int]]:
        """
        Extracts drama_id and episode_number from various TikTok URLs:
        - https://www.tiktok.com/shortdrama/episode/7703478731414705172/1
        - https://www.tiktok.com/shortdrama/episode/7703478731414705172
        - or raw drama ID numbers
        """
        url = url.strip()
        # Direct drama ID string (all digits)
        if url.isdigit() and len(url) > 10:
            return url, 1
            
        # Match shortdrama/episode/ID/EP
        m = re.search(r'/shortdrama/episode/(\d+)(?:/(\d+))?', url)
        if m:
            drama_id = m.group(1)
            ep_num = int(m.group(2)) if m.group(2) else 1
            return drama_id, ep_num
            
        # Match series or collection
        m = re.search(r'/series/[^/?#]+-(\d+)', url)
        if m:
            return m.group(1), 1
            
        return None, None

    def fetch_drama_episodes(self, drama_id: str, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Fetches full metadata and all episodes for a drama ID with automatic pagination.
        """
        all_episodes = []
        cursor = "0"
        has_more = True
        drama_info = {}
        total_episodes = 0
        page = 1

        session = requests.Session(impersonate='chrome120')
        if cookies:
            session.cookies.update(cookies)

        while has_more:
            params = {
                'dramaID': drama_id,
                'cursor': cursor,
                'count': '30',
                'aid': '1988'
            }
            headers = dict(self.DEFAULT_HEADERS)
            headers['Referer'] = f"https://www.tiktok.com/shortdrama/episode/{drama_id}/1"

            try:
                resp = session.get(self.ITEM_LIST_API, params=params, headers=headers, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
                if data.get('statusCode') != 0 and data.get('status_code') != 0:
                    break

                items = data.get('itemList', [])
                if not items:
                    break

                for it in items:
                    d_info = it.get('dramaInfo', {})
                    if not drama_info and d_info:
                        drama_info = {
                            'dramaID': d_info.get('dramaID', drama_id),
                            'dramaName': d_info.get('dramaName', 'Unknown Drama'),
                            'description': d_info.get('description', ''),
                            'numVideos': d_info.get('numVideos', len(items)),
                            'author': it.get('author', {}).get('uniqueId', ''),
                            'cover': (d_info.get('cover', {}).get('urlList') or [''])[0]
                        }

                    video_data = d_info.get('DramaVideoData', {})
                    ep_num = video_data.get('EpisodeNumber') or (len(all_episodes) + 1)
                    
                    episode_entry = {
                        'id': it.get('id'),
                        'episodeNumber': ep_num,
                        'title': it.get('desc') or f"Episode {ep_num}",
                        'duration': it.get('video', {}).get('duration', 0),
                        'cover': it.get('video', {}).get('cover') or drama_info.get('cover', ''),
                        'isLimitedFree': d_info.get('isLimitedFree', True),
                        'url': f"https://www.tiktok.com/shortdrama/episode/{drama_id}/{ep_num}"
                    }
                    all_episodes.append(episode_entry)

                raw_total = data.get('totalEpisodeCount') or drama_info.get('numVideos', 0)
                try:
                    total_episodes = int(raw_total)
                except (ValueError, TypeError):
                    total_episodes = len(all_episodes)

                has_more = bool(data.get('hasMore', False)) and len(all_episodes) < total_episodes
                cursor = str(data.get('cursor', ''))
                page += 1

                if not cursor or cursor == "0" or not has_more:
                    break

            except Exception as e:
                print(f"[API] Error fetching page {page}: {e}")
                break

        # Sort episodes by episode number
        all_episodes.sort(key=lambda x: x['episodeNumber'])
        
        return {
            'dramaID': drama_id,
            'dramaInfo': drama_info,
            'totalEpisodes': total_episodes or len(all_episodes),
            'episodes': all_episodes
        }
