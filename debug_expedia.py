#!/usr/bin/env python3
"""
Script de diagnostic pour Expedia - Pourquoi 42 vidéos au lieu de 757 ?
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from PIL import Image
import pytesseract

def test_ocr_mobile():
    """Test OCR sur la version mobile d'Expedia"""
    print("🔍 TEST 1: OCR Mobile pour détecter le nombre de vidéos")
    
    # Configuration mobile
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    # Configuration mobile
    opts.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1')
    opts.add_argument('--window-size=375,812')

    try:
        driver = uc.Chrome(options=opts)
        driver.get("https://m.youtube.com/@Expedia")
        
        # Cookies
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept')]"))
            ).click()
            time.sleep(1)
        except:
            pass
        
        time.sleep(3)
        
        # Screenshot et OCR
        driver.save_screenshot("expedia_mobile.png")
        image = Image.open("expedia_mobile.png")
        # Crop le header (où sont les stats)
        header_crop = image.crop((0, 0, 375, 300))
        header_crop.save("expedia_mobile_header.png")
        
        # OCR
        text = pytesseract.image_to_string(header_crop, lang='fra+eng')
        print(f"📱 Texte OCR détecté:\n{text}")
        
        # Chercher les vidéos
        video_match = re.search(r'(\d+(?:[,\s]\d+)*)\s*vidéos?', text, re.IGNORECASE)
        if video_match:
            count = video_match.group(1).replace(',', '').replace(' ', '')
            print(f"✅ OCR trouvé: {count} vidéos")
            return int(count)
        else:
            print("❌ OCR n'a pas trouvé le nombre de vidéos")
            return 0
            
    except Exception as e:
        print(f"❌ Erreur OCR: {e}")
        return 0
    finally:
        driver.quit()

def test_css_selectors():
    """Test des différents sélecteurs CSS sur la version desktop"""
    print("\n🔍 TEST 2: Sélecteurs CSS Desktop")
    
    opts = uc.ChromeOptions()
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--window-size=1920,1080')

    try:
        driver = uc.Chrome(options=opts)
        driver.get("https://www.youtube.com/@Expedia/videos")
        
        # Cookies
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accept')]"))
            ).click()
            time.sleep(2)
        except:
            pass
        
        # Attendre le chargement
        time.sleep(5)
        
        # Test différents sélecteurs
        selectors_to_test = [
            ("ytd-rich-item-renderer", "Rich Item Renderer"),
            ("ytd-grid-video-renderer", "Grid Video Renderer"),
            ("ytd-video-renderer", "Video Renderer"),
            ("a[href*='watch?v=']", "Liens vidéo directs"),
            ("ytd-rich-grid-media", "Rich Grid Media"),
            ("#contents ytd-rich-item-renderer", "Contents Rich Item"),
            ("#contents a[href*='watch?v=']", "Contents Video Links"),
            ("div[class*='video']", "Divs avec 'video'"),
            ("[id*='video']", "Éléments avec ID 'video'"),
        ]
        
        print("🎯 Test des sélecteurs:")
        best_selector = None
        max_videos = 0
        
        for selector, name in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                video_count = 0
                
                # Compter les vrais liens vidéo
                for elem in elements:
                    try:
                        if selector == "a[href*='watch?v=']" or "#contents a[href*='watch?v=']" in selector:
                            href = elem.get_attribute('href')
                            if href and 'watch?v=' in href:
                                video_count += 1
                        else:
                            # Chercher un lien vidéo dans l'élément
                            video_links = elem.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']")
                            if video_links:
                                video_count += 1
                    except:
                        continue
                
                print(f"  {name:25} → {len(elements):3} éléments, {video_count:3} vidéos")
                
                if video_count > max_videos:
                    max_videos = video_count
                    best_selector = selector
                    
            except Exception as e:
                print(f"  {name:25} → Erreur: {e}")
        
        print(f"\n🏆 Meilleur sélecteur: '{best_selector}' → {max_videos} vidéos")
        
        # Test de scroll pour voir si ça charge plus
        print(f"\n🔄 Test scroll pour charger plus de vidéos...")
        initial_count = max_videos
        
        for i in range(3):
            driver.execute_script(f"window.scrollTo(0, {(i+1) * 2000});")
            time.sleep(2)
            
            if best_selector:
                elements = driver.find_elements(By.CSS_SELECTOR, best_selector)
                video_count = 0
                for elem in elements:
                                         try:
                         if "a[href*='watch?v=']" in best_selector:
                             href = elem.get_attribute('href')
                             if href and 'watch?v=' in href:
                                 video_count += 1
                         else:
                             video_links = elem.find_elements(By.CSS_SELECTOR, "a[href*='watch?v=']")
                             if video_links:
                                 video_count += 1
                     except:
                         continue
                
                print(f"  Après scroll {i+1}: {video_count} vidéos (+{video_count - max_videos})")
                max_videos = max(max_videos, video_count)
        
        print(f"\n📊 TOTAL APRÈS SCROLLS: {max_videos} vidéos trouvées")
        print(f"🎯 OBJECTIF SOCIAL BLADE: 757 vidéos")
        print(f"📉 MANQUE: {757 - max_videos} vidéos ({((757 - max_videos)/757)*100:.1f}%)")
        
        return best_selector, max_videos
        
    except Exception as e:
        print(f"❌ Erreur test sélecteurs: {e}")
        return None, 0
    finally:
        driver.quit()

def main():
    print("🚀 DIAGNOSTIC EXPEDIA - Pourquoi 42 au lieu de 757 vidéos ?")
    print("=" * 60)
    
    # Test 1: OCR
    ocr_count = test_ocr_mobile()
    
    # Test 2: Sélecteurs CSS
    best_selector, css_count = test_css_selectors()
    
    # Résumé
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 60)
    print(f"🎯 Social Blade:     757 vidéos")
    print(f"📱 OCR Mobile:       {ocr_count} vidéos")
    print(f"🖥️  CSS Desktop:      {css_count} vidéos")
    print(f"🤖 Notre scraper:    42 vidéos (actuel)")
    print("")
    print("🔍 PROBLÈMES IDENTIFIÉS:")
    
    if ocr_count < 500:
        print("❌ OCR mobile ne détecte pas correctement")
    else:
        print("✅ OCR mobile fonctionne")
    
    if css_count < 500:
        print("❌ Sélecteurs CSS obsolètes/incomplets")
        print(f"   Meilleur sélecteur trouvé: {best_selector}")
    else:
        print("✅ Sélecteurs CSS fonctionnent")
    
    if css_count > 0 and css_count < 757:
        print("⚠️  Scroll incomplet - toutes les vidéos ne se chargent pas")

if __name__ == "__main__":
    main() 