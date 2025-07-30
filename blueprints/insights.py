"""
Insights Blueprint
Handles all analytics, insights, and dashboard routes.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, render_template, request, flash, session
from blueprints.auth import login_required
from services.insights_service import BrandInsightsService
from services.country_metrics_service import CountryMetricsService
from services.europe_metrics_service import EuropeMetricsService


insights_bp = Blueprint('insights', __name__)


@insights_bp.route('/test-insights')
@login_required
def test_insights():
    """Route de test pour vérifier les insights"""
    insights = [
        {
            'type': 'success',
            'icon': 'bx-trophy',
            'title': 'Test Insight 1',
            'message': 'Ceci est un test pour vérifier que les insights fonctionnent'
        },
        {
            'type': 'warning',
            'icon': 'bx-bulb',
            'title': 'Test Insight 2',
            'message': 'Deuxième insight de test'
        }
    ]
    
    countries_data = [
        {'country': 'Test Country', 'competitor_count': 5, 'video_count': 100, 'avg_views_per_video': 1000, 'engagement_rate': 2.5, 'opportunity_score': 75}
    ]
    
    return render_template('countries_analysis_pro.html',
                         countries_data=countries_data,
                         insights=insights,
                         top_videos_by_country={},
                         total_countries=1)


@insights_bp.route('/countries-analysis')
@login_required
def countries_analysis():
    """Analyse comparative par pays avec insights exploitables"""
    print("[DEBUG] ✅ Route blueprint countries_analysis appelée !")
    from yt_channel_analyzer.database import get_db_connection
    import sqlite3
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les métriques détaillées par pays
        cursor.execute("""
            SELECT 
                c.country,
                COUNT(DISTINCT c.id) as competitor_count,
                COUNT(DISTINCT v.id) as video_count,
                COALESCE(AVG(v.view_count), 0) as avg_views_per_video,
                COALESCE(AVG(CAST(v.like_count AS FLOAT) / NULLIF(v.view_count, 0) * 100), 0) as avg_engagement_rate,
                MAX(v.view_count) as max_views,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(AVG(v.duration_seconds), 0) as avg_duration,
                -- Distribution par catégorie
                SUM(CASE WHEN LOWER(v.category) = 'hero' THEN 1 ELSE 0 END) as hero_count,
                SUM(CASE WHEN LOWER(v.category) = 'hub' THEN 1 ELSE 0 END) as hub_count,
                SUM(CASE WHEN LOWER(v.category) = 'help' THEN 1 ELSE 0 END) as help_count,
                -- Top performer
                (SELECT cc.name FROM concurrent cc 
                 JOIN video vv ON cc.id = vv.concurrent_id 
                 WHERE cc.country = c.country 
                 ORDER BY vv.view_count DESC 
                 LIMIT 1) as top_performer,
                -- Opportunity Score (basé sur le potentiel vs performance actuelle)
                CASE 
                    WHEN COUNT(DISTINCT v.id) = 0 THEN 100  -- Pas de contenu = opportunité max
                    WHEN AVG(v.view_count) < 10000 AND COUNT(DISTINCT v.id) < 100 THEN 80
                    WHEN AVG(v.view_count) < 50000 AND COUNT(DISTINCT v.id) < 200 THEN 60
                    WHEN AVG(v.view_count) < 100000 THEN 40
                    ELSE 20
                END as opportunity_score
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            WHERE c.country IS NOT NULL AND c.country != ''
            GROUP BY c.country
            ORDER BY total_views DESC
        """)
        
        countries_data = []
        for row in cursor.fetchall():
            total_videos = row[8] + row[9] + row[10]
            countries_data.append({
                'country': row[0],
                'competitor_count': row[1],
                'video_count': row[2],
                'avg_views_per_video': int(row[3]),
                'engagement_rate': round(row[4], 2),
                'max_views': row[5],
                'total_views': row[6],
                'avg_duration': int(row[7]),
                'hero_count': row[8],
                'hub_count': row[9],
                'help_count': row[10],
                'hero_percentage': round((row[8] / total_videos * 100) if total_videos > 0 else 0, 1),
                'hub_percentage': round((row[9] / total_videos * 100) if total_videos > 0 else 0, 1),
                'help_percentage': round((row[10] / total_videos * 100) if total_videos > 0 else 0, 1),
                'top_performer': row[11],
                'opportunity_score': row[12]
            })
        
        # Calculer les insights automatiques
        insights = []
        
        print(f"[DEBUG] Nombre de pays trouvés : {len(countries_data)}")
        if countries_data:
            print(f"[DEBUG] Premier pays : {countries_data[0]}")
        
        # Ajoutons toujours quelques insights par défaut
        if countries_data:
            # Insight 1: Pays avec le plus de vidéos
            most_videos = max(countries_data, key=lambda x: x['video_count'])
            insights.append({
                'type': 'success',
                'icon': 'bx-trophy',
                'title': 'Leader en volume',
                'message': f"{most_videos['country']} domine avec {most_videos['video_count']:,} vidéos analysées"
            })
            
            # Insight 2: Pays avec le meilleur engagement
            if countries_data and any(c['engagement_rate'] > 0 for c in countries_data):
                best_engagement = max(countries_data, key=lambda x: x['engagement_rate'])
                insights.append({
                    'type': 'success',
                    'icon': 'bx-trending-up',
                    'title': 'Meilleur engagement',
                    'message': f"{best_engagement['country']} a le meilleur taux d'engagement avec {best_engagement['engagement_rate']:.2f}%"
                })
            
            # Insight 3: Opportunités par distribution de contenu
            for country in countries_data:
                help_pct = country.get('help_percentage', 0)
                if help_pct < 20 and country['video_count'] > 50:
                    insights.append({
                        'type': 'warning',
                        'icon': 'bx-bulb',
                        'title': f"Opportunité SEO en {country['country']}",
                        'message': f"Seulement {help_pct:.1f}% de contenu 'Help'. Potentiel d'amélioration du SEO avec plus de tutoriels."
                    })
                    break
            
            # Insight 4: Marché sous-exploité
            underutilized = min([c for c in countries_data if c['video_count'] > 0], 
                              key=lambda x: x['video_count'], default=None)
            if underutilized and underutilized['video_count'] < 200:
                insights.append({
                    'type': 'info',
                    'icon': 'bx-target-lock',
                    'title': 'Marché sous-exploité',
                    'message': f"{underutilized['country']} n'a que {underutilized['video_count']} vidéos. Grande opportunité de croissance."
                })
            
            # Insight 5: Analyse des performances moyennes
            avg_views = sum(c['avg_views_per_video'] for c in countries_data) / len(countries_data)
            high_performers = [c for c in countries_data if c['avg_views_per_video'] > avg_views * 1.5]
            if high_performers:
                top_performer = max(high_performers, key=lambda x: x['avg_views_per_video'])
                insights.append({
                    'type': 'info',
                    'icon': 'bx-bar-chart-alt-2',
                    'title': 'Performance exceptionnelle',
                    'message': f"{top_performer['country']} surperforme avec {top_performer['avg_views_per_video']:,} vues/vidéo en moyenne"
                })
        
        # S'assurer qu'on a au moins un insight - FORCER TOUJOURS UN INSIGHT
        if not insights:
            insights.append({
                'type': 'info',
                'icon': 'bx-info-circle',
                'title': 'Analyse en cours',
                'message': f"Analyse de {len(countries_data)} pays en cours. Plus d'insights disponibles avec plus de données."
            })
        
        # TOUJOURS ajouter un insight de debug pour s'assurer que ça marche
        insights.append({
            'type': 'info',
            'icon': 'bx-bug',
            'title': 'Debug Info',
            'message': f"Route blueprint fonctionnelle - {len(countries_data)} pays analysés"
        })
        
        print(f"[DEBUG] Nombre d'insights générés : {len(insights)}")
        for i, insight in enumerate(insights):
            print(f"[DEBUG] Insight {i+1}: {insight['title']} - {insight['message']}")
        
        # Récupérer les données pour le drill-down (top vidéos par pays)
        cursor.execute("""
            SELECT 
                c.country,
                v.title,
                v.view_count,
                cc.name as competitor_name,
                v.url,
                v.category
            FROM video v
            JOIN concurrent cc ON v.concurrent_id = cc.id
            JOIN (
                SELECT country, MAX(view_count) as max_views
                FROM video v2
                JOIN concurrent c2 ON v2.concurrent_id = c2.id
                WHERE c2.country IS NOT NULL
                GROUP BY c2.country
            ) c ON cc.country = c.country AND v.view_count = c.max_views
            ORDER BY v.view_count DESC
        """)
        
        top_videos_by_country = {}
        for row in cursor.fetchall():
            country = row[0]
            if country not in top_videos_by_country:
                top_videos_by_country[country] = []
            top_videos_by_country[country].append({
                'title': row[1],
                'views': row[2],
                'competitor': row[3],
                'url': row[4],
                'category': row[5]
            })
        
        conn.close()
        
        return render_template('countries_analysis_pro.html',
                             countries_data=countries_data,
                             insights=insights,
                             top_videos_by_country=top_videos_by_country,
                             total_countries=len(countries_data))
    
    except sqlite3.Error as e:
        print(f"[ERROR] Database error in countries_analysis: {e}")
        flash("Erreur lors du chargement des analyses par pays", "error")
        return render_template('countries_analysis_pro.html',
                             countries_data=[],
                             insights=[],
                             top_videos_by_country={},
                             total_countries=0)


@insights_bp.route('/learn')
@login_required
def learn():
    """Page d'apprentissage et de guide de l'application"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Statistiques rapides pour le guide d'apprentissage
        cursor.execute("SELECT COUNT(*) FROM concurrent")
        total_competitors = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video")
        total_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video WHERE category IS NOT NULL AND category != '' AND category != 'uncategorized'")
        classified_videos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT concurrent_id) FROM video WHERE category IS NOT NULL AND category != '' AND category != 'uncategorized'")
        competitors_with_classification = cursor.fetchone()[0]
        
        conn.close()
        
        # Données pour le guide d'apprentissage
        learning_stats = {
            'total_competitors': total_competitors,
            'total_videos': total_videos,
            'classified_videos': classified_videos,
            'competitors_with_classification': competitors_with_classification,
            'classification_percentage': round((classified_videos / total_videos * 100) if total_videos > 0 else 0, 1)
        }
        
        # Available learning guides
        guides = [
            {
                'file': 'hero_hub_help_strategy.md',
                'icon': '🎯',
                'title': 'Hero Hub Help Strategy',
                'description': 'Understand Google\'s matrix to optimize your content',
                'duration': '15 min',
                'level': 'Beginner'
            },
            {
                'file': 'competitor_analysis.md',
                'icon': '🔍',
                'title': 'Competitive Analysis',
                'description': 'Methods to analyze your YouTube competitors',
                'duration': '20 min',
                'level': 'Intermediate'
            },
            {
                'file': 'content_classification.md',
                'icon': '📊',
                'title': 'Content Classification',
                'description': 'How to effectively classify your videos',
                'duration': '12 min',
                'level': 'Beginner'
            },
            {
                'file': 'semantic_analysis.md',
                'icon': '🧠',
                'title': 'Semantic Analysis',
                'description': 'Use AI to understand content',
                'duration': '25 min',
                'level': 'Advanced'
            },
            {
                'file': 'engagement_optimization.md',
                'icon': '📈',
                'title': 'Engagement Optimization',
                'description': 'Techniques to improve engagement',
                'duration': '18 min',
                'level': 'Intermediate'
            },
            {
                'file': 'data_interpretation.md',
                'icon': '📋',
                'title': 'Data Interpretation',
                'description': 'How to read and use your analyses',
                'duration': '22 min',
                'level': 'Intermediate'
            }
        ]
        
        return render_template('learn_sneat_pro.html',
                             learning_stats=learning_stats,
                             guides=guides,
                             dev_mode=session.get('dev_mode', False))
                             
    except Exception as e:
        print(f"[LEARN] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return render_template('learn_sneat_pro.html',
                             learning_stats={'total_competitors': 0, 'total_videos': 0, 'classified_videos': 0, 'competitors_with_classification': 0, 'classification_percentage': 0},
                             guides=[],
                             dev_mode=session.get('dev_mode', False))


@insights_bp.route('/learn/guide/<guide_name>')
@login_required  
def learn_guide(guide_name):
    """Page d'un guide spécifique"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        # Pour le guide Hero Hub Help Strategy
        if guide_name == 'hero_hub_help_strategy':
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Obtenir les statistiques pour le guide
            cursor.execute("SELECT COUNT(*) FROM concurrent")
            total_competitors = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM video")
            total_videos = cursor.fetchone()[0]
            
            conn.close()
            
            # Données du guide Hero Hub Help
            guide_data = {
                'guide_name': 'hero_hub_help_strategy',
                'guide_title': 'Stratégie Hero Hub Help',
                'guide_description': 'Comprendre la matrice Google pour optimiser votre contenu YouTube',
                'guide_icon': '🎯',
                'guide_duration': '15 min',
                'guide_level': 'Débutant',
                'guide_category': 'Stratégie',
                'guide_number': 1
            }
            
            # Statistiques pour le guide
            stats = {
                'total_competitors': total_competitors,
                'total_videos': total_videos
            }
            
            # Exemples de marques pour le guide Hero Hub Help
            brands_data = [
                {
                    'logo': '📷',
                    'name': 'CANON',
                    'hero': [
                        'Lancement nouveau reflex EOS R5',
                        'Campagne "Unforgettable Moments"',
                        'Partenariats avec photographes célèbres',
                        'Films publicitaires cinématographiques'
                    ],
                    'hub': [
                        'Série "Canon Creator Lab"',
                        'Tips hebdomadaires de photographie',
                        'Behind the scenes avec artistes',
                        'Communauté Canon Explorers'
                    ],
                    'help': [
                        'Tutoriels réglages manuels',
                        'Guide entretien matériel',
                        'FAQ résolution problèmes',
                        'Comparatifs objectifs'
                    ]
                },
                {
                    'logo': '📸',
                    'name': 'NIKON',
                    'hero': [
                        'Révélation Nikon Z9 flagship',
                        'Expédition photographique Antarctique',
                        'Collaborations National Geographic',
                        'Concours "Nikon Photo Contest"'
                    ],
                    'hub': [
                        'Série "Nikon School Online"',
                        'Portraits de photographes pros',
                        'Techniques avancées hebdo',
                        'Communauté Nikon Ambassadors'
                    ],
                    'help': [
                        'Mode d\'emploi complet',
                        'Dépannage et réparations',
                        'Calibrage couleurs',
                        'Optimisation autofocus'
                    ]
                },
                {
                    'logo': '👜',
                    'name': 'HERMÈS',
                    'hero': [
                        'Défilé Hermès Paris Fashion Week',
                        'Lancement collection capsule',
                        'Documentaire savoir-faire artisan',
                        'Ouverture boutique flagship'
                    ],
                    'hub': [
                        'Série "L\'Objet Hermès"',
                        'Histoire des créations iconiques',
                        'Rencontres avec artisans',
                        'Coulisses ateliers français'
                    ],
                    'help': [
                        'Guide entretien cuir',
                        'Authentification produits',
                        'Conseils styling et porter',
                        'Service client et réparations'
                    ]
                }
            ]
            
            return render_template('learn_guide_sneat_pro.html', 
                                 **guide_data,
                                 stats=stats,
                                 brands_data=brands_data)
        
        # Pour les autres guides, redirection temporaire
        else:
            from flask import redirect, url_for
            flash(f"Guide '{guide_name}' en cours de développement", "info")
            return redirect(url_for('insights.learn'))
        
    except Exception as e:
        from flask import redirect, url_for
        print(f"[LEARN_GUIDE] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        flash("Erreur lors du chargement du guide", "error")
        return redirect(url_for('insights.learn'))


@insights_bp.route('/insights')
@login_required
def insights():
    """
    Brand insights page - refactored using service layer architecture.
    Complexity reduced from 62 to ~5 by extracting business logic.
    """
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        
        # Use service layer for business logic
        service = BrandInsightsService(conn)
        insights_data = service.generate_brand_insights('%Center Parcs%')
        
        return render_template('insights_sneat_pro.html', insights=insights_data)
        
    except Exception as e:
        print(f"[INSIGHTS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return render_template('insights_sneat_pro.html', 
                             insights={'success': False, 'error': str(e)})
    finally:
        if 'conn' in locals():
            conn.close()


@insights_bp.route('/brand-insights')
@login_required
def brand_insights():
    """Page des insights par marque Center Parcs - structure identique à country-insights"""
    try:
        print("[BRAND_INSIGHTS] 🏢 Génération des insights par chaîne Center Parcs...")
        print("[BRAND_INSIGHTS] 🔍 ULTRA-VERBOSE DEBUG MODE ACTIVÉ")
        
        from yt_channel_analyzer.database import get_db_connection
        from services.local_global_metrics_service import LocalGlobalMetricsService
        from services.brand_metrics_service import BrandMetricsService
        
        conn = get_db_connection()
        service = BrandMetricsService(conn)
        local_global_service = LocalGlobalMetricsService(conn)
        
        # Récupérer les chaînes Center Parcs
        center_parcs_channels = service.get_center_parcs_channels()
        print(f"[BRAND_INSIGHTS] 📊 Chaînes trouvées: {list(center_parcs_channels.keys())}")
        print(f"[BRAND_INSIGHTS] 📊 Détail des chaînes: {center_parcs_channels}")
        
        # Générer les métriques pour chaque chaîne
        insights_by_brand = {}
        
        for brand_key, channel_info in center_parcs_channels.items():
            try:
                competitor_id = channel_info['competitor_id']
                print(f"[BRAND_INSIGHTS] 📊 Calcul des métriques pour {brand_key} (ID {competitor_id})...")
                
                # Calculer les métriques de base
                brand_metrics = service.calculate_brand_metrics(competitor_id)
                
                # Ajouter les métriques duales Local vs Global par pays
                country = channel_info['country']
                if country and country in ['Germany', 'France', 'Netherlands', 'United Kingdom']:
                    enhanced_metrics = local_global_service.calculate_enhanced_country_metrics(country)
                    # Fusionner les métriques duales dans les métriques de marque
                    if 'video_length' in enhanced_metrics and 'dual_metric' in enhanced_metrics['video_length']:
                        brand_metrics['video_length']['dual_metric'] = enhanced_metrics['video_length']['dual_metric']
                    if 'video_frequency' in enhanced_metrics and 'dual_metric' in enhanced_metrics['video_frequency']:
                        brand_metrics['video_frequency']['dual_metric'] = enhanced_metrics['video_frequency']['dual_metric']
                    if 'hub_help_hero' in enhanced_metrics and 'dual_metric' in enhanced_metrics['hub_help_hero']:
                        brand_metrics['hub_help_hero']['dual_metric'] = enhanced_metrics['hub_help_hero']['dual_metric']
                
                brand_metrics['competitor_id'] = competitor_id
                brand_metrics['channel_name'] = channel_info['name']
                brand_metrics['country'] = channel_info['country']
                
                insights_by_brand[brand_key] = brand_metrics
                
                print(f"[BRAND_INSIGHTS] ✅ Métriques générées pour {brand_key}")
                
            except Exception as e:
                print(f"[BRAND_INSIGHTS] ❌ Erreur pour {brand_key}: {e}")
                import traceback
                traceback.print_exc()
                
                # Créer des métriques vides en cas d'erreur
                insights_by_brand[brand_key] = service._empty_brand_metrics()
                insights_by_brand[brand_key]['error'] = str(e)
        
        conn.close()
        
        print(f"[BRAND_INSIGHTS] ✅ Métriques générées pour {len(insights_by_brand)} chaînes Center Parcs")
        print(f"[BRAND_INSIGHTS] 🎨 RENDU DU TEMPLATE: brand_insights_sneat_pro.html")
        print(f"[BRAND_INSIGHTS] 📋 DONNÉES PASSÉES: brands={list(center_parcs_channels.keys())}")
        print(f"[BRAND_INSIGHTS] 📊 SAMPLE INSIGHT: {list(insights_by_brand.keys())[:1]}")

        return render_template('brand_insights_sneat_pro.html', 
                             insights=insights_by_brand,
                             brands=list(center_parcs_channels.keys()),
                             dev_mode=session.get('dev_mode', False))
        
    except Exception as e:
        print(f"[BRAND_INSIGHTS] ❌ Erreur: {e}")
        print(f"[BRAND_INSIGHTS] ❌ Type d'erreur: {type(e)}")
        import traceback
        print(f"[BRAND_INSIGHTS] ❌ Stack trace:")
        traceback.print_exc()
        
        return render_template('brand_insights_sneat_pro.html', 
                             insights={},
                             brands=[],
                             error=str(e),
                             dev_mode=session.get('dev_mode', False))

@insights_bp.route('/country-insights')
@login_required
def country_insights():
    """Page des insights par pays avec 7 métriques clés - Enhanced with Local vs Global analysis"""
    try:
        print("[COUNTRY_INSIGHTS] 🌍 Génération des insights par pays avec analyse Local vs Global...")
        
        # Récupérer les pays réels de la base de données
        from yt_channel_analyzer.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT country FROM concurrent WHERE country IS NOT NULL AND country != '' ORDER BY country")
        real_countries = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"[COUNTRY_INSIGHTS] Pays trouvés: {real_countries}")
        
        # Générer les 7 métriques par pays
        insights_by_country = {}
        
        for country in real_countries:
            try:
                print(f"[COUNTRY_INSIGHTS] 📊 Calcul des métriques Local vs Global pour {country}...")
                
                # Utiliser le nouveau service avec analyse Local vs Global
                conn = get_db_connection()
                from services.local_global_metrics_service import LocalGlobalMetricsService
                enhanced_service = LocalGlobalMetricsService(conn)
                country_metrics = enhanced_service.calculate_enhanced_country_metrics(country)
                
                # Ajouter le nombre de concurrents
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM concurrent WHERE country = ?", (country,))
                competitors_count = cursor.fetchone()[0]
                conn.close()
                
                country_metrics['competitors_count'] = competitors_count
                insights_by_country[country] = country_metrics
                
                print(f"[COUNTRY_INSIGHTS] ✅ Métriques Local vs Global générées pour {country}")
                if country_metrics.get('has_dual_metrics'):
                    dual_info = country_metrics.get('dual_metrics_info', {})
                    print(f"[COUNTRY_INSIGHTS] 📊 Métriques duales: video_length={dual_info.get('video_length')}, frequency={dual_info.get('frequency')}, shorts={dual_info.get('shorts')}")
                
            except Exception as e:
                print(f"[COUNTRY_INSIGHTS] ❌ Erreur pour {country}: {e}")
                import traceback
                traceback.print_exc()
                
                # Créer des métriques vides en cas d'erreur
                insights_by_country[country] = {
                    'error': str(e),
                    'video_length': {'total_videos': 0, 'avg_duration_minutes': 0, 'min_duration_minutes': 0, 'max_duration_minutes': 0, 'shorts_percentage': 0},
                    'video_frequency': {'total_videos': 0, 'videos_per_week': 0, 'days_active': 0, 'consistency_score': 0},
                    'most_liked_topics': [],
                    'organic_vs_paid': {'organic_percentage': 0, 'paid_percentage': 0, 'organic_count': 0},
                    'hub_help_hero': {'hero_percentage': 0, 'hub_percentage': 0, 'help_percentage': 0, 'hero_count': 0, 'hub_count': 0, 'help_count': 0},
                    'thumbnail_consistency': {'total_videos': 0, 'with_thumbnails': 0, 'consistency_score': 0},
                    'tone_of_voice': {'emotional_words': 0, 'action_words': 0, 'avg_title_length': 0, 'top_keywords': [], 'dominant_tone': 'Family'},
                    'shorts_distribution': {'total_videos': 0, 'shorts_count': 0, 'regular_count': 0, 'shorts_percentage': 0.0, 'regular_percentage': 0.0},
                    'competitors_count': 0,
                    'total_videos': 0,
                    'has_dual_metrics': False
                }
        
        print(f"[COUNTRY_INSIGHTS] ✅ Métriques générées pour {len(insights_by_country)} pays")

        return render_template('country_insights_sneat_pro.html', 
                             insights=insights_by_country,
                             countries=real_countries,
                             dev_mode=session.get('dev_mode', False))
        
    except Exception as e:
        print(f"[COUNTRY_INSIGHTS] ❌ Erreur: {e}")
        print(f"[COUNTRY_INSIGHTS] ❌ Type d'erreur: {type(e)}")
        import traceback
        print(f"[COUNTRY_INSIGHTS] ❌ Stack trace:")
        traceback.print_exc()
        
        return render_template('country_insights_sneat_pro.html', 
                             insights={},
                             countries=[],
                             error=str(e),
                             dev_mode=session.get('dev_mode', False))


@insights_bp.route('/europe-insights')
@login_required
def europe_insights():
    """Page des insights européens - consolidation de tous les pays"""
    try:
        print("[EUROPE_INSIGHTS] 🌍 Génération des insights européens consolidés...")
        print("[EUROPE_INSIGHTS] 🔍 Architecture: CHANNELS < COUNTRIES < EUROPE")
        
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        service = EuropeMetricsService(conn)
        
        # Get European countries for context
        european_countries = service.get_european_countries()
        print(f"[EUROPE_INSIGHTS] 🗺️ {len(european_countries)} pays européens trouvés")
        
        # Calculate consolidated Europe metrics
        europe_metrics = service.calculate_europe_metrics()
        
        conn.close()
        
        print(f"[EUROPE_INSIGHTS] ✅ Métriques européennes générées")
        print(f"[EUROPE_INSIGHTS] 📊 Total: {europe_metrics.get('total_videos', 0)} vidéos, {europe_metrics.get('total_countries', 0)} pays")
        
        return render_template('europe_insights_sneat_pro.html', 
                             europe_data=europe_metrics,
                             countries=european_countries,
                             dev_mode=session.get('dev_mode', False))
        
    except Exception as e:
        print(f"[EUROPE_INSIGHTS] ❌ Erreur: {e}")
        print(f"[EUROPE_INSIGHTS] ❌ Type d'erreur: {type(e)}")
        import traceback
        print(f"[EUROPE_INSIGHTS] ❌ Stack trace:")
        traceback.print_exc()
        
        return render_template('europe_insights_sneat_pro.html', 
                             europe_data={},
                             countries={},
                             error=str(e),
                             dev_mode=session.get('dev_mode', False))


@insights_bp.route('/top-topics')
@login_required
def top_topics():
    """Page d'analyse des sujets populaires"""
    try:
        import os
        import json
        from yt_channel_analyzer.background_tasks import task_manager
        
        # Vérifier si une analyse de topics est en cours
        results_file = 'topic_analysis_results.json'
        advanced_results = {}
        analysis_status = 'not_started'
        
        running_tasks = task_manager.get_running_tasks()
        topic_analysis_running = any(task.channel_url == "topic_analysis" for task in running_tasks)
        
        if topic_analysis_running:
            analysis_status = 'in_progress'
        elif os.path.exists(results_file):
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    advanced_results = json.load(f)
                analysis_status = 'completed'
            except (json.JSONDecodeError, IOError, FileNotFoundError) as e:
                print(f"[WARNING] Error loading topic analysis results: {e}")
                analysis_status = 'error'
        
        # Préparer les résultats pour le template
        if advanced_results and analysis_status == 'completed':
            # Utiliser les résultats avancés s'ils sont disponibles
            topics_data = advanced_results
        else:
            # Analyse de base depuis la base de données
            from yt_channel_analyzer.database import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # D'abord obtenir les vraies statistiques globales
            cursor.execute("SELECT COUNT(*) FROM video WHERE title IS NOT NULL")
            total_videos_in_db = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM video WHERE title IS NOT NULL AND view_count > 1000")
            videos_with_decent_views = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT concurrent_id) FROM video WHERE title IS NOT NULL")
            total_competitors_analyzed = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM playlist WHERE name IS NOT NULL")
            total_playlists_analyzed = cursor.fetchone()[0]
            
            # Ensuite analyser les titres avec données concurrents et catégories
            cursor.execute("""
                SELECT 
                    v.title, 
                    v.view_count, 
                    v.like_count, 
                    v.comment_count,
                    v.category,
                    c.name as competitor_name,
                    c.country
                FROM video v
                JOIN concurrent c ON v.concurrent_id = c.id
                WHERE v.title IS NOT NULL 
                AND v.view_count > 1000
                ORDER BY v.view_count DESC 
                LIMIT 2000
            """)
            
            videos = cursor.fetchall()
            word_stats = {}
            
            # Mots vides à ignorer
            stop_words = {'de', 'la', 'le', 'et', 'à', 'un', 'une', 'du', 'des', 'les', 'en', 'pour', 'avec', 'sur', 'dans', 'par', 'ce', 'qui', 'que', 'est', 'il', 'se', 'ne', 'pas', 'tout', 'être', 'avoir', 'faire', 'voir', 'plus', 'bien', 'où', 'comment', 'quand'}
            
            for video in videos:
                title = video[0].lower() if video[0] else ''
                view_count = video[1] or 0
                like_count = video[2] or 0
                comment_count = video[3] or 0
                category = video[4] or 'uncategorized'
                competitor_name = video[5] or 'Inconnu'
                country = video[6] or 'Inconnu'
                
                words = title.split()
                for word in words:
                    # Nettoyer le mot
                    word = ''.join(c for c in word if c.isalnum())
                    if len(word) > 3 and word not in stop_words:
                        if word not in word_stats:
                            word_stats[word] = {
                                'count': 0, 
                                'total_views': 0, 
                                'total_likes': 0, 
                                'total_comments': 0,
                                'categories': {},
                                'competitors': {},
                                'countries': {}
                            }
                        
                        word_stats[word]['count'] += 1
                        word_stats[word]['total_views'] += view_count
                        word_stats[word]['total_likes'] += like_count
                        word_stats[word]['total_comments'] += comment_count
                        
                        # Compter catégories
                        if category not in word_stats[word]['categories']:
                            word_stats[word]['categories'][category] = 0
                        word_stats[word]['categories'][category] += 1
                        
                        # Compter concurrents
                        if competitor_name not in word_stats[word]['competitors']:
                            word_stats[word]['competitors'][competitor_name] = 0
                        word_stats[word]['competitors'][competitor_name] += 1
                        
                        # Compter pays
                        if country not in word_stats[word]['countries']:
                            word_stats[word]['countries'][country] = 0
                        word_stats[word]['countries'][country] += 1
            
            # Trier par popularité (nombre d'occurrences)
            top_topics = sorted(word_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:20]
            
            topics_data = {
                'top_keywords': [
                    {
                        'keyword': topic[0],
                        'count': topic[1]['count'],
                        'total_views': topic[1]['total_views'],
                        'total_likes': topic[1]['total_likes'],
                        'total_comments': topic[1]['total_comments'],
                        'avg_views': topic[1]['total_views'] // max(topic[1]['count'], 1),
                        'categories': topic[1]['categories'],
                        'competitors': topic[1]['competitors'],
                        'countries': topic[1]['countries']
                    }
                    for topic in top_topics
                ],
                'analysis_method': 'enhanced_keyword_extraction',
                'total_videos_analyzed': total_videos_in_db,
                'videos_with_decent_views': videos_with_decent_views,
                'total_competitors_analyzed': total_competitors_analyzed,
                'total_playlists_analyzed': total_playlists_analyzed
            }
            
            conn.close()
        
        # Transformer les données pour le template
        topics = []
        summary = {}
        
        if topics_data and 'top_keywords' in topics_data:
            for keyword_data in topics_data['top_keywords']:
                # Déterminer la catégorie principale
                top_category = 'uncategorized'
                top_competitor = 'Divers'
                countries = {}
                
                if 'categories' in keyword_data and keyword_data['categories']:
                    top_category = max(keyword_data['categories'].items(), key=lambda x: x[1])[0]
                    
                if 'competitors' in keyword_data and keyword_data['competitors']:
                    top_competitor = max(keyword_data['competitors'].items(), key=lambda x: x[1])[0]
                    
                if 'countries' in keyword_data and keyword_data['countries']:
                    countries = dict(list(keyword_data['countries'].items())[:3])  # Top 3 pays
                
                topics.append({
                    'topic': keyword_data['keyword'],
                    'frequency': keyword_data['count'],
                    'avg_views': keyword_data['avg_views'],
                    'total_likes': keyword_data['total_likes'],
                    'total_comments': keyword_data.get('total_comments', 0),
                    'top_category': top_category,
                    'top_competitor': top_competitor,
                    'countries': countries
                })
            
            summary = {
                'total_topics': len(topics_data['top_keywords']),
                'analyzed_videos': topics_data.get('total_videos_analyzed', 0),
                'analyzed_playlists': topics_data.get('total_playlists_analyzed', 0)
            }
        
        return render_template('top_topics_sneat_pro.html',
                             topics=topics,
                             summary=summary,
                             analysis_status=analysis_status,
                             has_advanced_results=bool(advanced_results),
                             sort_by=request.args.get('sort_by', 'frequency'),
                             order=request.args.get('order', 'desc'),
                             category_filter=request.args.get('category', 'all'),
                             limit=int(request.args.get('limit', 50)))
                             
    except Exception as e:
        print(f"[TOP_TOPICS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        flash("Erreur lors de l'analyse des sujets", "error")
        return render_template('top_topics_sneat_pro.html',
                             topics=[],
                             summary={'total_topics': 0, 'analyzed_videos': 0, 'analyzed_playlists': 0},
                             analysis_status='error',
                             has_advanced_results=False,
                             sort_by='frequency',
                             order='desc',
                             category_filter='all',
                             limit=50)


@insights_bp.route('/frequency-dashboard-test')
def frequency_dashboard_test():
    """Test simple pour debugging"""
    return "TEST: Route frequency dashboard fonctionne !"

@insights_bp.route('/frequency-dashboard')
@login_required
def frequency_dashboard():
    """Dashboard pour analyser la fréquence de publication Hero/Hub/Help"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Récupérer les statistiques de fréquence depuis la table competitor_frequency_stats
        cursor.execute('''
            SELECT 
                c.id,
                c.name,
                c.country,
                cfs.avg_videos_per_week,
                cfs.frequency_hero,
                cfs.frequency_hub,
                cfs.frequency_help,
                COUNT(v.id) as video_count
            FROM concurrent c
            LEFT JOIN competitor_frequency_stats cfs ON c.id = cfs.competitor_id
            LEFT JOIN video v ON c.id = v.concurrent_id
            WHERE c.name IS NOT NULL
            GROUP BY c.id, c.name, c.country
            ORDER BY cfs.avg_videos_per_week DESC
        ''')
        
        competitors_data = cursor.fetchall()
        competitors = []
        
        for row in competitors_data:
            competitors.append({
                'id': row[0],
                'name': row[1],
                'country': row[2] or 'Unknown',
                'avg_frequency': {
                    'total': round(row[3] or 0, 1),
                    'hero': round(row[4] or 0, 1),
                    'hub': round(row[5] or 0, 1),
                    'help': round(row[6] or 0, 1)
                },
                'video_count': row[7],
                'thumbnail_local': f"/static/competitors/images/{row[0]}.jpg"
            })
        
        # Calculer les statistiques globales
        cursor.execute('''
            SELECT 
                AVG(avg_videos_per_week) as avg_total,
                AVG(frequency_hero) as avg_hero,
                AVG(frequency_hub) as avg_hub,
                AVG(frequency_help) as avg_help,
                COUNT(*) as total_competitors
            FROM competitor_frequency_stats
            WHERE avg_videos_per_week > 0
        ''')
        
        global_stats_row = cursor.fetchone()
        
        # Statistiques par pays
        cursor.execute('''
            SELECT 
                c.country,
                COUNT(DISTINCT c.id) as competitor_count,
                AVG(cfs.avg_videos_per_week) as avg_frequency,
                AVG(cfs.frequency_hero) as avg_hero,
                AVG(cfs.frequency_hub) as avg_hub,
                AVG(cfs.frequency_help) as avg_help
            FROM concurrent c
            JOIN competitor_frequency_stats cfs ON c.id = cfs.competitor_id
            WHERE c.country IS NOT NULL AND cfs.avg_videos_per_week > 0
            GROUP BY c.country
            ORDER BY avg_frequency DESC
        ''')
        
        country_data = {}
        for row in cursor.fetchall():
            country_data[row[0]] = {
                'competitor_count': row[1],
                'avg_frequency': round(row[2] or 0, 1),
                'avg_hero': round(row[3] or 0, 1),
                'avg_hub': round(row[4] or 0, 1),
                'avg_help': round(row[5] or 0, 1)
            }
        
        conn.close()
        
        # Préparer les données pour le template
        frequency_stats = {
            'avg_per_week': round(global_stats_row[0] or 0, 1),
            'most_active_day': 'Tuesday',
            'consistency_score': 78,
            'optimal_time': '10:00 AM'
        }
        
        category_frequency = {
            'hero_per_week': round(global_stats_row[1] or 0, 1),
            'hero_percentage': 20,
            'hub_per_week': round(global_stats_row[2] or 0, 1),
            'hub_percentage': 60,
            'help_per_week': round(global_stats_row[3] or 0, 1),
            'help_percentage': 20
        }
        
        # Pattern hebdomadaire (données statiques pour l'exemple)
        weekly_pattern = [
            {'name': 'Monday', 'short_name': 'M', 'video_count': 45, 'percentage': 80, 'is_most_active': False},
            {'name': 'Tuesday', 'short_name': 'T', 'video_count': 56, 'percentage': 100, 'is_most_active': True},
            {'name': 'Wednesday', 'short_name': 'W', 'video_count': 42, 'percentage': 75, 'is_most_active': False},
            {'name': 'Thursday', 'short_name': 'T', 'video_count': 38, 'percentage': 68, 'is_most_active': False},
            {'name': 'Friday', 'short_name': 'F', 'video_count': 35, 'percentage': 62, 'is_most_active': False},
            {'name': 'Saturday', 'short_name': 'S', 'video_count': 28, 'percentage': 50, 'is_most_active': False},
            {'name': 'Sunday', 'short_name': 'S', 'video_count': 32, 'percentage': 57, 'is_most_active': False}
        ]
        
        # Analyse d'impact
        impact_analysis = {
            'high_frequency_performers': [c for c in competitors if c['avg_frequency']['total'] > 2.0][:5],
            'low_frequency_performers': [c for c in competitors if c['avg_frequency']['total'] < 1.0][:5],
            'optimal_frequency_insights': {
                'high_performers_avg_frequency': 2.5,
                'low_performers_avg_frequency': 0.7,
                'frequency_impact': 'positive',
                'recommendation': 'Maintenir une fréquence de 2-3 vidéos par semaine pour optimiser l\'engagement'
            },
            'category_insights': {
                'hero': {'avg_frequency': category_frequency['hero_per_week'], 'avg_engagement': 2.0, 'competitors': len([c for c in competitors if c['avg_frequency']['hero'] > 0])},
                'hub': {'avg_frequency': category_frequency['hub_per_week'], 'avg_engagement': 3.0, 'competitors': len([c for c in competitors if c['avg_frequency']['hub'] > 0])},
                'help': {'avg_frequency': category_frequency['help_per_week'], 'avg_engagement': 2.5, 'competitors': len([c for c in competitors if c['avg_frequency']['help'] > 0])}
            }
        }
        
        # Insights et recommandations
        frequency_insights = [
            {'title': 'Fréquence Optimale', 'description': 'Les meilleurs performeurs publient 2-3 vidéos par semaine', 'type': 'success'},
            {'title': 'Consistance Importante', 'description': 'La régularité est plus importante que la quantité', 'type': 'info'},
            {'title': 'Balance Hero-Hub-Help', 'description': 'Maintenir un équilibre 20-60-20 pour une stratégie optimale', 'type': 'warning'}
        ]
        
        recommendations = {
            'hero_frequency': '0.5',
            'hero_days': 'Lun, Jeu',
            'hub_frequency': '1.5',
            'hub_days': 'Mar, Mer, Sam',
            'help_frequency': '0.5',
            'help_days': 'Ven'
        }
        
        optimal_times = {
            'weekdays': '10:00 AM',
            'weekends': '2:00 PM'
        }
        
        return render_template('frequency_dashboard_sneat_pro.html',
                             competitors=competitors,
                             country_data=country_data,
                             impact_analysis=impact_analysis,
                             total_competitors=len(competitors),
                             frequency_stats=frequency_stats,
                             category_frequency=category_frequency,
                             weekly_pattern=weekly_pattern,
                             competitor_frequencies=competitors,
                             frequency_insights=frequency_insights,
                             recommendations=recommendations,
                             optimal_times=optimal_times,
                             analyzed_videos=sum(c['video_count'] for c in competitors),
                             dev_mode=session.get('dev_mode', False))
        
    except Exception as e:
        print(f"[FREQUENCY_DASHBOARD] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        
        # Données par défaut en cas d'erreur
        default_impact_analysis = {
            'high_frequency_performers': [],
            'low_frequency_performers': [],
            'optimal_frequency_insights': {
                'high_performers_avg_frequency': 2.0,
                'low_performers_avg_frequency': 0.5,
                'frequency_impact': 'positive',
                'recommendation': 'Erreur lors du chargement des données'
            },
            'category_insights': {
                'hero': {'avg_frequency': 0.5, 'avg_engagement': 2.0, 'competitors': 0},
                'hub': {'avg_frequency': 1.5, 'avg_engagement': 3.0, 'competitors': 0},
                'help': {'avg_frequency': 0.8, 'avg_engagement': 2.5, 'competitors': 0}
            }
        }
        
        return render_template('frequency_dashboard_sneat_pro.html', 
                             error=f"Erreur lors du chargement: {str(e)}", 
                             competitors=[], 
                             country_data={}, 
                             impact_analysis=default_impact_analysis,
                             total_competitors=0,
                             frequency_stats={'avg_per_week': 0, 'most_active_day': 'N/A', 'consistency_score': 0, 'optimal_time': 'N/A'},
                             category_frequency={'hero_per_week': 0, 'hero_percentage': 0, 'hub_per_week': 0, 'hub_percentage': 0, 'help_per_week': 0, 'help_percentage': 0},
                             weekly_pattern=[],
                             competitor_frequencies=[],
                             frequency_insights=[],
                             recommendations={'hero_frequency': '0', 'hero_days': 'N/A', 'hub_frequency': '0', 'hub_days': 'N/A', 'help_frequency': '0', 'help_days': 'N/A'},
                             optimal_times={'weekdays': 'N/A', 'weekends': 'N/A'},
                             analyzed_videos=0,
                             dev_mode=session.get('dev_mode', False))


@insights_bp.route('/sentiment-analysis')
@login_required
def sentiment_analysis():
    """Page d'analyse des sentiments avec XLM-RoBERTa multilingue"""
    try:
        import sqlite3
        from pathlib import Path
        
        # Connexion à la base de données des sentiments
        MASSIVE_DB = Path('instance/youtube_emotions_massive.db')
        conn = sqlite3.connect(MASSIVE_DB)
        cursor = conn.cursor()
        
        # Récupérer les statistiques depuis comment_emotions 
        cursor.execute('SELECT COUNT(*) FROM comment_emotions')
        total_comments = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM comment_emotions WHERE emotion_type = "positive"')
        positive_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM comment_emotions WHERE emotion_type = "negative"')
        negative_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM comment_emotions WHERE emotion_type = "neutral"')
        neutral_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT video_id) FROM comment_emotions')
        analyzed_videos = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(confidence) FROM comment_emotions')
        avg_confidence = cursor.fetchone()[0] or 0
        
        # Calculer les pourcentages
        positive_percentage = (positive_count / max(total_comments, 1)) * 100
        negative_percentage = (negative_count / max(total_comments, 1)) * 100
        neutral_percentage = (neutral_count / max(total_comments, 1)) * 100
        
        # Récupérer quelques exemples de commentaires par sentiment
        sentiment_results = {
            'positive': [],
            'negative': [],
            'neutral': []
        }
        
        # Récupérer les commentaires par type
        for emotion_type in ['positive', 'negative', 'neutral']:
            cursor.execute('''
                SELECT ce.comment_id, ce.video_id, ce.confidence, ce.language, 
                       ce.like_count, ce.author_name, cr.comment_text
                FROM comment_emotions ce
                JOIN comments_raw cr ON ce.comment_id = cr.comment_id
                WHERE ce.emotion_type = ?
                ORDER BY ce.confidence DESC
                LIMIT 20
            ''', (emotion_type,))
            
            for row in cursor.fetchall():
                sentiment_results[emotion_type].append({
                    'comment_id': row[0],
                    'video_id': row[1],
                    'confidence': round(row[2], 3),
                    'language': row[3],
                    'like_count': row[4] or 0,
                    'author_name': row[5],
                    'text': row[6][:200] + '...' if row[6] and len(row[6]) > 200 else row[6]
                })
        
        # Récupérer les données par pays pour la heatmap 
        # Note: Utilisation de données simulées car les tables video/concurrent ne sont pas dans cette DB
        cursor.execute("""
            SELECT 
                ce.language as country,
                ce.emotion_type,
                COUNT(*) as count,
                AVG(ce.confidence) as avg_confidence
            FROM comment_emotions ce
            WHERE ce.language IS NOT NULL
            GROUP BY ce.language, ce.emotion_type
            ORDER BY ce.language, ce.emotion_type
        """)
        
        country_sentiment_data = {}
        for row in cursor.fetchall():
            country = row[0]
            emotion = row[1]
            count = row[2]
            confidence = row[3]
            
            if country not in country_sentiment_data:
                country_sentiment_data[country] = {}
            country_sentiment_data[country][emotion] = {
                'count': count,
                'confidence': round(confidence, 3)
            }
        
        # Récupérer les top 5 concurrents par sentiment
        # Note: Utilisation des données d'auteurs comme proxy pour les concurrents
        cursor.execute("""
            SELECT 
                cr.author_name as competitor_name,
                ce.emotion_type,
                COUNT(*) as count,
                AVG(ce.confidence) as avg_confidence,
                AVG(cr.like_count) as avg_likes
            FROM comment_emotions ce
            JOIN comments_raw cr ON ce.comment_id = cr.comment_id
            WHERE cr.author_name IS NOT NULL
            GROUP BY cr.author_name, ce.emotion_type
            HAVING COUNT(*) > 2
            ORDER BY count DESC
            LIMIT 15
        """)
        
        competitor_sentiment_data = []
        for row in cursor.fetchall():
            competitor_sentiment_data.append({
                'competitor': row[0],
                'emotion': row[1], 
                'count': row[2],
                'confidence': round(row[3], 3),
                'avg_likes': round(row[4] or 0, 1)
            })
        
        # Récupérer l'évolution temporelle
        cursor.execute("""
            SELECT 
                DATE(cr.published_at) as date,
                ce.emotion_type,
                COUNT(*) as count,
                AVG(ce.confidence) as avg_confidence
            FROM comment_emotions ce
            JOIN comments_raw cr ON ce.comment_id = cr.comment_id
            WHERE cr.published_at IS NOT NULL
            GROUP BY DATE(cr.published_at), ce.emotion_type
            ORDER BY date DESC
            LIMIT 30
        """)
        
        temporal_sentiment_data = []
        for row in cursor.fetchall():
            temporal_sentiment_data.append({
                'date': row[0],
                'emotion': row[1],
                'count': row[2],
                'confidence': round(row[3], 3)
            })
        
        # Récupérer les vidéos classées par nombre de commentaires positifs
        cursor.execute("""
            SELECT 
                ce.video_id,
                COUNT(CASE WHEN ce.emotion_type = 'positive' THEN 1 END) as positive_count,
                COUNT(CASE WHEN ce.emotion_type = 'negative' THEN 1 END) as negative_count,
                COUNT(CASE WHEN ce.emotion_type = 'neutral' THEN 1 END) as neutral_count,
                COUNT(*) as total_comments,
                AVG(ce.confidence) as avg_confidence,
                MAX(CASE WHEN ce.emotion_type = 'positive' THEN ce.confidence ELSE 0 END) as max_positive_confidence,
                -- Déterminer le sentiment dominant
                CASE 
                    WHEN COUNT(CASE WHEN ce.emotion_type = 'positive' THEN 1 END) >= COUNT(CASE WHEN ce.emotion_type = 'negative' THEN 1 END) 
                         AND COUNT(CASE WHEN ce.emotion_type = 'positive' THEN 1 END) >= COUNT(CASE WHEN ce.emotion_type = 'neutral' THEN 1 END) THEN 'positive'
                    WHEN COUNT(CASE WHEN ce.emotion_type = 'negative' THEN 1 END) >= COUNT(CASE WHEN ce.emotion_type = 'neutral' THEN 1 END) THEN 'negative'
                    ELSE 'neutral'
                END as dominant_sentiment
            FROM comment_emotions ce
            GROUP BY ce.video_id
            HAVING COUNT(CASE WHEN ce.emotion_type = 'positive' THEN 1 END) > 0
            ORDER BY positive_count DESC, total_comments DESC
            LIMIT 100
        """)
        
        top_videos_by_positive = []
        for idx, row in enumerate(cursor.fetchall()):
            top_videos_by_positive.append({
                'rank': idx + 1,
                'video_id': row[0],
                'positive_count': row[1],
                'negative_count': row[2], 
                'neutral_count': row[3],
                'total_comments': row[4],
                'avg_confidence': round(row[5], 2),
                'max_positive_confidence': round(row[6], 2),
                'dominant_sentiment': row[7],
                'positive_percentage': round((row[1] / row[4] * 100) if row[4] > 0 else 0, 1),
                # Mock data for display - in real app would join with video table
                'title': f'Vidéo {row[0]}',
                'thumbnail_url': f'https://i.ytimg.com/vi/{row[0]}/mqdefault.jpg',
                'competitor_name': 'Analysé',
                'view_count': row[4] * 1000,  # Estimate
                'like_count': row[1] * 10,    # Estimate
                'comment_count': row[4],
                'published_at_formatted': '2025'
            })
        
        # Stats pour le template
        stats = {
            'total_videos_analyzed': total_comments,  # Afficher le nombre de commentaires comme "analysés"
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_percentage': round(positive_percentage, 1),
            'negative_percentage': round(negative_percentage, 1),
            'neutral_percentage': round(neutral_percentage, 1),
            'engagement_correlation': round(avg_confidence, 3),
            'country_sentiment_data': country_sentiment_data,
            'competitor_sentiment_data': competitor_sentiment_data,
            'temporal_sentiment_data': temporal_sentiment_data
        }
        
        conn.close()
        
        return render_template('sentiment_analysis_sneat_pro.html',
                             sentiment_results=sentiment_results,
                             all_videos=top_videos_by_positive,  # Les vidéos classées par commentaires positifs
                             stats=stats,
                             current_page=1,
                             total_pages=1,
                             per_page=50,
                             total_videos=total_comments,
                             sentiment_filter='all',
                             sort_by='confidence',
                             order='desc')
                             
    except Exception as e:
        print(f"[SENTIMENT_ANALYSIS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        flash("Erreur lors de l'analyse des sentiments", "error")
        return render_template('sentiment_analysis_sneat_pro.html',
                             sentiment_results={'positive': [], 'negative': [], 'neutral': []},
                             all_videos=[],
                             stats={'total_videos_analyzed': 0, 'positive_count': 0, 'negative_count': 0, 'neutral_count': 0, 'positive_percentage': 0, 'negative_percentage': 0, 'neutral_percentage': 0, 'engagement_correlation': 0},
                             current_page=1,
                             total_pages=1,
                             per_page=50,
                             total_videos=0,
                             sentiment_filter='all',
                             sort_by='confidence',
                             order='desc')