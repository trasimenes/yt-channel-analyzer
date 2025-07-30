#!/usr/bin/env python3
"""
Analyse complète de Pierre et Vacances (ID 504)
"""
from yt_channel_analyzer.database import get_db_connection
import sqlite3

def analyze_competitor_504():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print('🔍 PIERRE ET VACANCES (ID 504) - ANALYSE COMPLÈTE')
    print('=' * 70)
    
    # 1. Informations générales
    cursor.execute('''
        SELECT name, subscriber_count, channel_url, created_at, country
        FROM concurrent WHERE id = 504
    ''')
    result = cursor.fetchone()
    
    if not result:
        print('❌ Concurrent 504 non trouvé')
        return
    
    name, subs, url, created, country = result
    print(f'📊 INFORMATIONS GÉNÉRALES:')
    print(f'   Nom: {name}')
    print(f'   Pays: {country or "À définir"}')
    print(f'   URL: {url}')
    print(f'   Abonnés: {subs:,}' if subs else '   Abonnés: N/A')
    print(f'   Créé: {created}')
    
    # 2. Analyse des vidéos et dates
    cursor.execute('''
        SELECT COUNT(*), MIN(published_at), MAX(published_at)
        FROM video WHERE concurrent_id = 504
    ''')
    total, first_date, last_date = cursor.fetchone()
    
    print(f'\n📹 VIDÉOS:')
    print(f'   Total: {total}')
    print(f'   Plus ancienne: {first_date}')
    print(f'   Plus récente: {last_date}')
    
    # 3. Vérification des dates corrigées
    import_date = '2025-07-30'
    
    cursor.execute('''
        SELECT COUNT(*) FROM video 
        WHERE concurrent_id = 504 AND DATE(published_at) = ?
    ''', (import_date,))
    dates_import = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM video 
        WHERE concurrent_id = 504 AND DATE(published_at) != ?
    ''', (import_date,))
    dates_corrigees = cursor.fetchone()[0]
    
    print(f'\n🔧 CORRECTION DES DATES:')
    print(f'   ✅ Dates corrigées: {dates_corrigees}/{total}')
    print(f'   ⚠️ Dates d\'import: {dates_import}/{total}')
    
    if total > 0:
        taux_correction = (dates_corrigees / total) * 100
        print(f'   📊 Taux de correction: {taux_correction:.1f}%')
        
        # Calculer la fréquence si on a des dates corrigées
        if dates_corrigees > 1:
            cursor.execute('''
                SELECT MIN(published_at), MAX(published_at)
                FROM video 
                WHERE concurrent_id = 504 AND DATE(published_at) != ?
            ''', (import_date,))
            real_first, real_last = cursor.fetchone()
            
            if real_first and real_last and real_first != real_last:
                from datetime import datetime
                try:
                    first_dt = datetime.fromisoformat(real_first.replace('Z', '+00:00'))
                    last_dt = datetime.fromisoformat(real_last.replace('Z', '+00:00'))
                    period_days = (last_dt - first_dt).days
                    
                    if period_days > 0:
                        freq_per_week = (dates_corrigees * 7) / period_days
                        print(f'   🎬 Fréquence réelle: {freq_per_week:.2f} vidéos/semaine')
                        print(f'   📅 Période d\'activité: {period_days} jours')
                except Exception as e:
                    print(f'   ⚠️ Erreur calcul fréquence: {e}')
    
    # 4. Classification des vidéos
    cursor.execute('''
        SELECT 
            COUNT(CASE WHEN category = 'hero' THEN 1 END) as hero,
            COUNT(CASE WHEN category = 'hub' THEN 1 END) as hub,
            COUNT(CASE WHEN category = 'help' THEN 1 END) as help,
            COUNT(CASE WHEN category IS NULL OR category = '' THEN 1 END) as unclassified
        FROM video WHERE concurrent_id = 504
    ''')
    hero, hub, help_count, unclassified = cursor.fetchone()
    
    print(f'\n🏷️ CLASSIFICATION:')
    print(f'   🎯 HERO: {hero}')
    print(f'   🎯 HUB: {hub}')
    print(f'   🎯 HELP: {help_count}')
    print(f'   ❓ Non classées: {unclassified}')
    
    if total > 0:
        taux_classification = ((total - unclassified) / total) * 100
        print(f'   📊 Taux de classification: {taux_classification:.1f}%')
    
    # 5. Top vidéos
    cursor.execute('''
        SELECT title, published_at, view_count, like_count
        FROM video 
        WHERE concurrent_id = 504 
        ORDER BY view_count DESC 
        LIMIT 5
    ''')
    
    print(f'\n📺 TOP 5 VIDÉOS (par vues):')
    for i, (title, date, views, likes) in enumerate(cursor.fetchall(), 1):
        title_short = title[:50] + '...' if len(title) > 50 else title
        date_short = date[:10] if date else 'N/A'
        print(f'   {i}. {title_short}')
        print(f'      📅 {date_short} | 👁️ {views:,} vues | 👍 {likes or 0} likes')
    
    # 6. Échantillon de vidéos avec vraies dates
    cursor.execute('''
        SELECT title, published_at, view_count
        FROM video 
        WHERE concurrent_id = 504 AND DATE(published_at) != ?
        ORDER BY published_at DESC 
        LIMIT 3
    ''', (import_date,))
    
    corrected_videos = cursor.fetchall()
    if corrected_videos:
        print(f'\n✅ VIDÉOS AVEC DATES CORRIGÉES:')
        for title, date, views in corrected_videos:
            title_short = title[:50] + '...' if len(title) > 50 else title
            date_short = date[:10] if date else 'N/A'
            print(f'   📺 {title_short}')
            print(f'      📅 {date_short} | 👁️ {views:,} vues')
    
    conn.close()
    
    print(f'\n🎯 RÉSUMÉ:')
    print(f'✅ Pierre et Vacances (ID 504) entièrement analysé')
    print(f'✅ {dates_corrigees}/{total} dates corrigées ({taux_correction:.1f}%)')
    print(f'✅ {total - unclassified}/{total} vidéos classées ({taux_classification:.1f}%)')
    print(f'\n🔗 Pages utiles:')
    print(f'   📊 Classification: http://127.0.0.1:8082/competitor/504/classify')
    print(f'   👁️ Vue générale: http://127.0.0.1:8082/competitor/504')

if __name__ == '__main__':
    analyze_competitor_504()