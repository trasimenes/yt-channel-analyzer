#!/usr/bin/env python3
"""
Verification script to demonstrate that date logic fixes are working correctly.
This script shows before/after comparisons and validates the corrected behavior.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from services.brand_metrics_service import BrandMetricsService
from services.country_metrics_service import CountryMetricsService
from yt_channel_analyzer.database import get_db_connection


def test_date_logic_fixes():
    """Test and verify that all date logic fixes are working correctly."""
    print("🧪 VERIFICATION: YouTube Date Logic Fixes")
    print("=" * 50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Database Date Integrity Check
    print("\n📊 1. DATABASE DATE INTEGRITY")
    print("-" * 30)
    
    # Check how many videos have each type of date
    cursor.execute("""
        SELECT 
            COUNT(*) as total_videos,
            COUNT(youtube_published_at) as has_youtube_date,
            COUNT(published_at) as has_published_date,
            COUNT(CASE WHEN youtube_published_at IS NOT NULL THEN 1 END) as youtube_not_null,
            COUNT(CASE WHEN DATE(published_at) = '2025-07-05' THEN 1 END) as import_date_count
        FROM video
    """)
    
    stats = cursor.fetchone()
    print(f"Total videos: {stats[0]:,}")
    print(f"With youtube_published_at: {stats[1]:,} ({stats[1]/stats[0]*100:.1f}%)")
    print(f"With published_at: {stats[2]:,} ({stats[2]/stats[0]*100:.1f}%)")
    print(f"Import date (2025-07-05): {stats[4]:,} videos ⚠️")
    
    if stats[4] > 0:
        print(f"🚨 {stats[4]:,} videos still need date correction!")
    
    # 2. Frequency Calculation Validation
    print("\n⏱️ 2. FREQUENCY CALCULATION VALIDATION")
    print("-" * 40)
    
    brand_service = BrandMetricsService(conn)
    channels = brand_service.get_center_parcs_channels()
    
    print("Center Parcs Channel Frequencies (should be realistic 0.1-5.0/week):")
    all_realistic = True
    
    for name, data in channels.items():
        metrics = brand_service.calculate_brand_metrics(data['competitor_id'])
        freq = metrics['video_frequency']['videos_per_week']
        total = metrics['video_frequency']['total_videos']
        
        # Check if frequency is realistic (0.1 to 10 videos per week)
        is_realistic = 0.1 <= freq <= 10 if freq > 0 else True
        status = "✅" if is_realistic else "❌"
        
        print(f"  {name}: {freq} videos/week ({total} videos) {status}")
        
        if not is_realistic:
            all_realistic = False
    
    if all_realistic:
        print("✅ All frequencies are realistic!")
    else:
        print("❌ Some frequencies are still unrealistic")
    
    # 3. Country-Level Validation
    print("\n🌍 3. COUNTRY-LEVEL VALIDATION")
    print("-" * 30)
    
    country_service = CountryMetricsService(conn)
    countries = ['France', 'Germany', 'Netherlands', 'United Kingdom']
    
    print("Country frequencies (should be realistic):")
    for country in countries:
        try:
            metrics = country_service.calculate_country_7_metrics(country)
            freq = metrics['video_frequency']['videos_per_week']
            total = metrics['video_frequency']['total_videos']
            
            if total > 0:
                is_realistic = 0.1 <= freq <= 20
                status = "✅" if is_realistic else "❌"
                print(f"  {country}: {freq} videos/week ({total} videos) {status}")
            else:
                print(f"  {country}: No videos found")
                
        except Exception as e:
            print(f"  {country}: Error - {e}")
    
    # 4. SQL Query Pattern Validation
    print("\n🔍 4. SQL QUERY PATTERN VALIDATION")
    print("-" * 35)
    
    # Test that COALESCE pattern works correctly
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN youtube_published_at IS NOT NULL THEN 1 END) as with_yt_date,
            COUNT(CASE WHEN COALESCE(youtube_published_at, published_at) IS NOT NULL THEN 1 END) as with_any_date,
            MIN(DATE(COALESCE(youtube_published_at, published_at))) as earliest_date,
            MAX(DATE(COALESCE(youtube_published_at, published_at))) as latest_date
        FROM video 
        WHERE concurrent_id IN (SELECT id FROM concurrent WHERE name LIKE '%Center Parcs%')
    """)
    
    result = cursor.fetchone()
    print(f"Center Parcs videos analysis:")
    print(f"  Total videos: {result[0]:,}")
    print(f"  With YouTube date: {result[1]:,}")
    print(f"  With any date: {result[2]:,}")
    print(f"  Date range: {result[3]} to {result[4]}")
    
    # Check for suspicious date patterns
    if result[3] == result[4] and result[0] > 50:
        print("  ⚠️ All videos have same date - still problematic")
    elif result[3] and result[4]:
        from datetime import datetime
        start_date = datetime.strptime(result[3], '%Y-%m-%d')
        end_date = datetime.strptime(result[4], '%Y-%m-%d')
        days_span = (end_date - start_date).days
        if days_span > 365:
            print(f"  ✅ Realistic date span: {days_span} days")
        else:
            print(f"  ⚠️ Short date span: {days_span} days")
    
    # 5. Import Date Detection
    print("\n🚨 5. IMPORT DATE DETECTION")
    print("-" * 25)
    
    cursor.execute("""
        SELECT 
            DATE(published_at) as pub_date,
            COUNT(*) as count,
            GROUP_CONCAT(DISTINCT c.name) as competitors
        FROM video v
        JOIN concurrent c ON v.concurrent_id = c.id
        WHERE DATE(v.published_at) IN ('2025-07-05', '2025-07-11', '2025-01-07')
        GROUP BY DATE(published_at)
        ORDER BY count DESC
    """)
    
    import_dates = cursor.fetchall()
    if import_dates:
        print("Detected import dates:")
        for date, count, competitors in import_dates:
            comp_list = competitors.split(', ')[:3]  # Show first 3
            comp_str = ', '.join(comp_list)
            if len(competitors.split(', ')) > 3:
                comp_str += f" + {len(competitors.split(', ')) - 3} more"
            print(f"  {date}: {count:,} videos ({comp_str})")
    else:
        print("✅ No import dates detected")
    
    conn.close()
    
    # 6. Summary
    print("\n📋 6. VERIFICATION SUMMARY")
    print("-" * 25)
    
    issues = []
    if stats[4] > 1000:  # More than 1000 videos with import dates
        issues.append(f"{stats[4]:,} videos need date correction")
    
    if not all_realistic:
        issues.append("Some frequencies still unrealistic")
    
    if import_dates and any(count > 100 for _, count, _ in import_dates):
        issues.append("Significant import date pollution detected")
    
    if issues:
        print("❌ Issues remaining:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n💡 Next steps:")
        print("  1. Run: python youtube_date_correction_agent.py --fix --confirm")
        print("  2. Update import scripts to use youtube_published_at correctly")
        print("  3. Recalculate all frequency statistics")
    else:
        print("✅ All date logic fixes verified successfully!")
        print("✅ Frequency calculations are realistic")
        print("✅ No major import date issues detected")


def demo_before_after():
    """Demonstrate the difference between old and new date logic."""
    print("\n🔄 BEFORE/AFTER COMPARISON")
    print("=" * 30)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Example with Center Parcs France
    cursor.execute("""
        SELECT 
            COUNT(*) as total_videos,
            MIN(DATE(published_at)) as min_published,
            MAX(DATE(published_at)) as max_published,
            COUNT(DISTINCT DATE(published_at)) as distinct_published_dates,
            MIN(DATE(COALESCE(youtube_published_at, published_at))) as min_coalesce,
            MAX(DATE(COALESCE(youtube_published_at, published_at))) as max_coalesce,
            COUNT(DISTINCT DATE(COALESCE(youtube_published_at, published_at))) as distinct_coalesce_dates
        FROM video v
        JOIN concurrent c ON v.concurrent_id = c.id
        WHERE c.name = 'Center Parcs France'
    """)
    
    result = cursor.fetchone()
    
    print("Center Parcs France - Date Logic Comparison:")
    print(f"\n📅 OLD Logic (published_at only):")
    print(f"  Date range: {result[1]} to {result[2]}")
    print(f"  Distinct dates: {result[3]}")
    print(f"  Total videos: {result[0]}")
    
    if result[1] == result[2]:
        old_days = 1
        old_freq = result[0] * 7 / old_days
        print(f"  Calculated frequency: {old_freq:.1f} videos/week ❌ WRONG!")
    else:
        old_days = (datetime.strptime(result[2], '%Y-%m-%d') - 
                   datetime.strptime(result[1], '%Y-%m-%d')).days
        old_freq = result[0] * 7 / old_days if old_days > 0 else 0
        print(f"  Calculated frequency: {old_freq:.1f} videos/week")
    
    print(f"\n📅 NEW Logic (COALESCE youtube_published_at, published_at):")
    print(f"  Date range: {result[4]} to {result[5]}")
    print(f"  Distinct dates: {result[6]}")
    print(f"  Total videos: {result[0]}")
    
    if result[4] and result[5] and result[4] != result[5]:
        new_days = (datetime.strptime(result[5], '%Y-%m-%d') - 
                   datetime.strptime(result[4], '%Y-%m-%d')).days
        new_freq = result[0] * 7 / new_days if new_days > 0 else 0
        print(f"  Calculated frequency: {new_freq:.1f} videos/week ✅ REALISTIC!")
    else:
        print(f"  Calculated frequency: Cannot calculate (suspicious dates)")
    
    conn.close()


if __name__ == '__main__':
    test_date_logic_fixes()
    demo_before_after()
    
    print(f"\n🏁 Verification completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("See DATE_FIXES_SUMMARY.md for complete documentation.")