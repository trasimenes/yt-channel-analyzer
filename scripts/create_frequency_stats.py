import sqlite3
from datetime import datetime
from collections import defaultdict

def get_db_connection():
    """Crée une connexion à la base de données SQLite."""
    conn = sqlite3.connect('instance/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_frequency_stats_table():
    """Crée la table de statistiques de fréquence si elle n'existe pas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitor_frequency_stats (
                competitor_id INTEGER PRIMARY KEY,
                total_videos INTEGER,
                total_weeks INTEGER,
                avg_videos_per_week REAL,
                frequency_total REAL,
                frequency_hero REAL,
                frequency_hub REAL,
                frequency_help REAL,
                calculation_method TEXT,
                last_updated TEXT
            )
        ''')
        print("✅ La table 'competitor_frequency_stats' est prête.")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table: {e}")
    finally:
        conn.close()

def calculate_and_populate_frequency_stats():
    """Calcule et peuple les statistiques de fréquence pour tous les concurrents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Récupérer toutes les vidéos avec des dates de publication valides
        cursor.execute('''
            SELECT 
                c.id as competitor_id,
                v.published_at,
                COALESCE(v.youtube_published_at, v.published_at) as effective_date,
                v.category
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE effective_date IS NOT NULL
            ORDER BY c.id, effective_date
        ''')
        videos = cursor.fetchall()
        
        # Grouper les vidéos par concurrent
        competitor_videos = defaultdict(list)
        for video in videos:
            competitor_videos[video['competitor_id']].append(video)
            
        print(f"📊 Calcul de la fréquence pour {len(competitor_videos)} concurrents...")
        
        for competitor_id, video_list in competitor_videos.items():
            
            # Trier par date effective
            video_list.sort(key=lambda x: x['effective_date'])
            
            # Utiliser les dates effectives pour le calcul
            dates = [datetime.fromisoformat(v['effective_date'].replace('Z', '+00:00')) for v in video_list]
            
            if len(dates) < 2:
                # Pas assez de données pour un calcul fiable
                total_weeks = 1
                avg_videos_per_week = len(dates)
                method = 'estimation_simple'
            else:
                total_duration_days = (dates[-1] - dates[0]).days
                total_weeks = max(1, round(total_duration_days / 7))
                avg_videos_per_week = round(len(video_list) / total_weeks, 2) if total_weeks > 0 else 0
                method = 'dates_reelles'
            
            # Fréquence par catégorie
            category_counts = defaultdict(int)
            for video in video_list:
                category_counts[video['category'] or 'hub'] += 1 # Fallback sur 'hub'
                
            frequency_hero = round(category_counts['hero'] / total_weeks, 2) if total_weeks > 0 else 0
            frequency_hub = round(category_counts['hub'] / total_weeks, 2) if total_weeks > 0 else 0
            frequency_help = round(category_counts['help'] / total_weeks, 2) if total_weeks > 0 else 0
            
            # Insertion dans la base de données
            cursor.execute('''
                INSERT OR REPLACE INTO competitor_frequency_stats (
                    competitor_id, total_videos, total_weeks, avg_videos_per_week,
                    frequency_total, frequency_hero, frequency_hub, frequency_help,
                    calculation_method, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                competitor_id, len(video_list), total_weeks, avg_videos_per_week,
                avg_videos_per_week, frequency_hero, frequency_hub, frequency_help,
                method, datetime.now().isoformat()
            ))
            
            print(f"  - Concurrent {competitor_id}: {avg_videos_per_week} vidéos/semaine ({total_weeks} semaines analysées)")

        conn.commit()
        print("\n🎉 Toutes les statistiques de fréquence ont été calculées et stockées.")
        
    except Exception as e:
        print(f"❌ Erreur lors du calcul et de la population des stats de fréquence: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    create_frequency_stats_table()
    calculate_and_populate_frequency_stats() 