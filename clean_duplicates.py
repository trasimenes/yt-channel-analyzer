#!/usr/bin/env python3
"""
Script pour nettoyer les duplicatas des compétiteurs et forcer les industries
"""

import json
import os
import re
from datetime import datetime
from collections import Counter

# Importer le classificateur
from yt_channel_analyzer.ai_classifier import industry_classifier

def normalize_channel_name(channel_name):
    """Normalise un nom de chaîne pour détecter les duplicatas intelligemment"""
    if not channel_name:
        return ""
    
    # Convertir en minuscules
    normalized = channel_name.lower()
    
    # Remplacer les caractères spéciaux par des espaces
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Supprimer les espaces multiples et les mots très courts
    words = [word for word in normalized.split() if len(word) > 1]
    
    # Rejoindre sans espaces pour détecter "clubmed" = "club med"
    normalized = ''.join(words)
    
    # Normaliser les variations communes
    replacements = {
        'clubmed': 'clubmed',
        'clubmediterranee': 'clubmed',
        'marriottbonvoy': 'marriott',
        'bonvoy': 'marriott',
        'bookingcom': 'booking',
        'airbnbcom': 'airbnb',
    }
    
    for pattern, replacement in replacements.items():
        if pattern in normalized:
            normalized = replacement
            break
    
    return normalized

def suggest_default_industry(channel_name, description):
    """Suggère une industrie par défaut basée sur des heuristics simples"""
    text = f"{channel_name} {description}".lower()
    
    # Mots-clés pour différentes industries
    industry_hints = {
        'hospitality': ['hotel', 'resort', 'travel', 'vacation', 'tourism', 'booking', 'accommodation'],
        'food': ['restaurant', 'food', 'cuisine', 'recipe', 'cooking', 'chef', 'meal', 'drink'],
        'technology': ['tech', 'software', 'app', 'digital', 'innovation', 'startup'],
        'fashion': ['fashion', 'style', 'clothing', 'outfit', 'brand'],
        'entertainment': ['entertainment', 'show', 'movie', 'music', 'game'],
        'health': ['health', 'medical', 'fitness', 'wellness'],
        'education': ['education', 'course', 'learning', 'tutorial'],
    }
    
    # Compter les occurrences pour chaque industrie
    scores = {}
    for industry, keywords in industry_hints.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score > 0:
            scores[industry] = score
    
    # Retourner l'industrie avec le score le plus élevé, ou 'hospitality' par défaut
    if scores:
        return max(scores.keys(), key=lambda x: scores[x])
    else:
        return 'hospitality'

def load_cache():
    """Charger le cache existant"""
    cache_file = 'cache_recherches/recherches.json'
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lors du chargement du cache: {e}")
            return {}
    return {}

def save_cache(cache_data):
    """Sauvegarder le cache mis à jour"""
    cache_file = 'cache_recherches/recherches.json'
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")
        return False

def clean_duplicates_and_fix_industries():
    """Nettoie les duplicatas et force les industries"""
    print("🧹 Nettoyage des duplicatas et correction des industries...")
    
    # Charger le cache
    cache_data = load_cache()
    if not cache_data:
        print("❌ Aucune donnée trouvée")
        return
    
    print(f"📊 {len(cache_data)} entrées trouvées dans le cache")
    
    # Regrouper par nom normalisé (même logique que dans concurrents())
    channels_by_name = {}
    removed_duplicates = []
    fixed_industries = []
    
    for key, data in cache_data.items():
        channel_name = data.get('name', 'Unknown')
        videos_count = len(data.get('videos', []))
        
        print(f"\n🔄 Traitement: {channel_name} ({videos_count} vidéos)")
        
        # Normaliser le nom
        clean_name = normalize_channel_name(channel_name)
        print(f"   📝 Nom normalisé: '{clean_name}'")
        
        # Vérifier si c'est un duplicata
        if clean_name in channels_by_name:
            existing_key, existing_data = channels_by_name[clean_name]
            existing_count = len(existing_data.get('videos', []))
            existing_name = existing_data.get('name')
            
            # Garder celui avec le plus de vidéos
            if videos_count > existing_count:
                print(f"   🔄 DUPLICATA: '{existing_name}' ({existing_count} vidéos) → '{channel_name}' ({videos_count} vidéos)")
                removed_duplicates.append((existing_key, existing_name, existing_count))
                channels_by_name[clean_name] = (key, data)
            else:
                print(f"   🔄 DUPLICATA: '{channel_name}' ({videos_count} vidéos) ignoré (gardé '{existing_name}' avec {existing_count} vidéos)")
                removed_duplicates.append((key, channel_name, videos_count))
                continue
        else:
            channels_by_name[clean_name] = (key, data)
        
        # Forcer l'industrie si manquante
        current_data = channels_by_name[clean_name][1]
        if not current_data.get('industry'):
            # Essayer la classification intelligente
            detected_industry = industry_classifier.classify_industry(
                channel_name,
                current_data.get('description', ''),
                current_data.get('videos', [])
            )
            
            if not detected_industry:
                detected_industry = suggest_default_industry(
                    channel_name, 
                    current_data.get('description', '')
                )
                print(f"   💡 Industrie suggérée: {detected_industry}")
            else:
                print(f"   🏢 Industrie détectée: {detected_industry}")
            
            current_data['industry'] = detected_industry
            fixed_industries.append((channel_name, detected_industry))
        
        # Forcer la région si manquante
        if not current_data.get('region'):
            detected_region = industry_classifier.get_region_from_name(channel_name)
            current_data['region'] = detected_region
            print(f"   🌍 Région détectée: {detected_region}")
        
        # S'assurer que custom_tags existe
        if 'custom_tags' not in current_data:
            current_data['custom_tags'] = []
    
    # Créer le nouveau cache sans les duplicatas
    new_cache = {}
    for clean_name, (key, data) in channels_by_name.items():
        new_cache[key] = data
        data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Sauvegarder
    if save_cache(new_cache):
        print(f"\n✅ Nettoyage terminé!")
        print(f"📈 Résultats:")
        print(f"   • Entrées originales: {len(cache_data)}")
        print(f"   • Entrées finales: {len(new_cache)}")
        print(f"   • Duplicatas supprimés: {len(removed_duplicates)}")
        print(f"   • Industries corrigées: {len(fixed_industries)}")
        
        if removed_duplicates:
            print(f"\n🗑️ Duplicatas supprimés:")
            for key, name, count in removed_duplicates:
                print(f"   - {name} ({count} vidéos)")
        
        if fixed_industries:
            print(f"\n🏢 Industries corrigées:")
            for name, industry in fixed_industries:
                print(f"   - {name} → {industry}")
    else:
        print("❌ Erreur lors de la sauvegarde")

def show_current_status():
    """Afficher le statut actuel"""
    cache_data = load_cache()
    if not cache_data:
        print("❌ Aucune donnée trouvée")
        return
    
    print(f"📊 Statut actuel: {len(cache_data)} compétiteurs")
    
    # Analyser les duplicatas potentiels
    names_normalized = {}
    for key, data in cache_data.items():
        name = data.get('name', 'Unknown')
        normalized = normalize_channel_name(name)
        videos_count = len(data.get('videos', []))
        
        if normalized not in names_normalized:
            names_normalized[normalized] = []
        names_normalized[normalized].append((name, videos_count, key))
    
    # Trouver les duplicatas
    duplicates = {k: v for k, v in names_normalized.items() if len(v) > 1}
    
    if duplicates:
        print(f"\n🔍 {len(duplicates)} groupes de duplicatas détectés:")
        for normalized, entries in duplicates.items():
            print(f"\n  📝 Groupe '{normalized}':")
            entries.sort(key=lambda x: x[1], reverse=True)  # Trier par nombre de vidéos
            for i, (name, count, key) in enumerate(entries):
                status = "🟢 À GARDER" if i == 0 else "🔴 À SUPPRIMER"
                print(f"    {status} {name} ({count} vidéos)")
    else:
        print("\n✅ Aucun duplicata détecté")
    
    # Analyser les industries manquantes
    missing_industry = [data.get('name') for data in cache_data.values() if not data.get('industry')]
    if missing_industry:
        print(f"\n❓ {len(missing_industry)} compétiteurs sans industrie:")
        for name in missing_industry[:10]:  # Afficher les 10 premiers
            print(f"   - {name}")
        if len(missing_industry) > 10:
            print(f"   ... et {len(missing_industry) - 10} autres")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        show_current_status()
    else:
        clean_duplicates_and_fix_industries() 