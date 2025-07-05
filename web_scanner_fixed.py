#!/usr/bin/env python3
"""
Web Scanner Fixed - Interface web simple pour scanner des graphiques
HTML intégré pour éviter les problèmes de templates
"""

from flask import Flask, request, jsonify
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
    Page principale avec HTML intégré
    """
    screen_width, screen_height = pyautogui.size()
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>🎯 Graph Scanner Web</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 900px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            background: linear-gradient(135deg, #d32f2f, #f44336);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: -30px -30px 30px -30px;
        }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        
        .control-group {{ 
            margin: 20px 0; 
            padding: 20px; 
            border: 2px solid #e0e0e0; 
            border-radius: 10px; 
            background: #fafafa;
            transition: all 0.3s;
        }}
        .control-group:hover {{ border-color: #d32f2f; }}
        .control-group h3 {{ 
            margin-top: 0; 
            color: #d32f2f; 
            display: flex; 
            align-items: center;
            font-size: 1.3em;
        }}
        
        .input-row {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
            gap: 20px; 
            margin: 15px 0; 
        }}
        .input-group {{ display: flex; flex-direction: column; }}
        .input-group label {{ 
            font-weight: bold; 
            margin-bottom: 8px; 
            color: #333;
            font-size: 0.9em;
        }}
        .input-group input {{ 
            padding: 12px; 
            border: 2px solid #ddd; 
            border-radius: 6px; 
            font-size: 16px;
            transition: border-color 0.3s;
        }}
        .input-group input:focus {{ 
            border-color: #d32f2f; 
            outline: none; 
        }}
        
        .btn {{ 
            padding: 15px 30px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: bold; 
            font-size: 18px; 
            transition: all 0.3s;
            margin: 0 10px;
        }}
        .btn-primary {{ 
            background: linear-gradient(135deg, #d32f2f, #f44336); 
            color: white; 
            box-shadow: 0 4px 15px rgba(211, 47, 47, 0.3);
        }}
        .btn-primary:hover {{ 
            transform: translateY(-2px); 
            box-shadow: 0 6px 20px rgba(211, 47, 47, 0.4);
        }}
        .btn-secondary {{ 
            background: linear-gradient(135deg, #666, #777); 
            color: white; 
        }}
        .btn-secondary:hover {{ background: linear-gradient(135deg, #555, #666); }}
        .btn:disabled {{ 
            background: #ccc; 
            cursor: not-allowed; 
            transform: none;
            box-shadow: none;
        }}
        
        .status {{ 
            padding: 15px; 
            margin: 20px 0; 
            border-radius: 8px; 
            font-weight: bold;
            font-size: 16px;
        }}
        .status.success {{ 
            background: #e8f5e8; 
            color: #2e7d2e; 
            border: 2px solid #4caf50; 
        }}
        .status.error {{ 
            background: #ffe8e8; 
            color: #d32f2f; 
            border: 2px solid #f44336; 
        }}
        
        .preview {{ 
            background: linear-gradient(135deg, #f9f9f9, #f0f0f0); 
            padding: 25px; 
            border-radius: 10px; 
            margin: 20px 0; 
            border: 1px solid #e0e0e0; 
        }}
        .rectangle-preview {{ 
            border: 4px solid #d32f2f; 
            background: rgba(211, 47, 47, 0.1); 
            position: relative;
            margin: 20px 0;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            min-height: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            transition: all 0.3s;
        }}
        .rectangle-preview:hover {{ 
            background: rgba(211, 47, 47, 0.2); 
            transform: scale(1.02);
        }}
        
        .button-container {{ 
            text-align: center; 
            margin: 40px 0; 
            padding: 20px;
        }}
        
        .instructions {{ 
            background: linear-gradient(135deg, #e3f2fd, #f0f8ff); 
            padding: 25px; 
            border-radius: 10px; 
            border-left: 5px solid #2196f3;
            margin-top: 30px;
        }}
        .instructions h3 {{ color: #1976d2; margin-top: 0; }}
        .instructions ol {{ margin: 15px 0; padding-left: 25px; }}
        .instructions li {{ margin: 10px 0; line-height: 1.6; }}
        
        .stat-badge {{ 
            background: linear-gradient(135deg, #2196f3, #21cbf3); 
            color: white; 
            padding: 6px 12px; 
            border-radius: 20px; 
            font-size: 12px; 
            margin-left: 15px;
            box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
        }}
        
        .tip {{ 
            background: #fff3e0; 
            border: 1px solid #ff9800; 
            border-radius: 8px; 
            padding: 15px; 
            margin: 15px 0;
        }}
        .tip strong {{ color: #f57c00; }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 20px; }}
            .input-row {{ grid-template-columns: 1fr; }}
            .btn {{ margin: 5px 0; width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Graph Scanner</h1>
            <p>Scanner automatique de graphiques avec balayage horizontal</p>
        </div>
        
        <div class="control-group">
            <h3>🔴 Rectangle de scan <span class="stat-badge">{screen_width} × {screen_height} px</span></h3>
            <div class="input-row">
                <div class="input-group">
                    <label>📍 Position X:</label>
                    <input type="number" id="region-x" value="{scanner.region['x']}" min="0" max="{screen_width}">
                </div>
                <div class="input-group">
                    <label>📍 Position Y:</label>
                    <input type="number" id="region-y" value="{scanner.region['y']}" min="0" max="{screen_height}">
                </div>
                <div class="input-group">
                    <label>📏 Largeur:</label>
                    <input type="number" id="region-width" value="{scanner.region['width']}" min="100" max="{screen_width}">
                </div>
                <div class="input-group">
                    <label>📏 Hauteur:</label>
                    <input type="number" id="region-height" value="{scanner.region['height']}" min="100" max="{screen_height}">
                </div>
            </div>
        </div>
        
        <div class="control-group">
            <h3>⚙️ Configuration du scan</h3>
            <div class="input-row">
                <div class="input-group">
                    <label>⏱️ Durée (secondes):</label>
                    <input type="number" id="duration" value="10" min="1" max="60" step="0.5">
                </div>
                <div class="input-group">
                    <label>📸 Intervalle (secondes):</label>
                    <input type="number" id="interval" value="0.25" min="0.1" max="2" step="0.05">
                </div>
                <div class="input-group">
                    <label>📊 Captures estimées:</label>
                    <input type="text" id="captures-estimate" readonly style="background: #f0f0f0; font-weight: bold;">
                </div>
            </div>
        </div>
        
        <div class="preview">
            <h3>📐 Aperçu du rectangle de scan</h3>
            <div id="rectangle-preview" class="rectangle-preview">
                <p>🔴 Zone de scan simulée - Le curseur bougera de gauche à droite dans cette zone</p>
            </div>
            <p><strong>Écran détecté:</strong> {screen_width} × {screen_height} pixels</p>
        </div>
        
        <div class="button-container">
            <button id="start-btn" class="btn btn-primary" onclick="startScan()">
                🚀 Commencer le scan
            </button>
            <button id="stop-btn" class="btn btn-secondary" onclick="stopScan()" disabled>
                ⏹️ Arrêter le scan
            </button>
        </div>
        
        <div id="status" class="status" style="display: none;"></div>
        
        <div class="tip">
            <strong>💡 Pour YouTube Analytics:</strong> Utilisez région 250×200 avec taille 1100×400 pour couvrir le graphique d'abonnés
        </div>
        
        <div class="instructions">
            <h3>📋 Mode d'emploi</h3>
            <ol>
                <li><strong>Configurez le rectangle rouge</strong> pour qu'il couvre votre graphique</li>
                <li><strong>Ouvrez YouTube Analytics</strong> dans un autre onglet</li>
                <li><strong>Positionnez le graphique</strong> sous le rectangle (utilisez les coordonnées)</li>
                <li><strong>Ajustez durée et intervalle</strong> selon vos besoins</li>
                <li><strong>Cliquez "Commencer"</strong> puis basculez rapidement vers le graphique</li>
                <li><strong>Le curseur bougera automatiquement</strong> de gauche à droite</li>
                <li><strong>Les captures sont sauvegardées</strong> dans web_scans/</li>
            </ol>
        </div>
    </div>
    
    <script>
        let scanInterval;
        
        function updatePreview() {{
            const x = parseInt(document.getElementById('region-x').value) || 0;
            const y = parseInt(document.getElementById('region-y').value) || 0;
            const width = parseInt(document.getElementById('region-width').value) || 100;
            const height = parseInt(document.getElementById('region-height').value) || 100;
            
            const duration = parseFloat(document.getElementById('duration').value) || 1;
            const interval = parseFloat(document.getElementById('interval').value) || 0.25;
            const estimatedCaptures = Math.floor(duration / interval);
            
            document.getElementById('captures-estimate').value = estimatedCaptures + ' captures';
            
            const preview = document.getElementById('rectangle-preview');
            const scale = Math.min(500 / width, 250 / height, 1);
            const previewWidth = Math.max(250, width * scale);
            const previewHeight = Math.max(80, height * scale);
            
            preview.style.width = previewWidth + 'px';
            preview.style.height = previewHeight + 'px';
            preview.innerHTML = `<div>
                <p><strong>🔴 Rectangle: ({{}x{{}}, {{}}y{{}})</strong></p>
                <p><strong>📏 Taille: {{}} × {{}} pixels</strong></p>
                <p><strong>📸 {{}} captures en {{}}s</strong></p>
            </div>`.replace('{}', x).replace('{}', y).replace('{}', width).replace('{}', height).replace('{}', estimatedCaptures).replace('{}', duration);
        }}
        
        function startScan() {{
            const region = {{
                x: parseInt(document.getElementById('region-x').value),
                y: parseInt(document.getElementById('region-y').value),
                width: parseInt(document.getElementById('region-width').value),
                height: parseInt(document.getElementById('region-height').value)
            }};
            
            const duration = parseFloat(document.getElementById('duration').value);
            const interval = parseFloat(document.getElementById('interval').value);
            
            // Validation
            if (region.width < 100 || region.height < 50) {{
                showStatus('❌ Rectangle trop petit (minimum 100×50 pixels)', 'error');
                return;
            }}
            
            if (region.x + region.width > {screen_width} || region.y + region.height > {screen_height}) {{
                showStatus('❌ Rectangle dépasse les bords de l\\'écran', 'error');
                return;
            }}
            
            showStatus('🚀 Scan démarrera dans 3 secondes... Basculez vers votre graphique !', 'success');
            
            setTimeout(() => {{
                fetch('/api/start_scan', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{region, duration, interval}})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        showStatus('✅ Scan en cours ! Le curseur se déplace sur votre graphique', 'success');
                        document.getElementById('start-btn').disabled = true;
                        document.getElementById('stop-btn').disabled = false;
                        startStatusPolling();
                    }} else {{
                        showStatus('❌ Erreur: ' + data.error, 'error');
                    }}
                }})
                .catch(error => {{
                    showStatus('❌ Erreur de connexion: ' + error, 'error');
                }});
            }}, 3000);
        }}
        
        function stopScan() {{
            fetch('/api/stop_scan', {{method: 'POST'}})
            .then(response => response.json())
            .then(data => {{
                showStatus('⏹️ Scan arrêté par l\\'utilisateur', 'success');
                document.getElementById('start-btn').disabled = false;
                document.getElementById('stop-btn').disabled = true;
                stopStatusPolling();
            }})
            .catch(error => {{
                showStatus('❌ Erreur lors de l\\'arrêt: ' + error, 'error');
            }});
        }}
        
        function showStatus(message, type) {{
            const status = document.getElementById('status');
            status.innerHTML = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }}
        
        function startStatusPolling() {{
            scanInterval = setInterval(() => {{
                fetch('/api/status')
                .then(response => response.json())
                .then(data => {{
                    if (!data.scanning) {{
                        showStatus(`🎉 Scan terminé ! ${{data.captures_count}} captures sauvegardées dans web_scans/`, 'success');
                        document.getElementById('start-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = true;
                        stopStatusPolling();
                    }} else {{
                        showStatus(`📸 Scan en cours... ${{data.captures_count}} captures réalisées`, 'success');
                    }}
                }});
            }}, 1000);
        }}
        
        function stopStatusPolling() {{
            if (scanInterval) {{
                clearInterval(scanInterval);
            }}
        }}
        
        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {{
            updatePreview();
            
            // Mettre à jour l'aperçu en temps réel
            ['region-x', 'region-y', 'region-width', 'region-height', 'duration', 'interval'].forEach(id => {{
                document.getElementById(id).addEventListener('input', updatePreview);
            }});
        }});
    </script>
</body>
</html>'''
    
    return html

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

if __name__ == '__main__':
    print("🎯 WEB SCANNER FIXED - Interface web corrigée")
    print("=" * 60)
    print("✅ HTML intégré (pas de templates externes)")
    print("✅ Rectangle rouge configurable") 
    print("✅ Scan horizontal automatique")
    print("✅ Interface moderne et responsive")
    print()
    print("🚀 Lancement du serveur web...")
    print("📱 Ouvrez votre navigateur sur: http://localhost:5001")
    print()
    
    app.run(debug=True, port=5001) 