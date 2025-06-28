# 📊 Guide d'Usage API YouTube - YT Channel Analyzer

## 🚀 Vue d'ensemble

Ce système track automatiquement votre consommation de l'API YouTube en temps réel et l'affiche sur votre interface web.

## 📋 Comment ça marche

### 1. **Tracking Automatique**
- Chaque appel API est automatiquement comptabilisé
- Les coûts en quota sont calculés selon la documentation YouTube API
- Les données sont sauvegardées dans `api_quota_tracking.json`
- Reset automatique chaque nouveau jour

### 2. **Coûts par Opération**
```
🔍 search: 100 unités          (recherche de chaînes)
📺 channels: 1 unité           (infos chaîne)
🎥 videos: 1 unité             (détails vidéos)
📋 playlistItems: 1 unité      (vidéos d'une playlist)
```

### 3. **Limites de Quota**
- **Quota quotidien**: 10,000 unités par défaut
- **Statut Sain**: < 8,000 unités (🟢)
- **Statut Attention**: 8,000-9,500 unités (🟡)
- **Statut Critique**: > 9,500 unités (🔴)

## 🔧 Configuration

### 1. **Clé API YouTube**
```bash
# Dans votre fichier .env
YOUTUBE_API_KEY=AIzaSyC_YOUR_ACTUAL_API_KEY_HERE
```

### 2. **Obtenir une Clé API**
1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un nouveau projet
3. Activer "YouTube Data API v3"
4. Créer des identifiants → Clé API
5. Copier la clé dans votre `.env`

## 📊 Interface Web

### Dashboard API Usage
- **Today's Requests**: Quota utilisé aujourd'hui
- **Daily Quota**: Limite quotidienne (10,000)
- **Remaining**: Quota restant
- **Usage Percent**: Pourcentage d'utilisation
- **API Calls**: Nombre total d'appels
- **API Status**: Statut santé (🟢🟡🔴)

### Boutons d'Action
- **🔄 Refresh**: Recharge les données
- **↻ Reset**: Reset manuel du compteur

## 📁 Fichiers Générés

### `api_quota_tracking.json`
```json
{
  "date": "2025-06-28",
  "quota_used": 347,
  "requests_made": 15,
  "last_updated": "2025-06-28T17:22:51.123456"
}
```

## 🔍 Monitoring en Temps Réel

### Logs Console
```bash
[QUOTA] 📊 Endpoint: channels | Coût: 1 | Total utilisé: 347/10000
[QUOTA] 📊 Endpoint: videos | Coût: 1 | Total utilisé: 348/10000
[QUOTA] 📊 Endpoint: search | Coût: 100 | Total utilisé: 448/10000
```

### Interface Web
- Barre de progression avec couleurs dynamiques
- Mise à jour automatique lors des appels API
- Alertes visuelles quand le quota approche la limite

## 🚨 Gestion des Alertes

### Seuils d'Alerte Automatiques
- **60%**: Barre orange
- **80%**: Barre rouge + alerte
- **95%**: Statut critique

### Actions Recommandées
- **< 80%**: Usage normal ✅
- **80-95%**: Réduire les analyses ou attendre demain ⚠️
- **> 95%**: Arrêter les analyses jusqu'à demain 🛑

## 🔧 Dépannage

### Quota Non Trackée
1. Vérifier que `YOUTUBE_API_KEY` est définie
2. Vérifier les permissions du fichier de tracking
3. Regarder les logs pour les erreurs API

### Reset Manuel
```bash
# Via l'interface web
Cliquer sur "Reset" → Confirmer

# Ou supprimer le fichier
rm api_quota_tracking.json
```

### Problèmes Courants
1. **"Quota exceeded"**: Attendre le reset automatique à minuit UTC
2. **Clé API invalide**: Vérifier la clé dans `.env`
3. **API désactivée**: Activer YouTube Data API v3 sur Google Cloud

## 📈 Optimisation

### Réduire la Consommation
1. **Mettre en cache** les résultats fréquents
2. **Limiter** le nombre de vidéos analysées
3. **Éviter** les recherches répétitives
4. **Utiliser** la pagination intelligente

### Exemples de Coûts
```
Analyse complète chaîne 100 vidéos:
- 1 x channels (1 unité)
- 2 x playlistItems (2 unités)  
- 2 x videos (2 unités)
Total: ~5 unités

Recherche + analyse:
- 1 x search (100 unités)
- Analyse chaîne (5 unités)
Total: ~105 unités
```

## 🎯 Bonnes Pratiques

### Pour les Analyses Fréquentes
1. **Analyser tôt le matin** pour maximum de quota
2. **Grouper** les analyses similaires
3. **Éviter** les analyses pendant les pics d'utilisation
4. **Surveiller** le dashboard avant gros traitements

### Pour la Production
1. **Configurer** des alertes email/webhook
2. **Sauvegarder** l'historique de consommation
3. **Implémenter** des files d'attente pour les gros volumes
4. **Prévoir** une stratégie de fallback

## 📞 Support

En cas de problème:
1. Vérifier les logs console
2. Regarder le fichier `api_quota_tracking.json`
3. Tester la clé API manuellement
4. Consulter la [documentation YouTube API](https://developers.google.com/youtube/v3)

---

🎉 **Votre consommation API est maintenant trackée en temps réel !** 

Surveillez le dashboard pour optimiser vos analyses et éviter les dépassements de quota. 