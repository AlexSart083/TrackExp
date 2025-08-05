"""
Modulo per autenticazione e sicurezza - Versione Database Completa
Sostituisce completamente il vecchio auth_security.py
"""

import streamlit as st
import time
from datetime import datetime, timedelta
import re
from database_manager import SupabaseDatabaseManager, PasswordManager

class SecurityConfig:
    """Configurazione sicurezza"""
    SESSION_TIMEOUT = int(st.secrets.get("auth", {}).get("session_timeout_minutes", 30))
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = 15  # minuti
    
    @staticmethod
    def hash_password(password):
        """Hash password - ora usa PasswordManager"""
        return PasswordManager.hash_password(password)
    
    @staticmethod 
    def verify_password(password, hashed):
        """Verifica password - ora usa PasswordManager"""
        return PasswordManager.verify_password(password, hashed)

class UserAuthenticator:
    """Gestione autenticazione utenti - Versione Database"""
    
    @staticmethod
    def register_user(username, password, display_name=None):
        """Registra nuovo utente nel database"""
        try:
            # Validazione input
            if not username or not password:
                return False, "Username e password sono obbligatori"
            
            # Validazione email
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', username):
                return False, "Formato email non valido"
            
            # Validazione forza password
            is_strong, message = PasswordManager.is_strong_password(password)
            if not is_strong:
                return False, message
            
            # Salva nel database
            db = SupabaseDatabaseManager()
            password_hash = PasswordManager.hash_password(password)
            success = db.save_user(username, password_hash, display_name)
            
            if success:
                return True, "Utente registrato con successo!"
            else:
                return False, "Username già esistente"
                
        except Exception as e:
            st.error(f"Errore registrazione: {e}")
            return False, f"Errore: {e}"
    
    @staticmethod
    def authenticate_user(username, password):
        """Autentica utente dal database"""
        try:
            if not username or not password:
                return False, None
            
            db = SupabaseDatabaseManager()
            user = db.get_user(username)
            
            if user and PasswordManager.verify_password(password, user['password_hash']):
                return True, user['display_name']
            else:
                return False, None
                
        except Exception as e:
            st.error(f"Errore autenticazione: {e}")
            return False, None
    
    @staticmethod
    def change_password(username, current_password, new_password):
        """Cambia password utente"""
        try:
            db = SupabaseDatabaseManager()
            user = db.get_user(username)
            
            if not user:
                return False, "Utente non trovato"
            
            # Verifica password corrente
            if not PasswordManager.verify_password(current_password, user['password_hash']):
                return False, "Password corrente non corretta"
            
            # Validazione nuova password
            is_strong, message = PasswordManager.is_strong_password(new_password)
            if not is_strong:
                return False, message
            
            # Aggiorna password
            new_password_hash = PasswordManager.hash_password(new_password)
            success = db.update_user_password(username, new_password_hash)
            
            if success:
                return True, "Password cambiata con successo"
            else:
                return False, "Errore nell'aggiornamento della password"
                
        except Exception as e:
            return False, f"Errore: {e}"

class SessionManager:
    """Gestione sessioni utente"""
    
    @staticmethod
    def check_session_timeout(session_state):
        """Controlla timeout sessione"""
        if 'last_activity' in session_state:
            last_activity = session_state.last_activity
            timeout = timedelta(minutes=SecurityConfig.SESSION_TIMEOUT)
            
            if datetime.now() - last_activity > timeout:
                return True
        
        # Aggiorna ultima attività
        session_state.last_activity = datetime.now()
        return False
    
    @staticmethod
    def get_remaining_session_time(session_state):
        """Ottieni tempo rimanente sessione"""
        if 'last_activity' in session_state:
            last_activity = session_state.last_activity
            timeout = timedelta(minutes=SecurityConfig.SESSION_TIMEOUT)
            elapsed = datetime.now() - last_activity
            remaining = timeout - elapsed
            
            if remaining.total_seconds() > 0:
                return int(remaining.total_seconds() / 60)
        
        return SecurityConfig.SESSION_TIMEOUT

class DataManager:
    """Manager per caricamento e salvataggio dati - Versione Database"""
    
    @staticmethod
    def carica_dati(username):
        """Carica dati dell'utente dal database"""
        try:
            db = SupabaseDatabaseManager()
            return db.load_expense_data(username)
        except Exception as e:
            st.error(f"Errore nel caricamento dal database: {e}")
            return [], [], []
    
    @staticmethod 
    def salva_dati(username, spese_giornaliere, spese_ricorrenti, conti):
        """Salva dati dell'utente nel database"""
        try:
            db = SupabaseDatabaseManager()
            db.save_expense_data(username, spese_giornaliere, spese_ricorrenti, conti)
        except Exception as e:
            st.error(f"Errore nel salvataggio nel database: {e}")
            raise e
    
    @staticmethod
    def esporta_dati_per_backup(username):
        """Esporta dati per backup"""
        try:
            import json
            db = SupabaseDatabaseManager()
            spese_g, spese_r, conti = db.load_expense_data(username)
            
            backup_data = {
                'username': username,
                'export_date': datetime.now().isoformat(),
                'spese_giornaliere': spese_g,
                'spese_ricorrenti': spese_r,
                'conti': conti
            }
            
            return json.dumps(backup_data, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Errore nell'esportazione: {e}")
            return None
    
    @staticmethod
    def carica_backup(file_content):
        """Carica dati da backup JSON"""
        try:
            import json
            data = json.loads(file_content)
            return data['spese_giornaliere'], data['spese_ricorrenti'], data['conti']
        except Exception as e:
            raise Exception(f"Formato backup non valido: {e}")

class LoginAttemptTracker:
    """Tracker tentativi di login - ora in memoria session_state"""
    
    @staticmethod
    def is_locked_out(username):
        """Controlla se utente è bloccato"""
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        
        attempts = st.session_state.login_attempts.get(username, {})
        if attempts.get('count', 0) >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
            lockout_time = attempts.get('lockout_time')
            if lockout_time and datetime.now() < lockout_time:
                return True
        
        return False
    
    @staticmethod
    def record_failed_attempt(username):
        """Registra tentativo fallito"""
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        
        if username not in st.session_state.login_attempts:
            st.session_state.login_attempts[username] = {'count': 0}
        
        st.session_state.login_attempts[username]['count'] += 1
        
        if st.session_state.login_attempts[username]['count'] >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
            st.session_state.login_attempts[username]['lockout_time'] = datetime.now() + timedelta(minutes=SecurityConfig.LOCKOUT_TIME)
    
    @staticmethod
    def reset_attempts(username):
        """Reset tentativi dopo login riuscito"""
        if 'login_attempts' in st.session_state and username in st.session_state.login_attempts:
            del st.session_state.login_attempts[username]

class FileManager:
    """File Manager - mantenuto per compatibilità ma ora non più necessario"""
    
    @staticmethod
    def ensure_data_directory():
        """Non più necessario con database"""
        pass
    
    @staticmethod
    def get_user_file_path(username):
        """Non più necessario con database"""
        return f"database_user_{username}"

# Mantieni anche le altre classi che esistono nel tuo auth_security.py originale
# come PrivacyManager, FormComponents, UIHelpers, StateManager, LoginForm
# COPIA TUTTO IL RESTO dal tuo auth_security.py esistente qui sotto:

# [PLACEHOLDER: Copia qui tutte le altre classi dal tuo auth_security.py originale]
