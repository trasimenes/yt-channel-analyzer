#!/usr/bin/env python3
"""
Script de migration pour appliquer la classification intelligente 
aux compétiteurs existants dans le cache
"""

import json
import os
from datetime import datetime

# Importer le classificateur
from yt_channel_analyzer.ai_classifier import industry_classifier

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
        return 'hospitality'  # Par défaut

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

def migrate_existing_competitors():
    """Migrer tous les compétiteurs existants avec la classification intelligente"""
    print("🚀 Début de la migration des tags intelligents...")
    
    # Charger le cache existant
    cache_data = load_cache()
    if not cache_data:
        print("❌ Aucune donnée trouvée dans le cache")
        return
    
    print(f"📊 {len(cache_data)} compétiteurs trouvés dans le cache")
    
    # Statistiques
    stats = {
        'total': len(cache_data),
        'updated': 0,
        'already_tagged': 0,
        'industries_detected': {},
        'regions_detected': {}
    }
    
    # Traiter chaque compétiteur
    for competitor_id, competitor_data in cache_data.items():
        channel_name = competitor_data.get('name', 'Unknown')
        print(f"\n🔄 Traitement: {channel_name}")
        
        # Vérifier si déjà taggé (pour éviter d'écraser les tags manuels)
        has_region = competitor_data.get('region') is not None
        has_industry = competitor_data.get('industry') is not None
        has_custom_tags = competitor_data.get('custom_tags') is not None
        
        if has_region and has_industry and has_custom_tags:
            print(f"   ✅ Déjà taggé, passage...")
            stats['already_tagged'] += 1
            continue
        
        # Classification intelligente
        description = competitor_data.get('description', '')
        videos = competitor_data.get('videos', [])
        
        # Détecter l'industrie si pas déjà définie
        if not has_industry:
            detected_industry = industry_classifier.classify_industry(
                channel_name, description, videos
            )
            
            # Si aucune industrie détectée, forcer une industrie par défaut
            if not detected_industry:
                # Utiliser la même logique que dans app.py
                detected_industry = suggest_default_industry(channel_name, description)
                print(f"   💡 Industrie suggérée par défaut: {detected_industry}")
            else:
                print(f"   🏢 Industrie détectée: {detected_industry}")
            
            competitor_data['industry'] = detected_industry
            stats['industries_detected'][detected_industry] = stats['industries_detected'].get(detected_industry, 0) + 1
        
        # Détecter la région si pas déjà définie
        if not has_region:
            detected_region = industry_classifier.get_region_from_name(channel_name)
            competitor_data['region'] = detected_region
            stats['regions_detected'][detected_region] = stats['regions_detected'].get(detected_region, 0) + 1
            print(f"   🌍 Région détectée: {detected_region}")
        
        # Initialiser les tags personnalisés si pas déjà fait
        if not has_custom_tags:
            competitor_data['custom_tags'] = []
        
        # Mettre à jour la date de modification
        competitor_data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        stats['updated'] += 1
    
    # Sauvegarder le cache mis à jour
    if save_cache(cache_data):
        print(f"\n✅ Migration terminée avec succès!")
        print(f"📈 Statistiques:")
        print(f"   • Total: {stats['total']} compétiteurs")
        print(f"   • Mis à jour: {stats['updated']}")
        print(f"   • Déjà taggés: {stats['already_tagged']}")
        
        if stats['industries_detected']:
            print(f"   • Industries détectées:")
            for industry, count in stats['industries_detected'].items():
                print(f"     - {industry}: {count}")
        
        if stats['regions_detected']:
            print(f"   • Régions détectées:")
            for region, count in stats['regions_detected'].items():
                print(f"     - {region}: {count}")
        
        print(f"\n🎯 Les compétiteurs sont maintenant tagués intelligemment!")
        print(f"   Vous pouvez modifier les tags via l'interface web.")
    else:
        print("❌ Erreur lors de la sauvegarde")

def show_current_tags():
    """Afficher les tags actuels de tous les compétiteurs"""
    print("📋 Tags actuels des compétiteurs:")
    
    cache_data = load_cache()
    if not cache_data:
        print("❌ Aucune donnée trouvée")
        return
    
    for competitor_id, competitor_data in cache_data.items():
        name = competitor_data.get('name', 'Unknown')
        region = competitor_data.get('region', 'Non défini')
        industry = competitor_data.get('industry', 'Non défini')
        custom_tags = competitor_data.get('custom_tags', [])
        
        print(f"\n• {name}")
        print(f"  Région: {region}")
        print(f"  Industrie: {industry}")
        if custom_tags:
            print(f"  Tags: {', '.join(custom_tags)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        show_current_tags()
    else:
        migrate_existing_competitors() 