import requests
from bs4 import BeautifulSoup, Tag
from datetime import datetime

def simple_scrape_youtube_videos(channel_url, max_videos=None, start_date=None, end_date=None):
    """
    Scrape la page /videos d'une chaîne YouTube (sans Tor), extrait titres, URLs, et date si possible.
    Filtre selon dates et limite le nombre de vidéos.
    """
    url = channel_url.rstrip('/')
    if not url.endswith('/videos'):
        videos_url = url + '/videos'
    else:
        videos_url = url
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    resp = requests.get(videos_url, headers=headers, timeout=10)
    soup = BeautifulSoup(resp.text, 'html.parser')
    videos = []
    for a in soup.select('a#video-title'):
        title = a.get('title')
        href = a.get('href')
        if not href or not isinstance(href, str):
            continue
        url = 'https://www.youtube.com' + href
        # Essayer de récupérer la date de publication si possible
        parent = a.find_parent('ytd-grid-video-renderer') or a.find_parent('ytd-rich-item-renderer')
        date_str = None
        if parent and isinstance(parent, Tag):
            meta_span = parent.select_one('#metadata-line span')
            if meta_span:
                date_str = meta_span.text.strip()
        video = {'title': title, 'url': url, 'date': date_str}
        # Si dates fournies, essayer de filtrer (approximatif)
        if start_date or end_date:
            # Impossible de parser la vraie date sans API, donc on ne filtre que si date_str contient l'année
            if date_str and (start_date or end_date):
                try:
                    for fmt in ["%Y", "%d %b %Y", "%b %Y"]:
                        if any(c.isdigit() for c in date_str):
                            dt = datetime.strptime(date_str, fmt)
                            if start_date and dt < datetime.fromisoformat(start_date):
                                continue
                            if end_date and dt > datetime.fromisoformat(end_date):
                                continue
                except Exception:
                    pass
        videos.append(video)
        if max_videos is not None and len(videos) >= max_videos:
            break
    return videos 