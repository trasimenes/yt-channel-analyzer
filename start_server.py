#!/usr/bin/env python3
"""
Script pour démarrer le serveur sur un port libre
"""

import socket
from app import app

def find_free_port(start_port=8080):
    """Trouve un port libre à partir du port donné"""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                continue
    raise Exception("Aucun port libre trouvé")

if __name__ == "__main__":
    # Trouver un port libre
    port = find_free_port(8080)
    
    print(f"🚀 Démarrage du serveur sur le port {port}")
    print(f"📱 Accédez à l'application: http://localhost:{port}")
    print(f"🔧 Pour arrêter: Ctrl+C")
    
    # Démarrer le serveur
    app.run(debug=True, host='0.0.0.0', port=port) 