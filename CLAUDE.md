# YT Channel Analyzer - Structure du Projet

## Vue d'ensemble
Application Flask d'analyse de chaînes YouTube avec système de classification sémantique et d'analyse concurrentielle.

## 🧠 Hiérarchie de Classification - RÈGLE ABSOLUE

### ⚠️ PRIORITÉ ABSOLUE : HUMAIN > SENTENCE TRANSFORMER > PATTERNS

Cette hiérarchie est **FONDAMENTALE** et doit être respectée dans **TOUS** les systèmes de classification :

1. **🥇 HUMAIN** (Priorité absolue)
   - `is_human_validated = 1` ET `classification_source = 'human'`
   - **INTOUCHABLE** : Jamais écrasé par l'IA ou les patterns
   - Source de vérité absolue pour l'entraînement des modèles
   - "Ce que je fais à la main est supérieur aux sentence transformers, supérieur aux patterns à la noix"

2. **🥈 SENTENCE TRANSFORMER** (Priorité secondaire)
   - `classification_source = 'semantic'` ou `'ai'`
   - Utilise les embeddings sémantiques pour comprendre le sens
   - Peut être écrasé par une validation humaine
   - Plus intelligent que les patterns de mots-clés

3. **🥉 PATTERNS** (Priorité tertiaire)
   - `classification_source = 'keyword'` ou `'auto'`
   - Règles basées sur des mots-clés multilingues
   - Fallback quand les autres méthodes échouent
   - "Patterns à la noix" mais utiles pour du volume

### 🔒 Protection des Classifications Humaines

#### Dans le code :
```python
# ✅ CORRECT : Vérifier la protection humaine
if is_human_validated != 1 and classification_source != 'human':
    # Seulement alors on peut reclassifier
    
# ❌ INCORRECT : Écraser sans vérifier
UPDATE video SET category = ? WHERE id = ?
```

#### Dans les requêtes SQL :
```sql
-- ✅ CORRECT : Exclure les validations humaines
WHERE (is_human_validated = 0 OR is_human_validated IS NULL)
AND (classification_source != 'human' OR classification_source IS NULL)

-- ❌ INCORRECT : Ignorer la protection
WHERE category IS NULL OR category = 'uncategorized'
```

### 🎯 Implémentation dans le Système

#### Modules concernés :
- `yt_channel_analyzer/database/classification.py` : Logique de classification
- `yt_channel_analyzer/supervised_learning.py` : Entraînement des modèles
- `yt_channel_analyzer/semantic_classifier.py` : Classification sémantique
- `app.py` : Routes de classification manuelle

#### Colonnes de tracking :
- `is_human_validated` : Flag de protection absolue
- `classification_source` : Source de la classification
- `human_verified` : Alias pour compatibilité

## Structure de la base de données

### Tables principales
- **concurrent**: Concurrents/chaînes YouTube (355 playlists disponibles)
- **playlist**: Playlists des concurrents (355 entrées)
- **video**: Vidéos des concurrents
- **playlist_video**: Liaison many-to-many entre playlists et vidéos

### Tables de classification
- **classification_feedback**: Feedback utilisateur sur les classifications
- **classification_patterns**: Patterns de classification
- **custom_classification_rules**: Règles personnalisées
- **learned_patterns**: Patterns appris par l'IA

### Tables de statistiques
- **competitor_stats**: Statistiques des concurrents
- **competitor_frequency_stats**: Statistiques de fréquence
- **competitor_detailed_stats**: Statistiques détaillées
- **model_performance**: Performance des modèles

## Gestion des miniatures des concurrents

Les miniatures des chaînes YouTube sont stockées dans `/static/competitors/images/` avec comme nom de fichier `{concurrent_id}.jpg`.

Par exemple : 
- Center Parcs Ferienparks (ID 122) → `/static/competitors/images/122.jpg`

## Structure des playlists

### Colonnes disponibles
- `id`: ID unique
- `concurrent_id`: Référence au concurrent
- `playlist_id`: ID YouTube de la playlist
- `name`: Nom de la playlist
- `description`: Description
- `thumbnail_url`: URL de la miniature
- `category`: Catégorie (hero/hub/help)
- `video_count`: Nombre de vidéos
- `created_at`: Date de création
- `last_updated`: Dernière mise à jour
- `classification_source`: Source de classification (ai/human)
- `classification_date`: Date de classification
- `classification_confidence`: Confiance de la classification
- `human_verified`: Vérifié par un humain
- `is_human_validated`: Validé par un humain

### Métriques à calculer pour le top playlists
- **Nombre total de vues**: Somme des vues de toutes les vidéos de la playlist
- **Nombre total de likes**: Somme des likes de toutes les vidéos
- **Nombre total de commentaires**: Somme des commentaires
- **Ratio d'engagement**: (Likes + Commentaires) / Vues totales
- **Durée moyenne des vidéos**: Moyenne des durées des vidéos
- **Score de beauté moyen**: Moyenne des beauty_score des vidéos
- **Score d'émotion moyen**: Moyenne des emotion_score des vidéos
- **Score de qualité info moyen**: Moyenne des info_quality_score des vidéos
- **Score subjectif moyen**: Moyenne des scores subjectifs
- **Date de dernière vidéo**: Date de publication de la vidéo la plus récente

## Modèle de la page top-videos

### Fonctionnalités existantes
- Tri par différentes métriques (vues, likes, commentaires, etc.)
- Filtres par catégorie (hero/hub/help)
- Filtres par type (organic/paid)
- Pagination/limite d'affichage
- Cache avec timeout de 300s
- Interface glassmorphism

### Métriques affichées
- Miniature, titre, concurrent
- Catégorie, statut organique
- Vues, likes, commentaires
- Ratio d'engagement, durée
- Date de publication, heure
- Scores de beauté, émotion, qualité info
- Score subjectif moyen

## Architecture technique

### Backend
- Flask avec SQLite
- Modules dans `yt_channel_analyzer/database/`
- Gestion des connexions via `base.py`
- Managers spécialisés (VideoManager, etc.)

### Frontend
- Templates Jinja2 dans `templates/`
- Système de thèmes CSS
- Interface glassmorphism
- JavaScript pour interactions

### Environnement
- Python 3.12 avec `venv_semantic`
- Dependencies dans `requirements-semantic.txt`
- Modèles Transformers pour classification

## Prochaines étapes pour /top-playlists

1. Créer une table ou vue pour les statistiques des playlists
2. Calculer les métriques agrégées depuis les vidéos liées
3. Implémenter la route `/top-playlists` similaire à `/top-videos`
4. Créer le template HTML basé sur `top_videos.html`
5. Ajouter la navigation vers cette nouvelle page

## 🤖 Classification Sémantique Avancée

### Modèles de Sentence-Transformers
- **Modèle principal** : `all-mpnet-base-v2` (768 dimensions)
- **Performance** : +40% de précision vs modèle par défaut
- **Optimisation** : ONNX Runtime + quantization INT8
- **Gain de performance** : 75% réduction taille, +300% vitesse

### Classes de Classification
1. **OptimizedSemanticClassifier** (`yt_channel_analyzer/semantic_classifier.py`)
   - Utilise ONNX Runtime pour l'accélération
   - Quantization INT8 pour optimiser la mémoire
   - Cache Redis pour les embeddings fréquents
   
2. **AdvancedSemanticClassifier**
   - Modèle all-mpnet-base-v2 pour meilleure précision
   - Entraînement avec 64 exemples manuels (49 playlists + 15 vidéos)
   - Support multi-threading pour 24 threads + 64GB RAM

### Données d'Entraînement
- **64 exemples validés manuellement** extraits de la base
- **Catégories** : HERO/HUB/HELP
- **Protection absolue** : `is_human_validated = 1` jamais écrasé
- **Sources** : human > semantic > keyword patterns

### Dependencies Optimisation
```txt
# Ajoutées dans requirements-semantic.txt
optimum[onnxruntime]>=1.14.0
onnxruntime>=1.16.0
onnx>=1.14.0
accelerate>=0.22.0
datasets>=2.12.0
redis>=4.5.0
bitsandbytes>=0.41.0
```

## 🎨 Intégration Thème Sneat Bootstrap

### Compilation SCSS avec Dart Sass
- **Dart Sass 1.70.0** installé pour compilation native
- **Script automatisé** : `python build_theme.py`
- **Fichiers sources** : `/static/sneat/scss/`
- **Fichiers compilés** : `/static/sneat/assets/vendor/css/`

### Fichiers CSS Générés
1. **core.css** (2,535 bytes) - Layout et composants de base
2. **theme-default.css** (3,674 bytes) - Thème et navbar complets

### Corrections Layout
- **Navbar height** : Fixé à 4rem au lieu de 400px
- **Menu actif** : Underline sur Dashboard et items actifs
- **Layout wrapper** : Structure layout-menu-fixed corrigée
- **JavaScript** : getCssVar function ajoutée pour config.js

### Structure SCSS
```scss
// Variables Sneat dans core-simple.scss
:root {
  --bs-primary: #696cff;
  --bs-secondary: #8592a3;
  // ... autres variables de couleur
}

// Layout navbar dans theme-default-simple.scss
.layout-navbar {
  position: relative;
  z-index: 2;
  flex-wrap: nowrap;
  block-size: 4rem;  // Hauteur fixe 64px
  padding-block: 0.5rem;
}
```

### Pages Migrées vers Sneat
- ✅ `/concurrents` - Template Sneat + fonction refresh data
- ✅ `base.html` - Navbar Sneat complète avec search et user dropdown
- 🔄 En cours : `/insights`, `/fix-problems`, `/learn`, `/api-usage`, `/top-videos`

## 📊 Protocole de Comparaison à Trois Niveaux - Architecture en Empilement

### ⚠️ RÈGLE FONDAMENTALE : INTÉGRITÉ DES DONNÉES PAR NIVEAU

**Architecture hiérarchique :** `CHANNEL < COUNTRY < EUROPE`

```
🌍 EUROPE/INTERNATIONAL (Niveau 3)
    ↑ Consolidation depuis
🏠 COUNTRY (Niveau 2) 
    ↑ Consolidation depuis
📺 CHANNEL (Niveau 1)
```

### 🔒 SÉCURISATION ABSOLUE DES STATS CHANNEL

**PRIORITÉ CRITIQUE** : Les statistiques de chaque chaîne individuelle doivent être **blindées** car elles sont la fondation de tout le système.

#### Pourquoi c'est critique :
- **Effect domino** : Une erreur au niveau CHANNEL se propage à COUNTRY puis EUROPE
- **Fausses consolidations** : Si les stats d'une chaîne sont erronées, toutes les analyses pays/européennes sont fausses
- **Perte de confiance** : Un seul mauvais chiffre invalide tout le système d'analyse

#### Contrôles obligatoires au niveau CHANNEL :
```sql
-- Vérifications d'intégrité par chaîne
SELECT 
    c.name,
    COUNT(v.id) as video_count,
    SUM(v.view_count) as total_views,
    AVG(v.view_count) as avg_views,
    -- Détection d'anomalies
    CASE WHEN AVG(v.view_count) > 1000000 THEN 'SUSPECT_HIGH' 
         WHEN AVG(v.view_count) < 100 THEN 'SUSPECT_LOW' 
         ELSE 'OK' END as integrity_check
FROM concurrent c 
LEFT JOIN video v ON c.id = v.concurrent_id 
GROUP BY c.id, c.name
ORDER BY integrity_check DESC, total_views DESC;
```

### 🏗️ Niveaux Hiérarchiques

#### 📺 Niveau 1 : CHANNEL (Base de données)
**Scope** : Statistiques par chaîne individuelle
- **Source** : Données directes YouTube API
- **Responsabilité** : Exactitude des métriques individuelles
- **Contrôles** : Validation des vues, likes, durées, dates
- **Stockage** : Tables `concurrent`, `video`, `playlist`

#### 🏠 Niveau 2 : COUNTRY (Consolidation)
**Scope** : Agrégation par pays
- **Source** : Consolidation depuis les CHANNELS du pays
- **Calculs** :
  ```sql
  -- Exemple : Stats France
  SELECT 
      'France' as country,
      COUNT(DISTINCT c.id) as channel_count,
      COUNT(v.id) as total_videos,
      SUM(v.view_count) as country_views,
      AVG(v.view_count) as avg_views_per_video
  FROM concurrent c 
  JOIN video v ON c.id = v.concurrent_id 
  WHERE c.country = 'France'
  ```
- **Dépendances** : Intégrité des données CHANNEL

#### 🌍 Niveau 3 : EUROPE (Super-consolidation)
**Scope** : Vue globale européenne/internationale
- **Source** : Consolidation depuis les COUNTRIES
- **Calculs** :
  ```sql
  -- Stats européennes
  SELECT 
      'Europe' as region,
      COUNT(DISTINCT c.country) as country_count,
      COUNT(DISTINCT c.id) as total_channels,
      COUNT(v.id) as total_videos,
      SUM(v.view_count) as europe_views
  FROM concurrent c 
  JOIN video v ON c.id = v.concurrent_id 
  WHERE c.country IN ('France', 'Germany', 'Netherlands', 'United Kingdom')
  ```
- **Dépendances** : Intégrité des agrégations COUNTRY

### 🛡️ Protocoles de Sécurisation

#### 1. Validation des données CHANNEL
- **Seuils de cohérence** : Vues min/max par vidéo selon l'âge de la chaîne
- **Détection d'anomalies** : Pics suspects, valeurs nulles, dates incohérentes
- **Audit trail** : Traçabilité des modifications de stats

#### 2. Contrôles de consolidation COUNTRY
- **Somme de contrôle** : Vérification que SUM(channels) = country_total
- **Cohérence temporelle** : Dates de publication alignées avec les pays
- **Distribution normale** : Détection des outliers par pays

#### 3. Validation de super-consolidation EUROPE
- **Réconciliation** : SUM(countries) = europe_total
- **Benchmarks externes** : Comparaison avec sources publiques
- **Alertes automatiques** : Notification si écarts > 5%

### 🚨 Système d'Alertes d'Intégrité

```python
def validate_data_integrity():
    alerts = []
    
    # Niveau CHANNEL
    suspicious_channels = check_channel_anomalies()
    if suspicious_channels:
        alerts.append(f"⚠️ CHANNEL: {len(suspicious_channels)} chaînes suspectes")
    
    # Niveau COUNTRY  
    country_discrepancies = validate_country_consolidation()
    if country_discrepancies:
        alerts.append(f"⚠️ COUNTRY: Écarts de consolidation détectés")
        
    # Niveau EUROPE
    europe_integrity = validate_europe_consolidation()
    if not europe_integrity:
        alerts.append(f"🚨 EUROPE: Consolidation incohérente")
    
    return alerts
```

### 📋 TODO : Implémentation Sécurisée

1. **Audit des données actuelles** : Identifier les incohérences existantes
2. **Mise en place des contrôles** : Scripts de validation automatique  
3. **Dashboard d'intégrité** : Monitoring temps réel des 3 niveaux
4. **Processus de correction** : Workflow pour corriger les anomalies détectées
5. **Documentation des seuils** : Définir les limites acceptables par métrique

### 📈 Métriques Objectives par Dimension

#### 1. **Video Length** (Durée des Vidéos)
- **Données** : `video.duration_seconds`, `video.duration_text`
- **Métriques** :
  - Durée moyenne par niveau
  - Distribution par quartiles
  - Corrélation durée/performance
  - Tendances temporelles

#### 2. **Video Frequency** (Fréquence de Publication)
- **Données** : `video.published_at`, table `competitor_frequency_stats`
- **Métriques** :
  - Vidéos par semaine/mois
  - Régularité de publication
  - Saisonnalité
  - Fréquence par catégorie (Hero/Hub/Help)

#### 3. **Most Liked Topics** (Sujets les Plus Appréciés)
- **Données** : `video.title`, `video.like_count`, analyse sémantique
- **Métriques** :
  - Topics avec le meilleur engagement
  - Analyse lexicale des titres performants
  - Corrélation sujet/likes
  - Évolution des préférences

#### 4. **Hub-Hero-Help Distribution**
- **Données** : `video.category`, `playlist.category`
- **Métriques** :
  - % de répartition par catégorie
  - Performance par catégorie
  - Équilibre stratégique
  - Comparaison avec la théorie Google

#### 5. **Organic vs Paid Distribution**
- **Données** : `video.view_count` vs `paid_threshold` (settings)
- **Métriques** :
  - % de contenu organique vs payé
  - Performance comparative
  - Seuils de détection
  - ROI estimé par type

#### 6. **Thumbnail Consistency** (Cohérence des Miniatures)
- **Données** : `video.thumbnail_url`, `video.beauty_score`
- **Métriques** :
  - Scores de beauté moyens
  - Cohérence visuelle (à développer)
  - Patterns de couleurs
  - Efficacité par style

#### 7. **Tone of Voice** (Tonalité et Champs Sémantiques)
- **Données** : `video.title`, `video.description`, analyse NLP
- **Métriques** :
  - **Lexical Field** : Vocabulaire utilisé, richesse lexicale
  - **Semantic Field** : Champs sémantiques dominants
  - Sentiment analysis
  - Cohérence de marque

### 🔧 Implémentation Technique

#### Tables Concernées
```sql
-- Niveau géographique
concurrent.country

-- Niveau marque  
concurrent.name (pattern matching)

-- Métriques vidéo
video.duration_seconds, video.published_at, video.category
video.view_count, video.like_count, video.thumbnail_url

-- Statistiques précalculées
competitor_stats, competitor_frequency_stats
```

#### Fonctions d'Analyse
- `calculate_video_length_metrics(level, scope)`
- `analyze_publication_frequency(level, scope)`
- `extract_top_topics(level, scope)`
- `calculate_hhh_distribution(level, scope)`
- `detect_organic_vs_paid(level, scope)`
- `analyze_thumbnail_consistency(level, scope)`
- `analyze_tone_of_voice(level, scope)`

### 📊 Dashboard de Comparaison

#### Interface Utilisateur
- **Sélecteur de Niveau** : Européen/Local/Marque
- **Sélecteur de Scope** : Pays/Marque selon le niveau
- **Métriques Comparatives** : Tableaux et graphiques
- **Export des Données** : JSON/CSV pour analyse approfondie

#### Pages Dédiées
- `/comparison/european` - Vue européenne/internationale
- `/comparison/local/<country>` - Vue par pays
- `/comparison/brand/<brand_name>` - Vue par marque

## 📋 TODO FUTURES - Architecture Modulaire

### 🎯 TODO 21.07.2025 : Stratégie modulaire pour "Competitors" et cohabitation YAML + SQLite

**Objectif :** Isoler l'affichage statique du processing lourd pour une architecture plus maintenable.

#### Structure de projet cible

```
yt-channel-analyzer/
│
├── data/
│   ├── competitors.yaml     # source statique pour l'UI
│   └── competitors.db       # base SQLite pour le processing
│
├── competitors/             # module « Vue » uniquement YAML‑driven
│   ├── __init__.py
│   ├── loader.py           # charge data/competitors.yaml
│   ├── service.py          # logique métier légère (filtrage, tri, enrichissement)
│   └── renderer.py         # génère le HTML/list CLI
│
└── processing/             # module « Batch » uniquement DB‑driven
    ├── __init__.py
    ├── db.py              # wrapper sqlite3.connect(competitors.db)
    └── tasks.py           # fonctions lourdes de calcul, agrégations, rapports
```

#### Bénéfices attendus

1. **Isolation complète :**
   - L'UI "Competitors" ne touche jamais à SQLite — elle ne lit que le YAML
   - Les batchs « processing » ne génèrent pas de HTML — ils ne touchent que la DB

2. **Responsabilité unique :**
   - `loader.py` = lecture de fichier YAML
   - `service.py` = règles métier (filtrage, tri, enrichment)
   - `renderer.py` = présentation
   - `db.py` = connexion SQLite
   - `tasks.py` = calculs & agrégations

3. **Évolutivité :**
   - Changement d'API : modifier seulement `loader.py`
   - Changement de DB : modifier seulement `db.py`

4. **Testabilité :**
   - Mock `load_competitors()` pour tester la présentation
   - Mock connexion SQLite pour tester les calculs

#### Implémentation proposée

```python
# competitors/loader.py
import yaml
from pathlib import Path
from functools import lru_cache

@lru_cache(1)
def load_competitors() -> list[dict]:
    path = Path(__file__).parent.parent / "data" / "competitors.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f).get("competitors", [])

# competitors/service.py
from .loader import load_competitors

def get_active_competitors() -> list[dict]:
    all_ = load_competitors()
    active = [c for c in all_ if c.get("active", True)]
    return sorted(active, key=lambda c: c["name"])

def enrich_with_rank(comps: list[dict]) -> list[dict]:
    for i, c in enumerate(comps, 1):
        c["rank"] = i
    return comps

# processing/db.py
import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "competitors.db"

def get_connection():
    return sqlite3.connect(DB)
```

**Flux :** loader → service (logique métier) → renderer (UI)  
**Séparation :** Vue YAML ↔ Processing SQLite

## Commandes utiles

```bash
# Activer l'environnement
source venv_semantic/bin/activate

# Démarrer l'application
python app.py

# Compiler les thèmes SCSS
python build_theme.py

# Examiner la base de données
sqlite3 instance/database.db

# Entraîner les modèles sémantiques avec toutes les données humaines
python train_semantic_model.py

# Ou directement en Python :
python -c "from yt_channel_analyzer.semantic_training import SemanticTrainingManager; trainer = SemanticTrainingManager(); trainer.extract_human_classifications(); trainer.train_semantic_model()"
```