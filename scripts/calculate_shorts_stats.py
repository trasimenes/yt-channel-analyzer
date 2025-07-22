#!/usr/bin/env python3
"""
Script pour calculer les statistiques temporelles des Shorts
et mettre à jour les données avec les vraies dates de publication via l'API YouTube
"""

import sqlite3
from datetime import datetime, timedelta
import sys
import os
from collections import defaultdict

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_channel_analyzer.database.base import get_db_connection

def calculate_shorts_temporal_stats(competitor_id):
    """Calculer les statistiques temporelles des Shorts pour un concurrent"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer toutes les vidéos avec leurs dates
        cursor.execute("""
            SELECT 
                id, video_id, title, published_at, youtube_published_at, 
                is_short, view_count, duration_seconds
            FROM video 
            WHERE concurrent_id = ?
            ORDER BY published_at DESC
        """, (competitor_id,))
        
        videos = cursor.fetchall()
        
        # Analyser les dates disponibles
        real_dates_count = sum(1 for v in videos if v[4] is not None)  # youtube_published_at
        
        print(f"📊 Analyse pour le concurrent {competitor_id}:")
        print(f"   • {len(videos)} vidéos totales")
        print(f"   • {real_dates_count} avec vraies dates YouTube")
        
        if real_dates_count == 0:
            print("⚠️  Aucune vraie date YouTube disponible. Utilisation de l'API nécessaire.")
            return None
        
        # Utiliser youtube_published_at si disponible, sinon published_at
        videos_with_dates = []
        for v in videos:
            date_str = v[4] if v[4] else v[3]  # youtube_published_at ou published_at
            if date_str:
                try:
                    # Parser la date
                    if 'T' in date_str:
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
                    
                    videos_with_dates.append({
                        'id': v[0],
                        'video_id': v[1],
                        'title': v[2],
                        'date': date,
                        'is_short': v[5],
                        'view_count': v[6],
                        'duration_seconds': v[7]
                    })
                except Exception as e:
                    print(f"⚠️  Erreur parsing date pour vidéo {v[1]}: {e}")
        
        if not videos_with_dates:
            print("❌ Aucune vidéo avec date valide")
            return None
        
        # Trier par date
        videos_with_dates.sort(key=lambda x: x['date'])
        
        # Calculer la période
        first_date = videos_with_dates[0]['date']
        last_date = videos_with_dates[-1]['date']
        total_days = (last_date - first_date).days + 1
        total_weeks = total_days / 7
        total_months = total_days / 30.5
        
        # Compter les shorts
        shorts = [v for v in videos_with_dates if v['is_short']]
        regular_videos = [v for v in videos_with_dates if not v['is_short']]
        
        # Statistiques temporelles
        shorts_per_week = len(shorts) / total_weeks if total_weeks > 0 else 0
        shorts_per_month = len(shorts) / total_months if total_months > 0 else 0
        videos_per_week = len(videos_with_dates) / total_weeks if total_weeks > 0 else 0
        videos_per_month = len(videos_with_dates) / total_months if total_months > 0 else 0
        
        # Analyser la distribution temporelle
        shorts_by_month = defaultdict(int)
        regular_by_month = defaultdict(int)
        
        for v in videos_with_dates:
            month_key = v['date'].strftime('%Y-%m')
            if v['is_short']:
                shorts_by_month[month_key] += 1
            else:
                regular_by_month[month_key] += 1
        
        # Calculer les moyennes de vues
        avg_views_shorts = sum(v['view_count'] for v in shorts if v['view_count']) / len(shorts) if shorts else 0
        avg_views_regular = sum(v['view_count'] for v in regular_videos if v['view_count']) / len(regular_videos) if regular_videos else 0
        
        stats = {
            'competitor_id': competitor_id,
            'total_videos': len(videos_with_dates),
            'shorts_count': len(shorts),
            'regular_count': len(regular_videos),
            'shorts_percentage': (len(shorts) / len(videos_with_dates) * 100) if videos_with_dates else 0,
            'first_video_date': first_date.isoformat(),
            'last_video_date': last_date.isoformat(),
            'total_days': total_days,
            'shorts_per_week': round(shorts_per_week, 2),
            'shorts_per_month': round(shorts_per_month, 2),
            'videos_per_week': round(videos_per_week, 2),
            'videos_per_month': round(videos_per_month, 2),
            'avg_views_shorts': int(avg_views_shorts),
            'avg_views_regular': int(avg_views_regular),
            'performance_ratio': avg_views_shorts / avg_views_regular if avg_views_regular > 0 else 0,
            'months_active': list(sorted(set(shorts_by_month.keys()) | set(regular_by_month.keys()))),
            'shorts_by_month': dict(shorts_by_month),
            'regular_by_month': dict(regular_by_month)
        }
        
        # Afficher le résumé
        print(f"\n📊 Résultats de l'analyse temporelle:")
        print(f"   • Période: {first_date.date()} à {last_date.date()} ({total_days} jours)")
        print(f"   • Shorts: {len(shorts)} ({stats['shorts_percentage']:.1f}%)")
        print(f"   • Shorts par semaine: {stats['shorts_per_week']:.2f}")
        print(f"   • Shorts par mois: {stats['shorts_per_month']:.2f}")
        print(f"   • Performance Shorts vs Regular: {stats['performance_ratio']:.2f}x")
        
        return stats
        
    except Exception as e:
        print(f"❌ Erreur lors du calcul: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        conn.close()

def update_video_dates_from_youtube(competitor_id, limit=50):
    """Mettre à jour les dates de publication depuis l'API YouTube"""
    
    print(f"\n🔄 Mise à jour des dates YouTube pour le concurrent {competitor_id}...")
    
    try:
        from yt_channel_analyzer.youtube_api_client import create_youtube_client
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les vidéos sans vraie date YouTube
        cursor.execute("""
            SELECT id, video_id, title
            FROM video 
            WHERE concurrent_id = ? 
            AND (youtube_published_at IS NULL OR youtube_published_at = '')
            LIMIT ?
        """, (competitor_id, limit))
        
        videos_to_update = cursor.fetchall()
        
        if not videos_to_update:
            print("✅ Toutes les vidéos ont déjà leurs dates YouTube")
            return True
        
        print(f"📋 {len(videos_to_update)} vidéos à mettre à jour")
        
        # Initialiser le client YouTube
        youtube_client = create_youtube_client()
        
        # Traiter par batch de 50 (limite API)
        batch_size = 50
        updated_count = 0
        
        for i in range(0, len(videos_to_update), batch_size):
            batch = videos_to_update[i:i+batch_size]
            video_ids = [v[1] for v in batch]
            
            # Récupérer les infos depuis YouTube
            print(f"   • Récupération batch {i//batch_size + 1}...")
            videos_info = youtube_client.get_videos_details(video_ids)
            
            # Mettre à jour la base
            for video_info in videos_info:
                video_id = video_info['id']
                # Notre client retourne published_at directement, pas dans snippet
                published_at = video_info.get('published_at')
                duration_seconds = video_info.get('duration_seconds', 0)
                
                print(f"[UPDATE-DEBUG] 📝 Vidéo {video_id}: published_at='{published_at}', duration={duration_seconds}s")
                
                if published_at:
                    # Déterminer si c'est un Short basé sur la durée (notre client retourne déjà duration_seconds)
                    is_short = duration_seconds <= 60 if duration_seconds > 0 else False
                    
                    cursor.execute("""
                        UPDATE video 
                        SET youtube_published_at = ?, 
                            is_short = ?,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE video_id = ?
                    """, (published_at, 1 if is_short else 0, video_id))
                    updated_count += 1
        
        conn.commit()
        print(f"✅ {updated_count} vidéos mises à jour avec succès")
        
        # Calculer les nouvelles stats
        stats = calculate_shorts_temporal_stats(competitor_id)
        
        return stats
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour YouTube: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def main():
    """Fonction principale"""
    
    if len(sys.argv) > 1:
        competitor_id = int(sys.argv[1])
    else:
        # Par défaut: Airbnb (ID 13)
        competitor_id = 13
    
    print(f"🚀 Calcul des statistiques Shorts pour le concurrent ID {competitor_id}")
    
    # Essayer d'abord avec les données existantes
    stats = calculate_shorts_temporal_stats(competitor_id)
    
    if not stats or stats['total_days'] < 2:
        print("\n⚠️  Données temporelles insuffisantes. Mise à jour depuis YouTube...")
        # Mettre à jour depuis YouTube
        stats = update_video_dates_from_youtube(competitor_id)
    
    if stats:
        print("\n✅ Analyse terminée avec succès!")
        
        # Optionnel: sauvegarder les stats dans une table dédiée
        # save_shorts_stats(stats)
    else:
        print("\n❌ Impossible de calculer les statistiques")
        sys.exit(1)

if __name__ == "__main__":
    main()