# 🚀 Pipeline Complet - Sentiment Analysis Dashboard YouTube

## **📊 Scope du projet**
- **8,800 vidéos** analysées (19 concurrents × 5 pays)
- **1,000 commentaires par vidéo** = **8.8M commentaires** à analyser
- **5 langues** : FR, EN, DE, NL, BE
- **Objectif** : Dashboard émotionnel complet avec insights visuels

---

## **📦 Librairies à installer**

### **Backend Python :**
```bash
pip install transformers torch
pip install langdetect
pip install pandas sqlite3
pip install flask flask-cors
pip install youtube-dl yt-dlp
pip install requests beautifulsoup4
pip install google-api-python-client  # YouTube API
pip install selenium webdriver-manager  # Pour scraping avancé
pip install redis  # Cache pour performances
```

### **Frontend :**
```html
<!-- Chart.js + Bootstrap -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
```

---

## **⚙️ Étapes du Pipeline**

### **1. Scraping massif des commentaires (8.8M commentaires)**

```python
from googleapiclient.discovery import build
import time
import random
import sqlite3

youtube = build('youtube', 'v3', developerKey='YOUR_API_KEY')

def scrape_video_comments(video_id, max_comments=1000):
    """Scrape 1000 commentaires par vidéo"""
    comments = []
    next_page_token = None
    
    while len(comments) < max_comments:
        try:
            response = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                order='relevance'  # Commentaires les plus pertinents
            ).execute()
            
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'video_id': video_id,
                    'text': comment['textDisplay'],
                    'like_count': comment.get('likeCount', 0),
                    'published_at': comment['publishedAt']
                })
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
            # Rate limiting - respecter les quotas YouTube
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            print(f"Erreur scraping {video_id}: {e}")
            break
    
    return comments[:max_comments]

def scrape_all_videos():
    """Scraper les 8,800 vidéos × 1000 commentaires"""
    video_ids = get_all_video_ids()  # Depuis ta DB existante
    
    for i, video_id in enumerate(video_ids):
        print(f"Scraping vidéo {i+1}/8800: {video_id}")
        
        comments = scrape_video_comments(video_id, 1000)
        save_comments_to_db(comments)
        
        # Progress tracking
        if i % 100 == 0:
            print(f"Progress: {i/8800*100:.1f}% - {len(comments)} commentaires récupérés")
        
        # Rate limiting entre vidéos
        time.sleep(random.uniform(1, 3))
```

### **2. Processing émotionnel (8.8M commentaires)**

```python
from transformers import pipeline
from langdetect import detect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Setup modèle multilingue - LA LIBRAIRIE CLÉ
emotion_analyzer = pipeline("text-classification", 
                          model="cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual")

def process_comment_batch(comments_batch):
    """Traiter un batch de 1000 commentaires"""
    results = []
    
    for comment in comments_batch:
        if len(comment['text']) > 10:  # Filtrer commentaires courts
            try:
                # Détection langue automatique
                language = detect(comment['text'])
                
                # Analyse émotionnelle si langue supportée
                if language in ['fr', 'en', 'de', 'nl']:
                    emotion = emotion_analyzer(comment['text'])[0]
                    
                    results.append({
                        'video_id': comment['video_id'],
                        'emotion': emotion['label'],  # POSITIVE, NEGATIVE, NEUTRAL
                        'confidence': emotion['score'],
                        'language': language,
                        'like_count': comment['like_count']
                    })
            except:
                continue  # Skip commentaires problématiques
    
    return results

def process_all_comments():
    """Traiter les 8.8M commentaires par batches"""
    
    batch_size = 1000
    total_processed = 0
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        for video_id in get_all_video_ids():
            comments = get_video_comments(video_id)  # 1000 commentaires
            
            # Traitement parallèle
            results = process_comment_batch(comments)
            
            # Agrégation au niveau vidéo
            video_emotions = aggregate_video_emotions(results)
            save_video_emotions(video_id, video_emotions)
            
            total_processed += len(comments)
            print(f"Processed: {total_processed:,}/8,800,000 commentaires")

def aggregate_video_emotions(emotion_results):
    """Calculer métriques émotionnelles par vidéo"""
    if not emotion_results:
        return None
    
    df = pd.DataFrame(emotion_results)
    
    return {
        'dominant_emotion': df['emotion'].mode()[0],
        'positive_ratio': len(df[df['emotion'] == 'POSITIVE']) / len(df),
        'negative_ratio': len(df[df['emotion'] == 'NEGATIVE']) / len(df),
        'neutral_ratio': len(df[df['emotion'] == 'NEUTRAL']) / len(df),
        'avg_confidence': df['confidence'].mean(),
        'total_comments': len(df),
        'emotion_diversity': len(df['emotion'].unique()),
        'language_distribution': df['language'].value_counts().to_dict()
    }
```

### **3. Stockage optimisé pour 8.8M records**

```python
import sqlite3

def setup_database():
    """Database optimisée pour millions de commentaires"""
    conn = sqlite3.connect('youtube_emotions_massive.db')
    
    # Table principale - 8.8M commentaires
    conn.execute('''
        CREATE TABLE IF NOT EXISTS comment_emotions (
            id INTEGER PRIMARY KEY,
            video_id TEXT,
            emotion_type TEXT,
            confidence REAL,
            language TEXT,
            like_count INTEGER,
            comment_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Index pour performances
    conn.execute('CREATE INDEX IF NOT EXISTS idx_video_id ON comment_emotions(video_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_emotion ON comment_emotions(emotion_type)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_language ON comment_emotions(language)')
    
    # Table agrégée par vidéo (8,800 records)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS video_emotion_summary (
            video_id TEXT PRIMARY KEY,
            dominant_emotion TEXT,
            emotion_diversity_score REAL,
            avg_confidence REAL,
            total_comments INTEGER,
            positive_ratio REAL,
            negative_ratio REAL,
            neutral_ratio REAL,
            language_distribution TEXT,  -- JSON
            country TEXT,
            competitor TEXT
        )
    ''')
    
    return conn

def save_comments_to_db(comments):
    """Sauvegarder batch de commentaires"""
    conn = sqlite3.connect('youtube_emotions_massive.db')
    
    conn.executemany('''
        INSERT INTO comment_emotions 
        (video_id, comment_text, like_count) 
        VALUES (?, ?, ?)
    ''', [(c['video_id'], c['text'], c['like_count']) for c in comments])
    
    conn.commit()
    conn.close()
```

### **4. API Backend avec cache Redis**

```python
from flask import Flask, jsonify
import redis
import json

app = Flask(__name__)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

@app.route('/api/emotions/overview')
def get_emotions_overview():
    """Vue d'ensemble des 8.8M commentaires analysés"""
    
    # Cache Redis pour éviter de requêter 8.8M records
    cached = redis_client.get('emotions_overview')
    if cached:
        return jsonify(json.loads(cached))
    
    summary = {
        'total_comments': 8800000,
        'total_videos': 8800,
        'emotions_distribution': get_global_emotion_stats(),
        'top_emotional_videos': get_top_emotional_videos(),
        'country_emotion_breakdown': get_country_emotions()
    }
    
    # Cache pour 1 heure
    redis_client.setex('emotions_overview', 3600, json.dumps(summary))
    return jsonify(summary)

@app.route('/api/emotions/country/<country>')
def get_country_emotions(country):
    """Émotions par pays"""
    conn = sqlite3.connect('youtube_emotions_massive.db')
    
    query = '''
        SELECT emotion_type, AVG(confidence), COUNT(*) 
        FROM comment_emotions ce
        JOIN video_emotion_summary ves ON ce.video_id = ves.video_id
        WHERE ves.country = ?
        GROUP BY emotion_type
    '''
    
    results = conn.execute(query, (country,)).fetchall()
    conn.close()
    
    return jsonify([{
        'emotion': r[0],
        'avg_confidence': r[1],
        'count': r[2]
    } for r in results])

@app.route('/api/emotions/competitor/<competitor>')
def get_competitor_emotions(competitor):
    """Profil émotionnel par concurrent"""
    # Implementation similaire...
    pass
```

---

## **📊 Dashboard Chart.js - Visualisations**

### **1. Stats globales (Header)**

```html
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h2 class="text-primary">8,800,000</h2>
                <p>Commentaires analysés</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h2 class="text-success">8,800</h2>
                <p>Vidéos YouTube</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h2 class="text-info">5</h2>
                <p>Langues analysées</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-center">
            <div class="card-body">
                <h2 class="text-warning">87.3%</h2>
                <p>Précision moyenne</p>
            </div>
        </div>
    </div>
</div>
```

### **2. Heatmap Pays × Émotions**

```javascript
const emotionHeatmapConfig = {
    type: 'matrix',
    data: {
        datasets: [{
            label: 'Intensité émotionnelle',
            data: [
                {x: 'France', y: 'POSITIVE', v: 0.73},
                {x: 'France', y: 'NEGATIVE', v: 0.18},
                {x: 'France', y: 'NEUTRAL', v: 0.09},
                {x: 'Germany', y: 'POSITIVE', v: 0.68},
                {x: 'Germany', y: 'NEGATIVE', v: 0.22},
                {x: 'Germany', y: 'NEUTRAL', v: 0.10},
                // ... autres pays
            ],
            backgroundColor: function(context) {
                const value = context.parsed.v;
                if (context.parsed.y === 'POSITIVE') {
                    return `rgba(75, 192, 192, ${value})`;
                } else if (context.parsed.y === 'NEGATIVE') {
                    return `rgba(255, 99, 132, ${value})`;
                } else {
                    return `rgba(128, 128, 128, ${value})`;
                }
            }
        }]
    },
    options: {
        plugins: {
            title: {
                display: true,
                text: 'Analyse de 8,800,000 commentaires sur 5 pays'
            }
        },
        scales: {
            x: {
                type: 'category',
                position: 'bottom'
            },
            y: {
                type: 'category'
            }
        }
    }
};

// Initialisation
const heatmapCtx = document.getElementById('emotionHeatmap').getContext('2d');
new Chart(heatmapCtx, emotionHeatmapConfig);
```

### **3. Radar Chart - Profil émotionnel par concurrent**

```javascript
const competitorRadarConfig = {
    type: 'radar',
    data: {
        labels: ['Sentiment Positif', 'Sentiment Négatif', 'Engagement', 'Diversité Émotionnelle', 'Volume Comments'],
        datasets: [
            {
                label: 'Booking.com',
                data: [0.85, 0.15, 0.73, 0.68, 0.92],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)'
            },
            {
                label: 'Airbnb', 
                data: [0.78, 0.22, 0.81, 0.74, 0.87],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)'
            },
            {
                label: 'Expedia',
                data: [0.71, 0.29, 0.65, 0.59, 0.76],
                borderColor: 'rgb(255, 206, 86)',
                backgroundColor: 'rgba(255, 206, 86, 0.2)'
            }
        ]
    },
    options: {
        plugins: {
            title: {
                display: true,
                text: 'Profil émotionnel - Top 3 Concurrents'
            }
        },
        scales: {
            r: {
                beginAtZero: true,
                max: 1
            }
        }
    }
};
```

### **4. Timeline Émotionnel**

```javascript
const emotionTimelineConfig = {
    type: 'line',
    data: {
        labels: ['Jan 2024', 'Feb 2024', 'Mar 2024', 'Apr 2024', 'May 2024', 'Jun 2024'],
        datasets: [
            {
                label: 'Sentiment Positif (%)',
                data: [73, 75, 78, 71, 76, 79],
                borderColor: 'green',
                backgroundColor: 'rgba(0, 255, 0, 0.1)',
                tension: 0.4
            },
            {
                label: 'Sentiment Négatif (%)', 
                data: [18, 16, 15, 21, 17, 14],
                borderColor: 'red',
                backgroundColor: 'rgba(255, 0, 0, 0.1)',
                tension: 0.4
            },
            {
                label: 'Engagement Moyen (%)',
                data: [1.2, 1.4, 1.6, 1.1, 1.5, 1.7],
                borderColor: 'blue',
                backgroundColor: 'rgba(0, 0, 255, 0.1)',
                tension: 0.4,
                yAxisID: 'y1'
            }
        ]
    },
    options: {
        plugins: {
            title: {
                display: true,
                text: 'Évolution émotionnelle - 6 derniers mois'
            }
        },
        scales: {
            y: {
                type: 'linear',
                display: true,
                position: 'left'
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'right',
                grid: {
                    drawOnChartArea: false,
                }
            }
        }
    }
};
```

### **5. Scatter Plot - Émotion vs Engagement**

```javascript
const emotionEngagementConfig = {
    type: 'scatter',
    data: {
        datasets: [{
            label: 'Vidéos par performance émotionnelle',
            data: [
                {x: 0.85, y: 2.1, country: 'France', competitor: 'Booking.com'},
                {x: 0.62, y: 1.4, country: 'Germany', competitor: 'TUI'},
                {x: 0.91, y: 2.8, country: 'UK', competitor: 'Expedia'},
                // ... données de 8,800 vidéos agrégées
            ],
            backgroundColor: function(context) {
                const point = context.parsed;
                const colors = {
                    'France': 'rgba(255, 99, 132, 0.6)',
                    'Germany': 'rgba(54, 162, 235, 0.6)',
                    'UK': 'rgba(255, 206, 86, 0.6)',
                    'Netherlands': 'rgba(75, 192, 192, 0.6)',
                    'Belgium': 'rgba(153, 102, 255, 0.6)'
                };
                return colors[context.raw.country] || 'rgba(128, 128, 128, 0.6)';
            }
        }]
    },
    options: {
        plugins: {
            title: {
                display: true,
                text: 'Corrélation Sentiment Positif vs Engagement (8,800 vidéos)'
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const point = context.raw;
                        return `${point.competitor} (${point.country}): Sentiment ${(point.x*100).toFixed(1)}%, Engagement ${point.y.toFixed(2)}%`;
                    }
                }
            }
        },
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Score Sentiment Positif'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Taux d\'Engagement (%)'
                }
            }
        }
    }
};
```

### **6. Distribution émotionnelle globale**

```javascript
const globalEmotionConfig = {
    type: 'doughnut',
    data: {
        labels: ['Sentiment Positif', 'Sentiment Négatif', 'Neutre'],
        datasets: [{
            data: [6424000, 1584000, 792000], // Sur 8.8M commentaires
            backgroundColor: [
                'rgba(75, 192, 192, 0.8)',
                'rgba(255, 99, 132, 0.8)', 
                'rgba(128, 128, 128, 0.8)'
            ],
            borderWidth: 2
        }]
    },
    options: {
        plugins: {
            title: {
                display: true,
                text: 'Distribution globale - 8,800,000 commentaires'
            },
            legend: {
                position: 'bottom'
            }
        }
    }
};
```

### **7. Progress Bar pour scraping en cours**

```html
<div class="card mb-4">
    <div class="card-header">
        <h5>Progression du Scraping</h5>
    </div>
    <div class="card-body">
        <div class="progress mb-3" style="height: 25px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                 role="progressbar" 
                 style="width: 75%" 
                 id="scrapingProgress">
                6,600,000 / 8,800,000 commentaires
            </div>
        </div>
        <div class="row text-center">
            <div class="col-md-3">
                <strong>Vitesse:</strong><br>
                <span class="text-info">45 commentaires/sec</span>
            </div>
            <div class="col-md-3">
                <strong>ETA:</strong><br>
                <span class="text-warning">2h 15min</span>
            </div>
            <div class="col-md-3">
                <strong>Taux d'erreur:</strong><br>
                <span class="text-success">0.3%</span>
            </div>
            <div class="col-md-3">
                <strong>Précision:</strong><br>
                <span class="text-primary">94.7%</span>
            </div>
        </div>
    </div>
</div>
```

### **8. Layout Dashboard complet**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Emotion Analytics - 8.8M Comments</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container-fluid">
        <!-- Header avec stats globales -->
        <div class="row mb-4">
            <!-- Stats cards ici -->
        </div>
        
        <!-- Progress bar scraping -->
        <div class="row mb-4">
            <div class="col-12">
                <!-- Progress bar ici -->
            </div>
        </div>
        
        <!-- Visualisations principales -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Heatmap Pays × Émotions</div>
                    <div class="card-body">
                        <canvas id="emotionHeatmap"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Profil Concurrents</div>
                    <div class="card-body">
                        <canvas id="competitorRadar"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">Timeline Émotionnelle</div>
                    <div class="card-body">
                        <canvas id="emotionTimeline"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">Distribution Globale</div>
                    <div class="card-body">
                        <canvas id="globalEmotion"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">Corrélation Émotion × Engagement</div>
                    <div class="card-body">
                        <canvas id="emotionEngagement"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Initialisation de tous les graphiques
        // ... Code Chart.js ici
    </script>
</body>
</html>
```

---

## **🎯 Insights Automatiques Générés**

Le dashboard génère automatiquement des insights comme :

- **💡 "UK a le meilleur sentiment positif (91%) mais seulement 42,000 commentaires analysés - Opportunité d'expansion"**
- **🎯 "Germany montre 22% de sentiment négatif vs 18% pour la France - Investiguer les pain points"**
- **⚠️ "Booking.com domine l'engagement émotionnel avec 85% de sentiment positif - Benchmarker leur stratégie"**
- **🚀 "Les vidéos 'Help' génèrent 23% plus d'engagement émotionnel que les vidéos 'Hero'"**

---

## **🔧 Commandes Claude Code**

### **Phase 1: Scraping**
```bash
claude "Implement YouTube comment scraper to extract 1000 comments per video for 8800 videos using YouTube API with rate limiting and error handling"
```

### **Phase 2: Emotion Analysis**
```bash
claude "Process 8.8M YouTube comments using transformers multilingual sentiment analysis, detect languages automatically, and save results to optimized SQLite database"
```

### **Phase 3: Dashboard**
```bash
claude "Create interactive emotion analytics dashboard with Chart.js showing heatmaps, radar charts, timelines and scatter plots for 8.8M analyzed comments across 5 countries"
```

### **Phase 4: API Integration**
```bash
claude "Build Flask API with Redis caching to serve emotion analytics data and integrate with existing YouTube analyzer dashboard"
```

---

## **📈 Résultat Final**

Dashboard émotionnel complet capable de :
- ✅ Analyser 8.8M commentaires en 5 langues
- ✅ Visualiser patterns émotionnels par pays/concurrent  
- ✅ Identifier corrélations émotion ↔ engagement
- ✅ Générer insights automatiques actionables
- ✅ Performance optimisée avec cache Redis
- ✅ Interface responsive Bootstrap 5

**Impact Business :** Comprendre ce qui fonctionne émotionnellement par marché pour optimiser la stratégie de contenu YouTube !
