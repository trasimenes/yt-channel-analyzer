#!/usr/bin/env python3
"""
YouTube Date Correction Agent
Detects and corrects YouTube video publication dates that have been incorrectly set to import dates.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from collections import defaultdict
import os
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yt_channel_analyzer.database import get_db_connection
from yt_channel_analyzer.youtube_api import YouTubeAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeDateCorrectionAgent:
    """Agent dedicated to correcting all erroneous import dates and restoring real YouTube publication dates."""
    
    def __init__(self, db_path: str = './instance/database.db'):
        self.db_path = db_path
        self.suspicious_dates = []
        self.corrections_made = 0
        self.api_failures = 0
        
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def detect_suspicious_dates(self) -> Dict[str, List[Dict]]:
        """Analyze database for date anomalies."""
        logger.info("🔍 Starting date anomaly detection...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        anomalies = {
            'mass_identical_dates': [],
            'import_dates': [],
            'temporal_inconsistencies': [],
            'competitor_uniformity': []
        }
        
        # 1. Detect mass identical dates (>50 videos with same date)
        cursor.execute("""
            SELECT DATE(published_at) as pub_date, COUNT(*) as count
            FROM video
            WHERE published_at IS NOT NULL
            GROUP BY DATE(published_at)
            HAVING COUNT(*) > 50
            ORDER BY count DESC
        """)
        
        for row in cursor.fetchall():
            anomalies['mass_identical_dates'].append({
                'date': row['pub_date'],
                'count': row['count']
            })
            
        # 2. Detect known import dates
        known_import_dates = ['2025-07-05', '2025-01-07']  # Add other known import dates
        
        for import_date in known_import_dates:
            cursor.execute("""
                SELECT COUNT(*) as count, 
                       GROUP_CONCAT(DISTINCT c.name) as competitors
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE DATE(v.published_at) = ?
            """, (import_date,))
            
            row = cursor.fetchone()
            if row['count'] > 0:
                anomalies['import_dates'].append({
                    'date': import_date,
                    'count': row['count'],
                    'competitors': row['competitors']
                })
                
        # 3. Detect temporal inconsistencies
        cursor.execute("""
            SELECT v.id, v.video_id, v.title, c.name as competitor,
                   v.published_at, v.youtube_published_at
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.youtube_published_at IS NOT NULL
              AND v.published_at > v.youtube_published_at
            LIMIT 100
        """)
        
        for row in cursor.fetchall():
            anomalies['temporal_inconsistencies'].append({
                'video_id': row['video_id'],
                'title': row['title'],
                'competitor': row['competitor'],
                'published_at': row['published_at'],
                'youtube_published_at': row['youtube_published_at']
            })
            
        # 4. Detect competitor-wide date uniformity
        cursor.execute("""
            SELECT c.id, c.name, 
                   COUNT(*) as total_videos,
                   COUNT(DISTINCT DATE(v.published_at)) as distinct_dates,
                   MIN(DATE(v.published_at)) as min_date,
                   MAX(DATE(v.published_at)) as max_date
            FROM concurrent c
            JOIN video v ON c.id = v.concurrent_id
            GROUP BY c.id, c.name
            HAVING COUNT(DISTINCT DATE(v.published_at)) < 5
               AND COUNT(*) > 20
        """)
        
        for row in cursor.fetchall():
            anomalies['competitor_uniformity'].append({
                'competitor_id': row['id'],
                'competitor': row['name'],
                'total_videos': row['total_videos'],
                'distinct_dates': row['distinct_dates'],
                'date_range': f"{row['min_date']} to {row['max_date']}"
            })
            
        conn.close()
        self.suspicious_dates = anomalies
        return anomalies
        
    def backup_current_dates(self) -> bool:
        """Create video_dates_backup table."""
        logger.info("💾 Creating backup of current dates...")
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create backup table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video_dates_backup (
                    id INTEGER PRIMARY KEY,
                    video_id TEXT,
                    original_published_at DATETIME,
                    original_youtube_published_at DATETIME,
                    backup_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check if backup already exists
            cursor.execute("SELECT COUNT(*) FROM video_dates_backup")
            if cursor.fetchone()[0] > 0:
                logger.warning("⚠️ Backup already exists. Creating new backup with timestamp...")
                backup_table = f"video_dates_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                cursor.execute(f"""
                    CREATE TABLE {backup_table} AS 
                    SELECT * FROM video_dates_backup
                """)
                cursor.execute("DELETE FROM video_dates_backup")
            
            # Backup current dates
            cursor.execute("""
                INSERT INTO video_dates_backup (video_id, original_published_at, original_youtube_published_at)
                SELECT video_id, published_at, youtube_published_at
                FROM video
            """)
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Backup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False
            
    def fetch_youtube_dates(self, video_ids: List[str], batch_size: int = 50) -> Dict[str, Optional[str]]:
        """Retrieve actual dates from YouTube API."""
        logger.info(f"📡 Fetching YouTube dates for {len(video_ids)} videos...")
        
        youtube_dates = {}
        try:
            youtube = YouTubeAPI()
        except ValueError as e:
            logger.error(f"❌ YouTube API client not available: {e}")
            return youtube_dates
            
        # Process in batches
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            
            try:
                video_data = youtube.get_videos_info(batch)
                
                for video_id, data in video_data.items():
                    if 'snippet' in data and 'publishedAt' in data['snippet']:
                        published_at = data['snippet']['publishedAt']
                        youtube_dates[video_id] = published_at
                    
                logger.info(f"✅ Fetched batch {i//batch_size + 1}: {len(video_data)} videos")
                
            except Exception as e:
                logger.error(f"❌ API error for batch {i//batch_size + 1}: {e}")
                self.api_failures += 1
                
        return youtube_dates
        
    def apply_corrections(self, dry_run: bool = True, competitor_id: Optional[int] = None) -> Dict[str, int]:
        """Update database with correct dates."""
        logger.info(f"🔧 Applying corrections (dry_run={dry_run})...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get videos to correct
        query = """
            SELECT v.id, v.video_id, v.published_at, v.youtube_published_at, c.name as competitor
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE DATE(v.published_at) IN ('2025-07-05', '2025-01-07')
        """
        
        params = []
        if competitor_id:
            query += " AND v.concurrent_id = ?"
            params.append(competitor_id)
            
        cursor.execute(query, params)
        videos_to_correct = cursor.fetchall()
        
        logger.info(f"📊 Found {len(videos_to_correct)} videos to correct")
        
        if not videos_to_correct:
            return {'corrected': 0, 'failed': 0}
            
        # Group by availability of youtube_published_at
        with_yt_date = [v for v in videos_to_correct if v['youtube_published_at']]
        without_yt_date = [v for v in videos_to_correct if not v['youtube_published_at']]
        
        corrections = {'corrected': 0, 'failed': 0}
        
        # 1. Correct videos that already have youtube_published_at
        if with_yt_date:
            logger.info(f"📝 Correcting {len(with_yt_date)} videos with existing YouTube dates...")
            
            if not dry_run:
                for video in with_yt_date:
                    cursor.execute("""
                        UPDATE video 
                        SET published_at = youtube_published_at
                        WHERE id = ?
                    """, (video['id'],))
                    corrections['corrected'] += 1
                    
        # 2. Fetch and correct videos without youtube_published_at
        if without_yt_date:
            logger.info(f"🌐 Fetching dates for {len(without_yt_date)} videos from YouTube API...")
            
            video_ids = [v['video_id'] for v in without_yt_date]
            youtube_dates = self.fetch_youtube_dates(video_ids)
            
            if not dry_run:
                for video in without_yt_date:
                    if video['video_id'] in youtube_dates:
                        yt_date = youtube_dates[video['video_id']]
                        cursor.execute("""
                            UPDATE video 
                            SET published_at = ?,
                                youtube_published_at = ?
                            WHERE id = ?
                        """, (yt_date, yt_date, video['id']))
                        corrections['corrected'] += 1
                    else:
                        corrections['failed'] += 1
                        
        if not dry_run:
            conn.commit()
            logger.info(f"✅ Corrections applied: {corrections['corrected']} successful, {corrections['failed']} failed")
        else:
            logger.info(f"🔍 Dry run complete: Would correct {len(with_yt_date) + len([v for v in without_yt_date if v['video_id'] in youtube_dates])} videos")
            
        conn.close()
        self.corrections_made = corrections['corrected']
        return corrections
        
    def generate_report(self) -> str:
        """Produce detailed correction report."""
        report_lines = [
            "📊 RAPPORT DE CORRECTION DES DATES",
            "=" * 40,
            f"Date du rapport : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "📈 RÉSUMÉ",
            "-" * 20
        ]
        
        # Summary stats
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video WHERE DATE(published_at) IN ('2025-07-05', '2025-01-07')")
        suspicious_count = cursor.fetchone()[0]
        
        report_lines.extend([
            f"Vidéos analysées : {total_videos}",
            f"Dates suspectes détectées : {suspicious_count}",
            f"Corrections appliquées : {self.corrections_made}",
            f"Échecs API : {self.api_failures}",
            "",
            "🔍 ANOMALIES DÉTECTÉES",
            "-" * 20
        ])
        
        # Anomaly details
        if self.suspicious_dates:
            # Mass identical dates
            if self.suspicious_dates['mass_identical_dates']:
                report_lines.append("\n📅 Dates identiques massives:")
                for anomaly in self.suspicious_dates['mass_identical_dates']:
                    report_lines.append(f"  - {anomaly['date']}: {anomaly['count']} vidéos")
                    
            # Import dates
            if self.suspicious_dates['import_dates']:
                report_lines.append("\n📥 Dates d'import détectées:")
                for anomaly in self.suspicious_dates['import_dates']:
                    report_lines.append(f"  - {anomaly['date']}: {anomaly['count']} vidéos")
                    report_lines.append(f"    Concurrents: {anomaly['competitors']}")
                    
            # Competitor uniformity
            if self.suspicious_dates['competitor_uniformity']:
                report_lines.append("\n🏢 Uniformité par concurrent:")
                for anomaly in self.suspicious_dates['competitor_uniformity']:
                    report_lines.append(f"  - {anomaly['competitor']}: {anomaly['total_videos']} vidéos, seulement {anomaly['distinct_dates']} dates distinctes")
                    
        # Sample corrections
        if self.corrections_made > 0:
            report_lines.extend([
                "",
                "✅ ÉCHANTILLON DE CORRECTIONS",
                "-" * 20
            ])
            
            cursor.execute("""
                SELECT v.title, c.name as competitor, 
                       b.original_published_at, v.published_at as new_published_at
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                JOIN video_dates_backup b ON v.video_id = b.video_id
                WHERE v.published_at != b.original_published_at
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                report_lines.append(f"\n📹 {row['title'][:50]}...")
                report_lines.append(f"   Concurrent: {row['competitor']}")
                report_lines.append(f"   Avant: {row['original_published_at']}")
                report_lines.append(f"   Après: {row['new_published_at']}")
                
        # Recommendations
        report_lines.extend([
            "",
            "💡 RECOMMANDATIONS",
            "-" * 20,
            "1. Vérifier les calculs de fréquence après correction",
            "2. Mettre à jour les analyses temporelles",
            "3. Auditer les scripts d'import pour éviter ce problème",
            "4. Implémenter une validation automatique des dates",
            "",
            "🔄 COMMANDE DE ROLLBACK",
            "-" * 20,
            "python youtube_date_correction_agent.py --rollback",
            ""
        ])
        
        conn.close()
        
        report = "\n".join(report_lines)
        
        # Save report to file
        report_filename = f"date_correction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
            
        logger.info(f"📄 Report saved to {report_filename}")
        
        return report
        
    def rollback(self) -> bool:
        """Restore original dates from backup."""
        logger.info("🔄 Starting rollback...")
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if backup exists
            cursor.execute("SELECT COUNT(*) FROM video_dates_backup")
            if cursor.fetchone()[0] == 0:
                logger.error("❌ No backup found!")
                return False
                
            # Restore dates
            cursor.execute("""
                UPDATE video
                SET published_at = (
                    SELECT original_published_at 
                    FROM video_dates_backup 
                    WHERE video_dates_backup.video_id = video.video_id
                ),
                youtube_published_at = (
                    SELECT original_youtube_published_at 
                    FROM video_dates_backup 
                    WHERE video_dates_backup.video_id = video.video_id
                )
                WHERE video_id IN (SELECT video_id FROM video_dates_backup)
            """)
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Rollback completed: {affected_rows} videos restored")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
            
    def validate_corrections(self, sample_size: int = 10) -> List[Dict]:
        """Validate a sample of corrections manually."""
        logger.info(f"🔍 Validating {sample_size} sample corrections...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get sample of corrected videos
        cursor.execute("""
            SELECT v.id, v.video_id, v.title, c.name as competitor,
                   b.original_published_at, v.published_at as corrected_date
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            JOIN video_dates_backup b ON v.video_id = b.video_id
            WHERE v.published_at != b.original_published_at
            ORDER BY RANDOM()
            LIMIT ?
        """, (sample_size,))
        
        validations = []
        for row in cursor.fetchall():
            validations.append({
                'video_id': row['video_id'],
                'title': row['title'],
                'competitor': row['competitor'],
                'original_date': row['original_published_at'],
                'corrected_date': row['corrected_date'],
                'youtube_url': f"https://www.youtube.com/watch?v={row['video_id']}"
            })
            
        conn.close()
        return validations


def main():
    """Command-line interface for the correction agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Date Correction Agent')
    parser.add_argument('--analyze', action='store_true', help='Detection only, no modifications')
    parser.add_argument('--fix', action='store_true', help='Apply corrections')
    parser.add_argument('--confirm', action='store_true', help='Confirm corrections (required with --fix)')
    parser.add_argument('--competitor-id', type=int, help='Target specific competitor')
    parser.add_argument('--rollback', action='store_true', help='Restore from backup')
    parser.add_argument('--validate', type=int, default=10, help='Number of samples to validate')
    
    args = parser.parse_args()
    
    agent = YouTubeDateCorrectionAgent()
    
    if args.rollback:
        if agent.rollback():
            print("✅ Rollback completed successfully")
        else:
            print("❌ Rollback failed")
        return
        
    # Always start with analysis
    print("🔍 Analyzing date anomalies...")
    anomalies = agent.detect_suspicious_dates()
    
    # Display anomalies
    print(f"\n📊 Found {sum(len(v) for v in anomalies.values())} anomalies")
    
    if args.analyze:
        # Analysis only mode
        report = agent.generate_report()
        print(report)
        return
        
    if args.fix:
        if not args.confirm:
            print("\n⚠️ Please add --confirm to apply corrections")
            print("This will modify the database. Make sure you understand the impact.")
            return
            
        # Create backup
        if not agent.backup_current_dates():
            print("❌ Backup failed, aborting corrections")
            return
            
        # Apply corrections
        print("\n🔧 Applying corrections...")
        results = agent.apply_corrections(dry_run=False, competitor_id=args.competitor_id)
        
        # Validate sample
        print(f"\n🔍 Validating {args.validate} sample corrections...")
        validations = agent.validate_corrections(args.validate)
        
        for val in validations[:3]:  # Show first 3
            print(f"\n📹 {val['title'][:50]}...")
            print(f"   Original: {val['original_date']}")
            print(f"   Corrected: {val['corrected_date']}")
            print(f"   YouTube: {val['youtube_url']}")
            
        # Generate report
        report = agent.generate_report()
        print(f"\n{report}")
        
    else:
        # Default: show what would be done
        print("\n💡 To apply corrections, use:")
        print("   python youtube_date_correction_agent.py --fix --confirm")
        print("\n💡 To analyze only, use:")
        print("   python youtube_date_correction_agent.py --analyze")


if __name__ == '__main__':
    main()