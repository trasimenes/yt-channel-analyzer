import time
import json
import re
import requests
from typing import Dict, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Selenium imports (comme YScraper) - pour la partie scroll uniquement
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Undetected ChromeDriver (clé pour éviter la détection)
import undetected_chromedriver as uc

# OCR imports
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("[WARNING] OCR non disponible. Installez: pip install pytesseract pillow")

def extract_video_data_with_beautifulsoup(video_url: str) -> Dict:
    """
    Extrait les données d'une vidéo YouTube avec Beautiful Soup (plus rapide que Selenium).
    Args:
        video_url (str): URL de la vidéo YouTube
    Returns:
        Dict: Données de la vidéo (titre, vues, date, likes, chaîne)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }
    
    try:
        response = requests.get(video_url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        video_data = {'url': video_url}
        
        # === EXTRACTION DU TITRE ===
        title = ""
        # Priorité 1: meta og:title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content', '')
        else:
            # Priorité 2: title tag
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        # Nettoyer le titre
        if title:
            title = title.replace(' - YouTube', '').strip()
        video_data['title'] = title
        
        # === EXTRACTION DES LIKES ET VUES AVEC REGEX ===
        likes = ""
        views = ""
        publication_date = ""
        channel_name = ""
        
        # Méthode 1: Recherche directe des patterns dans le HTML
        
        # Pattern pour les likes - plusieurs formats possibles
        like_patterns = [
            r'"likeCount":"(\d+)"',  # Format direct
            r'"defaultText":{"runs":\[{"text":"([0-9,\.]+[KMB]?)"}],"accessibility"',  # Format dans runs
            r'"accessibilityData":{"label":"[^"]*(\d+[,\.]?\d*[KMB]?)[^"]*(?:like|j\'aime|me gusta)',  # Dans accessibility
            r'"text":"([0-9,\.]+[KMB]?)"[^}]*"navigationEndpoint"[^}]*"watchEndpoint"',  # Bouton like
            r'"toggledText":{"accessibility":{"accessibilityData":{"label":"[^"]*(\d+[,\.]?\d*[KMB]?)[^"]*(?:like|j\'aime)"',  # Toggled state
        ]
        
        for pattern in like_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                likes = matches[0]
                break
        
        # Pattern pour les vues
        view_patterns = [
            r'"viewCount":"(\d+)"',  # Format direct  
            r'"simpleText":"([0-9,\.]+[KMB]?)\s*(?:vue|view|visualizac)',  # Format simple
            r'"runs":\[{"text":"([0-9,\.]+[KMB]?)\s*(?:vue|view)"}]',  # Dans runs
            r'"videoViewCountRenderer":{"viewCount":{"simpleText":"([^"]+)"',  # Renderer spécifique
        ]
        
        for pattern in view_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                views = matches[0]
                break
        
        # Pattern pour la date de publication
        date_patterns = [
            r'"dateText":{"simpleText":"([^"]+)"',
            r'"publishDate":"([^"]+)"',
            r'"uploadDate":"([^"]+)"',
            r'"simpleText":"(il y a [^"]+)"',
            r'"simpleText":"(\d+ \w+ \d+)"',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                publication_date = matches[0]
                break
        
        # Pattern pour le nom de la chaîne
        channel_patterns = [
            r'"ownerText":{"runs":\[{"text":"([^"]+)"',
            r'"channelName":"([^"]+)"',
            r'"author":"([^"]+)"',
        ]
        
        for pattern in channel_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                channel_name = matches[0]
                break
        
        # === FALLBACK: RECHERCHE DANS LES SCRIPTS JSON ===
        if not likes or not views:
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = getattr(script, 'string', None) or getattr(script, 'get_text', lambda: '')()
                if script_text and 'ytInitialData' in script_text:
                    try:
                        # Extraction plus robuste du JSON
                        json_start = script_text.find('var ytInitialData = ')
                        if json_start == -1:
                            json_start = script_text.find('window["ytInitialData"] = ')
                        if json_start == -1:
                            json_start = script_text.find('ytInitialData')
                        
                        if json_start != -1:
                            # Trouver le début du JSON
                            brace_start = script_text.find('{', json_start)
                            if brace_start != -1:
                                # Compter les accolades pour trouver la fin
                                brace_count = 0
                                end_pos = brace_start
                                for i, char in enumerate(script_text[brace_start:], brace_start):
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            end_pos = i + 1
                                            break
                                
                                json_str = script_text[brace_start:end_pos]
                                data = json.loads(json_str)
                                
                                # Recherche des likes et vues dans la structure JSON
                                def find_in_dict(d, keys):
                                    if isinstance(d, dict):
                                        for key, value in d.items():
                                            if key in keys:
                                                return value
                                            result = find_in_dict(value, keys)
                                            if result:
                                                return result
                                    elif isinstance(d, list):
                                        for item in d:
                                            result = find_in_dict(item, keys)
                                            if result:
                                                return result
                                    return None
                                
                                # Chercher les likes
                                if not likes:
                                    like_keys = ['likeCount', 'defaultText', 'toggledText']
                                    like_result = find_in_dict(data, like_keys)
                                    if like_result:
                                        if isinstance(like_result, str):
                                            likes = like_result
                                        elif isinstance(like_result, dict):
                                            if 'simpleText' in like_result:
                                                likes = like_result['simpleText']
                                            elif 'runs' in like_result and like_result['runs']:
                                                likes = like_result['runs'][0].get('text', '')
                                
                                # Chercher les vues
                                if not views:
                                    view_keys = ['viewCount', 'videoViewCountRenderer']
                                    view_result = find_in_dict(data, view_keys)
                                    if view_result:
                                        if isinstance(view_result, str):
                                            views = view_result
                                        elif isinstance(view_result, dict):
                                            if 'simpleText' in view_result:
                                                views = view_result['simpleText']
                                            elif 'runs' in view_result and view_result['runs']:
                                                views = view_result['runs'][0].get('text', '')
                                
                                break
                    except (json.JSONDecodeError, IndexError, KeyError) as e:
                        continue
        
        # === NETTOYAGE DES DONNÉES ===
        # Nettoyer les likes (garder seulement les chiffres et K/M/B)
        if likes:
            clean_likes = re.search(r'(\d+(?:[,\.]\d+)*[KMB]?)', str(likes))
            if clean_likes:
                likes = clean_likes.group(1)
        
        # Nettoyer les vues  
        if views:
            clean_views = re.search(r'(\d+(?:[,\.]\d+)*[KMB]?)', str(views))
            if clean_views:
                views = clean_views.group(1)
        
        # Assignation des données extraites
        video_data['likes'] = likes
        video_data['views'] = views
        video_data['publication_date'] = publication_date
        
        # Chaîne
        video_data['channel'] = {
            'name': channel_name,
            'url': '',  # Sera rempli par l'appelant
        }
        
        # Miniature
        video_id = video_url.split("watch?v=")[1].split("&")[0] if "watch?v=" in video_url else ""
        video_data['thumbnail'] = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        
        print(f"[DEBUG] Données extraites pour {video_url}: Titre='{title[:30]}...', Likes='{likes}', Vues='{views}'")
        return video_data
        
    except Exception as e:
        print(f"[DEBUG] Erreur Beautiful Soup pour {video_url}: {e}")
        return {
            'url': video_url,
            'title': '',
            'likes': '',
            'views': '',
            'publication_date': '',
            'channel': {'name': '', 'url': ''},
            'thumbnail': ''
        }

def get_video_data(url: str) -> Dict:
    """
    Scrape toutes les infos d'une vidéo YouTube (titre, chaîne, vues, date, description, likes, etc.)
    Utilise la version mobile de YouTube pour plus de légèreté.
    Args:
        url (str): URL de la vidéo YouTube
    Returns:
        dict: Dictionnaire des infos extraites
    """
    # Configuration ChromeDriver desktop pour le scraping (meilleure compatibilité)
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--window-size=5120,2880  # iMac 5K Retina pour afficher plus de vidéos')

    try:
        driver = uc.Chrome(options=opts, version_main=None)
    except Exception as e:
        try:
            driver = uc.Chrome(options=opts)
        except Exception as e2:
            raise RuntimeError(f"Erreur ChromeDriver : {str(e)} | Fallback : {str(e2)} | Mettez à jour Chrome ou réessayez.")

    driver.get(url)

    # Gestion du consentement cookie (version robuste comme YScraper)
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]"))
        )
        accept_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]")
        if accept_btns:
            accept_btns[0].click()
            time.sleep(1)
    except Exception:
        pass

    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'h1.ytd-watch-metadata'))
    )

    video = {}
    # Titre
    title = driver.find_element(By.CSS_SELECTOR, 'h1.ytd-watch-metadata').text

    # Infos chaîne
    channel = {}
    channel_element = driver.find_element(By.ID, 'owner')
    channel_url = channel_element.find_element(By.CSS_SELECTOR, 'a.yt-simple-endpoint').get_attribute('href')
    channel_name = channel_element.find_element(By.ID, 'channel-name').text
    channel_image = channel_element.find_element(By.ID, 'img').get_attribute('src')
    channel_subs = channel_element.find_element(By.ID, 'owner-sub-count').text.replace(' subscribers', '')

    channel['url'] = channel_url
    channel['name'] = channel_name
    channel['image'] = channel_image
    channel['subs'] = channel_subs

    # Description (expand)
    try:
        driver.find_element(By.ID, 'description-inline-expander').click()
    except NoSuchElementException:
        pass

    info_container_elements = driver.find_elements(By.CSS_SELECTOR, '#info-container span')
    views = info_container_elements[0].text.replace(' views', '') if len(info_container_elements) > 0 else ''
    publication_date = info_container_elements[2].text if len(info_container_elements) > 2 else ''

    try:
        description = driver.find_element(By.CSS_SELECTOR, '#description-inline-expander .ytd-text-inline-expander span').text
    except NoSuchElementException:
        description = ''

    # Extraction des likes avec sélecteurs multiples pour plus de robustesse
    likes = ''
    try:
        # Nouveau sélecteur plus spécifique basé sur la structure DOM fournie
        like_button = driver.find_element(By.CSS_SELECTOR, 'like-button-view-model button .yt-spec-button-shape-next__button-text-content')
        likes = like_button.text.strip()
    except NoSuchElementException:
        try:
            # Fallback: ancien sélecteur
            likes = driver.find_element(By.ID, 'segmented-like-button').text
        except NoSuchElementException:
            try:
                # Fallback: sélecteur plus général pour le conteneur des likes
                like_container = driver.find_element(By.CSS_SELECTOR, 'segmented-like-dislike-button-view-model')
                like_text_elements = like_container.find_elements(By.CSS_SELECTOR, '.yt-spec-button-shape-next__button-text-content')
                if like_text_elements:
                    likes = like_text_elements[0].text.strip()
            except NoSuchElementException:
                likes = ''

    video['url'] = url
    video['title'] = title
    video['channel'] = channel
    video['views'] = views
    video['publication_date'] = publication_date
    video['description'] = description
    video['likes'] = likes

    driver.quit()
    return video

def get_channel_videos_data(channel_url: str, video_limit: int = 1000) -> List[Dict]:
    """
    Récupère les données des vidéos d'une chaîne YouTube avec extraction complète des likes.
    1. COMMENCE par détecter le nombre total de vidéos avec OCR mobile
    2. Récupère la liste des vidéos depuis la page desktop
    3. Visite chaque vidéo individuellement pour extraire les likes
    Args:
        channel_url (str): URL de la chaîne (ex: https://www.youtube.com/@nom)
        video_limit (int): Nombre max de vidéos à récupérer (0 = illimité, toutes les vidéos)
    Returns:
        List[Dict]: Liste des vidéos avec leurs données complètes (titre, url, vues, date, miniature, likes)
    """
    
    # ÉTAPE 1: Détecter le nombre total de vidéos avec Google Search EN PREMIER
    print(f"[DEBUG] 🔍 Détection du nombre total de vidéos avec Google Search...")
    total_videos_expected = extract_video_count_from_google(channel_url)
    
    if total_videos_expected > 0:
        print(f"[DEBUG] ✅ Objectif: {total_videos_expected} vidéos détectées via Google Search")
        # Ajuster la limite si aucune n'est spécifiée ou si elle est trop élevée
        if video_limit == 0:
            video_limit = total_videos_expected
            print(f"[DEBUG] Mode illimité: limite ajustée à {video_limit} vidéos")
        elif video_limit > total_videos_expected:
            video_limit = total_videos_expected
            print(f"[DEBUG] Limite ajustée à {video_limit} vidéos (maximum disponible)")
    else:
        print(f"[DEBUG] ⚠️ Nombre total non détecté par Google Search, utilisation de la limite: {video_limit}")
    
    # ÉTAPE 2: Configuration ChromeDriver desktop pour le scraping (meilleure compatibilité)
    print(f"[DEBUG] 🖥️ Configuration du navigateur desktop pour scraping...")
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--window-size=5120,2880  # iMac 5K Retina pour afficher plus de vidéos')

    try:
        driver = uc.Chrome(options=opts, version_main=None)
    except Exception as e:
        try:
            driver = uc.Chrome(options=opts)
        except Exception as e2:
            raise RuntimeError(f"Erreur ChromeDriver : {str(e)} | Fallback : {str(e2)} | Mettez à jour Chrome ou réessayez.")

    # Aller sur l'onglet /videos (version desktop)
    clean_url = channel_url.strip().rstrip('/')
    if not clean_url.endswith('/videos'):
        if '/@' in clean_url or '/c/' in clean_url or '/user/' in clean_url:
            videos_url = clean_url + '/videos'
        else:
            videos_url = clean_url + '/videos'
    else:
        videos_url = clean_url

    driver.get(videos_url)

    # Gestion du consentement cookie (version robuste comme YScraper)
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]"))
        )
        accept_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]")
        if accept_btns:
            accept_btns[0].click()
            time.sleep(1)
    except Exception:
        pass

    # Attendre le container principal (comme YScraper)
    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-rich-grid-renderer")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-grid-renderer")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-browse[page-subtype='channels'] #contents"))
            )
        )
    except TimeoutException:
        pass  # On tente quand même

    # OPTIMISATION: Zoomer à 25% pour afficher plus de vidéos par page et réduire le scroll
    print(f"[DEBUG] 🔍 Application du zoom 25% pour optimiser le scroll...")
    try:
        # Méthode 1: zoom via CSS
        driver.execute_script("document.body.style.zoom='25%'")
        time.sleep(0.5)
        
        # Méthode 2: zoom via CSS transform (backup)
        driver.execute_script("document.body.style.transform='scale(0.25)'")
        driver.execute_script("document.body.style.transformOrigin='top left'")
        time.sleep(0.5)
        
        # Vérifier si le zoom a fonctionné
        zoom_check = driver.execute_script("return document.body.style.zoom || document.body.style.transform")
        print(f"[DEBUG] ✅ Zoom appliqué: {zoom_check}")
        print(f"[DEBUG] 📏 Résolution: 5120x2880 + Zoom 25% = BEAUCOUP plus de vidéos!")
    except Exception as e:
        print(f"[DEBUG] ⚠️ Erreur zoom: {e}")
        # Continuer même si le zoom échoue

    # Scroll optimisé par gros chunks - BEAUCOUP plus efficace !
    scroll_position = 0
    scroll_attempts_no_change = 0
    MAX_NO_CHANGE_SCROLLS = 8 if video_limit > 0 else 15  # Plus patient pour capturer toutes les vidéos
    SCROLL_CHUNK_SIZE = 5000  # Chunk optimisé de 5000px (équilibre vitesse/completude)
    SCROLL_PAUSE_TIME = 2.0  # Plus de temps pour laisser YouTube charger
    scroll_count = 0

    while True:
        scroll_count += 1
        
        # Vérifier si on a assez de vidéos (seulement si limite définie)
        if video_limit > 0:
            try:
                current_video_item_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-rich-item-renderer, ytd-grid-video-renderer")
                if len(current_video_item_elements) >= video_limit:
                    print(f"[DEBUG] 🎯 Limite atteinte: {len(current_video_item_elements)} >= {video_limit} vidéos")
                    driver.execute_script("window.scrollBy(0, 500);")  # Un petit scroll final
                    time.sleep(1.0)
                    break
            except Exception:
                pass
        
        # SCROLL OPTIMISÉ: Par gros chunks de pixels fixes !
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        scroll_position += SCROLL_CHUNK_SIZE
        
        print(f"[DEBUG] 📏 MÉGA Scroll #{scroll_count}: {SCROLL_CHUNK_SIZE}px → position {scroll_position}px (hauteur: {last_height}px)")
        driver.execute_script(f"window.scrollTo(0, {scroll_position});")
        time.sleep(SCROLL_PAUSE_TIME)
        
        # Vérifier si on a atteint le bas ou si la page n'a pas changé
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        current_scroll_position = driver.execute_script("return window.pageYOffset;")
        
        if scroll_position >= new_height or current_scroll_position + 1000 >= new_height:
            scroll_attempts_no_change += 1
            print(f"[DEBUG] 🔍 Fin de page détectée (tentative {scroll_attempts_no_change}/{MAX_NO_CHANGE_SCROLLS})")
        else:
            scroll_attempts_no_change = 0
        
        if scroll_attempts_no_change >= MAX_NO_CHANGE_SCROLLS:
            print(f"[DEBUG] Fin de scroll atteinte après {scroll_count} scrolls de {SCROLL_CHUNK_SIZE}px")
            break

    # ÉTAPE 1: Extraction des URLs depuis la grille (comme YScraper)
    video_urls = []
    collected_urls_set = set()
    try:
        video_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-rich-item-renderer, ytd-grid-video-renderer")
        
        # Limiter seulement si nécessaire
        elements_to_process = video_elements[:video_limit] if video_limit > 0 else video_elements
        
        for elem in elements_to_process:
            try:
                # URL (sélecteurs multiples comme YScraper)
                title_link = None
                try:
                    title_link = elem.find_element(By.CSS_SELECTOR, "a#video-title-link")
                except NoSuchElementException:
                    try:
                        title_link = elem.find_element(By.CSS_SELECTOR, "a#video-title")
                    except NoSuchElementException:
                        continue
                
                url = title_link.get_attribute('href')
                
                if not url or "watch?v=" not in url:
                    continue
                    
                video_id_param = url.split("watch?v=")[1].split("&")[0]
                normalized_url = f"https://www.youtube.com/watch?v={video_id_param}"
                
                if normalized_url in collected_urls_set:
                    continue
                    
                video_urls.append(normalized_url)
                collected_urls_set.add(normalized_url)
                
                # Si limite atteinte, arrêter
                if video_limit > 0 and len(video_urls) >= video_limit:
                    break
                
            except Exception as e:
                print(f"[DEBUG] Erreur extraction URL vidéo : {e}")
                continue
                
    except Exception as e:
        print(f"[DEBUG] Erreur lors de l'extraction des URLs vidéos : {e}")

    print(f"[DEBUG] {len(video_urls)} URLs vidéos extraites, début de l'extraction détaillée...")

    # Fermer le driver Selenium maintenant que nous avons les URLs
    driver.quit()

    # ÉTAPE 2: Extraction rapide avec Beautiful Soup (parallélisable)
    videos_data = []
    print(f"[DEBUG] Début extraction Beautiful Soup pour {len(video_urls)} vidéos...")
    
    for i, video_url in enumerate(video_urls):
        print(f"[DEBUG] Extraction vidéo {i+1}/{len(video_urls)}: {video_url}")
        
        # Utiliser Beautiful Soup pour extraire les données
        video_data = extract_video_data_with_beautifulsoup(video_url)
        
        # Ajouter l'URL de la chaîne
        if 'channel' in video_data:
            video_data['channel']['url'] = channel_url
        
        videos_data.append(video_data)
        print(f"[DEBUG] ✓ Vidéo extraite: {video_data['title'][:50] if video_data['title'] else 'Sans titre'}... | Likes: {video_data['likes']}")
        
        # Petite pause pour être respectueux
        time.sleep(0.5)

    print(f"[DEBUG] Extraction terminée: {len(videos_data)} vidéos avec données complètes")
    return videos_data

def get_channel_videos_data_incremental_background(
    channel_url: str, 
    existing_videos: List[Dict] = None, 
    progress_callback=None,
    task_id: str = None
) -> List[Dict]:
    """
    Version background du scraping incrémental avec callbacks de progression.
    Scraping respectueux et lent pour éviter les limites YouTube.
    """
    
    if existing_videos is None:
        existing_videos = []
    
    # Extraire les URLs existantes pour éviter les doublons
    existing_urls = {video.get('url', '') for video in existing_videos if video.get('url')}
    
    def update_progress(step: str, progress: int, videos_found: int = 0, videos_processed: int = 0):
        if progress_callback:
            progress_callback(step, progress, videos_found, videos_processed)
        print(f"[TASK {task_id}] {step} - {progress}% - {videos_found} trouvées, {videos_processed} traitées")
    
    update_progress("Détection du nombre total de vidéos avec Google Search...", 5)
    
    # ÉTAPE 1: Détecter le nombre total de vidéos avec Google Search EN PREMIER
    print(f"[TASK {task_id}] 🔍 Détection du nombre total de vidéos avec Google Search...")
    total_videos_expected = extract_video_count_from_google(channel_url)
    
    if total_videos_expected > 0:
        print(f"[TASK {task_id}] ✅ Objectif: {total_videos_expected} vidéos détectées via Google Search")
        update_progress(f"Objectif: {total_videos_expected} vidéos détectées", 8)
    else:
        print(f"[TASK {task_id}] ⚠️ Nombre total non détecté par Google Search")
        update_progress("Nombre total non détecté, scroll jusqu'à la fin", 8)
    
    update_progress("Configuration du navigateur...", 10)
    
    # Configuration undetected ChromeDriver plus respectueuse
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--window-size=5120,2880  # iMac 5K Retina pour afficher plus de vidéos')
    # Plus respectueux
    opts.add_argument('--disable-background-timer-throttling')
    opts.add_argument('--disable-backgrounding-occluded-windows')

    try:
        driver = uc.Chrome(options=opts, version_main=None)
    except Exception as e:
        try:
            driver = uc.Chrome(options=opts)
        except Exception as e2:
            raise RuntimeError(f"Erreur ChromeDriver : {str(e)} | Fallback : {str(e2)}")

    # Aller sur l'onglet /videos
    clean_url = channel_url.strip().rstrip('/')
    if not clean_url.endswith('/videos'):
        if '/@' in clean_url or '/c/' in clean_url or '/user/' in clean_url:
            videos_url = clean_url + '/videos'
        else:
            videos_url = clean_url + '/videos'
    else:
        videos_url = clean_url

    update_progress("Chargement de la page YouTube...", 15)
    driver.get(videos_url)

    # Gestion du consentement cookie
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]"))
        )
        accept_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]")
        if accept_btns:
            accept_btns[0].click()
            time.sleep(2)  # Plus patient
    except Exception:
        pass

    # Attendre le container principal
    update_progress("Attente du chargement du contenu...", 18)
    try:
        WebDriverWait(driver, 20).until(  # Plus patient
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-rich-grid-renderer")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-grid-renderer")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-browse[page-subtype='channels'] #contents"))
            )
        )
    except TimeoutException:
        pass

    # OPTIMISATION: Zoomer à 25% pour afficher plus de vidéos par page
    update_progress("Optimisation: zoom à 25% pour réduire le scroll...", 19)
    try:
        # Méthode 1: zoom via CSS
        driver.execute_script("document.body.style.zoom='25%'")
        time.sleep(0.5)
        
        # Méthode 2: zoom via CSS transform (backup)
        driver.execute_script("document.body.style.transform='scale(0.25)'")
        driver.execute_script("document.body.style.transformOrigin='top left'")
        time.sleep(0.5)
        
        # Vérifier si le zoom a fonctionné
        zoom_check = driver.execute_script("return document.body.style.zoom || document.body.style.transform")
        print(f"[TASK {task_id}] ✅ Zoom appliqué: {zoom_check}")
        print(f"[TASK {task_id}] 📏 Résolution: 5120x2880 + Zoom 25% = BEAUCOUP plus de vidéos!")
    except Exception as e:
        print(f"[TASK {task_id}] ⚠️ Erreur zoom: {e}")
        # Continuer même si le zoom échoue

    # Scroll optimisé par gros chunks - BEAUCOUP plus efficace !
    scroll_position = 0
    scroll_attempts_no_change = 0
    MAX_NO_CHANGE_SCROLLS = 25  # TRÈS patient pour les chaînes avec 500+ vidéos
    SCROLL_CHUNK_SIZE = 5000  # Chunk optimisé de 5000px (équilibre vitesse/completude)
    SCROLL_PAUSE_TIME = 2.5  # Plus de temps pour laisser YouTube charger
    
    new_video_urls = []
    collected_urls_set = set()
    found_existing_video = False
    scroll_count = 0
    
    while True:
        scroll_count += 1
        update_progress(f"Scroll et découverte des vidéos... (scroll #{scroll_count})", min(20 + scroll_count * 2, 70))
        
        # Vérifier les vidéos actuellement visibles
        try:
            # DEBUGGING: Vérifier quels sélecteurs trouvent des éléments
            selectors_to_test = [
                "ytd-rich-item-renderer",
                "ytd-grid-video-renderer", 
                "ytd-video-renderer",
                "div[class*='video']",
                "[href*='watch?v=']",
                "a[href*='watch?v=']",
                "ytd-rich-grid-media"
            ]
            
            for selector in selectors_to_test:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"[DEBUG] Sélecteur '{selector}' trouve {len(elements)} éléments")
                else:
                    print(f"[DEBUG] Sélecteur '{selector}' trouve 0 éléments")
            
            # Essayer de trouver TOUS les liens vers des vidéos
            all_video_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']")
            print(f"[DEBUG] Total de liens vidéo trouvés: {len(all_video_links)}")
            
            if len(all_video_links) > 0:
                print(f"[DEBUG] Premier lien trouvé: {all_video_links[0].get_attribute('href')}")
                print(f"[DEBUG] Structure du parent: {all_video_links[0].find_element(By.XPATH, '..').tag_name}")
            
            # Utiliser le sélecteur qui marche le mieux
            current_video_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']")
            
            print(f"[TASK {task_id}] 🔍 Trouvé {len(current_video_elements)} éléments vidéo")
            
            for elem in current_video_elements:
                try:
                    # URL directement depuis le lien
                    url = elem.get_attribute('href')
                    
                    if not url or "watch?v=" not in url:
                        continue
                        
                    video_id_param = url.split("watch?v=")[1].split("&")[0]
                    normalized_url = f"https://www.youtube.com/watch?v={video_id_param}"
                    
                    if normalized_url in collected_urls_set:
                        continue
                    
                    # Vérifier si cette vidéo existe déjà en cache
                    if normalized_url in existing_urls:
                        found_existing_video = True
                        continue
                    
                    # Nouvelle vidéo à ajouter
                    new_video_urls.append(normalized_url)
                    collected_urls_set.add(normalized_url)
                    
                    # Mise à jour de la progression
                    total_videos_found = len(existing_videos) + len(new_video_urls)
                    
                    # CONTINUE même si objectif atteint - on veut TOUTES les vidéos disponibles !
                    if total_videos_expected > 0 and total_videos_found >= total_videos_expected:
                        update_progress(
                            f"Objectif dépassé: {total_videos_found}/{total_videos_expected} vidéos - continuons !",
                            70,
                            total_videos_found
                        )
                        # PAS de break ! On continue pour trouver TOUTES les vidéos
                    
                    update_progress(
                        f"Découverte: {len(new_video_urls)} nouvelles ({total_videos_found}/{total_videos_expected or '?'} total)",
                        min(20 + scroll_count * 2, 70),
                        total_videos_found
                    )
                        
                except Exception as e:
                    print(f"[DEBUG] Erreur traitement élément: {e}")
                    continue
                
        except Exception as e:
            print(f"[DEBUG] Erreur lors de la vérification des vidéos: {e}")
        
        # SCROLL OPTIMISÉ: Par gros chunks de pixels fixes !
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        scroll_position += SCROLL_CHUNK_SIZE
        
        print(f"[TASK {task_id}] 📏 Scroll optimisé de {SCROLL_CHUNK_SIZE}px → position {scroll_position}px (hauteur: {last_height}px)")
        driver.execute_script(f"window.scrollTo(0, {scroll_position});")
        time.sleep(SCROLL_PAUSE_TIME)
        
        # Vérifier si on a atteint le bas ou si la page n'a pas changé
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        current_scroll_position = driver.execute_script("return window.pageYOffset;")
        
        if scroll_position >= new_height or current_scroll_position + 1000 >= new_height:
            scroll_attempts_no_change += 1
            print(f"[TASK {task_id}] 🔍 Fin de page détectée (tentative {scroll_attempts_no_change}/{MAX_NO_CHANGE_SCROLLS})")
        else:
            scroll_attempts_no_change = 0
        
        if scroll_attempts_no_change >= MAX_NO_CHANGE_SCROLLS:
            update_progress("Fin du scroll atteinte", 75)
            break

    update_progress(f"Découverte terminée: {len(new_video_urls)} nouvelles vidéos", 80)

    # Fermer le driver Selenium
    driver.quit()

    # Extraction des données pour les nouvelles vidéos seulement
    new_videos_data = []
    
    if new_video_urls:
        update_progress("Extraction des données des nouvelles vidéos...", 85)
        
        for i, video_url in enumerate(new_video_urls):
            progress_extraction = 85 + (i / len(new_video_urls)) * 10
            update_progress(
                f"Extraction vidéo {i+1}/{len(new_video_urls)}",
                int(progress_extraction),
                len(existing_videos) + len(new_videos_data),
                i
            )
            
            # Utiliser Beautiful Soup pour extraire les données
            video_data = extract_video_data_with_beautifulsoup(video_url)
            
            # Ajouter l'URL de la chaîne
            if 'channel' in video_data:
                video_data['channel']['url'] = channel_url
            
            new_videos_data.append(video_data)
            
            # Pause respectueuse entre chaque extraction
            time.sleep(1.0)  # Plus respectueux
    
    # Combiner les vidéos existantes avec les nouvelles
    all_videos = new_videos_data + existing_videos
    
    update_progress("Tâche terminée avec succès", 100, len(all_videos), len(new_videos_data))
    
    return all_videos

# Fonction de compatibilité
def get_channel_video_links(channel_url: str, video_limit: int = 1000) -> List[str]:
    """Fonction de compatibilité - retourne seulement les URLs"""
    videos_data = get_channel_videos_data(channel_url, video_limit)
    return [video['url'] for video in videos_data]

def get_channel_videos_data_incremental(channel_url: str, existing_videos: List[Dict] = None, video_limit: int = 0) -> List[Dict]:
    """
    Récupère les données des vidéos d'une chaîne YouTube de façon incrémentale.
    Utilise les vidéos existantes pour ne récupérer que les nouvelles et les manquantes.
    
    Args:
        channel_url (str): URL de la chaîne (ex: https://www.youtube.com/@nom)
        existing_videos (List[Dict]): Vidéos déjà en cache (optionnel)
        video_limit (int): Nombre max de vidéos à récupérer (0 = illimité)
    
    Returns:
        List[Dict]: Liste complète des vidéos (existantes + nouvelles + anciennes manquantes)
    """
    
    if existing_videos is None:
        existing_videos = []
    
    # Extraire les URLs existantes pour éviter les doublons
    existing_urls = {video.get('url', '') for video in existing_videos if video.get('url')}
    
    print(f"[CACHE] {len(existing_videos)} vidéos déjà en cache pour cette chaîne")
    print(f"[DEBUG] Début du scraping incrémental...")
    
    # Configuration undetected ChromeDriver
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--window-size=5120,2880  # iMac 5K Retina pour afficher plus de vidéos')

    try:
        driver = uc.Chrome(options=opts, version_main=None)
    except Exception as e:
        try:
            driver = uc.Chrome(options=opts)
        except Exception as e2:
            raise RuntimeError(f"Erreur ChromeDriver : {str(e)} | Fallback : {str(e2)}")

    # Aller sur l'onglet /videos
    clean_url = channel_url.strip().rstrip('/')
    if not clean_url.endswith('/videos'):
        if '/@' in clean_url or '/c/' in clean_url or '/user/' in clean_url:
            videos_url = clean_url + '/videos'
        else:
            videos_url = clean_url + '/videos'
    else:
        videos_url = clean_url

    driver.get(videos_url)

    # Gestion du consentement cookie
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]"))
        )
        accept_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept all') or contains(., 'Accept') or contains(., 'I agree')]")
        if accept_btns:
            accept_btns[0].click()
            time.sleep(1)
    except Exception:
        pass

    # Attendre le container principal
    try:
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-rich-grid-renderer")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-grid-renderer")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-browse[page-subtype='channels'] #contents"))
            )
        )
    except TimeoutException:
        pass

    # Extraire le nombre total de vidéos affiché par YouTube
    total_videos_expected = 0
    try:
        # Chercher les métadonnées du canal avec différents sélecteurs
        metadata_selectors = [
            "yt-formatted-string#videosCountText",  # Nouveau format
            "#videos-count",  # Ancien format
            "[data-test-id='channel-video-count']",  # Format alternatif
            "span:contains('vidéos')",  # Recherche par texte
        ]
        
        for selector in metadata_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and ('vidéo' in text.lower() or 'video' in text.lower()):
                        # Extraire le nombre avec regex

                        numbers = re.findall(r'(\d+(?:[,\s]\d+)*)', text)
                        if numbers:
                            # Nettoyer le nombre (enlever espaces et virgules)
                            number_str = numbers[0].replace(',', '').replace(' ', '')
                            if number_str.isdigit():
                                total_videos_expected = int(number_str)
                                print(f"[DEBUG] Nombre total de vidéos détecté: {total_videos_expected}")
                                break
                if total_videos_expected > 0:
                    break
            except Exception:
                continue
        
        # Si pas trouvé avec les sélecteurs, chercher dans le HTML
        if total_videos_expected == 0:
            page_source = driver.page_source
            # Patterns pour différentes langues
            patterns = [
                r'(\d+(?:[,\s]\d+)*)\s*vidéos?',
                r'(\d+(?:[,\s]\d+)*)\s*videos?',
                r'videoCountText[^>]*>(\d+(?:[,\s]\d+)*)',
                r'"videoCount":"(\d+)"',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    number_str = matches[0].replace(',', '').replace(' ', '')
                    if number_str.isdigit():
                        total_videos_expected = int(number_str)
                        print(f"[DEBUG] Nombre total de vidéos trouvé dans le HTML: {total_videos_expected}")
                        break
                        
    except Exception as e:
        print(f"[DEBUG] Erreur lors de l'extraction du nombre total: {e}")
    
    if total_videos_expected > 0:
        print(f"[DEBUG] Objectif: {total_videos_expected} vidéos détectées sur la chaîne")
    else:
        print(f"[DEBUG] Nombre total non détecté, scroll jusqu'à la fin")

    # Scroll incrémental intelligent
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    scroll_attempts_no_change = 0
    MAX_NO_CHANGE_SCROLLS = 15 if video_limit == 0 else 7
    SCROLL_PAUSE_TIME = 2.0
    
    new_video_urls = []
    collected_urls_set = set()
    found_existing_video = False
    
    while True:
        # Vérifier les vidéos actuellement visibles
        try:
            current_video_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-rich-item-renderer, ytd-grid-video-renderer")
            
            for elem in current_video_elements:
                try:
                    # URL (sélecteurs multiples)
                    title_link = None
                    try:
                        title_link = elem.find_element(By.CSS_SELECTOR, "a#video-title-link")
                    except NoSuchElementException:
                        try:
                            title_link = elem.find_element(By.CSS_SELECTOR, "a#video-title")
                        except NoSuchElementException:
                            continue
                    
                    url = title_link.get_attribute('href')
                    
                    if not url or "watch?v=" not in url:
                        continue
                        
                    video_id_param = url.split("watch?v=")[1].split("&")[0]
                    normalized_url = f"https://www.youtube.com/watch?v={video_id_param}"
                    
                    if normalized_url in collected_urls_set:
                        continue
                    
                    # Vérifier si cette vidéo existe déjà en cache
                    if normalized_url in existing_urls:
                        found_existing_video = True
                        print(f"[CACHE] Vidéo déjà en cache trouvée: {normalized_url}")
                        continue
                    
                    # Nouvelle vidéo à ajouter
                    new_video_urls.append(normalized_url)
                    collected_urls_set.add(normalized_url)
                    
                    print(f"[NOUVEAU] Nouvelle vidéo trouvée: {normalized_url}")
                    
                    # Vérifier si on a atteint l'objectif total ou la limite
                    total_videos_found = len(existing_videos) + len(new_video_urls)
                    
                    # Si on a un objectif et qu'on l'a atteint, arrêter
                    if total_videos_expected > 0 and total_videos_found >= total_videos_expected:
                        print(f"[DEBUG] Objectif atteint: {total_videos_found}/{total_videos_expected} vidéos trouvées")
                        break
                    
                    # Si limite atteinte, arrêter
                    if video_limit > 0 and len(new_video_urls) >= video_limit:
                        break
                        
                except Exception as e:
                    continue
            
            # Si on a trouvé des vidéos existantes et qu'on a suffisamment de nouvelles, on peut s'arrêter
            if found_existing_video and video_limit > 0 and len(new_video_urls) >= video_limit:
                print(f"[DEBUG] Limite atteinte avec {len(new_video_urls)} nouvelles vidéos")
                break
                
        except Exception as e:
            print(f"[DEBUG] Erreur lors de la vérification des vidéos: {e}")
        
        # Continuer le scroll
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        
        if new_height == last_height:
            scroll_attempts_no_change += 1
        else:
            scroll_attempts_no_change = 0
        last_height = new_height
        
        if scroll_attempts_no_change >= MAX_NO_CHANGE_SCROLLS:
            print(f"[DEBUG] Fin de scroll atteinte après {scroll_attempts_no_change} tentatives sans changement")
            break

    total_final = len(existing_videos) + len(new_video_urls)
    if total_videos_expected > 0:
        print(f"[DEBUG] {len(new_video_urls)} nouvelles URLs vidéos trouvées ({total_final}/{total_videos_expected} objectif)")
    else:
        print(f"[DEBUG] {len(new_video_urls)} nouvelles URLs vidéos trouvées")

    # Fermer le driver Selenium
    driver.quit()

    # Extraction des données pour les nouvelles vidéos seulement
    new_videos_data = []
    
    if new_video_urls:
        print(f"[DEBUG] Début extraction Beautiful Soup pour {len(new_video_urls)} nouvelles vidéos...")
        
        for i, video_url in enumerate(new_video_urls):
            print(f"[DEBUG] Extraction nouvelle vidéo {i+1}/{len(new_video_urls)}: {video_url}")
            
            # Utiliser Beautiful Soup pour extraire les données
            video_data = extract_video_data_with_beautifulsoup(video_url)
            
            # Ajouter l'URL de la chaîne
            if 'channel' in video_data:
                video_data['channel']['url'] = channel_url
            
            new_videos_data.append(video_data)
            print(f"[DEBUG] ✓ Nouvelle vidéo extraite: {video_data['title'][:50] if video_data['title'] else 'Sans titre'}... | Likes: {video_data['likes']}")
            
            # Petite pause pour être respectueux
            time.sleep(0.5)
    
    # Combiner les vidéos existantes avec les nouvelles
    # Les nouvelles vidéos sont ajoutées au début (plus récentes)
    all_videos = new_videos_data + existing_videos
    
    print(f"[DEBUG] Total final: {len(all_videos)} vidéos ({len(new_videos_data)} nouvelles + {len(existing_videos)} existantes)")
    
    return all_videos 

def extract_total_video_count_from_page(channel_url: str) -> int:
    """
    Extrait le nombre total de vidéos d'une chaîne YouTube avec Beautiful Soup.
    Utilise une simple requête HTTP sans Selenium.
    """
    total_videos_expected = 0
    
    try:
        # Construire l'URL de la page /videos si nécessaire
        clean_url = channel_url.strip().rstrip('/')
        if not clean_url.endswith('/videos'):
            if '/@' in clean_url or '/c/' in clean_url or '/user/' in clean_url:
                videos_url = clean_url + '/videos'
            else:
                videos_url = clean_url + '/videos'
        else:
            videos_url = clean_url
        
        # Headers pour imiter un navigateur
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        }
        
        # Requête HTTP simple
        response = requests.get(videos_url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
        
        # Patterns optimisés pour le format YouTube 2024
        patterns = [
           r'<span[^>]*>(\d+)&nbsp;vidéos</span>',  # Format exact YouTube 2024 français
           r'<span[^>]*>(\d+)&nbsp;videos</span>',  # Format exact YouTube 2024 anglais
           r'>(\d+)&nbsp;vidéos?<',  # Format simplifié avec &nbsp;
           r'(\d+)&nbsp;vidéos?',  # Sans balises
           r'"videoCount":"(\d+)"',  # Format JSON fallback
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                # Nettoyer le nombre (enlever tous les caractères non-numériques)
                number_str = re.sub(r'[^\d]', '', matches[0])
                if number_str.isdigit():
                    total_videos_expected = int(number_str)
                    print(f"[DEBUG] Nombre total de vidéos détecté avec Beautiful Soup: {total_videos_expected}")
                    return total_videos_expected
                        
    except Exception as e:
        print(f"[DEBUG] Erreur lors de l'extraction du nombre total avec Beautiful Soup: {e}")
    
    return total_videos_expected 

def create_mobile_chrome_options():
    """
    Crée une nouvelle instance de ChromeOptions pour mobile.
    Plus légère et plus rapide que la version desktop.
    """
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-extensions')
    
    # Configuration mobile pour YouTube
    mobile_emulation = {
        "deviceMetrics": {"width": 375, "height": 812, "pixelRatio": 3.0},
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
    }
    opts.add_experimental_option("mobileEmulation", mobile_emulation)
    
    return opts

def extract_video_count_with_ocr(channel_url: str) -> int:
    """
    Extrait le nombre de vidéos d'une chaîne YouTube mobile avec OCR.
    Utilise une capture d'écran de la version mobile plus simple.
    """
    if not OCR_AVAILABLE:
        print("[DEBUG] OCR non disponible, retour à 0")
        return 0
    
    total_videos = 0
    
    try:
        # Convertir l'URL vers la version mobile
        if 'm.youtube.com' not in channel_url:
            mobile_url = channel_url.replace('www.youtube.com', 'm.youtube.com')
        else:
            mobile_url = channel_url
        
        print(f"[DEBUG] URL mobile: {mobile_url}")
        
        # Configuration Chrome mobile directe (éviter la réutilisation d'objets)
        try:
            driver = uc.Chrome(
                headless=True,
                use_subprocess=True,
                version_main=None
            )
            
            # Configurer l'émulation mobile après création
            driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                "mobile": True,
                "width": 375,
                "height": 812,
                "deviceScaleFactor": 3,
                "screenOrientation": {"type": "portraitPrimary", "angle": 0}
            })
            
            driver.execute_cdp_cmd('Emulation.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
            })
            
        except Exception as e:
            print(f"[DEBUG] Erreur configuration mobile CDP: {e}")
            driver = uc.Chrome(headless=True, use_subprocess=True)
        
        # Aller sur la version mobile
        driver.get(mobile_url)
        
        # Gérer les cookies si présents (version robuste)
        try:
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.common.by import By
            
            # Attendre un peu que la page se charge
            time.sleep(2)
            
            # Chercher n'importe quel bouton de gestion de cookies
            try:
                buttons = driver.find_elements(By.TAG_NAME, 'button')
                print(f"[DEBUG] {len(buttons)} boutons trouvés sur la page des cookies")
                
                for i, btn in enumerate(buttons):
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            text = btn.text.strip().lower()
                            # Accepter "Tout accepter", "Accepter", "Tout refuser", etc.
                            if text and any(keyword in text for keyword in ['accept', 'tout', 'refus', 'agree']):
                                print(f"[DEBUG] Clic sur bouton: {btn.text.strip()}")
                                btn.click()
                                time.sleep(3)
                                break
                    except:
                        continue
            except Exception as e:
                print(f"[DEBUG] Erreur recherche boutons: {e}")
        except Exception as e:
            print(f"[DEBUG] Gestion cookies: {e}")
            pass
        
        # Attendre que la page du canal soit chargée
        time.sleep(5)
        
        # Prendre une capture d'écran du haut de la page
        screenshot = driver.get_screenshot_as_png()
        image = Image.open(io.BytesIO(screenshot))
        
        # Recadrer pour ne garder que le haut (header avec infos du canal)
        width, height = image.size
        header_crop = image.crop((0, 0, width, height // 3))  # Premier tiers de la page
        
        # OCR sur l'image recadrée
        text = pytesseract.image_to_string(header_crop, lang='fra+eng')
        print(f"[DEBUG] Texte OCR détecté: {text[:200]}...")
        
        # Chercher le pattern "561 vidéos" dans le texte OCR
        patterns = [
            r'(\d+)\s*vidéos?',
            r'(\d+)\s*videos?',
            r'(\d+)\s*vids?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Prendre le plus grand nombre trouvé (probablement le nombre de vidéos)
                numbers = [int(m) for m in matches if m.isdigit()]
                if numbers:
                    total_videos = max(numbers)
                    print(f"[DEBUG] Nombre de vidéos détecté par OCR: {total_videos}")
                    break
        
        driver.quit()
        
    except Exception as e:
        print(f"[DEBUG] Erreur OCR: {e}")
        if 'driver' in locals():
            driver.quit()
    
    return total_videos 

def extract_video_count_from_google(channel_url: str) -> int:
    """
    Extrait le nombre total de vidéos d'une chaîne YouTube via OCR mobile.
    L'approche Google Search est bloquée, on utilise l'OCR qui fonctionnait bien.
    
    Args:
        channel_url (str): URL de la chaîne (ex: https://www.youtube.com/@ClubMed)
    
    Returns:
        int: Nombre total de vidéos détectées (0 si non trouvé)
    """
    print(f"[DEBUG] 🔍 Détection nombre de vidéos avec OCR mobile pour {channel_url}")
    return extract_video_count_with_ocr(channel_url) 