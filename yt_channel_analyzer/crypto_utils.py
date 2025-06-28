from cryptography.fernet import Fernet
import base64
import hashlib
import bcrypt

def derive_key(password: str) -> bytes:
    # On dérive une clé Fernet à partir d'un mot de passe utilisateur
    return base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())

def encrypt_api_key(api_key: str, password: str) -> bytes:
    key = derive_key(password)
    f = Fernet(key)
    return f.encrypt(api_key.encode())

def decrypt_api_key(token: bytes, password: str) -> str:
    key = derive_key(password)
    f = Fernet(key)
    return f.decrypt(token).decode()

def hash_password(password: str) -> str:
    """Chiffrer un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Vérifier un mot de passe contre son hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def encrypt_data(data: str, password: str) -> bytes:
    """Chiffrer des données avec un mot de passe"""
    key = derive_key(password)
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(token: bytes, password: str) -> str:
    """Déchiffrer des données avec un mot de passe"""
    key = derive_key(password)
    f = Fernet(key)
    return f.decrypt(token).decode() 