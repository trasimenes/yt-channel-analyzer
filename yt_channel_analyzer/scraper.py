import subprocess
from bs4 import BeautifulSoup, Tag
import os
import tempfile
import requests
from urllib.parse import quote
import json
from datetime import datetime

TORCRAWL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'torcrawl.py'))

def tor_scrape_youtube_videos(channel_url, max_videos=10, start_date=None, end_date=None):
    """
    Utilise TorCrawl.py pour récupérer la page /videos d'une chaîne YouTube via Tor,
    puis extrait les titres et URLs des vidéos avec BeautifulSoup.
    Filtre selon les dates si possible.
    """
    videos_url = channel_url.rstrip('/') + '/videos'
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
        tmpfile_path = tmpfile.name
    # Appel TorCrawl.py pour extraire la page dans un fichier temporaire
    cmd = [
        'python3', TORCRAWL_PATH, '-u', videos_url, '-e', '-w', '-o', tmpfile_path
    ]
    subprocess.run(cmd, check=True)
    # Lecture et parsing du HTML
    with open(tmpfile_path, 'r', encoding='utf-8') as f:
        html = f.read()
    os.remove(tmpfile_path)
    soup = BeautifulSoup(html, 'html.parser')
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
            meta = parent.select_one('#metadata-line span')
            if meta:
                date_str = meta.text.strip()
        # On ne peut pas parser la date exacte sans API, mais on peut afficher le texte
        video = {'title': title, 'url': url, 'date': date_str}
        # Si dates fournies, essayer de filtrer (approximatif)
        if start_date or end_date:
            # Impossible de parser la vraie date sans API, donc on ne filtre que si date_str contient l'année
            if date_str and (start_date or end_date):
                try:
                    # Cherche une année dans date_str
                    for fmt in ["%Y", "%d %b %Y", "%b %Y"]:
                        if any(c.isdigit() for c in date_str):
                            dt = datetime.strptime(date_str, fmt)
                            if start_date and dt < datetime.fromisoformat(start_date):
                                continue
                            if end_date and dt > datetime.fromisoformat(end_date):
                                continue
                except Exception:
                    pass  # Si parsing impossible, on garde la vidéo
        videos.append(video)
        if max_videos is not None and len(videos) >= max_videos:
            break
    return videos

def autocomplete_youtube_channels(query, max_results=5):
    """
    Scrape les suggestions de chaînes YouTube à partir du JSON embarqué dans la page de recherche publique.
    """
    search_url = f'https://www.youtube.com/results?search_query={quote(query)}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    resp = requests.get(search_url, headers=headers, timeout=5)
    soup = BeautifulSoup(resp.text, 'html.parser')
    suggestions = []
    # Chercher le script contenant 'var ytInitialData ='
    for script in soup.find_all('script'):
        script_content = script.get_text()
        if script_content and 'var ytInitialData =' in script_content:
            json_text = script_content.split('var ytInitialData =',1)[1].rsplit(';',1)[0].strip()
            try:
                data = json.loads(json_text)
                # Parcours du JSON pour trouver les chaînes
                sections = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
                for section in sections:
                    items = section.get('itemSectionRenderer', {}).get('contents', [])
                    for item in items:
                        channel = item.get('channelRenderer')
                        if channel:
                            # Récupération sécurisée du nom avec fallback
                            try:
                                name = channel.get('title', {}).get('simpleText', 'Nom inconnu')
                                if not name or name == '':
                                    name = 'Nom inconnu'
                            except:
                                name = 'Nom inconnu'
                            
                            # Récupération sécurisée de l'URL avec fallback
                            try:
                                url_path = channel.get('navigationEndpoint', {}).get('commandMetadata', {}).get('webCommandMetadata', {}).get('url', '')
                                url = 'https://www.youtube.com' + url_path if url_path else ''
                            except:
                                url = ''
                            
                            # Récupération sécurisée de la miniature
                            try:
                                thumbnails = channel.get('thumbnail', {}).get('thumbnails', [])
                                thumbnail_url = ''
                                if thumbnails:
                                    # Prendre la miniature de meilleure qualité (la dernière dans la liste)
                                    thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
                            except:
                                thumbnail_url = ''
                            
                            if name and url:  # Seulement ajouter si on a au moins un nom et une URL
                                suggestions.append({
                                    'name': name, 
                                    'url': url,
                                    'thumbnail': thumbnail_url
                                })
                                if len(suggestions) >= max_results:
                                    return suggestions
            except Exception:
                continue
    return suggestions 