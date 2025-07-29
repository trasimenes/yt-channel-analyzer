"""
Authentication Blueprint
Handles all authentication-related routes and user management.
Extracted from monolithic app.py to improve maintainability.
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
import os


auth_bp = Blueprint('auth', __name__)


def verify_credentials(username, password):
    """Vérifier les identifiants de connexion"""
    expected_username = os.getenv('YTA_USERNAME', 'admin')
    expected_password = os.getenv('YTA_PASSWORD', 'changeme123')
    return username == expected_username and password == expected_password


def authenticate_session(session):
    """Authentifier la session utilisateur"""
    session['authenticated'] = True
    session['username'] = os.getenv('YTA_USERNAME', 'admin')


def logout_session(session):
    """Déconnecter l'utilisateur"""
    session.pop('authenticated', None)
    session.pop('username', None)


def login_required(f):
    """Décorateur pour protéger les routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Permettre l'accès public à l'autocomplete pour la recherche navbar
        if request.endpoint == 'api.autocomplete':
            return f(*args, **kwargs)
        
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if verify_credentials(username, password):
            authenticate_session(session)
            return redirect(url_for('main.home'))
        else:
            from flask import current_app
            demo_mode = current_app.config.get('DEMO_MODE', False)
            return render_template('login_sneat_pro.html', error='Identifiants incorrects', demo_mode=demo_mode)
    
    from flask import current_app
    demo_mode = current_app.config.get('DEMO_MODE', False)
    return render_template('login_sneat_pro.html', demo_mode=demo_mode)


@auth_bp.route('/logout')
def logout():
    """Déconnexion"""
    logout_session(session)
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """Page de profil utilisateur"""
    return render_template('profile_sneat_pro.html', 
                         username=session.get('username', 'Utilisateur'))


@auth_bp.route('/profile/security')
@login_required  
def profile_security():
    """Page de sécurité du profil"""
    return render_template('profile_security_sneat_pro.html',
                         username=session.get('username', 'Utilisateur'))


@auth_bp.route('/update-password', methods=['POST'])
@login_required
def update_password():
    """API pour changer le mot de passe"""
    try:
        current_password = request.form.get('currentPassword')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')
        
        if not all([current_password, new_password, confirm_password]):
            return {'success': False, 'error': 'Tous les champs sont requis'}, 400
        
        if new_password != confirm_password:
            return {'success': False, 'error': 'Les nouveaux mots de passe ne correspondent pas'}, 400
        
        if len(new_password) < 8:
            return {'success': False, 'error': 'Le mot de passe doit contenir au moins 8 caractères'}, 400
        
        username = session.get('username', 'admin')
        if not verify_credentials(username, current_password):
            return {'success': False, 'error': 'Mot de passe actuel incorrect'}, 400
        
        # Update password in environment (temporary - should use proper user management)
        os.environ['YTA_PASSWORD'] = new_password
        
        # Optionally update config file or database here
        
        return {'success': True, 'message': 'Mot de passe mis à jour avec succès'}
        
    except Exception as e:
        return {'success': False, 'error': f'Erreur lors de la mise à jour: {str(e)}'}, 500


@auth_bp.route('/toggle-dev-mode', methods=['POST'])
@login_required
def toggle_dev_mode():
    """Basculer le mode développeur"""
    try:
        current_state = session.get('dev_mode', False)
        new_state = not current_state
        session['dev_mode'] = new_state
        session.permanent = True  # Forcer la persistence
        session.modified = True   # Marquer la session comme modifiée
        
        print(f"[TOGGLE-DEV-MODE] Mode développeur: {current_state} -> {new_state}")
        
        status = "activé" if new_state else "désactivé"
        flash(f'Mode développeur {status}', 'success')
        
        # Détecter si la requête est AJAX
        if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            # Requête AJAX - retourner status 200 pour recharger la page côté client
            return '', 200
        else:
            # Requête form classique - rediriger (compatibility)
            return redirect(request.referrer or url_for('main.home'))
    except Exception as e:
        flash(f'Erreur lors du basculement du mode développeur: {str(e)}', 'error')
        if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            return '', 500
        else:
            return redirect(request.referrer or url_for('main.home'))


@auth_bp.route('/toggle-performance-mode', methods=['POST'])
@login_required
def toggle_performance_mode():
    """Basculer le mode performance"""
    try:
        current_state = session.get('performance_mode', False)
        new_state = not current_state
        session['performance_mode'] = new_state
        
        return {
            'success': True,
            'performance_mode': new_state,
            'message': f"Mode performance {'activé' if new_state else 'désactivé'}"
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500