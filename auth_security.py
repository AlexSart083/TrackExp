"""
Modulo per la gestione dell'autenticazione e sicurezza
Contiene tutte le funzioni relative a:
- Hashing delle password
- Validazione password
- Gestione tentativi di login
- Autenticazione utenti
- Gestione sessioni
"""

import hashlib
import secrets
import time
import json
import os
import re
from datetime import datetime
from pathlib import Path

class SecurityConfig:
    """Configurazioni di sicurezza"""
    MIN_PASSWORD_LENGTH = 8
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 300  # 5 minuti in secondi
    SESSION_TIMEOUT = 3600  # 1 ora in secondi
    SALT_LENGTH = 32
    HASH_ITERATIONS = 100000

class FileManager:
    """Gestione sicura dei file"""
    
    @staticmethod
    def get_secure_data_dir():
        """Crea e restituisce la directory sicura per i dati"""
        data_dir = Path("secure_data")
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    @staticmethod
    def sanitize_username(username):
        """Sanitizza il nome utente"""
        return re.sub(r'[^a-zA-Z0-9_-]', '', username)
    
    @staticmethod
    def get_user_data_file(username):
        """Genera il percorso sicuro del file dati specifico per utente"""
        username_clean = FileManager.sanitize_username(username)
        data_dir = FileManager.get_secure_data_dir()
        return str(data_dir / f"spese_data_{username_clean}.json")
    
    @staticmethod
    def get_users_file():
        """Restituisce il percorso del file utenti sicuro"""
        data_dir = FileManager.get_secure_data_dir()
        return str(data_dir / "users_secure.json")
    
    @staticmethod
    def get_login_attempts_file():
        """Restituisce il percorso del file per il tracking dei tentativi di login"""
        data_dir = FileManager.get_secure_data_dir()
        return str(data_dir / "login_attempts.json")

class PasswordManager:
    """Gestione sicura delle password"""
    
    @staticmethod
    def generate_salt():
        """Genera un salt casuale per l'hashing della password"""
        return secrets.token_hex(SecurityConfig.SALT_LENGTH)
    
    @staticmethod
    def hash_password_secure(password, salt):
        """Hash sicuro della password con salt e PBKDF2"""
        return hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            SecurityConfig.HASH_ITERATIONS
        ).hex()
    
    @staticmethod
    def validate_password_strength(password):
        """Valida la forza della password"""
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            return False, f"La password deve essere di almeno {SecurityConfig.MIN_PASSWORD_LENGTH} caratteri"
        
        checks = {
            'uppercase': re.search(r'[A-Z]', password),
            'lowercase': re.search(r'[a-z]', password), 
            'digit': re.search(r'\d', password),
            'special': re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
        }
        
        missing = [key for key, value in checks.items() if not value]
        
        if len(missing) > 1:
            requirements = {
                'uppercase': 'lettere maiuscole',
                'lowercase': 'lettere minuscole', 
                'digit': 'numeri',
                'special': 'caratteri speciali (!@#$%^&*(),.?":{}|<>)'
            }
            missing_text = ', '.join([requirements[req] for req in missing])
            return False, f"La password deve contenere: {missing_text}"
        
        return True, "Password valida"

class LoginAttemptTracker:
    """Gestione dei tentativi di login"""
    
    @staticmethod
    def load_login_attempts():
        """Carica i tentativi di login"""
        attempts_file = FileManager.get_login_attempts_file()
        if os.path.exists(attempts_file):
            try:
                with open(attempts_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def save_login_attempts(attempts_data):
        """Salva i tentativi di login"""
        attempts_file = FileManager.get_login_attempts_file()
        try:
            with open(attempts_file, 'w') as f:
                json.dump(attempts_data, f)
        except Exception as e:
            raise Exception(f"Errore nel salvare i tentativi di login: {e}")
    
    @staticmethod
    def is_account_locked(username):
        """Controlla se l'account è bloccato"""
        attempts_data = LoginAttemptTracker.load_login_attempts()
        username_clean = FileManager.sanitize_username(username)
        
        if username_clean not in attempts_data:
            return False, 0
        
        user_attempts = attempts_data[username_clean]
        
        # Se non ci sono abbastanza tentativi falliti, non è bloccato
        if user_attempts.get('failed_attempts', 0) < SecurityConfig.MAX_LOGIN_ATTEMPTS:
            return False, 0
        
        # Controlla se il tempo di blocco è scaduto
        last_attempt = user_attempts.get('last_attempt', 0)
        current_time = time.time()
        
        if current_time - last_attempt > SecurityConfig.LOCKOUT_DURATION:
            # Reset dei tentativi se il tempo di blocco è scaduto
            attempts_data[username_clean] = {'failed_attempts': 0, 'last_attempt': 0}
            LoginAttemptTracker.save_login_attempts(attempts_data)
            return False, 0
        
        remaining_time = SecurityConfig.LOCKOUT_DURATION - (current_time - last_attempt)
        return True, int(remaining_time)
    
    @staticmethod
    def record_failed_login(username):
        """Registra un tentativo di login fallito"""
        attempts_data = LoginAttemptTracker.load_login_attempts()
        username_clean = FileManager.sanitize_username(username)
        
        if username_clean not in attempts_data:
            attempts_data[username_clean] = {'failed_attempts': 0, 'last_attempt': 0}
        
        attempts_data[username_clean]['failed_attempts'] += 1
        attempts_data[username_clean]['last_attempt'] = time.time()
        
        LoginAttemptTracker.save_login_attempts(attempts_data)
    
    @staticmethod
    def record_successful_login(username):
        """Registra un login riuscito (reset dei tentativi falliti)"""
        attempts_data = LoginAttemptTracker.load_login_attempts()
        username_clean = FileManager.sanitize_username(username)
        
        if username_clean in attempts_data:
            attempts_data[username_clean] = {'failed_attempts': 0, 'last_attempt': 0}
            LoginAttemptTracker.save_login_attempts(attempts_data)

class SessionManager:
    """Gestione delle sessioni"""
    
    @staticmethod
    def check_session_timeout(session_state):
        """Controlla se la sessione è scaduta"""
        if 'last_activity' not in session_state:
            session_state.last_activity = time.time()
            return False
        
        current_time = time.time()
        if current_time - session_state.last_activity > SecurityConfig.SESSION_TIMEOUT:
            return True
        
        # Aggiorna l'ultimo tempo di attività
        session_state.last_activity = current_time
        return False
    
    @staticmethod
    def get_remaining_session_time(session_state):
        """Restituisce il tempo rimanente della sessione in minuti"""
        if 'last_activity' not in session_state:
            return 60  # Default 60 minuti
        
        remaining = SecurityConfig.SESSION_TIMEOUT - (time.time() - session_state.last_activity)
        return max(0, int(remaining / 60))

class UserAuthenticator:
    """Classe principale per l'autenticazione degli utenti"""
    
    @staticmethod
    def authenticate_user(username, password):
        """Autentica l'utente con sicurezza migliorata"""
        users_file = FileManager.get_users_file()
        username_clean = FileManager.sanitize_username(username)
        
        # Controlla se l'account è bloccato
        is_locked, remaining_time = LoginAttemptTracker.is_account_locked(username_clean)
        if is_locked:
            return False, f"Account bloccato. Riprova tra {remaining_time} secondi."
        
        # Se il file utenti non esiste, crealo vuoto
        if not os.path.exists(users_file):
            with open(users_file, 'w') as f:
                json.dump({}, f)
            LoginAttemptTracker.record_failed_login(username_clean)
            return False, "Credenziali non valide"
        
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            if username_clean in users:
                user_data = users[username_clean]
                stored_hash = user_data['password_hash']
                salt = user_data['salt']
                
                # Verifica la password
                password_hash = PasswordManager.hash_password_secure(password, salt)
                if password_hash == stored_hash:
                    LoginAttemptTracker.record_successful_login(username_clean)
                    return True, "Login effettuato con successo"
                else:
                    LoginAttemptTracker.record_failed_login(username_clean)
                    return False, "Credenziali non valide"
            else:
                LoginAttemptTracker.record_failed_login(username_clean)
                return False, "Credenziali non valide"
        except Exception as e:
            return False, f"Errore del sistema: {e}"
    
    @staticmethod
    def register_user(username, password):
        """Registra un nuovo utente con sicurezza migliorata"""
        users_file = FileManager.get_users_file()
        username_clean = FileManager.sanitize_username(username)
        
        # Validazione username
        if len(username_clean) < 3:
            return False, "L'username deve essere di almeno 3 caratteri alfanumerici"
        
        if username != username_clean:
            return False, "L'username può contenere solo lettere, numeri, underscore e trattini"
        
        # Validazione password
        is_valid, message = PasswordManager.validate_password_strength(password)
        if not is_valid:
            return False, message
        
        # Carica utenti esistenti
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r') as f:
                    users = json.load(f)
            except:
                users = {}
        else:
            users = {}
        
        # Controlla se l'utente esiste già
        if username_clean in users:
            return False, "Username già esistente"
        
        # Genera salt e hash della password
        salt = PasswordManager.generate_salt()
        password_hash = PasswordManager.hash_password_secure(password, salt)
        
        # Aggiungi nuovo utente
        users[username_clean] = {
            'password_hash': password_hash,
            'salt': salt,
            'created_at': datetime.now().isoformat(),
            'original_username': username  # Mantieni l'username originale per display
        }
        
        try:
            with open(users_file, 'w') as f:
                json.dump(users, f, indent=2)
            return True, "Utente registrato con successo"
        except Exception as e:
            return False, f"Errore durante la registrazione: {e}"
    
    @staticmethod
    def change_password(username, old_password, new_password):
        """Cambia la password dell'utente"""
        # Verifica la password attuale
        is_valid, message = UserAuthenticator.authenticate_user(username, old_password)
        if not is_valid:
            return False, "Password attuale non corretta"
        
        # Valida la nuova password
        is_valid, message = PasswordManager.validate_password_strength(new_password)
        if not is_valid:
            return False, message
        
        users_file = FileManager.get_users_file()
        username_clean = FileManager.sanitize_username(username)
        
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            # Genera nuovo salt e hash
            salt = PasswordManager.generate_salt()
            password_hash = PasswordManager.hash_password_secure(new_password, salt)
            
            # Aggiorna la password
            users[username_clean]['password_hash'] = password_hash
            users[username_clean]['salt'] = salt
            users[username_clean]['password_changed_at'] = datetime.now().isoformat()
            
            with open(users_file, 'w') as f:
                json.dump(users, f, indent=2)
                
            return True, "Password cambiata con successo"
            
        except Exception as e:
            return False, f"Errore durante il cambio password: {e}"
