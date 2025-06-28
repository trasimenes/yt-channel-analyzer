#!/usr/bin/env python3
"""
Diagnostic de la structure de la page Expedia YouTube
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def handle_consent(driver):
    """Gestion rapide du consentement"""
    current_url = driver.current_url
    if "consent.youtube.com" in current_url:
        print("🔄 Gestion du consentement...")
        try:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//form//button[contains(@class, 'VfPpkd-LgbsSe')]"))
            )
            button.click()
            time.sleep(3)
            return True
        except:
            return False
    return True

def analyze_expedia_structure():
    print("🔍 DIAGNOSTIC - Structure page Expedia")
    print("=" * 50)
    
    # Configuration Chrome basique
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    try:
        # Charger la page
        url = "https://www.youtube.com/@Expedia/videos"
        print(f"📺 Chargement: {url}")
        driver.get(url)
        time.sleep(5)
        
        # Gérer consentement
        handle_consent(driver)
        time.sleep(5)
        
        print(f"🔗 URL finale: {driver.current_url}")
        
        # Analyser la structure de la page
        print("\n📊 ANALYSE DE LA STRUCTURE:")
        
        # 1. Conteneurs principaux
        containers = [
            ("ytd-rich-grid-renderer", "Grille principale"),
            ("ytd-rich-section-renderer", "Sections"),
            ("ytd-two-column-browse-results-renderer", "Layout principal"),
            ("ytd-section-list-renderer", "Liste sections"),
            ("ytd-rich-grid-contents", "Contenu grille")
        ]
        
        for selector, description in containers:
            elements = driver.find_elements(By.TAG_NAME, selector)
            print(f"   {description}: {len(elements)} éléments")
        
        # 2. Types de vidéos
        video_selectors = [
            ("ytd-rich-item-renderer", "Items riches"),
            ("ytd-grid-video-renderer", "Vidéos grille"),
            ("ytd-video-renderer", "Vidéos standard"),
            ("a[href*='watch?v=']", "Liens vidéos"),
            ("#video-title", "Titres vidéos")
        ]
        
        print("\n🎬 TYPES DE CONTENU VIDÉO:")
        for selector, description in video_selectors:
            if selector.startswith("#") or selector.startswith("["):
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            else:
                elements = driver.find_elements(By.TAG_NAME, selector)
            print(f"   {description}: {len(elements)} éléments")
        
        # 3. Pagination et chargement
        print("\n⏳ ÉLÉMENTS DE CHARGEMENT:")
        loading_selectors = [
            ("tp-yt-paper-spinner", "Spinners"),
            ("ytd-continuation-item-renderer", "Continuation"),
            ("[data-scroll-trigger]", "Triggers scroll"),
            ("ytd-rich-grid-renderer[has-continuation]", "Grille avec continuation")
        ]
        
        for selector, description in loading_selectors:
            if selector.startswith("["):
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            else:
                elements = driver.find_elements(By.TAG_NAME, selector)
            print(f"   {description}: {len(elements)} éléments")
        
        # 4. Hauteur et position de scroll
        print("\n📏 MÉTRIQUES DE PAGE:")
        height = driver.execute_script("return document.body.scrollHeight")
        client_height = driver.execute_script("return document.documentElement.clientHeight")
        scroll_position = driver.execute_script("return window.pageYOffset")
        
        print(f"   Hauteur totale: {height}px")
        print(f"   Hauteur visible: {client_height}px")
        print(f"   Position scroll: {scroll_position}px")
        print(f"   Ratio visible: {client_height/height*100:.1f}%")
        
        # 5. Test de scroll simple
        print("\n🔄 TEST DE SCROLL:")
        initial_height = height
        initial_videos = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']"))
        
        print(f"   Avant scroll: {initial_videos} vidéos, {initial_height}px")
        
        # Scroll vers le bas
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        new_videos = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']"))
        
        print(f"   Après scroll: {new_videos} vidéos, {new_height}px")
        print(f"   Changement: {new_videos - initial_videos} vidéos, {new_height - initial_height}px")
        
        # 6. Vérifier s'il y a des onglets ou sections
        print("\n📑 ONGLETS ET SECTIONS:")
        tab_selectors = [
            ("tp-yt-paper-tab", "Onglets"),
            ("yt-tab-shape", "Onglets modernes"),
            ("[role='tab']", "Onglets ARIA"),
            ("ytd-feed-filter-chip-bar-renderer", "Filtres")
        ]
        
        for selector, description in tab_selectors:
            if selector.startswith("["):
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            else:
                elements = driver.find_elements(By.TAG_NAME, selector)
            
            if elements:
                print(f"   {description}: {len(elements)} éléments")
                for i, elem in enumerate(elements[:3]):  # Afficher les 3 premiers
                    try:
                        text = elem.text.strip()
                        if text:
                            print(f"     - {text}")
                    except:
                        pass
        
        # 7. Extraire quelques URLs de vidéos pour vérifier la qualité
        print("\n🔗 ÉCHANTILLON DE VIDÉOS:")
        video_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']")
        unique_links = list(set([link.get_attribute('href') for link in video_links if link.get_attribute('href')]))
        
        print(f"   Total liens: {len(video_links)}")
        print(f"   Liens uniques: {len(unique_links)}")
        
        for i, link in enumerate(unique_links[:5]):
            if link and 'watch?v=' in link:
                video_id = link.split('watch?v=')[1].split('&')[0]
            else:
                video_id = "ID inconnu"
            print(f"   {i+1}. {video_id}")
        
        print("\n🎯 CONCLUSION:")
        if new_height == initial_height and new_videos == initial_videos:
            print("   ❌ AUCUN NOUVEAU CONTENU après scroll")
            print("   ➡️  YouTube semble limiter l'affichage à ~134 vidéos")
        else:
            print("   ✅ Nouveau contenu détecté après scroll")
            print("   ➡️  Le scroll fonctionne, il faut être plus patient")
        
        return len(unique_links)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 0
        
    finally:
        driver.quit()

if __name__ == "__main__":
    result = analyze_expedia_structure()
    print(f"\n🏁 Analyse terminée. {result} vidéos uniques détectées") 