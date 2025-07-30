#!/usr/bin/env python3
"""
Script de Correction des Dates YouTube - Interface Simplifiée
=============================================================

Script principal pour corriger les dates de publication YouTube incorrectes
qui ont été définies comme dates d'import au lieu des vraies dates YouTube.

🎯 USAGE RECOMMANDÉ :

1. 🔍 ANALYSE PRÉLIMINAIRE :
   python fix_youtube_dates.py --analyze

2. 🧪 TEST SUR UN CONCURRENT :
   python fix_youtube_dates.py --competitor-id 504 --dry-run

3. 🚀 CORRECTION RÉELLE (avec confirmation) :
   python fix_youtube_dates.py --competitor-id 504 --confirm --youtube-api-key YOUR_KEY

4. 🔄 ROLLBACK SI PROBLÈME :
   python fix_youtube_dates.py --rollback --backup-table video_dates_backup_123456789

🛡️ SÉCURITÉ : Mode dry-run par défaut, backup automatique, rollback disponible

Auteur: Claude Code Agent  
Date: 2025-07-30
"""

import sys
import argparse
import os
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from yt_channel_analyzer.database.youtube_date_corrector import YouTubeDateCorrectionAgent
from yt_channel_analyzer.database.base import get_db_connection


def get_competitor_info(competitor_id: int) -> dict:
    """Récupérer les informations d'un concurrent"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT c.id, c.name, c.channel_url, COUNT(v.id) as video_count
        FROM concurrent c
        LEFT JOIN video v ON c.id = v.concurrent_id
        WHERE c.id = ?
        GROUP BY c.id, c.name, c.channel_url
        """, (competitor_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'channel_url': row['channel_url'],
                'video_count': row['video_count']
            }
        return None


def analyze_all_competitors():
    """Analyser tous les concurrents pour détecter les anomalies"""
    print("🔍 ANALYSE GLOBALE DES ANOMALIES DE DATES")
    print("=" * 50)
    
    agent = YouTubeDateCorrectionAgent(dry_run=True)
    anomalies = agent.detect_suspicious_dates()
    
    if not anomalies:
        print("✅ Aucune anomalie de date détectée dans la base")
        return
    
    print(f"🚨 {len(anomalies)} anomalie(s) détectée(s) :\n")
    
    # Regrouper par type d'anomalie
    anomaly_types = {}
    for anomaly in anomalies:
        anomaly_type = anomaly.anomaly_type
        if anomaly_type not in anomaly_types:
            anomaly_types[anomaly_type] = []
        anomaly_types[anomaly_type].append(anomaly)
    
    # Afficher par type
    for anomaly_type, type_anomalies in anomaly_types.items():
        print(f"📊 {anomaly_type} ({len(type_anomalies)} concurrents)")
        print("-" * 40)
        
        for anomaly in type_anomalies:
            impact_percent = (anomaly.suspicious_dates / anomaly.total_videos) * 100
            print(f"   🚨 {anomaly.competitor_name} (ID: {anomaly.competitor_id})")
            print(f"      Vidéos affectées : {anomaly.suspicious_dates}/{anomaly.total_videos} ({impact_percent:.1f}%)")
            print(f"      Date problématique : {anomaly.most_common_date}")
            print(f"      Confiance : {anomaly.confidence_score:.1%}")
            print()
    
    # Recommandations
    print("💡 RECOMMANDATIONS :")
    print("-" * 20)
    
    critical_anomalies = [a for a in anomalies if a.confidence_score > 0.9]
    if critical_anomalies:
        print(f"🚨 {len(critical_anomalies)} anomalies critiques nécessitent une correction immédiate")
        for anomaly in critical_anomalies[:3]:
            print(f"   • python fix_youtube_dates.py --competitor-id {anomaly.competitor_id} --dry-run")
    
    print("\n📋 Pour analyser un concurrent spécifique :")
    print("   python fix_youtube_dates.py --competitor-id [ID] --dry-run")


def fix_competitor_dates(competitor_id: int, youtube_api_key: str = None, confirm: bool = False):
    """Corriger les dates d'un concurrent spécifique"""
    # Vérifier que le concurrent existe
    competitor = get_competitor_info(competitor_id)
    if not competitor:
        print(f"❌ Concurrent {competitor_id} introuvable")
        return False
    
    print(f"🔧 CORRECTION DES DATES : {competitor['name']}")
    print("=" * 60)
    print(f"📺 Chaîne : {competitor['name']}")
    print(f"🌐 URL : {competitor['channel_url']}")
    print(f"🎬 Vidéos : {competitor['video_count']}")
    print(f"📊 Mode : {'PRODUCTION' if confirm else 'DRY-RUN'}")
    if youtube_api_key:
        print("🔑 API YouTube : Configurée")
    else:
        print("⚠️ API YouTube : Non configurée (scraping fallback)")
    print()
    
    # Initialiser l'agent
    agent = YouTubeDateCorrectionAgent(
        youtube_api_key=youtube_api_key,
        dry_run=not confirm
    )
    
    # Phase 1: Détecter les anomalies pour ce concurrent
    print("🔍 Phase 1 : Détection des anomalies...")
    anomalies = agent.detect_suspicious_dates(competitor_id)
    
    if not anomalies:
        print("✅ Aucune anomalie détectée pour ce concurrent")
        return True
    
    anomaly = anomalies[0]  # Un seul concurrent
    print(f"🚨 Anomalie détectée : {anomaly.suspicious_dates}/{anomaly.total_videos} vidéos avec date {anomaly.most_common_date}")
    print(f"   Type : {anomaly.anomaly_type}")
    print(f"   Confiance : {anomaly.confidence_score:.1%}")
    
    # Phase 2: Backup (si confirmation)
    if confirm:
        print("\n💾 Phase 2 : Création du backup...")
        if not agent.backup_current_dates():
            print("❌ Échec du backup - abandon de la correction")
            return False
        print(f"✅ Backup créé : {agent.backup_table_name}")
    
    # Phase 3: Application des corrections
    print(f"\n🔧 Phase 3 : {'Application' if confirm else 'Simulation'} des corrections...")
    corrections = agent.apply_corrections(competitor_id, confirm)
    
    # Statistiques
    successful = [c for c in corrections if c.success]
    failed = [c for c in corrections if not c.success]
    
    print(f"\n📊 RÉSULTATS :")
    print(f"   Corrections {'appliquées' if confirm else 'simulées'} : {len(corrections)}")
    print(f"   Succès : {len(successful)}")
    print(f"   Échecs : {len(failed)}")
    print(f"   Taux de succès : {len(successful)/max(len(corrections),1):.1%}")
    
    # Échantillon des corrections
    if successful:
        print(f"\n✅ ÉCHANTILLON DE CORRECTIONS {'APPLIQUÉES' if confirm else 'SIMULÉES'} :")
        for correction in successful[:5]:
            print(f"   • {correction.video_id}")
            print(f"     {correction.old_date} → {correction.new_date}")
        if len(successful) > 5:
            print(f"   ... et {len(successful) - 5} autres")
    
    # Phase 4: Génération du rapport
    print(f"\n📄 Phase 4 : Génération du rapport...")
    report = agent.generate_report(anomalies, corrections)
    
    # Sauvegarder le rapport
    report_filename = f"youtube_date_correction_{competitor['name'].replace(' ', '_')}_{competitor_id}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Rapport sauvegardé : {report_filename}")
    
    # Phase 5: Validation (si corrections appliquées)
    if confirm and successful:
        print(f"\n🔍 Phase 5 : Validation des corrections...")
        validation = agent.validate_corrections(competitor_id, sample_size=min(5, len(successful)))
        print(f"   Score de cohérence : {validation['coherence_score']:.1%}")
        
        if validation['coherence_score'] < 0.8:
            print("⚠️ Score de cohérence faible - vérification manuelle recommandée")
            if agent.backup_table_name:
                print(f"🔄 Rollback disponible : python fix_youtube_dates.py --rollback --backup-table {agent.backup_table_name}")
        else:
            print("✅ Corrections cohérentes - qualité satisfaisante")
    
    return True


def rollback_corrections(backup_table_name: str):
    """Effectuer un rollback depuis une table de backup"""
    print(f"🔄 ROLLBACK DEPUIS : {backup_table_name}")
    print("=" * 50)
    
    # Vérifier que la table de backup existe
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (backup_table_name,)
        )
        
        if not cursor.fetchone():
            print(f"❌ Table de backup '{backup_table_name}' introuvable")
            print("\n📋 Tables de backup disponibles :")
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'video_dates_backup_%'"
            )
            backups = cursor.fetchall()
            for backup in backups:
                print(f"   • {backup['name']}")
            return False
    
    # Confirmer l'opération
    confirm = input(f"⚠️ Confirmer le rollback depuis '{backup_table_name}' ? (oui/non): ").lower()
    if confirm not in ['oui', 'o', 'yes', 'y']:
        print("❌ Rollback annulé")
        return False
    
    # Effectuer le rollback
    agent = YouTubeDateCorrectionAgent(dry_run=False)
    agent.backup_table_name = backup_table_name  # Utiliser la table spécifiée
    
    success = agent.rollback()
    if success:
        print("✅ Rollback effectué avec succès")
        print("📊 Toutes les dates ont été restaurées à leur état d'origine")
    else:
        print("❌ Échec du rollback")
    
    return success


def main():
    """Fonction principale avec interface en ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Script de correction des dates YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :

  # Analyser toutes les anomalies
  python fix_youtube_dates.py --analyze

  # Tester sur Pierre et Vacances
  python fix_youtube_dates.py --competitor-id 504 --dry-run

  # Corriger avec API YouTube
  python fix_youtube_dates.py --competitor-id 504 --confirm --youtube-api-key YOUR_KEY

  # Rollback si problème
  python fix_youtube_dates.py --rollback --backup-table video_dates_backup_123456789
        """
    )
    
    # Groupes d'arguments mutuellement exclusifs
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--analyze', action='store_true',
                            help="Analyser toutes les anomalies de dates")
    action_group.add_argument('--competitor-id', type=int,
                            help="ID du concurrent à corriger")
    action_group.add_argument('--rollback', action='store_true',
                            help="Effectuer un rollback")
    
    # Arguments optionnels
    parser.add_argument('--youtube-api-key', 
                       help="Clé API YouTube v3 (recommandé pour de meilleurs résultats)")
    parser.add_argument('--confirm', action='store_true',
                       help="Confirmer les modifications (sinon mode dry-run)")
    parser.add_argument('--dry-run', action='store_true',
                       help="Mode dry-run explicite (par défaut)")
    parser.add_argument('--backup-table',
                       help="Nom de la table de backup pour rollback")
    
    args = parser.parse_args()
    
    try:
        if args.analyze:
            analyze_all_competitors()
            
        elif args.competitor_id:
            # Vérifier les arguments
            if args.confirm and not args.youtube_api_key:
                print("⚠️ AVERTISSEMENT : Correction sans clé API YouTube")
                print("   Les résultats seront limités par le scraping (plus lent, moins fiable)")
                confirm = input("   Continuer quand même ? (oui/non): ").lower()
                if confirm not in ['oui', 'o', 'yes', 'y']:
                    print("❌ Opération annulée")
                    return
            
            success = fix_competitor_dates(
                competitor_id=args.competitor_id,
                youtube_api_key=args.youtube_api_key,
                confirm=args.confirm and not args.dry_run
            )
            
            if not success:
                sys.exit(1)
                
        elif args.rollback:
            if not args.backup_table:
                print("❌ --backup-table requis pour le rollback")
                sys.exit(1)
            
            success = rollback_corrections(args.backup_table)
            if not success:
                sys.exit(1)
        
        print("\n" + "=" * 60)
        print("✅ OPÉRATION TERMINÉE AVEC SUCCÈS")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Opération annulée par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur critique : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()