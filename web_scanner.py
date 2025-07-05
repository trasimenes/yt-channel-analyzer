#!/usr/bin/env python3
"""
Web Scanner - Interface web simple pour scanner des graphiques
Pas besoin de tkinter, fonctionne dans le navigateur
"""

from flask import Flask, render_template, request, jsonify
import pyautogui
import time
import os
import json
import threading
from datetime import datetime

app = Flask(__name__)

class WebScanner:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "web_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        pyautogui.FAILSAFE = False
        
        # Région par défaut
        screen_width, screen_height = pyautogui.size()
        self.region = {
            'x': screen_width // 4,
            'y': screen_height // 4,
            'width': screen_width // 2,
            'height': screen_height // 2
        }
    
    def perform_scan(self, region, duration, interval):
        """
        Effectuer le scan horizontal
        """
        try:
            self.scanning = True
            self.scan_data = []
            
            num_captures = int(duration / interval)
            
            # Positions de début et fin
            start_x = region['x'] + 20
            end_x = region['x'] + region['width'] - 20
            start_y = region['y'] + region['height'] // 2
            end_y = start_y
            
            # Étapes
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                # Position actuelle
                current_x = start_x + (i * step_x)
                current_y = start_y
                
                # Déplacer et capturer
                pyautogui.moveTo(current_x, current_y, duration=0.1)
                screenshot = pyautogui.screenshot()
                
                # Sauvegarder
                timestamp = int(time.time() * 1000)
                filename = f"web_scan_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                screenshot.save(filepath)
                
                # Stocker
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': current_y,
                    'filename': filename,
                    'timestamp': time.time()
                })
                
                time.sleep(interval)
            
            # Sauvegarder métadonnées
            if self.scan_data:
                self.save_metadata(region, duration, interval)
                
        except Exception as e:
            print(f"Erreur scan: {e}")
        finally:
            self.scanning = False
    
    def save_metadata(self, region, duration, interval):
        """
        Sauvegarder les métadonnées
        """
        timestamp = int(time.time())
        metadata_file = os.path.join(self.output_dir, f"metadata_{timestamp}.json")
        
        metadata = {
            'scan_info': {
                'total_captures': len(self.scan_data),
                'duration': duration,
                'interval': interval,
                'region': region,
                'scan_date': datetime.now().isoformat()
            },
            'captures': self.scan_data
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

# Instance globale
scanner = WebScanner()

@app.route('/')
def index():
    """
    Page principale
    """
    screen_width, screen_height = pyautogui.size()
    
    # HTML intégré directement
    html_template = '''<!DOCTYPE html>
<html>
<head>
    <title>Graph Scanner Web</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .control-group { margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
        .control-group h3 { margin-top: 0; color: #d32f2f; display: flex; align-items: center; }
        .input-row { display: flex; gap: 15px; margin: 10px 0; flex-wrap: wrap; }
        .input-group { display: flex; flex-direction: column; min-width: 120px; }
        .input-group label { font-weight: bold; margin-bottom: 5px; color: #333; }
        .input-group input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
        .btn { padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px; transition: all 0.3s; }
        .btn-primary { background: #d32f2f; color: white; }
        .btn-primary:hover { background: #b71c1c; }
        .btn-secondary { background: #666; color: white; }
        .btn-secondary:hover { background: #555; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .status { padding: 12px; margin: 15px 0; border-radius: 6px; font-weight: bold; }
        .status.success { background: #e8f5e8; color: #2e7d2e; border: 1px solid #4caf50; }
        .status.error { background: #ffe8e8; color: #d32f2f; border: 1px solid #f44336; }
        .preview { background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 15px 0; border: 1px solid #e0e0e0; }
        .rectangle-preview { 
            border: 3px solid #d32f2f; 
            background: rgba(211, 47, 47, 0.1); 
            position: relative;
            margin: 15px 0;
            padding: 20px;
            border-radius: 4px;
            text-align: center;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .button-container { text-align: center; margin: 30px 0; }
        .instructions { background: #e3f2fd; padding: 20px; border-radius: 8px; border-left: 4px solid #2196f3; }
        .instructions ol { margin: 10px 0; padding-left: 20px; }
        .instructions li { margin: 8px 0; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #d32f2f; margin-bottom: 10px; }
        .stat-badge { background: #2196f3; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-left: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Graph Scanner Web</h1>
            <p>Interface web pour scanner des graphiques YouTube Analytics avec balayage horizontal automatique</p>
        </div>
        
        <div class="control-group">
            <h3>🔴 Région de scan (Rectangle rouge) <span class="stat-badge">{{ screen_width }} x {{ screen_height }} px</span></h3>
            <div class="input-row">
                <div class="input-group">
                    <label>Position X:</label>
                    <input type="number" id="region-x" value="{{ region_x }}" min="0" max="{{ screen_width }}">
                </div>
                <div class="input-group">
                    <label>Position Y:</label>
                    <input type="number" id="region-y" value="{{ region_y }}" min="0" max="{{ screen_height }}">
                </div>
                <div class="input-group">
                    <label>Largeur:</label>
                    <input type="number" id="region-width" value="{{ region_width }}" min="100" max="{{ screen_width }}">
                </div>
                <div class="input-group">
                    <label>Hauteur:</label>
                    <input type="number" id="region-height" value="{{ region_height }}" min="100" max="{{ screen_height }}">
                </div>
            </div>
        </div>
        
        <div class="control-group">
            <h3>⚙️ Configuration du scan</h3>
            <div class="input-row">
                <div class="input-group">
                    <label>Durée (secondes):</label>
                    <input type="number" id="duration" value="10" min="1" max="60" step="0.5">
                </div>
                <div class="input-group">
                    <label>Intervalle (secondes):</label>
                    <input type="number" id="interval" value="0.25" min="0.1" max="2" step="0.05">
                </div>
                <div class="input-group">
                    <label>Captures estimées:</label>
                    <input type="text" id="captures-estimate" readonly style="background: #f0f0f0;">
                </div>
            </div>
        </div>
        
        <div class="preview">
            <h3>📐 Aperçu de la région de scan</h3>
            <div id="rectangle-preview" class="rectangle-preview">
                <p>🔴 Rectangle rouge simulé - Le scan ira de gauche à droite dans cette zone</p>
            </div>
            <p><strong>Écran détecté:</strong> {{ screen_width }} x {{ screen_height }} pixels</p>
        </div>
        
        <div class="button-container">
            <button id="start-btn" class="btn btn-primary" onclick="startScan()">
                🚀 Commencer le scan horizontal
            </button>
            <button id="stop-btn" class="btn btn-secondary" onclick="stopScan()" disabled>
                ⏹️ Arrêter le scan
            </button>
        </div>
        
        <div id="status" class="status" style="display: none;"></div>
        
        <div class="instructions">
            <h3>📋 Mode d'emploi</h3>
            <ol>
                <li><strong>Ajustez le rectangle rouge</strong> ci-dessus pour couvrir votre graphique</li>
                <li><strong>Ouvrez YouTube Analytics</strong> dans un autre onglet/fenêtre</li>
                <li><strong>Positionnez le graphique</strong> sous le rectangle rouge (utilisez les coordonnées)</li>
                <li><strong>Configurez la durée</strong> (10-20 secondes recommandé)</li>
                <li><strong>Cliquez "Commencer"</strong> et basculez vers votre graphique</li>
                <li><strong>Le scan va de gauche à droite</strong> automatiquement</li>
                <li><strong>Les captures sont sauvegardées</strong> dans le dossier web_scans/</li>
            </ol>
            <p><strong>💡 Astuce:</strong> Pour YouTube Analytics, utilisez région ~250x200 avec largeur 1100x400</p>
        </div>
    </div>
    
    <script>
        let scanInterval;
        
        function updatePreview() {
            const x = parseInt(document.getElementById('region-x').value) || 0;
            const y = parseInt(document.getElementById('region-y').value) || 0;
            const width = parseInt(document.getElementById('region-width').value) || 100;
            const height = parseInt(document.getElementById('region-height').value) || 100;
            
            const duration = parseFloat(document.getElementById('duration').value) || 1;
            const interval = parseFloat(document.getElementById('interval').value) || 0.25;
            const estimatedCaptures = Math.floor(duration / interval);
            
            document.getElementById('captures-estimate').value = estimatedCaptures + ' captures';
            
            const preview = document.getElementById('rectangle-preview');
            const scale = Math.min(400 / width, 200 / height, 1);
            const previewWidth = Math.max(200, width * scale);
            const previewHeight = Math.max(60, height * scale);
            
            preview.style.width = previewWidth + 'px';
            preview.style.height = previewHeight + 'px';
            preview.innerHTML = `<p>🔴 Rectangle: (${x}, ${y}) → ${width} x ${height} px<br/>
                                Scan: ${estimatedCaptures} captures en ${duration}s</p>`;
        }
        
        function startScan() {
            const region = {
                x: parseInt(document.getElementById('region-x').value),
                y: parseInt(document.getElementById('region-y').value),
                width: parseInt(document.getElementById('region-width').value),
                height: parseInt(document.getElementById('region-height').value)
            };
            
            const duration = parseFloat(document.getElementById('duration').value);
            const interval = parseFloat(document.getElementById('interval').value);
            
            // Validation
            if (region.width < 100 || region.height < 50) {
                showStatus('❌ Rectangle trop petit (min 100x50)', 'error');
                return;
            }
            
            showStatus('🚀 Démarrage du scan... Basculez vers votre graphique !', 'success');
            
            setTimeout(() => {
                fetch('/api/start_scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({region, duration, interval})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatus('✅ Scan en cours ! Le curseur bouge sur votre graphique', 'success');
                        document.getElementById('start-btn').disabled = true;
                        document.getElementById('stop-btn').disabled = false;
                        startStatusPolling();
                    } else {
                        showStatus('❌ Erreur: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showStatus('❌ Erreur de connexion: ' + error, 'error');
                });
            }, 2000); // 2 secondes pour laisser le temps de basculer
        }
        
        function stopScan() {
            fetch('/api/stop_scan', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                showStatus('⏹️ Scan arrêté par l\\'utilisateur', 'success');
                document.getElementById('start-btn').disabled = false;
                document.getElementById('stop-btn').disabled = true;
                stopStatusPolling();
            })
            .catch(error => {
                showStatus('❌ Erreur lors de l\\'arrêt: ' + error, 'error');
            });
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.innerHTML = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }
        
        function startStatusPolling() {
            scanInterval = setInterval(() => {
                fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (!data.scanning) {
                        showStatus(`🎉 Scan terminé ! ${data.captures_count} captures sauvegardées`, 'success');
                        document.getElementById('start-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = true;
                        stopStatusPolling();
                    } else {
                        showStatus(`📸 Scan en cours... ${data.captures_count} captures réalisées`, 'success');
                    }
                });
            }, 1000);
        }
        
        function stopStatusPolling() {
            if (scanInterval) {
                clearInterval(scanInterval);
            }
        }
        
        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            updatePreview();
            
            // Mettre à jour l'aperçu en temps réel
            ['region-x', 'region-y', 'region-width', 'region-height', 'duration', 'interval'].forEach(id => {
                document.getElementById(id).addEventListener('input', updatePreview);
            });
        });
    </script>
</body>
</html>'''
    
    return html_template.replace('{{ screen_width }}', str(screen_width)) \
                       .replace('{{ screen_height }}', str(screen_height)) \
                       .replace('{{ region_x }}', str(scanner.region['x'])) \
                       .replace('{{ region_y }}', str(scanner.region['y'])) \
                       .replace('{{ region_width }}', str(scanner.region['width'])) \
                       .replace('{{ region_height }}', str(scanner.region['height']))

@app.route('/api/start_scan', methods=['POST'])
def start_scan():
    """
    API pour démarrer le scan
    """
    if scanner.scanning:
        return jsonify({'error': 'Scan déjà en cours'}), 400
    
    data = request.json
    region = data.get('region')
    duration = float(data.get('duration', 10))
    interval = float(data.get('interval', 0.25))
    
    # Valider les données
    if not region:
        return jsonify({'error': 'Région requise'}), 400
    
    # Lancer le scan dans un thread
    scan_thread = threading.Thread(
        target=scanner.perform_scan,
        args=(region, duration, interval)
    )
    scan_thread.daemon = True
    scan_thread.start()
    
    return jsonify({'success': True, 'message': 'Scan démarré'})

@app.route('/api/stop_scan', methods=['POST'])
def stop_scan():
    """
    API pour arrêter le scan
    """
    scanner.scanning = False
    return jsonify({'success': True, 'message': 'Scan arrêté'})

@app.route('/api/status')
def get_status():
    """
    API pour obtenir le statut
    """
    return jsonify({
        'scanning': scanner.scanning,
        'captures_count': len(scanner.scan_data)
    })

# Template HTML intégré
@app.route('/templates/scanner.html')
def get_template():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Graph Scanner Web</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .control-group { margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .control-group h3 { margin-top: 0; color: #d32f2f; }
        .input-row { display: flex; gap: 15px; margin: 10px 0; }
        .input-group { display: flex; flex-direction: column; }
        .input-group label { font-weight: bold; margin-bottom: 5px; }
        .input-group input { padding: 5px; border: 1px solid #ccc; border-radius: 3px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .btn-primary { background: #d32f2f; color: white; }
        .btn-secondary { background: #666; color: white; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .status { padding: 10px; margin: 15px 0; border-radius: 5px; }
        .status.success { background: #e8f5e8; color: #2e7d2e; }
        .status.error { background: #ffe8e8; color: #d32f2f; }
        .preview { background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 15px 0; }
        .rectangle-preview { 
            border: 3px solid red; 
            background: rgba(255, 0, 0, 0.1); 
            position: relative;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Graph Scanner Web</h1>
        <p>Interface web pour scanner des graphiques avec balayage horizontal</p>
        
        <div class="control-group">
            <h3>🔴 Région de scan (Rectangle rouge)</h3>
            <div class="input-row">
                <div class="input-group">
                    <label>X:</label>
                    <input type="number" id="region-x" value="{{ region.x }}" min="0" max="{{ screen_width }}">
                </div>
                <div class="input-group">
                    <label>Y:</label>
                    <input type="number" id="region-y" value="{{ region.y }}" min="0" max="{{ screen_height }}">
                </div>
                <div class="input-group">
                    <label>Largeur:</label>
                    <input type="number" id="region-width" value="{{ region.width }}" min="100" max="{{ screen_width }}">
                </div>
                <div class="input-group">
                    <label>Hauteur:</label>
                    <input type="number" id="region-height" value="{{ region.height }}" min="100" max="{{ screen_height }}">
                </div>
            </div>
        </div>
        
        <div class="control-group">
            <h3>⚙️ Configuration du scan</h3>
            <div class="input-row">
                <div class="input-group">
                    <label>Durée (secondes):</label>
                    <input type="number" id="duration" value="10" min="1" max="60" step="0.5">
                </div>
                <div class="input-group">
                    <label>Intervalle (secondes):</label>
                    <input type="number" id="interval" value="0.25" min="0.1" max="2" step="0.05">
                </div>
            </div>
        </div>
        
        <div class="preview">
            <h3>📐 Aperçu de la région</h3>
            <div id="rectangle-preview" class="rectangle-preview">
                <p>Rectangle rouge simulé</p>
            </div>
            <p><strong>Écran:</strong> {{ screen_width }} x {{ screen_height }} pixels</p>
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <button id="start-btn" class="btn btn-primary" onclick="startScan()">
                🚀 Commencer le scan
            </button>
            <button id="stop-btn" class="btn btn-secondary" onclick="stopScan()" disabled>
                ⏹️ Arrêter
            </button>
        </div>
        
        <div id="status" class="status" style="display: none;"></div>
        
        <div class="control-group">
            <h3>📋 Instructions</h3>
            <ol>
                <li>Ajustez la position et taille du rectangle rouge ci-dessus</li>
                <li>Positionnez-le sur votre graphique (YouTube Analytics, etc.)</li>
                <li>Configurez la durée et l'intervalle de capture</li>
                <li>Cliquez sur "Commencer le scan"</li>
                <li>Le scan ira de gauche à droite dans le rectangle</li>
                <li>Les captures seront sauvegardées automatiquement</li>
            </ol>
        </div>
    </div>
    
    <script>
        let scanInterval;
        
        function updatePreview() {
            const x = document.getElementById('region-x').value;
            const y = document.getElementById('region-y').value;
            const width = document.getElementById('region-width').value;
            const height = document.getElementById('region-height').value;
            
            const preview = document.getElementById('rectangle-preview');
            preview.style.width = Math.max(200, width / 5) + 'px';
            preview.style.height = Math.max(100, height / 5) + 'px';
            preview.innerHTML = `<p>Rectangle: ${x}, ${y} (${width} x ${height})</p>`;
        }
        
        function startScan() {
            const region = {
                x: parseInt(document.getElementById('region-x').value),
                y: parseInt(document.getElementById('region-y').value),
                width: parseInt(document.getElementById('region-width').value),
                height: parseInt(document.getElementById('region-height').value)
            };
            
            const duration = parseFloat(document.getElementById('duration').value);
            const interval = parseFloat(document.getElementById('interval').value);
            
            fetch('/api/start_scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({region, duration, interval})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showStatus('Scan démarré !', 'success');
                    document.getElementById('start-btn').disabled = true;
                    document.getElementById('stop-btn').disabled = false;
                    startStatusPolling();
                } else {
                    showStatus('Erreur: ' + data.error, 'error');
                }
            });
        }
        
        function stopScan() {
            fetch('/api/stop_scan', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                showStatus('Scan arrêté', 'success');
                document.getElementById('start-btn').disabled = false;
                document.getElementById('stop-btn').disabled = true;
                stopStatusPolling();
            });
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }
        
        function startStatusPolling() {
            scanInterval = setInterval(() => {
                fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (!data.scanning) {
                        showStatus(`Scan terminé ! ${data.captures_count} captures`, 'success');
                        document.getElementById('start-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = true;
                        stopStatusPolling();
                    } else {
                        showStatus(`Scan en cours... ${data.captures_count} captures`, 'success');
                    }
                });
            }, 1000);
        }
        
        function stopStatusPolling() {
            if (scanInterval) {
                clearInterval(scanInterval);
            }
        }
        
        // Mettre à jour l'aperçu en temps réel
        document.addEventListener('DOMContentLoaded', function() {
            updatePreview();
            document.getElementById('region-x').addEventListener('input', updatePreview);
            document.getElementById('region-y').addEventListener('input', updatePreview);
            document.getElementById('region-width').addEventListener('input', updatePreview);
            document.getElementById('region-height').addEventListener('input', updatePreview);
        });
    </script>
</body>
</html>'''

if __name__ == '__main__':
    print("🎯 WEB SCANNER - Interface web pour scanner des graphiques")
    print("=" * 60)
    print("✅ Pas besoin de tkinter")
    print("✅ Rectangle rouge configurable") 
    print("✅ Scan horizontal automatique")
    print("✅ Interface web simple")
    print()
    print("🚀 Lancement du serveur web...")
    print("📱 Ouvrez votre navigateur sur: http://localhost:5000")
    print()
    
    app.run(debug=True, port=5000) 