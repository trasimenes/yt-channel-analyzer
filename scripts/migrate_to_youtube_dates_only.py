#!/usr/bin/env python3
"""
Migration définitive : SEULEMENT les dates YouTube API
- Supprime published_at (dates d'import)
- Garde UNIQUEMENT youtube_published_at (vraies dates YouTube)
- Renomme youtube_published_at en published_at pour simplicité
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_channel_analyzer.database import get_db_connection

def migrate_to_youtube_dates_only():
    """
    Migration définitive vers les dates YouTube uniquement
    """
    print("🔧 MIGRATION : Dates YouTube uniquement")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Statistiques avant migration
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN youtube_published_at IS NOT NULL THEN 1 END) as with_youtube,
                COUNT(CASE WHEN published_at IS NOT NULL THEN 1 END) as with_import
            FROM video
        """)
        stats = cursor.fetchone()
        print(f"📊 AVANT MIGRATION :")
        print(f"   Total vidéos: {stats[0]}")
        print(f"   Avec date YouTube: {stats[1]}")
        print(f"   Avec date import: {stats[2]}")
        
        # 2. Vérifier qu'on a des dates YouTube pour la majorité
        if stats[1] < stats[0] * 0.8:  # Au moins 80% doivent avoir des dates YouTube
            print(f"❌ ERREUR: Seulement {stats[1]}/{stats[0]} vidéos ont des dates YouTube")
            print("   Lancez d'abord la récupération des dates via l'API")
            return False
        
        # 3. Créer la nouvelle table avec SEULEMENT published_at (= youtube_published_at)
        print("\n🔄 Création de la nouvelle structure...")
        
        cursor.execute("""
            CREATE TABLE video_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concurrent_id INTEGER NOT NULL,
                video_id VARCHAR(50) UNIQUE NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                url VARCHAR(200) NOT NULL,
                thumbnail_url VARCHAR(200),
                published_at DATETIME,  -- SEULE date, issue de youtube_published_at
                duration_seconds INTEGER,
                duration_text VARCHAR(20),
                view_count BIGINT,
                like_count INTEGER,
                comment_count INTEGER,
                category VARCHAR(50),
                tags TEXT,
                beauty_score INTEGER,
                emotion_score INTEGER,
                info_quality_score INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                classification_source VARCHAR(20) DEFAULT "ai",
                classification_date DATETIME,
                classification_confidence INTEGER DEFAULT 50,
                human_verified BOOLEAN DEFAULT 0,
                is_short BOOLEAN DEFAULT 0,
                is_human_validated INTEGER DEFAULT 0,
                FOREIGN KEY (concurrent_id) REFERENCES concurrent (id) ON DELETE CASCADE
            )
        """)
        
        # 4. Copier toutes les données en utilisant youtube_published_at comme published_at
        print("📦 Copie des données...")
        cursor.execute("""
            INSERT INTO video_new (
                id, concurrent_id, video_id, title, description, url, thumbnail_url,
                published_at,  -- = youtube_published_at de l'ancienne table
                duration_seconds, duration_text, view_count, like_count, comment_count,
                category, tags, beauty_score, emotion_score, info_quality_score,
                created_at, last_updated, classification_source, classification_date,
                classification_confidence, human_verified, is_short, is_human_validated
            )
            SELECT 
                id, concurrent_id, video_id, title, description, url, thumbnail_url,
                youtube_published_at,  -- SEULE vraie date
                duration_seconds, duration_text, view_count, like_count, comment_count,
                category, tags, beauty_score, emotion_score, info_quality_score,
                created_at, last_updated, classification_source, classification_date,
                classification_confidence, human_verified, is_short, is_human_validated
            FROM video
        """)
        
        copied_count = cursor.rowcount
        print(f"✅ {copied_count} vidéos copiées")
        
        # 5. Remplacer l'ancienne table
        print("🔄 Remplacement de la table...")
        cursor.execute("DROP TABLE video")
        cursor.execute("ALTER TABLE video_new RENAME TO video")
        
        # 6. Recréer les index
        print("📊 Recréation des index...")
        cursor.execute("CREATE INDEX idx_video_concurrent_id ON video(concurrent_id)")
        cursor.execute("CREATE INDEX idx_video_video_id ON video(video_id)")
        cursor.execute("CREATE INDEX idx_video_published_at ON video(published_at)")
        cursor.execute("CREATE INDEX idx_video_view_count ON video(view_count)")
        cursor.execute("CREATE INDEX idx_video_category ON video(category)")
        cursor.execute("CREATE INDEX idx_video_engagement ON video(concurrent_id, view_count, like_count, comment_count)")
        cursor.execute("CREATE INDEX idx_video_short ON video(is_short)")
        cursor.execute("CREATE INDEX idx_video_classification ON video(classification_source, is_human_validated)")
        
        # 7. Statistiques finales
        cursor.execute("SELECT COUNT(*), COUNT(published_at) FROM video")
        final_stats = cursor.fetchone()
        
        print(f"\n📊 APRÈS MIGRATION :")
        print(f"   Total vidéos: {final_stats[0]}")
        print(f"   Avec published_at: {final_stats[1]}")
        
        conn.commit()
        
        print(f"\n🎉 MIGRATION RÉUSSIE !")
        print(f"✅ La table video a maintenant SEULEMENT published_at (= vraies dates YouTube)")
        print(f"⚠️  Toutes les requêtes peuvent maintenant utiliser published_at en sécurité")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_to_youtube_dates_only()
    if success:
        print("\n🚀 Redémarrez l'application pour utiliser la nouvelle structure")
    else:
        print("\n💥 Migration échouée - structure inchangée")