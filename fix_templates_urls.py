#!/usr/bin/env python3
"""
Script pour corriger les références url_for dans les templates
Suite à la migration vers l'architecture blueprint
"""
import os
import re
from pathlib import Path

# Mapping des anciennes routes vers les nouvelles avec blueprint
URL_MAPPING = {
    # Auth blueprint
    "'login'": "'auth.login'",
    '"login"': '"auth.login"',
    "'logout'": "'auth.logout'",
    '"logout"': '"auth.logout"',
    "'profile'": "'auth.profile'",
    '"profile"': '"auth.profile"',
    "'profile_security'": "'auth.profile_security'",
    '"profile_security"': '"auth.profile_security"',
    "'update-password'": "'auth.update-password'",
    '"update-password"': '"auth.update-password"',
    "'toggle-dev-mode'": "'auth.toggle-dev-mode'",
    '"toggle-dev-mode"': '"auth.toggle-dev-mode"',
    "'toggle-performance-mode'": "'auth.toggle-performance-mode'",
    '"toggle-performance-mode"': '"auth.toggle-performance-mode"',
    
    # Main blueprint
    "'home'": "'main.home'",
    '"home"': '"main.home"',
    "'home_old'": "'main.home_old'",
    '"home_old"': '"main.home_old"',
    "'dashboard-glass'": "'main.dashboard-glass'",
    '"dashboard-glass"': '"main.dashboard-glass"',
    "'fresh'": "'main.fresh'",
    '"fresh"': '"main.fresh"',
    "'tasks_page'": "'main.tasks_page'",
    '"tasks_page"': '"main.tasks_page"',
    "'performance-dashboard'": "'main.performance-dashboard'",
    '"performance-dashboard"': '"main.performance-dashboard"',
    
    # API blueprint
    "'performance-metrics'": "'api.performance-metrics'",
    '"performance-metrics"': '"api.performance-metrics"',
    "'clear_cache'": "'api.clear_cache'",
    '"clear_cache"': '"api.clear_cache"',
    "'optimize_database'": "'api.optimize_database'",
    '"optimize_database"': '"api.optimize_database"',
    "'preload_caches'": "'api.preload_caches'",
    '"preload_caches"': '"api.preload_caches"',
    "'export_performance_metrics'": "'api.export_performance_metrics'",
    '"export_performance_metrics"': '"api.export_performance_metrics"',
    "'recalculate-organic-status'": "'api.recalculate-organic-status'",
    '"recalculate-organic-status"': '"api.recalculate-organic-status"',
    "'get_tasks_status'": "'api.get_tasks_status'",
    '"get_tasks_status"': '"api.get_tasks_status"',
    "'get_tasks'": "'api.get_tasks'",
    '"get_tasks"': '"api.get_tasks"',
    "'delete_task'": "'api.delete_task'",
    '"delete_task"': '"api.delete_task"',
    "'cancel_task'": "'api.cancel_task'",
    '"cancel_task"': '"api.cancel_task"',
    "'resume_task'": "'api.resume_task'",
    '"resume_task"': '"api.resume_task"',
    "'clean_duplicate_tasks'": "'api.clean_duplicate_tasks'",
    '"clean_duplicate_tasks"': '"api.clean_duplicate_tasks"',
    "'migrate_tasks_to_database'": "'api.migrate_tasks_to_database'",
    '"migrate_tasks_to_database"': '"api.migrate_tasks_to_database"',
    "'launch-background-task'": "'api.launch-background-task'",
    '"launch-background-task"': '"api.launch-background-task"',
    
    # Competitors blueprint
    "'concurrents'": "'competitors.concurrents'",
    '"concurrents"': '"competitors.concurrents"',
    "'competitor_detail'": "'competitors.competitor_detail'",
    '"competitor_detail"': '"competitors.competitor_detail"',
    "'delete_competitor'": "'competitors.delete_competitor'",
    '"delete_competitor"': '"competitors.delete_competitor"',
    "'top-videos'": "'competitors.top-videos'",
    '"top-videos"': '"competitors.top-videos"',
    "'top-playlists'": "'competitors.top-playlists'",
    '"top-playlists"': '"competitors.top-playlists"',
    
    # Insights blueprint
    "'insights'": "'insights.insights'",
    '"insights"': '"insights.insights"',
    "'country-insights'": "'insights.country-insights'",
    '"country-insights"': '"insights.country-insights"',
    "'countries-analysis'": "'insights.countries-analysis'",
    '"countries-analysis"': '"insights.countries-analysis"',
    "'top-topics'": "'insights.top-topics'",
    '"top-topics"': '"insights.top-topics"',
    "'sentiment-analysis'": "'insights.sentiment-analysis'",
    '"sentiment-analysis"': '"insights.sentiment-analysis"',
    
    # Admin blueprint
    "'settings'": "'admin.settings'",
    '"settings"': '"admin.settings"',
    "'save-settings'": "'admin.save-settings'",
    '"save-settings"': '"admin.save-settings"',
    "'fix-problems'": "'admin.fix-problems'",
    '"fix-problems"': '"admin.fix-problems"',
    "'fix_problem'": "'admin.fix_problem'",
    '"fix_problem"': '"admin.fix_problem"',
    "'api-usage'": "'admin.api-usage'",
    '"api-usage"': '"admin.api-usage"',
    "'data-export'": "'admin.data-export'",
    '"data-export"': '"admin.data-export"',
    "'export_data'": "'admin.export_data'",
    '"export_data"': '"admin.export_data"',
    "'database-maintenance'": "'admin.database-maintenance'",
    '"database-maintenance"': '"admin.database-maintenance"',
    "'database_action'": "'admin.database_action'",
    '"database_action"': '"admin.database_action"',
    "'system-info'": "'admin.system-info'",
    '"system-info"': '"admin.system-info"',
    "'reset-api-quota'": "'admin.reset-api-quota'",
    '"reset-api-quota"': '"admin.reset-api-quota"',
}

def fix_url_for_in_file(filepath):
    """Corriger les url_for dans un fichier template"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Chercher tous les url_for dans le fichier
        url_for_pattern = r"url_for\((['\"][^'\"]+['\"])"
        
        for match in re.finditer(url_for_pattern, content):
            old_route = match.group(1)
            
            # Vérifier si c'est une route à convertir
            if old_route in URL_MAPPING:
                new_route = URL_MAPPING[old_route]
                old_full = f"url_for({old_route}"
                new_full = f"url_for({new_route}"
                
                if old_full in content:
                    content = content.replace(old_full, new_full)
                    changes_made.append(f"{old_route} → {new_route}")
        
        # Corriger aussi les références request.endpoint
        endpoint_mappings = {
            "== 'home'": "== 'main.home'",
            "== 'concurrents'": "== 'competitors.concurrents'",
            "== 'learn'": "== 'insights.insights'",  # ou autre mapping approprié
            "== 'insights'": "== 'insights.insights'",
            "== 'settings'": "== 'admin.settings'",
            "== 'fix-problems'": "== 'admin.fix-problems'",
            "== 'api-usage'": "== 'admin.api-usage'",
            "== 'top_videos'": "== 'competitors.top-videos'",
            "== 'top_playlists'": "== 'competitors.top-playlists'",
            "== 'sentiment_analysis'": "== 'insights.sentiment-analysis'",
            "== 'top_topics'": "== 'insights.top-topics'",
            "== 'countries_analysis'": "== 'insights.countries-analysis'",
            "== 'frequency_dashboard'": "== 'main.performance-dashboard'",  
            "== 'country_insights'": "== 'insights.country-insights'",
            "== 'tasks'": "== 'main.tasks_page'",
            "== 'business'": "== 'admin.settings'",  
            "== 'api_usage_page'": "== 'admin.api-usage'",
            "== 'data'": "== 'admin.data-export'",
            "== 'fix_problems'": "== 'admin.fix-problems'",
        }
        
        for old_check, new_check in endpoint_mappings.items():
            if old_check in content:
                content = content.replace(old_check, new_check)
                changes_made.append(f"endpoint {old_check} → {new_check}")
        
        # Sauvegarder si des changements ont été faits
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes_made
        
        return False, []
        
    except Exception as e:
        print(f"❌ Erreur sur {filepath}: {e}")
        return False, []

def main():
    """Corriger tous les templates"""
    print("🔧 Correction des références url_for dans les templates...")
    print("="*60)
    
    templates_dir = Path('templates')
    
    if not templates_dir.exists():
        print("❌ Dossier templates non trouvé")
        return
    
    total_files = 0
    modified_files = 0
    total_changes = 0
    
    # Parcourir tous les fichiers HTML
    for template_file in templates_dir.rglob('*.html'):
        total_files += 1
        modified, changes = fix_url_for_in_file(template_file)
        
        if modified:
            modified_files += 1
            total_changes += len(changes)
            print(f"✅ {template_file.relative_to(templates_dir)}: {len(changes)} changements")
            for change in changes[:5]:  # Afficher max 5 changements par fichier
                print(f"   - {change}")
            if len(changes) > 5:
                print(f"   ... et {len(changes) - 5} autres")
    
    print("="*60)
    print(f"📊 Résumé:")
    print(f"   - Fichiers analysés: {total_files}")
    print(f"   - Fichiers modifiés: {modified_files}")
    print(f"   - Total de changements: {total_changes}")
    print("="*60)

if __name__ == "__main__":
    main()