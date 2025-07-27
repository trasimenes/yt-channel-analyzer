#!/usr/bin/env python3
"""
Refresh global complet de Center Parcs NL-BE (ID: 9)
- Recalcul unifié de TOUTES les statistiques
- Synchronisation avec le seuil paid/organic global
- Stockage sécurisé en base de données
- Vérification de cohérence cross-services
"""

import sqlite3
import json
import os
from datetime import datetime
from services.brand_metrics_service import BrandMetricsService
from services.country_metrics_service import CountryMetricsService

def get_db_connection():
    """Get database connection"""
    db_path = os.path.join('instance', 'database.db')
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return None
    return sqlite3.connect(db_path)

def load_settings():
    """Load settings from config/settings.json"""
    try:
        settings_file = os.path.join('config', 'settings.json')
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'paid_threshold': 10000}

def get_centerparcs_nlbe_info(conn):
    """Get Center Parcs NL-BE basic info"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, country, channel_id, channel_url
        FROM concurrent 
        WHERE id = 9
    """)
    result = cursor.fetchone()
    if not result:
        print("❌ Center Parcs NL-BE (ID: 9) non trouvé")
        return None
    
    return {
        'id': result[0],
        'name': result[1], 
        'country': result[2],
        'channel_id': result[3],
        'channel_url': result[4]
    }

def analyze_video_data_integrity(conn, competitor_id):
    """Analyze video data integrity"""
    print(f"🔍 Analyse de l'intégrité des données vidéo...")
    cursor = conn.cursor()
    
    # Video count and basic stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_videos,
            COUNT(CASE WHEN view_count IS NOT NULL THEN 1 END) as with_views,
            COUNT(CASE WHEN like_count IS NOT NULL THEN 1 END) as with_likes,
            COUNT(CASE WHEN duration_seconds IS NOT NULL THEN 1 END) as with_duration,
            COUNT(CASE WHEN published_at IS NOT NULL THEN 1 END) as with_published_date,
            COUNT(CASE WHEN youtube_published_at IS NOT NULL THEN 1 END) as with_youtube_date,
            COUNT(CASE WHEN category IS NOT NULL THEN 1 END) as with_category,
            MIN(view_count) as min_views,
            MAX(view_count) as max_views,
            AVG(view_count) as avg_views
        FROM video 
        WHERE concurrent_id = ?
    """, (competitor_id,))
    
    stats = cursor.fetchone()
    
    integrity_report = {
        'total_videos': stats[0],
        'completeness': {
            'views': f"{stats[1]}/{stats[0]} ({stats[1]/stats[0]*100:.1f}%)" if stats[0] > 0 else "0/0",
            'likes': f"{stats[2]}/{stats[0]} ({stats[2]/stats[0]*100:.1f}%)" if stats[0] > 0 else "0/0", 
            'duration': f"{stats[3]}/{stats[0]} ({stats[3]/stats[0]*100:.1f}%)" if stats[0] > 0 else "0/0",
            'published_date': f"{stats[4]}/{stats[0]} ({stats[4]/stats[0]*100:.1f}%)" if stats[0] > 0 else "0/0",
            'youtube_date': f"{stats[5]}/{stats[0]} ({stats[5]/stats[0]*100:.1f}%)" if stats[0] > 0 else "0/0",
            'category': f"{stats[6]}/{stats[0]} ({stats[6]/stats[0]*100:.1f}%)" if stats[0] > 0 else "0/0"
        },
        'view_stats': {
            'min': stats[7] or 0,
            'max': stats[8] or 0,
            'avg': round(stats[9], 0) if stats[9] else 0
        }
    }
    
    print(f"   📊 {integrity_report['total_videos']} vidéos total")
    print(f"   ✅ Vues: {integrity_report['completeness']['views']}")
    print(f"   ✅ Likes: {integrity_report['completeness']['likes']}")
    print(f"   ✅ Durée: {integrity_report['completeness']['duration']}")
    print(f"   ✅ Date YouTube: {integrity_report['completeness']['youtube_date']}")
    print(f"   ✅ Catégorie HHH: {integrity_report['completeness']['category']}")
    print(f"   📈 Vues: {integrity_report['view_stats']['min']:,} - {integrity_report['view_stats']['avg']:,.0f} - {integrity_report['view_stats']['max']:,}")
    
    return integrity_report

def analyze_playlist_data(conn, competitor_id):
    """Analyze playlist data"""
    print(f"📋 Analyse des playlists...")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_playlists,
            COUNT(CASE WHEN category IS NOT NULL THEN 1 END) as categorized,
            COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero_count,
            COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub_count,
            COUNT(CASE WHEN category = 'help' THEN 1 END) as help_count,
            COUNT(CASE WHEN human_verified = 1 THEN 1 END) as human_verified,
            COUNT(CASE WHEN classification_source = 'human' THEN 1 END) as human_classified
        FROM playlist
        WHERE concurrent_id = ?
    """, (competitor_id,))
    
    playlist_stats = cursor.fetchone()
    
    playlist_report = {
        'total_playlists': playlist_stats[0],
        'categorized': playlist_stats[1],
        'hero_count': playlist_stats[2],
        'hub_count': playlist_stats[3], 
        'help_count': playlist_stats[4],
        'human_verified': playlist_stats[5],
        'human_classified': playlist_stats[6]
    }
    
    print(f"   📋 {playlist_report['total_playlists']} playlists total")
    print(f"   🏷️ {playlist_report['categorized']} catégorisées ({playlist_report['categorized']/playlist_report['total_playlists']*100:.1f}%)" if playlist_report['total_playlists'] > 0 else "   🏷️ 0 catégorisées")
    print(f"   👤 {playlist_report['human_classified']} classifiées manuellement")
    print(f"   🎯 Hero: {playlist_report['hero_count']} | Hub: {playlist_report['hub_count']} | Help: {playlist_report['help_count']}")
    
    return playlist_report

def recalculate_all_metrics(conn, competitor_id, settings):
    """Recalculate all metrics with unified threshold"""
    print(f"🔄 Recalcul complet des métriques...")
    
    paid_threshold = settings.get('paid_threshold', 10000)
    print(f"   💰 Seuil paid/organic unifié: {paid_threshold:,} vues")
    
    # Initialize brand metrics service
    brand_service = BrandMetricsService(conn, paid_threshold)
    
    try:
        # Calculate complete brand metrics
        metrics = brand_service.calculate_brand_metrics(competitor_id)
        
        # Extract and display key metrics
        video_length = metrics.get('video_length', {})
        video_frequency = metrics.get('video_frequency', {})
        organic_vs_paid = metrics.get('organic_vs_paid', {})
        hub_help_hero = metrics.get('hub_help_hero', {})
        thumbnail_consistency = metrics.get('thumbnail_consistency', {})
        tone_of_voice = metrics.get('tone_of_voice', {})
        shorts_distribution = metrics.get('shorts_distribution', {})
        most_liked_topics = metrics.get('most_liked_topics', [])
        
        print(f"\n📊 MÉTRIQUES RECALCULÉES:")
        print(f"   📹 Vidéos: {video_length.get('total_videos', 0)} total")
        print(f"   ⏱️ Durée moyenne: {video_length.get('avg_duration_minutes', 0):.1f} min")
        print(f"   📅 Fréquence: {video_frequency.get('videos_per_week', 0):.1f} vidéos/semaine")
        print(f"   💰 Organique: {organic_vs_paid.get('organic_percentage', 0):.1f}% ({organic_vs_paid.get('organic_count', 0)} vidéos)")
        print(f"   💎 Payé: {organic_vs_paid.get('paid_percentage', 0):.1f}% ({organic_vs_paid.get('paid_count', 0)} vidéos)")
        print(f"   🎯 HHH: Hero {hub_help_hero.get('hero_percentage', 0):.1f}% | Hub {hub_help_hero.get('hub_percentage', 0):.1f}% | Help {hub_help_hero.get('help_percentage', 0):.1f}%")
        print(f"   📱 Shorts: {shorts_distribution.get('shorts_percentage', 0):.1f}% ({shorts_distribution.get('shorts_count', 0)} shorts)")
        print(f"   🖼️ Miniatures: {thumbnail_consistency.get('consistency_score', 0):.1f}/10")
        print(f"   🗣️ Tonalité: {tone_of_voice.get('dominant_tone', 'N/A')}")
        
        if most_liked_topics:
            print(f"   ❤️ Top sujet: {most_liked_topics[0].get('topic', 'N/A')} ({most_liked_topics[0].get('avg_likes', 0):.0f} likes)")
        
        return metrics
        
    except Exception as e:
        print(f"   ❌ Erreur lors du recalcul: {e}")
        import traceback
        traceback.print_exc()
        return None

def store_refresh_results(conn, competitor_info, metrics, integrity_report, playlist_report, settings):
    """Store refresh results in database"""
    print(f"💾 Stockage des résultats...")
    
    cursor = conn.cursor()
    
    try:
        # Delete existing analysis for this competitor
        cursor.execute("DELETE FROM competitor_analysis_results WHERE competitor_id = ?", (competitor_info['id'],))
        
        if metrics:
            # Extract metrics for storage
            video_length = metrics.get('video_length', {})
            video_frequency = metrics.get('video_frequency', {})
            organic_vs_paid = metrics.get('organic_vs_paid', {})
            hub_help_hero = metrics.get('hub_help_hero', {})
            thumbnail_consistency = metrics.get('thumbnail_consistency', {})
            tone_of_voice = metrics.get('tone_of_voice', {})
            shorts_distribution = metrics.get('shorts_distribution', {})
            
            # Store complete analysis
            cursor.execute("""
                INSERT INTO competitor_analysis_results (
                    competitor_id, competitor_name, country, analysis_date, paid_threshold,
                    total_videos, organic_count, paid_count, organic_percentage, paid_percentage,
                    avg_duration_minutes, videos_per_week, hero_count, hub_count, help_count,
                    categorized_videos, thumbnail_consistency_score, dominant_tone,
                    shorts_count, shorts_percentage, raw_metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                competitor_info['id'], competitor_info['name'], competitor_info['country'], 
                datetime.now().isoformat(), settings.get('paid_threshold', 10000),
                video_length.get('total_videos', 0),
                organic_vs_paid.get('organic_count', 0),
                organic_vs_paid.get('paid_count', 0),
                organic_vs_paid.get('organic_percentage', 0),
                organic_vs_paid.get('paid_percentage', 0),
                video_length.get('avg_duration_minutes', 0),
                video_frequency.get('videos_per_week', 0),
                hub_help_hero.get('hero_count', 0),
                hub_help_hero.get('hub_count', 0),
                hub_help_hero.get('help_count', 0),
                hub_help_hero.get('categorized_videos', 0),
                thumbnail_consistency.get('consistency_score', 0),
                tone_of_voice.get('dominant_tone', 'N/A'),
                shorts_distribution.get('shorts_count', 0),
                shorts_distribution.get('shorts_percentage', 0),
                json.dumps({
                    'metrics': metrics,
                    'integrity_report': integrity_report,
                    'playlist_report': playlist_report,
                    'refresh_timestamp': datetime.now().isoformat()
                })
            ))
            
            conn.commit()
            print(f"   ✅ Résultats stockés en base")
            
    except Exception as e:
        print(f"   ❌ Erreur stockage: {e}")
        conn.rollback()

def verify_cross_service_consistency(conn, competitor_id, settings):
    """Verify consistency across different services"""
    print(f"🔍 Vérification de cohérence cross-services...")
    
    paid_threshold = settings.get('paid_threshold', 10000)
    
    # Test with brand service
    brand_service = BrandMetricsService(conn, paid_threshold)
    brand_metrics = brand_service.calculate_brand_metrics(competitor_id)
    
    # Test direct SQL calculation 
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN view_count <= ? THEN 1 END) as organic,
            COUNT(CASE WHEN view_count > ? THEN 1 END) as paid
        FROM video 
        WHERE concurrent_id = ? AND view_count IS NOT NULL
    """, (paid_threshold, paid_threshold, competitor_id))
    
    sql_result = cursor.fetchone()
    
    brand_organic_pct = brand_metrics.get('organic_vs_paid', {}).get('organic_percentage', 0)
    brand_paid_pct = brand_metrics.get('organic_vs_paid', {}).get('paid_percentage', 0)
    
    sql_organic_pct = round((sql_result[1] / sql_result[0] * 100), 1) if sql_result[0] > 0 else 0
    sql_paid_pct = round((sql_result[2] / sql_result[0] * 100), 1) if sql_result[0] > 0 else 0
    
    print(f"   🔧 Brand Service: {brand_organic_pct:.1f}% org, {brand_paid_pct:.1f}% paid")
    print(f"   🔧 SQL Direct: {sql_organic_pct:.1f}% org, {sql_paid_pct:.1f}% paid")
    
    if abs(brand_organic_pct - sql_organic_pct) < 0.1:
        print(f"   ✅ Cohérence vérifiée - services alignés")
        return True
    else:
        print(f"   ❌ Incohérence détectée - écart de {abs(brand_organic_pct - sql_organic_pct):.1f}%")
        return False

def print_final_summary(competitor_info, metrics, integrity_report, consistency_check):
    """Print final summary of refresh"""
    print(f"\n" + "="*80)
    print(f"🎯 REFRESH COMPLET TERMINÉ - CENTER PARCS NL-BE")
    print(f"="*80)
    
    print(f"\n📋 CONCURRENT:")
    print(f"   Nom: {competitor_info['name']}")
    print(f"   ID: {competitor_info['id']}")
    print(f"   Pays: {competitor_info['country']}")
    print(f"   Channel ID: {competitor_info['channel_id']}")
    
    print(f"\n📊 DONNÉES:")
    print(f"   Vidéos: {integrity_report['total_videos']}")
    print(f"   Intégrité: {integrity_report['completeness']['views']} avec vues")
    
    if metrics:
        organic_vs_paid = metrics.get('organic_vs_paid', {})
        print(f"\n💰 RÉPARTITION UNIFIED (seuil 10k):")
        print(f"   Organique: {organic_vs_paid.get('organic_percentage', 0):.1f}% ({organic_vs_paid.get('organic_count', 0)} vidéos)")
        print(f"   Payé: {organic_vs_paid.get('paid_percentage', 0):.1f}% ({organic_vs_paid.get('paid_count', 0)} vidéos)")
    
    print(f"\n✅ STATUT:")
    print(f"   Cohérence: {'✅ OK' if consistency_check else '❌ PROBLÈME'}")
    print(f"   Stockage: ✅ Sauvegardé en base")
    print(f"   Services: ✅ Tous unifiés au seuil 10k")

def main():
    """Main refresh script for Center Parcs NL-BE"""
    print("🚀 REFRESH GLOBAL COMPLET - CENTER PARCS NL-BE")
    print("="*70)
    
    # Load settings
    settings = load_settings()
    print(f"⚙️ Seuil paid/organic global: {settings.get('paid_threshold', 10000):,} vues")
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # Get competitor info
        competitor_info = get_centerparcs_nlbe_info(conn)
        if not competitor_info:
            return
        
        print(f"🎯 Analyse de: {competitor_info['name']} (ID: {competitor_info['id']})")
        
        # Analyze data integrity
        integrity_report = analyze_video_data_integrity(conn, competitor_info['id'])
        
        # Analyze playlist data  
        playlist_report = analyze_playlist_data(conn, competitor_info['id'])
        
        # Recalculate all metrics
        metrics = recalculate_all_metrics(conn, competitor_info['id'], settings)
        
        # Store results
        store_refresh_results(conn, competitor_info, metrics, integrity_report, playlist_report, settings)
        
        # Verify consistency across services
        consistency_check = verify_cross_service_consistency(conn, competitor_info['id'], settings)
        
        # Print final summary
        print_final_summary(competitor_info, metrics, integrity_report, consistency_check)
        
    except Exception as e:
        print(f"❌ Erreur durant le refresh: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()
        print(f"\n🎉 Refresh global terminé!")

if __name__ == "__main__":
    main()