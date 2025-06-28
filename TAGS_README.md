# 🤖 Système de Tagging Intelligent

## 📖 Vue d'ensemble

Le système de tagging intelligent classifie automatiquement vos compétiteurs par **région** et **industrie**, élimine les **duplicatas**, et vous permet de personnaliser les tags.

## ✨ Fonctionnalités

### 🎯 Classification Automatique
- **50+ marques reconnues** automatiquement (McDonald's → food, Marriott → hospitality)
- **Détection géographique** basée sur les noms (France → Europe, USA → North America)
- **Analyse de mots-clés** intelligente dans les descriptions et titres
- **Industrie par défaut** suggérée si aucune détectée

### 🔄 Élimination des Duplicatas
- **Détection intelligente** : "Club Med" = "ClubMed" = "Club Méditerranée"
- **Conservation automatique** de la version avec le plus de vidéos
- **Logging détaillé** des suppressions

### 🏷️ Interface Interactive
- **Tags cliquables** sur chaque carte de compétiteur
- **Modification en un clic** avec sélecteur d'options
- **Tags personnalisés** (à venir)
- **Design moderne** avec effets visuels

## 🚀 Utilisation

### Nettoyage Immédiat
```bash
# Voir l'état actuel (duplicatas, industries manquantes)
python3 clean_duplicates.py --status

# Nettoyer les duplicatas et forcer les industries
python3 clean_duplicates.py
```

### Migration Complète
```bash
# Migrer toutes les données existantes
python3 migrate_tags.py

# Voir les tags actuels
python3 migrate_tags.py --show
```

### Démarrage du Serveur
```bash
# Démarrage simple sur port libre
python3 start_server.py

# Démarrage avec nettoyage automatique
python3 setup_and_run.py
```

### Test du Classificateur
```bash
# Démonstration des capacités de classification
python3 demo_classifier.py
```

## 🔧 Configuration

### Industries Supportées
- `hospitality` - Hôtels, voyages, tourism
- `food` - Restaurants, cuisine, boissons
- `technology` - Tech, software, innovation
- `fashion` - Mode, style, vêtements
- `beauty` - Beauté, cosmétiques, soins
- `automotive` - Automobiles, véhicules
- `finance` - Banques, finance, assurance
- `health` - Santé, médical, fitness
- `retail` - Commerce, magasins
- `entertainment` - Divertissement, médias
- `education` - Éducation, formation
- `sports` - Sport, fitness

### Régions Supportées
- `Europe` - France, Belgique, Espagne, Italie, etc.
- `North America` - USA, Canada
- `Asia` - Japon, Chine, Corée, Inde
- `Worldwide` - International, global

## 🎨 Interface

### Tags Visuels
- 🌍 **Badge bleu** : Région (cliquable)
- 💼 **Badge vert** : Industrie (cliquable) 
- 🏷️ **Badge gris** : "Industrie" si non définie (cliquable)
- ➕ **Badge pointillé** : Ajouter tag personnalisé

### Interactions
- **Clic sur badge** → Modal de sélection
- **Modification temps réel** → Sauvegarde automatique
- **Alertes visuelles** → Confirmation des changements

## 📊 Exemples de Classification

| Chaîne | Industrie Détectée | Région Détectée | Méthode |
|--------|-------------------|-----------------|---------|
| McDonald's France | `food` | `Europe` | Base connue + géo |
| Club Med | `hospitality` | `Europe` | Base connue |
| Marriott Bonvoy | `hospitality` | `Europe` | Base connue |
| Apple | `technology` | `Europe` | Base connue |
| Gordon Ramsay | `food` | `Europe` | Mots-clés |
| TechCrunch | `technology` | `Europe` | Mots-clés |

## 🛠️ Développement

### Ajouter une Marque
Éditer `yt_channel_analyzer/ai_classifier.py` :
```python
KNOWN_BRANDS = {
    'nouvelle_marque': 'industrie',
    # ...
}
```

### Ajouter des Mots-clés
```python
INDUSTRY_KEYWORDS = {
    'industrie': ['mot1', 'mot2', 'mot3'],
    # ...
}
```

### Normalisation des Duplicatas
```python
replacements = {
    'pattern_source': 'pattern_cible',
    # ...
}
```

## 🐛 Problèmes Courants

### Port Occupé
```bash
# Utiliser le script de démarrage automatique
python3 start_server.py
```

### Industries Manquantes
```bash
# Forcer la classification
python3 clean_duplicates.py
```

### Duplicatas Persistants
```bash
# Vérifier la normalisation
python3 clean_duplicates.py --status
```

## 📈 Statistiques

Après nettoyage, vous obtiendrez :
- **Nombre de duplicatas supprimés**
- **Industries automatiquement détectées**
- **Régions assignées**
- **Compétiteurs avec tags complets**

## 🔮 Fonctionnalités à Venir

- [ ] Tags personnalisés persistants
- [ ] Recherche web automatique pour marques inconnues
- [ ] Apprentissage basé sur les corrections manuelles
- [ ] Export/import de configurations de tags
- [ ] Filtrage avancé par combinaisons de tags

---

*Système développé avec intelligence artificielle et logique métier pour une classification automatique et précise de vos compétiteurs YouTube.* 