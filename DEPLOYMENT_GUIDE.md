# 🚀 Guide de déploiement O2switch

## 📋 Prérequis
- Compte O2switch avec hébergement mutualisé ou VPS
- Accès SSH (inclus avec O2switch)
- Domaine configuré

## 🔧 Option 1: Hébergement mutualisé (recommandé)

### **Avantages :**
- ✅ **5€/mois** seulement
- ✅ **Python 3.9+** supporté
- ✅ **Flask** fonctionne
- ✅ **Maintenance automatique**

### **Limitations :**
- ❌ **Pas de Selenium** (pas de Chrome)
- ⚠️ **Mode API seulement** pour le scraping

### **Adaptations nécessaires :**

#### 1. Remplacer Selenium par requests + BeautifulSoup
```python
# Dans selenium_scraper.py - version O2switch
def get_channel_videos_lightweight(channel_url: str) -> List[Dict]:
    """Version allégée sans Selenium pour O2switch mutualisé"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Garder l'OCR mobile pour le comptage exact
    total_videos = extract_video_count_with_ocr(channel_url)
    
    # Scraping avec requests + BeautifulSoup
    response = requests.get(f"{channel_url}/videos", headers=headers)
    # ... parsing HTML
```

#### 2. Structure de fichiers O2switch
```
/www/
├── .htaccess                 # Configuration Apache
├── app.py                    # Point d'entrée Flask
├── requirements.txt          # Dependencies Python
├── yt_channel_analyzer/      # Code principal
├── templates/               # Templates HTML
├── static/                  # CSS/JS
└── cache_recherches/        # Cache JSON (writable)
```

#### 3. Configuration .htaccess
```apache
# .htaccess pour O2switch
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ app.py/$1 [QSA,L]

# Variables d'environnement
SetEnv FLASK_ENV production
SetEnv PYTHONPATH /home/ton-compte/www
```

#### 4. Adaptation app.py pour O2switch
```python
# En début de app.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Configuration production
if os.environ.get('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    # Désactiver les tâches Selenium
    SELENIUM_ENABLED = False
else:
    SELENIUM_ENABLED = True
```

## 🔧 Option 2: VPS O2switch (pour Selenium complet)

### **Avantages :**
- ✅ **Contrôle total** du serveur
- ✅ **Selenium + Chrome** possible
- ✅ **Performance optimale**
- ✅ **Toutes les fonctionnalités**

### **Coût :**
- 💰 **15-20€/mois** (VPS Standard)

### **Installation complète :**
```bash
# 1. Installer Chrome sur VPS Ubuntu
sudo apt update
sudo apt install -y chromium-browser

# 2. Dependencies Python
sudo apt install python3-pip python3-venv

# 3. Setup projet
cd /var/www/html
git clone ton-repo
cd yt-channel-analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Service systemd
sudo systemctl enable flask-app
sudo systemctl start flask-app
```

## 📊 Comparaison des options

| Feature | Mutualisé (5€) | VPS (20€) |
|---------|----------------|-----------|
| **OCR Mobile** | ✅ | ✅ |
| **Selenium Desktop** | ❌ | ✅ |
| **Analyse complète** | ⚠️ Limitée | ✅ Complète |
| **Maintenance** | ✅ Auto | ⚠️ Manuelle |
| **Performance** | ✅ Bonne | ✅ Excellente |
| **Sécurité** | ✅ Incluse | ⚠️ À configurer |

## 🎯 Recommandation

### **Pour débuter : Mutualisé + Mode API**
1. ✅ **Coût minimal** (5€/mois)
2. ✅ **OCR fonctionne** pour le comptage exact
3. ✅ **Analyse des vidéos** via API YouTube
4. ✅ **Interface complète** disponible

### **Pour production : VPS si besoin Selenium**
- Si tu veux la découverte automatique complète
- Si tu as plus de 10 chaînes à analyser régulièrement

## 🚀 Déploiement étape par étape

### 1. Préparer le code
```bash
# Créer une branche déploiement
git checkout -b o2switch-deploy

# Adapter le code pour le mode production
# (voir adaptations ci-dessus)
```

### 2. Upload sur O2switch
```bash
# Via SSH
scp -r . ton-user@ton-domaine.com:/www/

# Ou via interface web O2switch
```

### 3. Configuration
```bash
# SSH sur O2switch
ssh ton-user@ton-domaine.com

# Installer dependencies
cd /www
python3 -m pip install --user -r requirements.txt

# Permissions cache
chmod 755 cache_recherches/
```

### 4. Test
```bash
# Tester l'application
python3 app.py

# Vérifier dans le navigateur
https://ton-domaine.com
```

## 🔒 Sécurité production

### Variables d'environnement
```python
# config_production.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'your-password'
    CACHE_DIR = '/www/cache_recherches'
```

### Backup automatique
```bash
# Script backup daily
#!/bin/bash
cd /www
tar -czf backup-$(date +%Y%m%d).tar.gz cache_recherches/
# Upload vers cloud storage
```

## 📈 Monitoring

### Logs
```python
# logging_config.py
import logging

if app.config['ENV'] == 'production':
    logging.basicConfig(
        filename='/www/logs/app.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
```

---

**✅ Conclusion** : Ton projet est **parfaitement compatible** avec O2switch ! 

L'option **mutualisé à 5€/mois** est idéale pour commencer avec quelques adaptations mineures. 