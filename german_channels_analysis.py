#!/usr/bin/env python3
"""
Script d'analyse complète des chaînes allemandes
- Corrige l'incohérence paid/organic threshold  
- Recalcule toutes les métriques brand/country
- Stocke les résultats en base de données
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

def create_analysis_tables(conn):
    """Create tables to store analysis results"""
    cursor = conn.cursor()
    
    # Table pour les statistiques par concurrent
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitor_analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER NOT NULL,
            competitor_name TEXT NOT NULL,
            country TEXT NOT NULL,
            analysis_date TEXT NOT NULL,
            paid_threshold INTEGER NOT NULL,
            total_videos INTEGER,
            organic_count INTEGER,
            paid_count INTEGER,
            organic_percentage REAL,
            paid_percentage REAL,
            avg_duration_minutes REAL,
            videos_per_week REAL,
            hero_count INTEGER,
            hub_count INTEGER,
            help_count INTEGER,
            categorized_videos INTEGER,
            thumbnail_consistency_score REAL,
            dominant_tone TEXT,
            shorts_count INTEGER,
            shorts_percentage REAL,
            raw_metrics TEXT,  -- JSON dump of all metrics
            FOREIGN KEY (competitor_id) REFERENCES concurrent(id)
        )
    """)
    
    # Table pour les statistiques par pays
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS country_analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            analysis_date TEXT NOT NULL,
            paid_threshold INTEGER NOT NULL,
            total_competitors INTEGER,
            total_videos INTEGER,
            organic_count INTEGER,
            paid_count INTEGER,
            organic_percentage REAL,
            paid_percentage REAL,
            avg_duration_minutes REAL,
            videos_per_week REAL,
            categorized_videos INTEGER,
            raw_metrics TEXT  -- JSON dump of all metrics
        )
    """)
    
    conn.commit()
    print("✅ Tables d'analyse créées/vérifiées")

def analyze_german_competitors(conn, settings):
    """Analyze all German competitors"""
    cursor = conn.cursor()
    paid_threshold = settings.get('paid_threshold', 10000)
    
    # Get all German competitors
    cursor.execute("""
        SELECT id, name, country 
        FROM concurrent 
        WHERE country = 'Germany' 
        ORDER BY name
    """)
    german_competitors = cursor.fetchall()
    
    print(f"🇩🇪 Analyse de {len(german_competitors)} chaînes allemandes...")
    print(f"💰 Seuil paid/organic: {paid_threshold:,} vues")
    
    brand_service = BrandMetricsService(conn, paid_threshold)
    results = []
    
    for competitor_id, name, country in german_competitors:
        print(f"\n📊 Analyse de {name} (ID: {competitor_id})...")
        
        try:
            # Calculate brand metrics
            metrics = brand_service.calculate_brand_metrics(competitor_id)
            
            # Extract key metrics for storage
            video_length = metrics.get('video_length', {})
            video_frequency = metrics.get('video_frequency', {})
            organic_vs_paid = metrics.get('organic_vs_paid', {})
            hub_help_hero = metrics.get('hub_help_hero', {})
            thumbnail_consistency = metrics.get('thumbnail_consistency', {})
            tone_of_voice = metrics.get('tone_of_voice', {})
            shorts_distribution = metrics.get('shorts_distribution', {})
            
            # Store in database
            cursor.execute("""
                INSERT INTO competitor_analysis_results (
                    competitor_id, competitor_name, country, analysis_date, paid_threshold,
                    total_videos, organic_count, paid_count, organic_percentage, paid_percentage,
                    avg_duration_minutes, videos_per_week, hero_count, hub_count, help_count,
                    categorized_videos, thumbnail_consistency_score, dominant_tone,
                    shorts_count, shorts_percentage, raw_metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                competitor_id, name, country, datetime.now().isoformat(), paid_threshold,
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
                json.dumps(metrics)
            ))
            
            results.append({
                'name': name,
                'id': competitor_id,
                'organic_pct': organic_vs_paid.get('organic_percentage', 0),
                'paid_pct': organic_vs_paid.get('paid_percentage', 0),
                'total_videos': video_length.get('total_videos', 0)
            })
            
            print(f"   ✅ {organic_vs_paid.get('organic_percentage', 0):.1f}% organique, {organic_vs_paid.get('paid_percentage', 0):.1f}% payé ({video_length.get('total_videos', 0)} vidéos)")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            continue
    
    conn.commit()
    return results

def analyze_germany_country_metrics(conn, settings):
    """Analyze Germany as a country"""
    print(f"\n🏛️ Analyse des métriques pays pour l'Allemagne...")
    
    paid_threshold = settings.get('paid_threshold', 10000)
    country_service = CountryMetricsService(conn, paid_threshold)
    
    try:
        metrics = country_service.calculate_country_7_metrics('Germany')
        
        cursor = conn.cursor()
        
        # Count competitors
        cursor.execute("SELECT COUNT(*) FROM concurrent WHERE country = 'Germany'")
        total_competitors = cursor.fetchone()[0]
        
        # Extract key metrics
        video_length = metrics.get('video_length', {})
        video_frequency = metrics.get('video_frequency', {})
        organic_vs_paid = metrics.get('organic_vs_paid', {})
        hub_help_hero = metrics.get('hub_help_hero', {})
        
        # Store country results
        cursor.execute("""
            INSERT INTO country_analysis_results (
                country, analysis_date, paid_threshold, total_competitors,
                total_videos, organic_count, paid_count, organic_percentage, paid_percentage,
                avg_duration_minutes, videos_per_week, categorized_videos, raw_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'Germany', datetime.now().isoformat(), paid_threshold, total_competitors,
            video_length.get('total_videos', 0),
            organic_vs_paid.get('organic_count', 0),
            organic_vs_paid.get('paid_count', 0),
            organic_vs_paid.get('organic_percentage', 0),
            organic_vs_paid.get('paid_percentage', 0),
            video_length.get('avg_duration_minutes', 0),
            video_frequency.get('videos_per_week', 0),
            hub_help_hero.get('categorized_videos', 0),
            json.dumps(metrics)
        ))
        
        conn.commit()
        
        print(f"   ✅ Allemagne: {organic_vs_paid.get('organic_percentage', 0):.1f}% organique, {organic_vs_paid.get('paid_percentage', 0):.1f}% payé")
        print(f"   📊 {total_competitors} chaînes, {video_length.get('total_videos', 0)} vidéos total")
        
        return metrics
        
    except Exception as e:
        print(f"   ❌ Erreur analyse pays: {e}")
        return None

def print_summary(competitor_results, country_metrics):
    """Print analysis summary"""
    print(f"\n" + "="*80)
    print(f"📋 RÉSUMÉ DE L'ANALYSE ALLEMAGNE")
    print(f"="*80)
    
    if competitor_results:
        print(f"\n🏢 RÉSULTATS PAR CHAÎNE:")
        for result in sorted(competitor_results, key=lambda x: x['paid_pct'], reverse=True):
            print(f"   {result['name']:30} | {result['paid_pct']:5.1f}% paid | {result['total_videos']:4d} vidéos")
    
    if country_metrics:
        organic_pct = country_metrics.get('organic_vs_paid', {}).get('organic_percentage', 0)
        paid_pct = country_metrics.get('organic_vs_paid', {}).get('paid_percentage', 0)
        total_videos = country_metrics.get('video_length', {}).get('total_videos', 0)
        
        print(f"\n🇩🇪 RÉSULTAT PAYS ALLEMAGNE:")
        print(f"   Organique: {organic_pct:.1f}% | Payé: {paid_pct:.1f}% | Total: {total_videos} vidéos")
    
    print(f"\n✅ Analyse terminée et stockée en base de données")
    print(f"💾 Tables: competitor_analysis_results, country_analysis_results")

def main():
    """Main analysis script"""
    print("🚀 ANALYSE COMPLÈTE DES CHAÎNES ALLEMANDES")
    print("="*60)
    
    # Load settings
    settings = load_settings()
    print(f"⚙️ Seuil paid/organic: {settings.get('paid_threshold', 10000):,} vues")
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # Create analysis tables
        create_analysis_tables(conn)
        
        # Analyze German competitors
        competitor_results = analyze_german_competitors(conn, settings)
        
        # Analyze Germany as country
        country_metrics = analyze_germany_country_metrics(conn, settings)
        
        # Print summary
        print_summary(competitor_results, country_metrics)
        
    except Exception as e:
        print(f"❌ Erreur durant l'analyse: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()