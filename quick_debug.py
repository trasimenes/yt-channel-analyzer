#!/usr/bin/env python3
"""
Script simple pour diagnostiquer Expedia - Pourquoi 42 vidéos au lieu de 757 ?
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def test_expedia_css():
    """Test rapide des sélecteurs CSS pour Expedia"""
    print("🔍 TEST SÉLECTEURS CSS EXPEDIA")
    print("=" * 40)
    
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')

    driver = uc.Chrome(options=opts)
    
    try:
        driver.get("https://www.youtube.com/@Expedia/videos")
        
        # Cookies
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept')]"))
            ).click()
            time.sleep(2)
        except:
            pass
        
        time.sleep(5)
        
        # Test sélecteurs un par un
        selectors = [
            "ytd-rich-item-renderer",
            "ytd-grid-video-renderer", 
            "a[href*='watch?v=']",
            "ytd-rich-grid-media"
        ]
        
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"{selector:25} → {len(elements):3} éléments")
        
        # Compter les vrais liens vidéo
        video_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']")
        unique_videos = set()
        
        for link in video_links:
            href = link.get_attribute('href')
            if href and 'watch?v=' in href:
                video_id = href.split('watch?v=')[1].split('&')[0]
                unique_videos.add(video_id)
        
        print(f"\n📹 RÉSULTAT: {len(unique_videos)} vidéos uniques trouvées")
        print(f"🎯 OBJECTIF: 757 vidéos (Social Blade)")
        print(f"📉 MANQUE: {757 - len(unique_videos)} vidéos")
        
        # Test scroll
        print(f"\n🔄 Test avec scroll...")
        for i in range(5):
            driver.execute_script(f"window.scrollTo(0, {(i+1) * 3000});")
            time.sleep(2)
        
        # Recompter après scroll
        video_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']")
        unique_videos_after = set()
        
        for link in video_links:
            href = link.get_attribute('href')
            if href and 'watch?v=' in href:
                video_id = href.split('watch?v=')[1].split('&')[0]
                unique_videos_after.add(video_id)
        
        print(f"📹 APRÈS SCROLL: {len(unique_videos_after)} vidéos uniques")
        print(f"➕ NOUVELLES: {len(unique_videos_after) - len(unique_videos)} vidéos")
        
        return len(unique_videos_after)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 0
    finally:
        driver.quit()

if __name__ == "__main__":
    count = test_expedia_css()
    print(f"\n🏁 DIAGNOSTIC FINAL: {count}/757 vidéos trouvées")
    
    if count < 100:
        print("❌ PROBLÈME MAJEUR: Sélecteurs CSS ne fonctionnent pas")
    elif count < 500:
        print("⚠️  PROBLÈME PARTIEL: Scroll insuffisant ou structure différente")
    else:
        print("✅ Sélecteurs OK, problème ailleurs") 