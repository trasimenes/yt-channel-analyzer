#!/usr/bin/env python3
"""
Script de consolidation des données YouTube pour analyse approfondie
Étape 1: Récupération de TOUTES les données depuis SQLite
Étape 2: Consolidation avec métadonnées (pays, concurrent)
Étape 3: Préparation pour l'analyse sémantique
"""

import json
import sqlite3
import os
from datetime import datetime
from collections import Counter
import pandas as pd

class YouTubeDataConsolidator:
    def __init__(self, db_path='instance/database.db'):
        """Initialise le consolidateur avec la base de données existante"""
        self.db_path = db_path
        self.consolidated_data = {
            'videos': [],
            'playlists': [],
            'competitors': [],
            'metadata': {}
        }
    
    def connect_db(self):
        """Connexion à la base de données"""
        return sqlite3.connect(self.db_path)
    
    def step1_fetch_all_videos(self):
        """Étape 1: Récupération de TOUS les titres et métadonnées des vidéos"""
        print("📹 ÉTAPE 1: Récupération de tous les titres de vidéos...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # Requête pour récupérer TOUTES les vidéos avec métadonnées complètes
        query = '''
        SELECT 
            v.id, v.video_id, v.title, v.published_at, v.view_count, 
            v.like_count, v.comment_count, v.duration_seconds, v.category,
            v.beauty_score, v.emotion_score, v.info_quality_score,
            c.id as competitor_id, c.name as competitor_name, c.country,
            c.subscriber_count, c.view_count as channel_views,
            p.id as playlist_id, p.name as playlist_name, p.category as playlist_category
        FROM video v
        JOIN concurrent c ON v.concurrent_id = c.id
        LEFT JOIN playlist_video pv ON v.id = pv.video_id
        LEFT JOIN playlist p ON pv.playlist_id = p.id
        ORDER BY v.view_count DESC
        '''
        
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
        print(f"✅ {len(raw_data)} enregistrements récupérés depuis la base")
        
        # Organiser les données par vidéo unique
        videos_dict = {}
        for row in raw_data:
            (vid_db_id, video_id, title, published_at, view_count, like_count, comment_count,
             duration_seconds, category, beauty_score, emotion_score, info_quality_score,
             competitor_id, competitor_name, country, subscriber_count, channel_views,
             playlist_id, playlist_name, playlist_category) = row
            
            if video_id not in videos_dict:
                videos_dict[video_id] = {
                    'db_id': vid_db_id,
                    'video_id': video_id,
                    'title': title or '',
                    'published_at': published_at,
                    'view_count': view_count or 0,
                    'like_count': like_count or 0,
                    'comment_count': comment_count or 0,
                    'duration_seconds': duration_seconds or 0,
                    'category': category,
                    'beauty_score': beauty_score,
                    'emotion_score': emotion_score,
                    'info_quality_score': info_quality_score,
                    'competitor_id': competitor_id,
                    'competitor_name': competitor_name,
                    'country': country,
                    'subscriber_count': subscriber_count,
                    'channel_views': channel_views,
                    'playlists': []
                }
            
            # Ajouter playlist si elle existe
            if playlist_id and playlist_name:
                videos_dict[video_id]['playlists'].append({
                    'playlist_id': playlist_id,
                    'playlist_name': playlist_name,
                    'playlist_category': playlist_category
                })
        
        self.consolidated_data['videos'] = list(videos_dict.values())
        conn.close()
        
        print(f"🎯 {len(self.consolidated_data['videos'])} vidéos uniques consolidées")
        
        # Statistiques par pays
        country_stats = Counter(v['country'] for v in self.consolidated_data['videos'])
        print("📊 Répartition par pays:")
        for country, count in country_stats.most_common():
            print(f"  - {country}: {count:,} vidéos")
        
        return len(self.consolidated_data['videos'])
    
    def step2_fetch_all_descriptions(self):
        """Étape 2: Récupération de TOUTES les descriptions des vidéos"""
        print("\n📝 ÉTAPE 2: Récupération de toutes les descriptions de vidéos...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # Récupérer les descriptions
        cursor.execute('SELECT video_id, description FROM video WHERE description IS NOT NULL')
        descriptions = cursor.fetchall()
        
        # Associer descriptions aux vidéos
        description_dict = {video_id: desc for video_id, desc in descriptions}
        
        descriptions_added = 0
        for video in self.consolidated_data['videos']:
            video_id = video['video_id']
            if video_id in description_dict:
                video['description'] = description_dict[video_id]
                descriptions_added += 1
            else:
                video['description'] = ''
        
        conn.close()
        
        print(f"✅ {descriptions_added:,} descriptions ajoutées aux vidéos")
        print(f"📊 {len(descriptions) - descriptions_added} descriptions non matchées")
        
        return descriptions_added
    
    def step3_fetch_all_playlists(self):
        """Étape 3: Récupération de toutes les descriptions de playlists"""
        print("\n🎵 ÉTAPE 3: Récupération de toutes les playlists...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            p.id, p.playlist_id, p.name, p.description, p.category,
            p.video_count, p.created_at, p.last_updated,
            p.classification_source, p.human_verified, p.is_human_validated,
            c.id as competitor_id, c.name as competitor_name, c.country
        FROM playlist p
        JOIN concurrent c ON p.concurrent_id = c.id
        ORDER BY p.video_count DESC
        '''
        
        cursor.execute(query)
        playlist_data = cursor.fetchall()
        
        for row in playlist_data:
            (pl_id, playlist_id, name, description, category, video_count,
             created_at, last_updated, classification_source, human_verified,
             is_human_validated, competitor_id, competitor_name, country) = row
            
            playlist_info = {
                'db_id': pl_id,
                'playlist_id': playlist_id,
                'name': name or '',
                'description': description or '',
                'category': category,
                'video_count': video_count or 0,
                'created_at': created_at,
                'last_updated': last_updated,
                'classification_source': classification_source,
                'human_verified': bool(human_verified),
                'is_human_validated': bool(is_human_validated),
                'competitor_id': competitor_id,
                'competitor_name': competitor_name,
                'country': country
            }
            
            self.consolidated_data['playlists'].append(playlist_info)
        
        conn.close()
        
        print(f"✅ {len(self.consolidated_data['playlists'])} playlists récupérées")
        
        # Statistiques playlists
        category_stats = Counter(p['category'] for p in self.consolidated_data['playlists'] if p['category'])
        print("📊 Répartition par catégorie:")
        for category, count in category_stats.most_common():
            print(f"  - {category.upper()}: {count} playlists")
        
        return len(self.consolidated_data['playlists'])
    
    def step4_fetch_competitors(self):
        """Étape 4: Récupération des informations des concurrents"""
        print("\n🏢 ÉTAPE 4: Récupération des informations concurrents...")
        
        conn = self.connect_db()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            id, name, channel_id, country, subscriber_count, view_count,
            description, thumbnail_url, created_at, last_updated
        FROM concurrent
        ORDER BY subscriber_count DESC
        '''
        
        cursor.execute(query)
        competitor_data = cursor.fetchall()
        
        for row in competitor_data:
            (comp_id, name, channel_id, country, subscriber_count, view_count,
             description, thumbnail_url, created_at, last_updated) = row
            
            competitor_info = {
                'competitor_id': comp_id,
                'name': name,
                'channel_id': channel_id,
                'country': country,
                'subscriber_count': subscriber_count or 0,
                'view_count': view_count or 0,
                'description': description or '',
                'thumbnail_url': thumbnail_url,
                'created_at': created_at,
                'last_updated': last_updated
            }
            
            self.consolidated_data['competitors'].append(competitor_info)
        
        conn.close()
        
        print(f"✅ {len(self.consolidated_data['competitors'])} concurrents récupérés")
        
        # Statistiques concurrents
        country_stats = Counter(c['country'] for c in self.consolidated_data['competitors'])
        print("📊 Concurrents par pays:")
        for country, count in country_stats.most_common():
            print(f"  - {country}: {count} concurrents")
        
        return len(self.consolidated_data['competitors'])
    
    def generate_metadata(self):
        """Génère des métadonnées globales sur le dataset consolidé"""
        print("\n📋 Génération des métadonnées globales...")
        
        videos = self.consolidated_data['videos']
        playlists = self.consolidated_data['playlists']
        competitors = self.consolidated_data['competitors']
        
        # Statistiques globales
        total_views = sum(v['view_count'] for v in videos)
        total_likes = sum(v['like_count'] for v in videos)
        total_comments = sum(v['comment_count'] for v in videos)
        
        # Statistiques par pays
        country_breakdown = {}
        for country in set(v['country'] for v in videos):
            country_videos = [v for v in videos if v['country'] == country]
            country_breakdown[country] = {
                'videos': len(country_videos),
                'total_views': sum(v['view_count'] for v in country_videos),
                'avg_views': sum(v['view_count'] for v in country_videos) / len(country_videos),
                'competitors': len([c for c in competitors if c['country'] == country])
            }
        
        # Statistiques temporelles
        years = Counter()
        for video in videos:
            if video['published_at']:
                year = video['published_at'][:4]
                years[year] += 1
        
        self.consolidated_data['metadata'] = {
            'consolidation_date': datetime.now().isoformat(),
            'total_videos': len(videos),
            'total_playlists': len(playlists),
            'total_competitors': len(competitors),
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'avg_views_per_video': total_views / len(videos) if videos else 0,
            'engagement_rate': (total_likes + total_comments) / total_views if total_views > 0 else 0,
            'country_breakdown': country_breakdown,
            'temporal_distribution': dict(years.most_common()),
            'data_quality': {
                'videos_with_descriptions': len([v for v in videos if v.get('description', '').strip()]),
                'videos_with_categories': len([v for v in videos if v['category']]),
                'playlists_human_validated': len([p for p in playlists if p['is_human_validated']])
            }
        }
        
        print("✅ Métadonnées générées")
        return self.consolidated_data['metadata']
    
    def save_consolidated_data(self, output_file='youtube_consolidated_data.json'):
        """Sauvegarde toutes les données consolidées"""
        print(f"\n💾 Sauvegarde des données consolidées dans {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.consolidated_data, f, ensure_ascii=False, indent=2)
        
        file_size_mb = os.path.getsize(output_file) / 1024 / 1024
        print(f"✅ Données sauvegardées ({file_size_mb:.1f} MB)")
        
        # Créer aussi des fichiers séparés pour faciliter l'analyse
        with open('videos_only.json', 'w', encoding='utf-8') as f:
            json.dump(self.consolidated_data['videos'], f, ensure_ascii=False, indent=2)
        
        with open('playlists_only.json', 'w', encoding='utf-8') as f:
            json.dump(self.consolidated_data['playlists'], f, ensure_ascii=False, indent=2)
        
        # CSV pour analyse rapide
        df_videos = pd.DataFrame(self.consolidated_data['videos'])
        df_videos.to_csv('videos_consolidated.csv', index=False, encoding='utf-8')
        
        df_playlists = pd.DataFrame(self.consolidated_data['playlists'])
        df_playlists.to_csv('playlists_consolidated.csv', index=False, encoding='utf-8')
        
        print("✅ Fichiers séparés créés: videos_only.json, playlists_only.json, *.csv")
        
        return output_file
    
    def print_summary(self):
        """Affiche un résumé détaillé de la consolidation"""
        metadata = self.consolidated_data['metadata']
        
        print("\n" + "="*60)
        print("🎯 RÉSUMÉ DE LA CONSOLIDATION COMPLÈTE")
        print("="*60)
        
        print(f"📹 Total vidéos: {metadata['total_videos']:,}")
        print(f"🎵 Total playlists: {metadata['total_playlists']:,}")
        print(f"🏢 Total concurrents: {metadata['total_competitors']:,}")
        print(f"👁️  Vues totales: {metadata['total_views']:,}")
        print(f"👍 Likes totaux: {metadata['total_likes']:,}")
        print(f"💬 Commentaires totaux: {metadata['total_comments']:,}")
        print(f"📊 Engagement rate: {metadata['engagement_rate']*100:.2f}%")
        
        print("\n🌍 RÉPARTITION PAR PAYS:")
        for country, stats in metadata['country_breakdown'].items():
            print(f"  {country}: {stats['videos']:,} vidéos, {stats['competitors']} concurrents, "
                  f"{stats['avg_views']:,.0f} vues/vidéo en moyenne")
        
        print("\n📅 RÉPARTITION TEMPORELLE:")
        for year, count in sorted(metadata['temporal_distribution'].items()):
            print(f"  {year}: {count:,} vidéos")
        
        print(f"\n✅ QUALITÉ DES DONNÉES:")
        dq = metadata['data_quality']
        print(f"  • Vidéos avec description: {dq['videos_with_descriptions']:,} "
              f"({dq['videos_with_descriptions']/metadata['total_videos']*100:.1f}%)")
        print(f"  • Vidéos catégorisées: {dq['videos_with_categories']:,} "
              f"({dq['videos_with_categories']/metadata['total_videos']*100:.1f}%)")
        print(f"  • Playlists validées humainement: {dq['playlists_human_validated']:,} "
              f"({dq['playlists_human_validated']/metadata['total_playlists']*100:.1f}%)")
        
        print("\n🚀 PRÊT POUR L'ANALYSE SÉMANTIQUE!")
        print("="*60)

def main():
    """Script principal de consolidation"""
    print("🚀 DÉMARRAGE DE LA CONSOLIDATION YOUTUBE DATA")
    print("="*50)
    
    # Initialiser le consolidateur
    consolidator = YouTubeDataConsolidator()
    
    try:
        # Étape 1: Récupérer toutes les vidéos
        consolidator.step1_fetch_all_videos()
        
        # Étape 2: Récupérer toutes les descriptions
        consolidator.step2_fetch_all_descriptions()
        
        # Étape 3: Récupérer toutes les playlists
        consolidator.step3_fetch_all_playlists()
        
        # Étape 4: Récupérer les concurrents
        consolidator.step4_fetch_competitors()
        
        # Générer les métadonnées
        consolidator.generate_metadata()
        
        # Sauvegarder tout
        output_file = consolidator.save_consolidated_data()
        
        # Afficher le résumé
        consolidator.print_summary()
        
        print(f"\n✅ CONSOLIDATION TERMINÉE!")
        print(f"📁 Fichier principal: {output_file}")
        print("🎯 Utilisez maintenant le script d'analyse sémantique sur ces données!")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        raise

if __name__ == "__main__":
    main()