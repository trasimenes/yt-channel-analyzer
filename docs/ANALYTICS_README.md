# 📊 Système d'Analytics - Suivi des Subscribers

Ce système vous permet de tracker l'évolution des subscribers de vos concurrents, d'analyser les corrélations avec les types de publications, et d'exporter toutes les données vers Excel.

## 🚀 Fonctionnalités

### 1. **Tracking Automatique**
- ✅ Enregistrement automatique des variations de subscribers lors des refresh
- ✅ Historique complet des métriques (subscribers, vues, vidéos)
- ✅ Calcul automatique des variations et taux de croissance

### 2. **Analyse de Corrélation**
- ✅ Corrélation entre types de contenu (HERO/HUB/HELP) et croissance
- ✅ Analyse de performance par catégorie
- ✅ Recommandations stratégiques automatiques

### 3. **Export Excel Complet**
- ✅ Résumé des concurrents avec métriques clés
- ✅ Évolution détaillée des subscribers
- ✅ Analyse de contenu par catégorie
- ✅ Graphiques et visualisations
- ✅ Recommandations pour chaque concurrent

## 🛠️ Installation

### 1. Mettre à jour les dépendances
```bash
pip install -r requirements.txt
```

### 2. Mettre à jour la base de données
```bash
python update_database_for_analytics.py
```

### 3. (Optionnel) Tester avec la démonstration
```bash
python demo_analytics.py
```

## 📈 Utilisation

### Interface Web

1. **Dashboard Analytics**
   - Visitez `/analytics` pour voir le tableau de bord
   - Vue d'ensemble de tous les concurrents
   - Métriques de croissance en temps réel

2. **Export Excel**
   - Cliquez sur "Export Excel" dans le dashboard
   - Fichier complet avec toutes les analyses
   - Prêt pour présentation ou analyse approfondie

3. **Analytics par Concurrent**
   - Visitez `/competitor/{id}/analytics` pour des détails
   - Historique détaillé de la croissance
   - Analyse de corrélation contenu/performance

### API

#### Exporter vers Excel
```bash
POST /api/export-excel
```

#### Récupérer l'analyse de croissance
```bash
GET /api/competitor-growth/{competitor_id}?days=30
```

#### Enregistrer manuellement des stats
```bash
POST /api/record-stats
{
  "competitor_id": 1,
  "stats": {
    "subscriber_count": 15000,
    "view_count": 500000,
    "video_count": 25
  },
  "notes": "Mise à jour manuelle"
}
```

#### Analyse de corrélation contenu
```bash
GET /api/content-correlation/{competitor_id}?days=30
```

## 📊 Structure des Données Excel

Le fichier Excel exporté contient 4 feuilles :

### 1. **Résumé Concurrents**
- Nom et URL de chaque concurrent
- Subscribers, vues totales, nombre de vidéos
- Croissance sur 30 jours et taux de croissance
- Statut (🔺 Croissance, 🔻 Déclin, ➡️ Stable)

### 2. **Évolution Subscribers**
- Historique détaillé par concurrent et par date
- Variations quotidiennes
- Taux de changement en pourcentage
- Notes et contexte

### 3. **Analyse Contenu**
- Performance par catégorie (HERO/HUB/HELP)
- Nombre de vidéos et vues moyennes par catégorie
- Impact estimé sur la croissance des subscribers
- Score de performance

### 4. **Recommandations**
- Recommandations stratégiques par concurrent
- Métriques clés sur 30 jours
- Conseils basés sur l'analyse de contenu

## 🔄 Tracking Automatique

Le système enregistre automatiquement les variations lors de :

1. **Refresh de concurrents** (`/api/refresh-competitor`)
   - Nouvelles données de subscribers/vues/vidéos
   - Calcul automatique des variations
   - Enregistrement dans l'historique

2. **Mise à jour via API YouTube**
   - Lors des appels aux APIs YouTube
   - Données fraîches des chaînes
   - Tracking en temps réel

## 📋 Exemples d'Utilisation

### Analyser la croissance d'un concurrent
```python
from yt_channel_analyzer.analytics_export import SubscriberTracker

tracker = SubscriberTracker()
analysis = tracker.get_growth_analysis(competitor_id=1, days=30)

print(f"Croissance: {analysis['total_subscriber_growth']:+,} subscribers")
print(f"Taux: {analysis['growth_rate_percent']:.1f}%")
```

### Corrélation contenu/croissance
```python
from yt_channel_analyzer.analytics_export import CompetitorAnalyzer

analyzer = CompetitorAnalyzer()
correlation = analyzer.analyze_content_correlation(competitor_id=1, days=30)

for category, data in correlation['category_analysis'].items():
    print(f"{category}: {data['count']} vidéos, impact: {data['subscriber_impact']:.1f}")
```

### Export Excel programmé
```python
from yt_channel_analyzer.analytics_export import export_analytics_to_excel

# Export complet
excel_path = export_analytics_to_excel()
print(f"Export créé: {excel_path}")
```

## 🎯 Cas d'Usage

### 1. **Analyse Concurrentielle**
- Identifier les concurrents qui croissent le plus vite
- Comprendre quels types de contenu fonctionnent
- Adapter sa stratégie en conséquence

### 2. **Reporting Client**
- Export Excel prêt pour présentation
- Données consolidées et visualisations
- Recommandations stratégiques incluses

### 3. **Veille Stratégique**
- Suivi automatique des tendances
- Alertes sur les croissances anormales
- Analyse des corrélations contenu/performance

### 4. **Optimisation Éditoriale**
- Identifier les catégories les plus performantes
- Comprendre l'impact des types de publications
- Optimiser le calendrier éditorial

## 📂 Structure des Fichiers

```
yt-channel-analyzer/
├── yt_channel_analyzer/
│   ├── analytics_export.py          # Module principal d'analytics
│   └── database.py                  # Base de données (modifiée)
├── templates/
│   └── analytics_dashboard.html     # Interface web
├── exports/                         # Fichiers Excel générés
├── update_database_for_analytics.py # Script de mise à jour DB
├── demo_analytics.py               # Script de démonstration
└── ANALYTICS_README.md             # Ce fichier
```

## 🔧 Configuration

### Variables d'Environnement
Aucune configuration supplémentaire requise. Le système utilise la base de données SQLite existante.

### Personnalisation
- Modifiez les seuils de catégorisation dans `analytics_export.py`
- Adaptez les styles Excel dans la classe `ExcelExporter`
- Ajustez les périodes d'analyse par défaut

## 🐛 Dépannage

### Erreur "Table competitor_stats_history n'existe pas"
```bash
python update_database_for_analytics.py
```

### Problème d'import Excel
Vérifiez que vous avez installé toutes les dépendances :
```bash
pip install pandas openpyxl scipy numpy
```

### Données manquantes
Le système nécessite au moins 2 points de données pour calculer les tendances. Attendez quelques refresh ou utilisez le script de démo.

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs dans la console
2. Testez avec `python demo_analytics.py`
3. Consultez la base de données avec un outil SQLite

## 🎉 Prochaines Étapes

Une fois le système configuré :
1. Ajoutez vos concurrents via l'interface web
2. Effectuez quelques refresh pour collecter des données
3. Visitez `/analytics` pour voir les premiers résultats
4. Exportez vers Excel pour une analyse approfondie
5. Configurez des refresh automatiques pour un suivi continu 