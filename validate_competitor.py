#!/usr/bin/env python3
"""
Script de validation rapide d'un competitor spécifique
======================================================

Usage: python validate_competitor.py [competitor_id]
"""

import sys
from key_metrics_validator import KeyMetricsValidator, ValidationStatus


def validate_single_competitor(competitor_id: int):
    """Valide un competitor spécifique et affiche les résultats."""
    
    validator = KeyMetricsValidator()
    
    try:
        report = validator.validate_competitor(competitor_id)
        
        # Affichage coloré du résultat
        status_colors = {
            ValidationStatus.EXCELLENT: "🟢",
            ValidationStatus.GOOD: "🟡",
            ValidationStatus.WARNING: "🟠", 
            ValidationStatus.CRITICAL: "🔴",
            ValidationStatus.INSUFFICIENT_DATA: "⚪"
        }
        
        color = status_colors.get(report.overall_status, "❓")
        powerpoint_status = "✅ Prêt" if report.powerpoint_ready else "❌ Pas prêt"
        
        print(f"🎯 VALIDATION COMPETITOR {competitor_id}")
        print("=" * 60)
        print(f"{color} {report.competitor_name} ({report.country})")
        print(f"📊 {report.total_videos} vidéos | {powerpoint_status} pour PowerPoint")
        print(f"📝 {report.summary}")
        print()
        
        # Métriques détaillées
        print("📈 MÉTRIQUES DÉTAILLÉES")
        print("-" * 40)
        
        for metric in report.metrics_results:
            metric_emoji = {
                ValidationStatus.EXCELLENT: "✅",
                ValidationStatus.GOOD: "✅",
                ValidationStatus.WARNING: "⚠️",
                ValidationStatus.CRITICAL: "❌",
                ValidationStatus.INSUFFICIENT_DATA: "❓"
            }.get(metric.status, "❓")
            
            print(f"{metric_emoji} {metric.metric_name}: {metric.value}")
            print(f"   {metric.message}")
            
            if metric.status in [ValidationStatus.CRITICAL, ValidationStatus.WARNING]:
                print(f"   💡 {metric.recommendation}")
            print()
        
        # Problèmes et recommandations
        if report.critical_issues:
            print("🚨 PROBLÈMES CRITIQUES")
            print("-" * 40)
            for issue in report.critical_issues:
                print(f"❌ {issue}")
            print()
        
        if report.warnings:
            print("⚠️  ALERTES")
            print("-" * 40)
            for warning in report.warnings:
                print(f"⚠️  {warning}")
            print()
        
        # Actions recommandées
        critical_metrics = [m for m in report.metrics_results if m.status == ValidationStatus.CRITICAL]
        if critical_metrics:
            print("🔧 ACTIONS PRIORITAIRES")
            print("-" * 40)
            for metric in critical_metrics:
                print(f"🔹 {metric.metric_name}: {metric.recommendation}")
            print()
        
        return report
        
    except Exception as e:
        print(f"❌ Erreur lors de la validation du competitor {competitor_id}: {e}")
        return None


def main():
    """Fonction principale."""
    
    if len(sys.argv) != 2:
        print("Usage: python validate_competitor.py [competitor_id]")
        print("\nExemples:")
        print("  python validate_competitor.py 22    # Valider ARD Reisen")
        print("  python validate_competitor.py 122   # Valider Center Parcs Ferienparks")
        
        # Afficher les IDs disponibles
        validator = KeyMetricsValidator()
        with validator.get_db_connection() as conn:
            competitors = conn.execute("""
                SELECT id, name, country 
                FROM concurrent 
                ORDER BY country, name
            """).fetchall()
        
        print("\n📋 COMPETITORS DISPONIBLES:")
        print("-" * 60)
        current_country = None
        for comp in competitors:
            if comp['country'] != current_country:
                current_country = comp['country']
                print(f"\n🌍 {current_country}:")
            print(f"   {comp['id']:3d} - {comp['name']}")
        
        return
    
    try:
        competitor_id = int(sys.argv[1])
        validate_single_competitor(competitor_id)
    except ValueError:
        print("❌ L'ID du competitor doit être un nombre entier")


if __name__ == "__main__":
    main()