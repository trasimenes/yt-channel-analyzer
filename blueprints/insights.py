"""
Insights Blueprint
Handles all analytics, insights, and dashboard routes.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, render_template, request, flash, session
from blueprints.auth import login_required
from services.insights_service import BrandInsightsService
from services.country_metrics_service import CountryMetricsService


insights_bp = Blueprint('insights', __name__)


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


@insights_bp.route('/country-insights')
@login_required
def country_insights():
    """Page des insights par pays avec 7 métriques clés"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        # Paramètres de la requête
        selected_country = request.args.get('country', 'France')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtenir la liste des pays disponibles
        cursor.execute("SELECT DISTINCT country FROM concurrent WHERE country IS NOT NULL ORDER BY country")
        available_countries = [row[0] for row in cursor.fetchall()]
        
        if not available_countries:
            conn.close()
            return render_template('country_insights_sneat_pro.html', 
                                 insights={'success': False, 'error': 'Aucun pays trouvé'})
        
        # Si le pays sélectionné n'est pas dans la liste, prendre le premier
        if selected_country not in available_countries:
            selected_country = available_countries[0]
        
        # Utiliser le service pour calculer les métriques
        service = CountryMetricsService(conn)
        country_metrics = service.calculate_country_7_metrics(selected_country)
        
        # Ajouter le nombre de concurrents
        cursor.execute("SELECT COUNT(*) FROM concurrent WHERE country = ?", (selected_country,))
        country_metrics['competitors_count'] = cursor.fetchone()[0]
        
        conn.close()
        
        insights_data = {
            'success': True,
            'country': selected_country,
            'available_countries': available_countries,
            'metrics': country_metrics
        }
        
        return render_template('country_insights_sneat_pro.html', 
                             insights=insights_data)
        
    except Exception as e:
        print(f"[COUNTRY_INSIGHTS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return render_template('country_insights_sneat_pro.html',
                             insights={'success': False, 'error': str(e)})


@insights_bp.route('/countries-analysis')
@login_required
def countries_analysis():
    """Page d'analyse comparative des pays"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Statistiques par pays avec protection contre les outliers
        cursor.execute("""
            SELECT 
                c.country as name,
                COUNT(DISTINCT c.id) as competitor_count,
                COUNT(v.id) as total_videos,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(SUM(v.like_count), 0) as total_likes,
                COALESCE(SUM(v.comment_count), 0) as total_comments,
                COALESCE(AVG(v.view_count), 0) as avg_views_per_video,
                CASE 
                    WHEN SUM(v.view_count) > 0 THEN 
                        (CAST(SUM(v.like_count) + SUM(v.comment_count) AS FLOAT) / SUM(v.view_count) * 100)
                    ELSE 0 
                END as engagement_rate
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            WHERE c.country IS NOT NULL 
            AND c.country != ''
            AND (v.view_count IS NULL OR v.view_count <= 10000000)  -- Protection contre outliers
            GROUP BY c.country
            HAVING COUNT(DISTINCT c.id) > 0  -- Au moins un concurrent
            ORDER BY total_views DESC
        """)
        
        countries = []
        for row in cursor.fetchall():
            countries.append({
                'name': row[0],
                'competitor_count': row[1],
                'total_videos': row[2],
                'total_views': row[3],
                'total_likes': row[4],
                'total_comments': row[5],
                'avg_views_per_video': int(row[6]) if row[6] else 0,
                'engagement_rate': round(row[7], 2) if row[7] else 0.0
            })
        
        # Statistiques globales
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT c.country) as total_countries,
                COUNT(DISTINCT c.id) as total_competitors,
                COUNT(v.id) as total_videos,
                COALESCE(SUM(v.view_count), 0) as total_views,
                COALESCE(AVG(
                    CASE 
                        WHEN v.view_count > 0 THEN 
                            (CAST(v.like_count + v.comment_count AS FLOAT) / v.view_count * 100)
                        ELSE 0 
                    END
                ), 0) as avg_engagement_rate
            FROM concurrent c
            LEFT JOIN video v ON c.id = v.concurrent_id
            WHERE c.country IS NOT NULL 
            AND c.country != ''
            AND (v.view_count IS NULL OR v.view_count <= 10000000)
        """)
        
        global_stats_row = cursor.fetchone()
        global_stats = {
            'total_countries': global_stats_row[0] if global_stats_row else 0,
            'total_competitors': global_stats_row[1] if global_stats_row else 0,
            'total_videos': global_stats_row[2] if global_stats_row else 0,
            'total_views': global_stats_row[3] if global_stats_row else 0,
            'avg_engagement_rate': round(global_stats_row[4], 2) if global_stats_row and global_stats_row[4] else 0.0
        }
        
        conn.close()
        
        return render_template('countries_analysis_sneat_pro.html',
                             countries=countries,
                             global_stats=global_stats)
                             
    except Exception as e:
        print(f"[COUNTRIES_ANALYSIS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        flash("Erreur lors du chargement de l'analyse des pays", "error")
        return render_template('countries_analysis_sneat_pro.html',
                             countries=[],
                             global_stats={'total_countries': 0, 'total_competitors': 0, 
                                         'total_videos': 0, 'total_views': 0, 'avg_engagement_rate': 0.0})


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
            
            # Analyser les titres pour extraire les mots-clés populaires
            cursor.execute("""
                SELECT title, view_count, like_count, comment_count
                FROM video 
                WHERE title IS NOT NULL 
                AND view_count > 1000
                ORDER BY view_count DESC 
                LIMIT 1000
            """)
            
            videos = cursor.fetchall()
            word_stats = {}
            
            # Mots vides à ignorer
            stop_words = {'de', 'la', 'le', 'et', 'à', 'un', 'une', 'du', 'des', 'les', 'en', 'pour', 'avec', 'sur', 'dans', 'par', 'ce', 'qui', 'que', 'est', 'il', 'se', 'ne', 'pas', 'tout', 'être', 'avoir', 'faire', 'voir', 'plus', 'bien', 'où', 'comment', 'quand'}
            
            for video in videos:
                title = video[0].lower()
                view_count = video[1] or 0
                like_count = video[2] or 0
                
                words = title.split()
                for word in words:
                    # Nettoyer le mot
                    word = ''.join(c for c in word if c.isalnum())
                    if len(word) > 3 and word not in stop_words:
                        if word not in word_stats:
                            word_stats[word] = {'count': 0, 'total_views': 0, 'total_likes': 0}
                        word_stats[word]['count'] += 1
                        word_stats[word]['total_views'] += view_count
                        word_stats[word]['total_likes'] += like_count
            
            # Trier par popularité (nombre d'occurrences)
            top_topics = sorted(word_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:20]
            
            topics_data = {
                'top_keywords': [
                    {
                        'keyword': topic[0],
                        'count': topic[1]['count'],
                        'total_views': topic[1]['total_views'],
                        'total_likes': topic[1]['total_likes'],
                        'avg_views': topic[1]['total_views'] // max(topic[1]['count'], 1)
                    }
                    for topic in top_topics
                ],
                'analysis_method': 'basic_keyword_extraction',
                'total_videos_analyzed': len(videos)
            }
            
            conn.close()
        
        return render_template('top_topics_sneat_pro.html',
                             topics_data=topics_data,
                             analysis_status=analysis_status,
                             has_advanced_results=bool(advanced_results))
                             
    except Exception as e:
        print(f"[TOP_TOPICS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        flash("Erreur lors de l'analyse des sujets", "error")
        return render_template('top_topics_sneat_pro.html',
                             topics_data={'top_keywords': [], 'analysis_method': 'error', 'total_videos_analyzed': 0},
                             analysis_status='error',
                             has_advanced_results=False)


@insights_bp.route('/sentiment-analysis')
@login_required
def sentiment_analysis():
    """Page d'analyse des sentiments"""
    try:
        from yt_channel_analyzer.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Analyse basique des sentiments basée sur les mots-clés
        positive_keywords = ['amazing', 'beautiful', 'fantastic', 'wonderful', 'great', 'excellent', 'perfect', 'love', 'best', 'awesome']
        negative_keywords = ['bad', 'terrible', 'awful', 'worst', 'hate', 'horrible', 'boring', 'stupid']
        
        # Analyser les titres de vidéos
        cursor.execute("""
            SELECT 
                v.title,
                v.view_count,
                v.like_count,
                v.comment_count,
                c.name as competitor_name
            FROM video v
            JOIN concurrent c ON v.concurrent_id = c.id
            WHERE v.title IS NOT NULL
            AND v.view_count > 100
            ORDER BY v.view_count DESC
            LIMIT 1000
        """)
        
        videos = cursor.fetchall()
        
        sentiment_results = {
            'positive': [],
            'negative': [],
            'neutral': []
        }
        
        for video in videos:
            title = video[0].lower()
            view_count = video[1] or 0
            like_count = video[2] or 0
            comment_count = video[3] or 0
            competitor_name = video[4]
            
            engagement = ((like_count + comment_count) / max(view_count, 1)) * 100
            
            video_data = {
                'title': video[0],
                'view_count': view_count,
                'like_count': like_count,
                'comment_count': comment_count,
                'competitor_name': competitor_name,
                'engagement': round(engagement, 2)
            }
            
            # Classification simple par mots-clés
            has_positive = any(keyword in title for keyword in positive_keywords)
            has_negative = any(keyword in title for keyword in negative_keywords)
            
            if has_positive and not has_negative:
                sentiment_results['positive'].append(video_data)
            elif has_negative and not has_positive:
                sentiment_results['negative'].append(video_data)
            else:
                sentiment_results['neutral'].append(video_data)
        
        # Limiter les résultats
        for category in sentiment_results:
            sentiment_results[category] = sentiment_results[category][:20]
        
        # Calculer les statistiques
        total_analyzed = len(videos)
        
        # Calculer la corrélation engagement/sentiment (approximation)
        engagement_correlation = 0.0
        if total_analyzed > 10:  # Seulement si on a assez de données
            try:
                # Corrélation simple : comparer engagement moyen des vidéos positives vs négatives
                positive_engagements = [v['engagement'] for v in sentiment_results['positive'] if v['engagement'] > 0]
                negative_engagements = [v['engagement'] for v in sentiment_results['negative'] if v['engagement'] > 0]
                
                if positive_engagements and negative_engagements:
                    avg_pos_engagement = sum(positive_engagements) / len(positive_engagements)
                    avg_neg_engagement = sum(negative_engagements) / len(negative_engagements) 
                    
                    # Si l'engagement positif > négatif, corrélation positive
                    if avg_pos_engagement > avg_neg_engagement:
                        engagement_correlation = min(0.8, (avg_pos_engagement - avg_neg_engagement) / max(avg_pos_engagement, 1) * 2)
                    else:
                        engagement_correlation = max(-0.3, (avg_pos_engagement - avg_neg_engagement) / max(avg_neg_engagement, 1) * 2)
            except (ValueError, TypeError, ZeroDivisionError, KeyError) as e:
                print(f"[WARNING] Error calculating engagement correlation: {e}")
                engagement_correlation = 0.2  # Valeur par défaut positive
        
        stats = {
            'total_videos_analyzed': total_analyzed,
            'positive_count': len(sentiment_results['positive']),
            'negative_count': len(sentiment_results['negative']),
            'neutral_count': len(sentiment_results['neutral']),
            'engagement_correlation': round(engagement_correlation, 3)
        }
        
        conn.close()
        
        return render_template('sentiment_analysis_sneat_pro.html',
                             sentiment_results=sentiment_results,
                             stats=stats)
                             
    except Exception as e:
        print(f"[SENTIMENT_ANALYSIS] ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        flash("Erreur lors de l'analyse des sentiments", "error")
        return render_template('sentiment_analysis_sneat_pro.html',
                             sentiment_results={'positive': [], 'negative': [], 'neutral': []},
                             stats={'total_videos_analyzed': 0, 'positive_count': 0, 'negative_count': 0, 'neutral_count': 0, 'engagement_correlation': 0})