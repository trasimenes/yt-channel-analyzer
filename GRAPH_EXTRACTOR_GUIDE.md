# Graph Data Extractor - Guide d'utilisation

🎯 **Outil d'extraction de données de graphiques sans Plot Digitizer**

## 📋 Vue d'ensemble

Cet outil vous permet d'extraire des données numériques depuis des graphiques affichés à l'écran, en utilisant plusieurs méthodes :

1. **Balayage horizontal avec captures** - Simule une souris qui suit la courbe
2. **Détection automatique de courbe** - Analyse et suit automatiquement une courbe colorée
3. **Extraction depuis vidéo** - Analyse des graphiques dans des vidéos
4. **OCR intelligent** - Extrait les valeurs numériques automatiquement

## 🚀 Installation

### 1. Dépendances Python
```bash
pip install opencv-python pyautogui pytesseract pillow
```

### 2. Tesseract OCR
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra

# Windows
# Télécharger depuis : https://github.com/UB-Mannheim/tesseract/wiki
```

### 3. Permissions (macOS)
- Aller dans **Préférences Système** > **Sécurité et confidentialité** > **Confidentialité**
- Autoriser l'accès à l'écran pour votre terminal/IDE

## 🎯 Utilisation pratique

### Méthode 1 : Balayage horizontal (Recommandée)

Cette méthode simule une souris qui suit votre courbe de gauche à droite :

```python
from yt_channel_analyzer.graph_data_extractor import GraphDataExtractor

# Créer l'extracteur
extractor = GraphDataExtractor()

# Configuration
extractor.screenshot_interval = 0.25  # Capture toutes les 1/4 secondes

# Lancer l'extraction
data_points = extractor.horizontal_scan_with_screenshots(
    start_x=100, start_y=300,  # Point de départ
    end_x=800, end_y=200,      # Point d'arrivée
    duration=10.0,             # Durée en secondes
    extract_ocr=True           # Activer l'OCR
)
```

### Méthode 2 : Fonction rapide

Pour une utilisation simple et rapide :

```python
from yt_channel_analyzer.graph_data_extractor import quick_horizontal_scan

# Fonction interactive simple
data_points = quick_horizontal_scan(duration=10.0)
```

### Méthode 3 : Détection automatique de courbe

Pour détecter automatiquement une courbe colorée :

```python
extractor = GraphDataExtractor()

# Définir la région à analyser (x, y, largeur, hauteur)
region = (100, 100, 600, 400)

# Couleur de la courbe à suivre (Rouge, Vert, Bleu)
curve_color = (255, 0, 0)  # Rouge

# Lancer la détection
data_points = extractor.detect_and_follow_curve(
    region=region,
    curve_color=curve_color,
    tolerance=30
)
```

### Méthode 4 : Extraction depuis vidéo

Pour analyser des graphiques dans des vidéos :

```python
extractor = GraphDataExtractor()

# Analyser une vidéo
data_points = extractor.extract_from_video(
    video_path="path/to/your/video.mp4",
    frame_interval=30  # Analyser toutes les 30 frames
)
```

## 📊 Cas d'usage pratiques

### 1. Analyser des graphiques YouTube Analytics

```python
# Ouvrir YouTube Analytics dans votre navigateur
# Aller sur la page des statistiques de vues
# Utiliser l'extraction horizontale

extractor = GraphDataExtractor()

# Pour une courbe comme celle montrée dans l'image
data_points = extractor.horizontal_scan_with_screenshots(
    start_x=250, start_y=650,  # Début de la courbe
    end_x=1200, end_y=300,     # Fin de la courbe
    duration=15.0              # 15 secondes pour parcourir
)

# Les données extraites contiendront :
# - Timestamps
# - Valeurs numériques (8.56K, etc.)
# - Positions x,y
# - Captures d'écran
```

### 2. Extraire des données de Social Blade

```python
# Ouvrir Social Blade avec un graphique de croissance
# Configurer pour suivre la courbe rouge

extractor = GraphDataExtractor()

# Région du graphique
region = (200, 200, 800, 500)

# Détecter la courbe rouge automatiquement
data_points = extractor.detect_and_follow_curve(
    region=region,
    curve_color=(255, 0, 0),  # Rouge
    tolerance=20
)
```

### 3. Analyser des présentations avec graphiques

```python
# Pour des graphiques dans des présentations PDF/PowerPoint
# Prendre une capture d'écran ou exporter en vidéo

extractor = GraphDataExtractor()

# Méthode vidéo pour des présentations enregistrées
data_points = extractor.extract_from_video(
    video_path="presentation_with_graphs.mp4",
    frame_interval=60  # Analyser toutes les 2 secondes
)
```

## 🛠️ Démonstration interactive

Lancez le script de démonstration :

```bash
python demo_graph_extractor.py
```

Ce script vous guidera à travers toutes les fonctionnalités avec des exemples pratiques.

## 📈 Format des données extraites

Les données sont retournées sous forme de liste de dictionnaires :

```json
[
  {
    "index": 0,
    "timestamp": 0.25,
    "x": 250,
    "y": 600,
    "value": 8560,
    "ocr_text": "8.56K",
    "source": "horizontal_scan"
  },
  {
    "index": 1,
    "timestamp": 0.50,
    "x": 275,
    "y": 590,
    "value": 8620,
    "ocr_text": "8.62K",
    "source": "horizontal_scan"
  }
]
```

## 💾 Sauvegarde automatique

Les données sont automatiquement sauvegardées dans :
- `graph_extractions/` - Dossier principal
- `consolidated_data_YYYYMMDD_HHMMSS.json` - Fichier de données
- `scan_XXXX_Xs.png` - Captures d'écran individuelles

## 🔧 Configuration avancée

### Personnaliser l'intervalle de capture

```python
extractor = GraphDataExtractor()
extractor.screenshot_interval = 0.1  # Plus rapide (10 captures/sec)
extractor.screenshot_interval = 0.5  # Plus lent (2 captures/sec)
```

### Améliorer la détection OCR

```python
extractor = GraphDataExtractor()
extractor.curve_color = (255, 0, 0)  # Rouge
extractor.tolerance = 50  # Plus tolérant pour la détection
```

### Filtrer les valeurs extraites

```python
# Filtrer les valeurs numériques
valid_points = [p for p in data_points if p.get('value') is not None]

# Convertir les suffixes K, M
def convert_value(text):
    if text.endswith('K'):
        return float(text[:-1]) * 1000
    elif text.endswith('M'):
        return float(text[:-1]) * 1000000
    return float(text)
```

## 🎯 Conseils pratiques

### 1. Préparation de l'écran
- Augmentez la résolution du graphique
- Utilisez un fond contrasté
- Assurez-vous que les valeurs sont lisibles

### 2. Positionnement optimal
- Commencez légèrement avant le début de la courbe
- Terminez légèrement après la fin
- Maintenez une vitesse constante

### 3. Amélioration de la précision
- Utilisez des durées plus longues (15-20 secondes)
- Réduisez l'intervalle de capture (0.1-0.2 secondes)
- Testez différentes couleurs de détection

### 4. Traitement des erreurs
- Vérifiez les captures d'écran en cas d'échec OCR
- Ajustez la tolérance de couleur
- Nettoyez les données aberrantes

## 🚨 Limitations et solutions

### Problèmes courants

1. **OCR imprécis** : Augmentez la résolution, améliorez le contraste
2. **Couleur non détectée** : Ajustez la tolérance, vérifiez la couleur exacte
3. **Captures manquées** : Réduisez l'intervalle, augmentez la durée
4. **Permissions refusées** : Vérifiez les autorisations système

### Solutions alternatives

```python
# Si l'OCR ne fonctionne pas bien
extractor.extract_ocr = False  # Désactiver l'OCR
# Puis traiter manuellement les captures d'écran

# Si la détection automatique échoue
# Utiliser le mode manuel avec clics
extractor.interactive_setup()
```

## 📞 Support et dépannage

### Vérification de l'installation

```bash
python -c "import cv2, pyautogui, pytesseract; print('✅ Toutes les dépendances installées')"
```

### Test rapide

```python
import pyautogui
import pytesseract
from PIL import Image

# Test capture d'écran
screenshot = pyautogui.screenshot()
print(f"✅ Capture d'écran : {screenshot.size}")

# Test OCR
text = pytesseract.image_to_string(screenshot)
print(f"✅ OCR fonctionne : {len(text)} caractères détectés")
```

## 🎉 Exemples d'utilisation réels

### YouTube Analytics - Croissance d'abonnés

```python
# Graphique comme dans l'image fournie
extractor = GraphDataExtractor()

# Configuration pour YouTube Analytics
data_points = extractor.horizontal_scan_with_screenshots(
    start_x=250, start_y=650,   # Début 2022
    end_x=1350, end_y=300,      # Fin 2025
    duration=20.0,              # 20 secondes
    extract_ocr=True
)

# Filtrer et nettoyer les données
subscriber_data = []
for point in data_points:
    if point.get('value'):
        subscriber_data.append({
            'timestamp': point['timestamp'],
            'subscribers': point['value'],
            'growth_rate': point.get('growth_rate', 0)
        })

print(f"📊 {len(subscriber_data)} points d'abonnés extraits")
```

Cet outil vous donne une alternative puissante aux plot digitizers traditionnels, avec des fonctionnalités spécialement adaptées aux graphiques web et aux analytics en temps réel ! 