import os
import json
import base64
from .crypto_utils import hash_password, verify_password, encrypt_data, decrypt_data

# Configuration sécurisée - TOUT vient des variables d'environnement
AUTH_CONFIG_FILE = "auth_config.json"

def get_master_key():
    """Récupérer la clé maître depuis les variables d'environnement"""
    return os.getenv('YTA_MASTER_KEY', 'DEFAULT_FALLBACK_KEY_CHANGE_ME')

def get_default_credentials():
    """Récupérer les identifiants depuis les variables d'environnement"""
    return {
        "username": os.getenv('YTA_USERNAME', 'admin'),
        "password": os.getenv('YTA_PASSWORD', 'changeme123')
    }

def init_auth_config():
    """Initialiser le fichier de configuration d'authentification chiffré"""
    if not os.path.exists(AUTH_CONFIG_FILE):
        master_key = get_master_key()
        credentials = get_default_credentials()
        
        # Créer le fichier avec les identifiants chiffrés
        encrypted_username = encrypt_data(credentials["username"], master_key)
        encrypted_password_hash = encrypt_data(
            hash_password(credentials["password"]), 
            master_key
        )
        
        config = {
            "encrypted_username": base64.b64encode(encrypted_username).decode(),
            "encrypted_password_hash": base64.b64encode(encrypted_password_hash).decode(),
            "created_from_env": True
        }
        
        with open(AUTH_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"[AUTH] Configuration initialisée avec les variables d'environnement")

def verify_credentials(username, password):
    """Vérifier les identifiants de connexion"""
    try:
        init_auth_config()
        master_key = get_master_key()
        
        with open(AUTH_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Déchiffrer le nom d'utilisateur
        encrypted_username = base64.b64decode(config["encrypted_username"])
        stored_username = decrypt_data(encrypted_username, master_key)
        
        # Déchiffrer le hash du mot de passe
        encrypted_password_hash = base64.b64decode(config["encrypted_password_hash"])
        stored_password_hash = decrypt_data(encrypted_password_hash, master_key)
        
        # Vérifier les identifiants
        if username == stored_username and verify_password(password, stored_password_hash):
            print(f"[AUTH] Connexion réussie pour {username}")
            return True
        
        print(f"[AUTH] Tentative de connexion échouée pour {username}")
        return False
        
    except Exception as e:
        print(f"[AUTH] Erreur lors de la vérification: {e}")
        return False

def is_authenticated(session):
    """Vérifier si l'utilisateur est authentifié dans la session"""
    return session.get('authenticated', False)

def authenticate_session(session):
    """Marquer la session comme authentifiée"""
    session['authenticated'] = True
    session.permanent = True

def logout_session(session):
    """Déconnecter l'utilisateur"""
    session.pop('authenticated', None)

def regenerate_config():
    """Régénérer la configuration avec de nouvelles variables d'environnement"""
    if os.path.exists(AUTH_CONFIG_FILE):
        os.remove(AUTH_CONFIG_FILE)
    init_auth_config()
    print("[AUTH] Configuration régénérée avec les nouvelles variables d'environnement") 