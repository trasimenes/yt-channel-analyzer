#!/usr/bin/env python3
"""
Fix all date-related issues in the YouTube Channel Analyzer application.
This script corrects code that uses import dates instead of YouTube publish dates.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict


class DateIssueFixer:
    """Fix date-related issues in the codebase."""
    
    def __init__(self, project_root: str = '.'):
        self.project_root = Path(project_root)
        self.fixes_applied = []
        
    def fix_all_date_issues(self) -> List[Dict[str, str]]:
        """Fix all date issues in the codebase."""
        print("🔧 Starting date issue fixes...")
        
        # 1. Fix brand_metrics_service.py
        self.fix_brand_metrics_service()
        
        # 2. Fix analytics.py
        self.fix_analytics_module()
        
        # 3. Fix any other modules with date issues
        self.fix_other_modules()
        
        print(f"\n✅ Fixed {len(self.fixes_applied)} date issues")
        return self.fixes_applied
    
    def fix_brand_metrics_service(self):
        """Fix date issues in brand_metrics_service.py"""
        file_path = self.project_root / 'services' / 'brand_metrics_service.py'
        
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            return
            
        print(f"📝 Fixing {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # Fix 1: Update the frequency calculation to use youtube_published_at
        # Replace the query in _calculate_video_frequency_metrics
        old_query = '''"""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                MIN(DATE(v.published_at)) as first_video_date,
                MAX(DATE(v.published_at)) as last_video_date
            FROM video v
            WHERE v.concurrent_id = ? AND v.published_at IS NOT NULL
        """, (competitor_id,))'''
        
        new_query = '''"""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_videos,
                MIN(DATE(COALESCE(v.youtube_published_at, v.published_at))) as first_video_date,
                MAX(DATE(COALESCE(v.youtube_published_at, v.published_at))) as last_video_date,
                COUNT(v.youtube_published_at) as youtube_dates_count
            FROM video v
            WHERE v.concurrent_id = ? 
              AND (v.youtube_published_at IS NOT NULL OR v.published_at IS NOT NULL)
        """, (competitor_id,))'''
        
        content = content.replace(old_query, new_query)
        
        # Fix 2: Update the date parsing logic to handle youtube dates
        old_parsing = '''if first_date and last_date:
            from datetime import datetime
            first_dt = datetime.strptime(first_date, '%Y-%m-%d')
            last_dt = datetime.strptime(last_date, '%Y-%m-%d')'''
            
        new_parsing = '''if first_date and last_date:
            from datetime import datetime
            # Handle both date formats (with or without time)
            try:
                # Try parsing as date only first
                first_dt = datetime.strptime(first_date, '%Y-%m-%d')
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
            except ValueError:
                # Try with full datetime format
                first_dt = datetime.fromisoformat(first_date.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_date.replace('Z', '+00:00'))'''
                
        content = content.replace(old_parsing, new_parsing)
        
        # Fix 3: Add check for youtube_dates_count
        old_freq_data = 'freq_data = self.cursor.fetchone()'
        new_freq_data = '''freq_data = self.cursor.fetchone()'''
        
        # Find and update the fetching logic
        if 'total_videos, first_date, last_date = freq_data' in content:
            content = content.replace(
                'total_videos, first_date, last_date = freq_data',
                'total_videos, first_date, last_date = freq_data[:3]\n        youtube_dates_count = freq_data[3] if len(freq_data) > 3 else 0'
            )
        
        # Fix 4: Add safety check for unreliable dates
        safety_check = '''
            # If no authentic YouTube dates and dates seem suspicious, don't calculate
            if youtube_dates_count == 0 and first_date == last_date:
                print(f"[BRAND_METRICS] ⚠️ {competitor_id}: Dates suspectes détectées - toutes identiques")
                return {
                    'total_videos': total_videos,
                    'videos_per_week': 0,  # Can't calculate reliably
                    'days_active': 0,
                    'consistency_score': 0
                }
        '''
        
        # Insert safety check after parsing dates
        if 'if first_date and last_date:' in content and safety_check not in content:
            # Find the right place to insert
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'youtube_dates_count = freq_data[3]' in line:
                    # Insert after this line
                    lines.insert(i + 1, safety_check)
                    content = '\n'.join(lines)
                    break
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.fixes_applied.append({
                'file': str(file_path),
                'changes': 'Updated frequency calculation to use youtube_published_at with COALESCE'
            })
            print(f"✅ Fixed brand_metrics_service.py")
        else:
            print(f"ℹ️ No changes needed in brand_metrics_service.py")
    
    def fix_analytics_module(self):
        """Fix date issues in analytics.py"""
        file_path = self.project_root / 'yt_channel_analyzer' / 'database' / 'analytics.py'
        
        if not file_path.exists():
            print(f"⚠️ File not found: {file_path}")
            return
            
        print(f"📝 Fixing {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # Fix 1: Update the base query to include youtube_published_at in SELECT
        old_select = '''SELECT 
                    c.name, c.id, v.published_at, v.category, v.view_count,
                    v.like_count, v.comment_count, v.duration_seconds, v.youtube_published_at
                FROM video v'''
                
        # The select already includes youtube_published_at, good!
        
        # Fix 2: Update WHERE clause to be more inclusive
        old_where = 'WHERE v.published_at IS NOT NULL'
        new_where = 'WHERE (v.youtube_published_at IS NOT NULL OR v.published_at IS NOT NULL)'
        
        content = content.replace(old_where, new_where)
        
        # Fix 3: Fix the date parsing in _analyze_frequency_data
        # The youtube_published_at is already at index 8, which is correct
        # But we need to ensure the date parsing handles both formats
        
        old_date_parse = '''if len(row) > 8 and row[8]:  # youtube_published_at existe à l'index 8
                    pub_date = datetime.fromisoformat(row[8].replace('Z', '+00:00'))
                else:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))'''
                    
        new_date_parse = '''if len(row) > 8 and row[8]:  # youtube_published_at existe à l'index 8
                    try:
                        pub_date = datetime.fromisoformat(row[8].replace('Z', '+00:00'))
                    except ValueError:
                        # Try parsing as date only
                        pub_date = datetime.strptime(row[8], '%Y-%m-%d')
                else:
                    try:
                        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    except ValueError:
                        # Try parsing as date only
                        pub_date = datetime.strptime(published_at, '%Y-%m-%d')'''
                        
        content = content.replace(old_date_parse, new_date_parse)
        
        # Fix 4: Update the timing analysis to use youtube_published_at
        old_timing = '''if video['published_at']:
                try:
                    pub_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))'''
                    
        new_timing = '''# Use youtube_published_at if available, fallback to published_at
                actual_date = video.get('youtube_published_at') or video.get('published_at')
                if actual_date:
                try:
                    pub_date = datetime.fromisoformat(actual_date.replace('Z', '+00:00'))'''
                    
        # This needs a more careful replacement
        # Let's fix the _analyze_optimal_timing method
        timing_pattern = r"if video\['published_at'\]:\s*try:\s*pub_date = datetime\.fromisoformat\(video\['published_at'\]\.replace\('Z', '\+00:00'\)\)"
        timing_replacement = """# Use youtube_published_at if available, fallback to published_at
            actual_date = video.get('youtube_published_at') or video.get('published_at')
            if actual_date:
                try:
                    pub_date = datetime.fromisoformat(actual_date.replace('Z', '+00:00'))"""
                    
        content = re.sub(timing_pattern, timing_replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.fixes_applied.append({
                'file': str(file_path),
                'changes': 'Updated frequency and timing analysis to prioritize youtube_published_at'
            })
            print(f"✅ Fixed analytics.py")
        else:
            print(f"ℹ️ No changes needed in analytics.py")
    
    def fix_other_modules(self):
        """Fix date issues in other modules."""
        # Add any other modules that need fixing here
        modules_to_check = [
            'blueprints/competitors.py',
            'blueprints/insights.py',
            'services/competitor_service.py'
        ]
        
        for module in modules_to_check:
            file_path = self.project_root / module
            if file_path.exists():
                self.check_and_fix_date_usage(file_path)
    
    def check_and_fix_date_usage(self, file_path: Path):
        """Check and fix date usage in a file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        changes_made = []
        
        # Pattern 1: Find queries using only published_at without youtube_published_at
        if 'published_at' in content and 'youtube_published_at' not in content:
            # Check if it's a database query
            if 'SELECT' in content or 'WHERE' in content:
                print(f"⚠️ {file_path} may need review - uses published_at without youtube_published_at")
                changes_made.append('Potential date issue - needs manual review')
        
        # Pattern 2: Replace common date calculation patterns
        patterns = [
            # MIN/MAX without COALESCE
            (r'MIN\s*\(\s*v\.published_at\s*\)', 'MIN(COALESCE(v.youtube_published_at, v.published_at))'),
            (r'MAX\s*\(\s*v\.published_at\s*\)', 'MAX(COALESCE(v.youtube_published_at, v.published_at))'),
            # Date calculations
            (r'DATE\s*\(\s*v\.published_at\s*\)', 'DATE(COALESCE(v.youtube_published_at, v.published_at))'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes_made.append(f'Updated pattern: {pattern}')
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.fixes_applied.append({
                'file': str(file_path),
                'changes': ', '.join(changes_made)
            })
            print(f"✅ Fixed {file_path.name}")
    
    def generate_report(self):
        """Generate a report of all fixes applied."""
        print("\n📊 DATE FIX REPORT")
        print("=" * 50)
        print(f"Total files modified: {len(self.fixes_applied)}")
        print()
        
        for fix in self.fixes_applied:
            print(f"📄 {fix['file']}")
            print(f"   Changes: {fix['changes']}")
            print()
        
        print("\n💡 NEXT STEPS:")
        print("1. Run the YouTube Date Correction Agent to fix existing data")
        print("2. Test the frequency calculations with the corrected code")
        print("3. Verify that all date-based metrics are now accurate")
        print("4. Update import scripts to use youtube_published_at correctly")


def main():
    """Main entry point."""
    print("🚀 YouTube Channel Analyzer - Date Issue Fixer")
    print("=" * 50)
    
    fixer = DateIssueFixer()
    fixer.fix_all_date_issues()
    fixer.generate_report()
    
    print("\n✅ Date issue fixes completed!")
    print("Run 'python youtube_date_correction_agent.py --analyze' to check data integrity")


if __name__ == '__main__':
    main()