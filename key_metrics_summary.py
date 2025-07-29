#!/usr/bin/env python3
"""
Key Metrics Summary - Résumé rapide des problèmes détectés
==========================================================

Script pour afficher un résumé visuel des résultats de validation.
"""

from key_metrics_validator import KeyMetricsValidator, ValidationStatus


def print_summary():
    """Affiche un résumé coloré des résultats de validation."""
    
    validator = KeyMetricsValidator()
    reports = validator.validate_all_competitors()
    
    print("🎯 RÉSUMÉ VALIDATION KEY METRICS")
    print("=" * 60)
    
    # Statistiques globales
    total = len(reports)
    powerpoint_ready = sum(1 for r in reports if r.powerpoint_ready)
    critical = sum(1 for r in reports if r.overall_status == ValidationStatus.CRITICAL)
    warning = sum(1 for r in reports if r.overall_status == ValidationStatus.WARNING)
    excellent = sum(1 for r in reports if r.overall_status == ValidationStatus.EXCELLENT)
    
    print(f"📊 STATISTIQUES GLOBALES")
    print(f"   Total competitors analysés: {total}")
    print(f"   ✅ Prêts pour PowerPoint: {powerpoint_ready} ({powerpoint_ready/total*100:.0f}%)")
    print(f"   🟢 Excellents: {excellent}")
    print(f"   🟠 Alertes: {warning}")
    print(f"   🔴 Critiques: {critical}")
    print()
    
    # Top 3 problèmes les plus fréquents
    print("🚨 TOP 3 PROBLÈMES LES PLUS FRÉQUENTS")
    problem_counts = {}
    
    for report in reports:
        for issue in report.critical_issues:
            problem_counts[issue] = problem_counts.get(issue, 0) + 1
        for warning in report.warnings:
            problem_counts[warning] = problem_counts.get(warning, 0) + 1
    
    top_problems = sorted(problem_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    for i, (problem, count) in enumerate(top_problems, 1):
        print(f"   {i}. {problem} ({count} competitors)")
    print()
    
    # Competitors prêts pour PowerPoint
    print("✅ COMPETITORS PRÊTS POUR POWERPOINT")
    ready_competitors = [r for r in reports if r.powerpoint_ready]
    
    if ready_competitors:
        for comp in ready_competitors:
            print(f"   🟢 {comp.competitor_name} ({comp.country})")
    else:
        print("   ❌ Aucun competitor prêt actuellement")
    print()
    
    # Competitors nécessitant une intervention critique
    print("🔴 INTERVENTIONS CRITIQUES REQUISES")
    critical_competitors = [r for r in reports if r.overall_status == ValidationStatus.CRITICAL]
    
    if critical_competitors:
        for comp in critical_competitors:
            print(f"   🔴 {comp.competitor_name} ({comp.country})")
            for issue in comp.critical_issues:
                print(f"      - {issue}")
    else:
        print("   ✅ Aucune intervention critique requise")
    print()
    
    # Actions prioritaires
    print("🔧 ACTIONS PRIORITAIRES")
    print("   1. 🗓️  Corriger les dates YouTube avec l'agent de correction")
    print("   2. 📂 Compléter la classification Hero/Hub/Help des vidéos non catégorisées")
    print("   3. 📊 Rafraîchir les données de vues via l'API YouTube")
    print("   4. ✅ Re-valider après corrections")
    print()
    
    # Competitors par pays avec leurs statuts
    print("🌍 STATUT PAR PAYS")
    countries = {}
    for report in reports:
        country = report.country or "Non spécifié"
        if country not in countries:
            countries[country] = {'excellent': 0, 'warning': 0, 'critical': 0, 'total': 0}
        
        countries[country]['total'] += 1
        if report.overall_status == ValidationStatus.EXCELLENT:
            countries[country]['excellent'] += 1
        elif report.overall_status == ValidationStatus.WARNING:
            countries[country]['warning'] += 1
        elif report.overall_status == ValidationStatus.CRITICAL:
            countries[country]['critical'] += 1
    
    for country, stats in countries.items():
        total_country = stats['total']
        excellent_pct = (stats['excellent'] / total_country) * 100
        warning_pct = (stats['warning'] / total_country) * 100
        critical_pct = (stats['critical'] / total_country) * 100
        
        print(f"   🏁 {country}: {total_country} competitors")
        print(f"      🟢 {stats['excellent']} excellent ({excellent_pct:.0f}%)")
        print(f"      🟠 {stats['warning']} alertes ({warning_pct:.0f}%)")
        print(f"      🔴 {stats['critical']} critiques ({critical_pct:.0f}%)")
    
    print()
    print("📄 Pour le rapport détaillé, voir: key_metrics_validation_report_*.md")


if __name__ == "__main__":
    print_summary()