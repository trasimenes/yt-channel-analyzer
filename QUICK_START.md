# ⚡ YT Channel Analyzer - Guide de Démarrage Rapide

## 🎯 TL;DR : Savoir Immédiatement Sur Quoi Tu Travailles

```bash
# 🔍 VÉRIFICATION INSTANTANÉE
./check_environment.sh

# 🔧 ALIAS PRATIQUES (optionnel)
source alias_setup.sh
ytenv  # = check_environment.sh
```

## 🏗️ Deux Environnements, Deux Usages

### 🔬 **Branche `main` - DÉVELOPPEMENT**
- **Taille** : ~5.5GB (avec modèles ML)
- **Utilisation** : Classification, entraînement, développement
- **Lancer** : `python run_development.py`

### 🚀 **Branche `production` - SERVEUR**
- **Taille** : ~50MB (sans modèles ML)
- **Utilisation** : Interface utilisateur, affichage données
- **Lancer** : `python app.py`

## 🔄 Commandes Essentielles

```bash
# VÉRIFIER L'ENVIRONNEMENT
./check_environment.sh

# BASCULER ENTRE LES BRANCHES
git checkout main        # → Développement (avec ML)
git checkout production  # → Production (sans ML)

# SYNCHRONISER MAIN → PRODUCTION
git checkout production
./sync_to_production.sh

# DÉMARRER L'APPLICATION
python app.py                    # Standard
python run_development.py       # Avec ML (si disponible)
```

## 📊 Ce Que Te Dit `check_environment.sh`

```
🔍 ENVIRONNEMENT DE TRAVAIL ACTUEL
==================================
📍 Branche Git: main
🧠 Modèles ML: ✅ PRÉSENTS (~5.5GB)
🔬 Mode: DÉVELOPPEMENT (Classification + Entraînement)
💡 Lancer: python run_development.py
```

**En un coup d'œil** :
- ✅ **Branche** : main/production
- ✅ **Modèles ML** : présents/absents
- ✅ **Mode** : développement/production
- ✅ **Commande** : comment lancer l'app

## 🎯 Workflow Typique

### 1. **Développement** (branche main)
```bash
git checkout main
./check_environment.sh    # Vérifier ML présents
python run_development.py # Développer avec ML
```

### 2. **Test Production** (branche production)
```bash
git checkout production
./check_environment.sh    # Vérifier ML absents
python app.py             # Tester en mode léger
```

### 3. **Déploiement Serveur**
```bash
# Sur le serveur O2switch
git pull origin production
touch tmp/restart.txt
```

## 🔧 Alias Disponibles (optionnel)

```bash
source alias_setup.sh

ytenv          # Vérifier l'environnement
ytdev          # Basculer sur main (développement)
ytprod         # Basculer sur production
ytstart        # Démarrer l'app
ytsync         # Synchroniser main → production
```

## 📁 Documentation Complète

- `README_DEVELOPMENT.md` : Guide développement (branche main)
- `README_PRODUCTION.md` : Guide production (branche production)
- `CLAUDE.md` : Instructions architecture complète

## 🚨 En Cas de Doute

```bash
# Toujours commencer par :
./check_environment.sh

# Puis suivre les recommandations affichées
```

---

🎯 **Maintenant tu sais toujours instantanément sur quoi tu travailles !**