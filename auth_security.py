"""
Modulo Auth Security per la Gestione Spese Mensili
Gestisce autenticazione, sicurezza e sessioni
"""

import streamlit as st
import bcrypt
import time
import re
from datetime import datetime, timedelta
from database_manager import SupabaseDatabaseManager

class SecurityConfig:
    """Configurazioni di sicurezza"""
    
    MIN_PASSWORD_LENGTH = 8
    SESSION_TIMEOUT_MINUTES = 30
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

class UserAuthenticator:
    """Gestione autenticazione utenti"""
    
    @staticmethod
    def register(username, password, display_name=None):
        """Registra un nuovo utente"""
        try:
            # Validazione input
            if not UserAuthenticator._validate_username(username):
                return False, "Username non valido (3-30 caratteri, solo lettere, numeri e underscore)"
            
            if not UserAuthenticator._validate_password(password):
                return False, f"Password non valida (minimo {SecurityConfig.MIN_PASSWORD_LENGTH} caratteri, deve contenere maiuscole, minuscole e numeri)"
            
            # Controlla se l'utente esiste già
            db = SupabaseDatabaseManager()
            if db.user_exists(username):
                return False, "Username già esistente"
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Crea l'utente
            success = db.create_user(username, password_hash, display_name or username)
            
            if success:
                return True, "Utente registrato con successo"
            else:
                return False, "Errore durante la registrazione"
                
        except Exception as e:
            return False, f"Errore durante la registrazione: {str(e)}"
    
    @staticmethod
    def login(username, password):
        """Effettua il login"""
        try:
            # Controlla tentativi di login
            if LoginAttemptTracker.is_locked_out(username):
                remaining_time = LoginAttemptTracker.get_lockout_remaining_time(username)
                return False, f"Account temporaneamente bloccato. Riprova tra {remaining_time} minuti."
            
            db = SupabaseDatabaseManager()
            user_data = db.get_user(username)
            
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                # Login riuscito
                LoginAttemptTracker.reset_attempts(username)
                return True, "Login effettuato con successo"
            else:
                # Login fallito
                LoginAttemptTracker.record_failed_attempt(username)
                return False, "Credenziali non valide"
                
        except Exception as e:
            return False, f"Errore durante il login: {str(e)}"
    
    @staticmethod
    def change_password(username, current_password, new_password):
        """Cambia la password dell'utente"""
        try:
            # Valida la nuova password
            if not UserAuthenticator._validate_password(new_password):
                return False, f"Nuova password non valida (minimo {SecurityConfig.MIN_PASSWORD_LENGTH} caratteri, deve contenere maiuscole, minuscole e numeri)"
            
            # Verifica password attuale
            db = SupabaseDatabaseManager()
            user_data = db.get_user(username)
            
            if not user_data or not bcrypt.checkpw(current_password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
                return False, "Password attuale non corretta"
            
            # Hash nuova password
            new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Aggiorna password
            success = db.update_user_password(username, new_password_hash)
            
            if success:
                return True, "Password cambiata con successo"
            else:
                return False, "Errore durante il cambio password"
                
        except Exception as e:
            return False, f"Errore durante il cambio password: {str(e)}"
    
    @staticmethod
    def _validate_username(username):
        """Valida il formato dell'username"""
        if not username or len(username) < 3 or len(username) > 30:
            return False
        
        # Solo lettere, numeri e underscore
        if not re.match("^[a-zA-Z0-9_]+$", username):
            return False
        
        return True
    
    @staticmethod
    def _validate_password(password):
        """Valida il formato della password"""
        if not password or len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            return False
        
        # Almeno una maiuscola, una minuscola e un numero
        if not re.search("[a-z]", password) or not re.search("[A-Z]", password) or not re.search("[0-9]", password):
            return False
        
        return True

class SessionManager:
    """Gestione delle sessioni utente"""
    
    @staticmethod
    def update_session_activity(session_state):
        """Aggiorna l'attività della sessione"""
        session_state['last_activity'] = time.time()
    
    @staticmethod
    def check_session_timeout(session_state):
        """Controlla se la sessione è scaduta"""
        if 'last_activity' not in session_state:
            return True
        
        last_activity = session_state['last_activity']
        current_time = time.time()
        timeout_seconds = SecurityConfig.SESSION_TIMEOUT_MINUTES * 60
        
        return (current_time - last_activity) > timeout_seconds
    
    @staticmethod
    def get_remaining_session_time(session_state):
        """Ottiene il tempo rimanente della sessione in minuti"""
        if 'last_activity' not in session_state:
            return 0
        
        last_activity = session_state['last_activity']
        current_time = time.time()
        timeout_seconds = SecurityConfig.SESSION_TIMEOUT_MINUTES * 60
        elapsed_seconds = current_time - last_activity
        remaining_seconds = max(0, timeout_seconds - elapsed_seconds)
        
        return int(remaining_seconds / 60)

class FileManager:
    """Gestione dei file (placeholder per future funzionalità)"""
    
    @staticmethod
    def sanitize_filename(filename):
        """Sanifica il nome del file"""
        # Rimuove caratteri non sicuri
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        return filename[:50]  # Limita lunghezza

class LoginAttemptTracker:
    """Tracciamento tentativi di login"""
    
    @staticmethod
    def record_failed_attempt(username):
        """Registra un tentativo di login fallito"""
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        
        if username not in st.session_state.login_attempts:
            st.session_state.login_attempts[username] = {
                'count': 0,
                'last_attempt': None,
                'locked_until': None
            }
        
        st.session_state.login_attempts[username]['count'] += 1
        st.session_state.login_attempts[username]['last_attempt'] = datetime.now()
        
        # Se supera il limite, blocca l'account
        if st.session_state.login_attempts[username]['count'] >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
            lockout_until = datetime.now() + timedelta(minutes=SecurityConfig.LOCKOUT_DURATION_MINUTES)
            st.session_state.login_attempts[username]['locked_until'] = lockout_until
    
    @staticmethod
    def reset_attempts(username):
        """Reset dei tentativi di login dopo successo"""
        if 'login_attempts' in st.session_state and username in st.session_state.login_attempts:
            del st.session_state.login_attempts[username]
    
    @staticmethod
    def is_locked_out(username):
        """Controlla se l'account è bloccato"""
        if 'login_attempts' not in st.session_state:
            return False
        
        if username not in st.session_state.login_attempts:
            return False
        
        locked_until = st.session_state.login_attempts[username].get('locked_until')
        if locked_until and datetime.now() < locked_until:
            return True
        
        # Se il blocco è scaduto, rimuovilo
        if locked_until and datetime.now() >= locked_until:
            st.session_state.login_attempts[username]['locked_until'] = None
            st.session_state.login_attempts[username]['count'] = 0
        
        return False
    
    @staticmethod
    def get_lockout_remaining_time(username):
        """Ottiene il tempo rimanente di blocco in minuti"""
        if 'login_attempts' not in st.session_state:
            return 0
        
        if username not in st.session_state.login_attempts:
            return 0
        
        locked_until = st.session_state.login_attempts[username].get('locked_until')
        if locked_until:
            remaining = locked_until - datetime.now()
            return max(0, int(remaining.total_seconds() / 60))
        
        return 0
