# Guide de Déploiement Sécurisé - YouTube Channel Analyzer

## 🔒 Sécurité : Aucun mot de passe en clair

Cette application utilise un système d'authentification entièrement basé sur des **variables d'environnement**. Aucun mot de passe n'apparaît en clair dans le code source.

## 📋 Variables d'environnement requises

### Sur Render.com

1. **Connectez-vous à Render** et créez un nouveau Web Service
2. **Dans Settings > Environment**, ajoutez ces variables :

```bash
# AUTHENTIFICATION (obligatoire)
YTA_USERNAME=votre_nom_utilisateur
YTA_PASSWORD=votre_mot_de_passe_securise
YTA_MASTER_KEY=votre_cle_maitre_unique_generee

# FLASK (obligatoire)
FLASK_SECRET_KEY=VotreCleSecreteFlaskTresLongueEtSecure2025!

# OPTIONNEL
FLASK_DEBUG=False
```

### ⚠️ IMPORTANT - Génération de clés sécurisées

**Ne jamais utiliser les valeurs d'exemple !** Générez vos propres clés :

```python
# Pour générer des clés sécurisées :
import secrets
print("YTA_MASTER_KEY:", secrets.token_urlsafe(32))
print("FLASK_SECRET_KEY:", secrets.token_urlsafe(32))
```

## 🚀 Étapes de déploiement sur Render

### 1. Préparation du repository
```bash
# S'assurer que .env n'est pas committé
echo ".env" >> .gitignore
echo "auth_config.json" >> .gitignore
echo "cache_recherches/" >> .gitignore

git add .
git commit -m "Application sécurisée prête pour production"
git push origin main
```

### 2. Configuration Render
1. **Repository** : Connectez votre repo GitHub
2. **Build Command** : `pip install -r requirements.txt`
3. **Start Command** : `python app.py`
4. **Environment Variables** : Ajoutez toutes les variables listées ci-dessus

### 3. Vérification de sécurité
- ✅ Aucun mot de passe en dur dans le code
- ✅ Variables d'environnement chiffrées
- ✅ Sessions sécurisées avec timeout
- ✅ Authentification sur toutes les routes
- ✅ Configuration auth chiffrée

## 🔐 Comment fonctionne la sécurité

1. **Variables d'environnement** : Les vrais identifiants sont uniquement dans Render
2. **Chiffrement double** : 
   - Mot de passe hashé avec bcrypt
   - Hash chiffré avec Fernet + clé maître
3. **Stockage sécurisé** : auth_config.json contient uniquement des données chiffrées
4. **Sessions** : Timeout automatique après 24h

## 🛡️ Bonnes pratiques appliquées

- **Principe du moindre privilège** : Un seul utilisateur admin
- **Chiffrement en couches** : bcrypt + Fernet
- **Variables d'environnement** : Séparation code/configuration
- **Sessions sécurisées** : Timeout et clé secrète forte
- **Protection CSRF** : Sessions Flask sécurisées

## 🔄 Mise à jour des identifiants

Pour changer les identifiants en production :

1. **Modifier les variables** dans Render Environment
2. **Redémarrer le service** pour prendre en compte les changements
3. **Le fichier auth_config.json** sera automatiquement régénéré avec les nouvelles valeurs chiffrées

## ⚡ Variables locales pour développement

Créez un fichier `.env` local (JAMAIS commité) :

```bash
cp env.example .env
# Éditez .env avec vos valeurs de développement
```

---
**Note de sécurité** : Ce système garantit qu'aucun mot de passe ne transite jamais en clair et que GitHub/Render ne peuvent pas voir vos vrais identifiants. 