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

## 📊 Protocole de Comparaison à Trois Niveaux

### Vue d'ensemble
Le système d'analyse utilise un protocole de comparaison structuré à **trois niveaux hiérarchiques** pour permettre des insights précis et contextualisés.

### 🌍 Niveau 1 : Européen/International
**Scope** : Vue globale et benchmarking international
- **Pays inclus** : France, Germany, Netherlands, United Kingdom, International
- **Objectif** : Identifier les tendances macro et les best practices globales
- **Cas d'usage** : Stratégie globale, expansion internationale, benchmarks de référence

### 🏠 Niveau 2 : Local (Par Pays)
**Scope** : Analyse spécifique par marché national
- **Segmentation** : Par pays défini dans `concurrent.country`
- **Objectif** : Comprendre les spécificités culturelles et locales
- **Cas d'usage** : Adaptation locale, stratégie pays, concurrence directe

### 🏢 Niveau 3 : Marque (Exemple : Center Parcs)
**Scope** : Analyse intra-marque et déclinaisons
- **Segmentation** : Par nom de marque ou groupe
- **Objectif** : Cohérence de marque et variations par filiale
- **Cas d'usage** : Gouvernance de marque, alignement stratégique

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

# Entraîner les modèles sémantiques
python -c "from yt_channel_analyzer.semantic_classifier import AdvancedSemanticClassifier; clf = AdvancedSemanticClassifier(); clf.train_from_database()"
```