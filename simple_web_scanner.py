#!/usr/bin/env python3
"""
Simple Web Scanner - Version simplifiée et fonctionnelle
"""

from flask import Flask, request, jsonify
import pyautogui
import time
import os
import json
import threading
from datetime import datetime

app = Flask(__name__)

class SimpleScanner:
    def __init__(self):
        self.scanning = False
        self.scan_data = []
        self.output_dir = "simple_scans"
        os.makedirs(self.output_dir, exist_ok=True)
        pyautogui.FAILSAFE = False
    
    def perform_scan(self, region, duration, interval):
        try:
            self.scanning = True
            self.scan_data = []
            
            num_captures = int(duration / interval)
            start_x = region['x'] + 20
            end_x = region['x'] + region['width'] - 20
            y_pos = region['y'] + region['height'] // 2
            
            step_x = (end_x - start_x) / max(1, num_captures - 1)
            
            for i in range(num_captures):
                if not self.scanning:
                    break
                
                current_x = start_x + (i * step_x)
                pyautogui.moveTo(current_x, y_pos, duration=0.1)
                
                screenshot = pyautogui.screenshot()
                timestamp = int(time.time() * 1000)
                filename = f"scan_{timestamp}_{i:03d}.png"
                filepath = os.path.join(self.output_dir, filename)
                screenshot.save(filepath)
                
                self.scan_data.append({
                    'index': i,
                    'x': current_x,
                    'y': y_pos,
                    'filename': filename
                })
                
                time.sleep(interval)
                
        except Exception as e:
            print(f"Erreur: {e}")
        finally:
            self.scanning = False

scanner = SimpleScanner()

@app.route('/')
def index():
    screen_w, screen_h = pyautogui.size()
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Graph Scanner Simple</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        .header {{ text-align: center; background: #d32f2f; color: white; padding: 20px; margin: -30px -30px 30px -30px; border-radius: 10px 10px 0 0; }}
        .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }}
        .section h3 {{ margin-top: 0; color: #d32f2f; }}
        .inputs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .input-group {{ display: flex; flex-direction: column; }}
        .input-group label {{ font-weight: bold; margin-bottom: 5px; }}
        .input-group input {{ padding: 10px; border: 1px solid #ccc; border-radius: 4px; }}
        .btn {{ padding: 15px 25px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin: 5px; }}
        .btn-start {{ background: #d32f2f; color: white; }}
        .btn-stop {{ background: #666; color: white; }}
        .btn:disabled {{ background: #ccc; cursor: not-allowed; }}
        .status {{ padding: 15px; margin: 15px 0; border-radius: 6px; font-weight: bold; }}
        .status.success {{ background: #e8f5e8; color: #2e7d2e; }}
        .status.error {{ background: #ffe8e8; color: #d32f2f; }}
        .preview {{ background: #f9f9f9; padding: 20px; border-radius: 8px; text-align: center; }}
        .rectangle {{ border: 3px solid #d32f2f; background: rgba(211,47,47,0.1); padding: 20px; margin: 15px 0; }}
        .buttons {{ text-align: center; margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Graph Scanner Simple</h1>
            <p>Scanner horizontal pour graphiques YouTube Analytics</p>
        </div>
        
        <div class="section">
            <h3>🔴 Rectangle de scan</h3>
            <div class="inputs">
                <div class="input-group">
                    <label>X:</label>
                    <input type="number" id="x" value="{screen_w//4}" min="0" max="{screen_w}">
                </div>
                <div class="input-group">
                    <label>Y:</label>
                    <input type="number" id="y" value="{screen_h//4}" min="0" max="{screen_h}">
                </div>
                <div class="input-group">
                    <label>Largeur:</label>
                    <input type="number" id="w" value="{screen_w//2}" min="100" max="{screen_w}">
                </div>
                <div class="input-group">
                    <label>Hauteur:</label>
                    <input type="number" id="h" value="{screen_h//2}" min="100" max="{screen_h}">
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>⚙️ Configuration</h3>
            <div class="inputs">
                <div class="input-group">
                    <label>Durée (sec):</label>
                    <input type="number" id="duration" value="10" min="1" max="60" step="0.5">
                </div>
                <div class="input-group">
                    <label>Intervalle (sec):</label>
                    <input type="number" id="interval" value="0.25" min="0.1" max="2" step="0.05">
                </div>
                <div class="input-group">
                    <label>Captures:</label>
                    <input type="text" id="estimate" readonly style="background: #f0f0f0;">
                </div>
            </div>
        </div>
        
        <div class="preview">
            <h3>📐 Aperçu</h3>
            <div class="rectangle" id="rect-preview">
                <p>🔴 Zone de scan - Le curseur ira de gauche à droite</p>
            </div>
            <p>Écran: {screen_w} x {screen_h} pixels</p>
        </div>
        
        <div class="buttons">
            <button id="start" class="btn btn-start" onclick="startScan()">🚀 Commencer</button>
            <button id="stop" class="btn btn-stop" onclick="stopScan()" disabled>⏹️ Arrêter</button>
        </div>
        
        <div id="status" style="display: none;"></div>
        
        <div class="section">
            <h3>📋 Instructions</h3>
            <ol>
                <li>Ajustez le rectangle pour couvrir votre graphique</li>
                <li>Ouvrez YouTube Analytics dans un autre onglet</li>
                <li>Cliquez "Commencer" puis basculez vers le graphique</li>
                <li>Le scan ira de gauche à droite automatiquement</li>
            </ol>
            <p><strong>💡 YouTube Analytics:</strong> Essayez X=250, Y=200, Largeur=1100, Hauteur=400</p>
        </div>
    </div>
    
    <script>
        let interval;
        
        function updatePreview() {{
            const x = parseInt(document.getElementById('x').value) || 0;
            const y = parseInt(document.getElementById('y').value) || 0;
            const w = parseInt(document.getElementById('w').value) || 100;
            const h = parseInt(document.getElementById('h').value) || 100;
            const dur = parseFloat(document.getElementById('duration').value) || 1;
            const int = parseFloat(document.getElementById('interval').value) || 0.25;
            
            const captures = Math.floor(dur / int);
            document.getElementById('estimate').value = captures + ' captures';
            
            const preview = document.getElementById('rect-preview');
            preview.innerHTML = `<p><strong>Rectangle: (${{x}}, ${{y}}) - ${{w}} x ${{h}}px</strong><br>Scan: ${{captures}} captures en ${{dur}}s</p>`;
        }}
        
        function startScan() {{
            const region = {{
                x: parseInt(document.getElementById('x').value),
                y: parseInt(document.getElementById('y').value),
                width: parseInt(document.getElementById('w').value),
                height: parseInt(document.getElementById('h').value)
            }};
            const duration = parseFloat(document.getElementById('duration').value);
            const inter = parseFloat(document.getElementById('interval').value);
            
            showStatus('🚀 Scan démarre dans 3 secondes...', 'success');
            
            setTimeout(() => {{
                fetch('/start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{region, duration, interval: inter}})
                }})
                .then(r => r.json())
                .then(data => {{
                    if (data.success) {{
                        document.getElementById('start').disabled = true;
                        document.getElementById('stop').disabled = false;
                        pollStatus();
                    }}
                }});
            }}, 3000);
        }}
        
        function stopScan() {{
            fetch('/stop', {{method: 'POST'}});
        }}
        
        function showStatus(msg, type) {{
            const status = document.getElementById('status');
            status.innerHTML = msg;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }}
        
        function pollStatus() {{
            interval = setInterval(() => {{
                fetch('/status')
                .then(r => r.json())
                .then(data => {{
                    if (!data.scanning) {{
                        showStatus(`✅ Terminé! ${{data.count}} captures`, 'success');
                        document.getElementById('start').disabled = false;
                        document.getElementById('stop').disabled = true;
                        clearInterval(interval);
                    }} else {{
                        showStatus(`📸 En cours... ${{data.count}} captures`, 'success');
                    }}
                }});
            }}, 1000);
        }}
        
        // Init
        document.addEventListener('DOMContentLoaded', () => {{
            updatePreview();
            ['x', 'y', 'w', 'h', 'duration', 'interval'].forEach(id => {{
                document.getElementById(id).addEventListener('input', updatePreview);
            }});
        }});
    </script>
</body>
</html>"""
    
    return html

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    thread = threading.Thread(target=scanner.perform_scan, 
                            args=(data['region'], data['duration'], data['interval']))
    thread.daemon = True
    thread.start()
    return jsonify({'success': True})

@app.route('/stop', methods=['POST']) 
def stop():
    scanner.scanning = False
    return jsonify({'success': True})

@app.route('/status')
def status():
    return jsonify({'scanning': scanner.scanning, 'count': len(scanner.scan_data)})

if __name__ == '__main__':
    print("🎯 SIMPLE WEB SCANNER")
    print("=" * 40)
    print("✅ Interface simplifiée")
    print("✅ Rectangle rouge configurable")
    print("✅ Scan horizontal automatique")
    print("✅ Pas de problèmes de templates")
    print()
    print("📱 Ouvrez: http://localhost:5002")
    
    app.run(debug=True, port=5002) 