"""
Modulo per autenticazione e sicurezza - Versione Database Completa
Include tutte le classi necessarie per compatibilità
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
    
    # Proprietà per compatibilità con ui_components.py
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL_CHARS = True
    
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
        """Registra nuovo utente nel database - versione compatibile"""
        try:
            # Validazione input
            if not username or not password:
                return False, "Username e password sono obbligatori"
            
            # Sanitizza username
            username_clean = username.strip().lower()
            
            # Validazione username
            if len(username_clean) < 3:
                return False, "Username deve essere lungo almeno 3 caratteri"
            
            # Validazione forza password
            is_strong, message = PasswordManager.is_strong_password(password)
            if not is_strong:
                return False, message
            
            # Salva nel database
            db = SupabaseDatabaseManager()
            password_hash = PasswordManager.hash_password(password)
            
            # Usa username originale come display_name se non fornito
            if not display_name:
                display_name = username
            
            success = db.save_user(username_clean, password_hash, display_name)
            
            if success:
                return True, "Registrazione completata con successo!"
            else:
                return False, "Username già esistente. Scegli un username diverso."
                
        except Exception as e:
            st.error(f"Errore registrazione: {e}")
            return False, f"Errore durante la registrazione: {e}"
    
    @staticmethod
    def authenticate_user(username, password):
        """Autentica utente dal database - versione compatibile con ui_components.py"""
        try:
            if not username or not password:
                return False, "Username e password sono obbligatori"
            
            # Sanitizza username
            username_clean = username.strip().lower()
            
            db = SupabaseDatabaseManager()
            user = db.get_user(username_clean)
            
            if user and PasswordManager.verify_password(password, user['password_hash']):
                # Reset dei tentativi falliti
                LoginAttemptTracker.reset_attempts(username_clean)
                return True, "Login effettuato con successo"
            else:
                # Registra tentativo fallito
                LoginAttemptTracker.record_failed_attempt(username_clean)
                return False, "Username o password non corretti"
                
        except Exception as e:
            st.error(f"Errore autenticazione: {e}")
            return False, f"Errore di connessione: {e}"
    
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
        """Controlla se utente è bloccato - ritorna tupla per compatibilità"""
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        
        attempts = st.session_state.login_attempts.get(username, {})
        if attempts.get('count', 0) >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
            lockout_time = attempts.get('lockout_time')
            if lockout_time and datetime.now() < lockout_time:
                remaining_seconds = (lockout_time - datetime.now()).total_seconds()
                remaining_minutes = int(remaining_seconds / 60)
                return True, remaining_minutes
        
        return False, 0
    
    @staticmethod
    def is_account_locked(username):
        """Alias per compatibilità con ui_components.py"""
        is_locked, remaining_time = LoginAttemptTracker.is_locked_out(username)
        return is_locked, remaining_time
    
    @staticmethod
    def load_login_attempts():
        """Carica i tentativi di login per compatibilità"""
        if 'login_attempts' not in st.session_state:
            st.session_state.login_attempts = {}
        
        # Converti in formato compatibile
        attempts_data = {}
        for username, data in st.session_state.login_attempts.items():
            attempts_data[username] = {
                'failed_attempts': data.get('count', 0),
                'lockout_time': data.get('lockout_time')
            }
        
        return attempts_data
    
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
    
    @staticmethod
    def get_remaining_lockout_time(username):
        """Ottiene tempo rimanente di blocco"""
        if 'login_attempts' not in st.session_state:
            return 0
        
        attempts = st.session_state.login_attempts.get(username, {})
        lockout_time = attempts.get('lockout_time')
        if lockout_time and datetime.now() < lockout_time:
            remaining_seconds = (lockout_time - datetime.now()).total_seconds()
            return int(remaining_seconds / 60)
        
        return 0

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
    
    @staticmethod
    def sanitize_username(username):
        """Sanitizza username per compatibilità - ora semplicemente ritorna l'username"""
        return username.strip().lower()
    
    @staticmethod
    def username_exists(username):
        """Controlla se username esiste - ora usa il database"""
        try:
            db = SupabaseDatabaseManager()
            user = db.get_user(username)
            return user is not None
        except Exception:
            return False
    
    @staticmethod
    def save_user_data(username, password_hash, display_name=None):
        """Salva dati utente - ora usa il database"""
        try:
            db = SupabaseDatabaseManager()
            return db.save_user(username, password_hash, display_name)
        except Exception:
            return False
    
    @staticmethod
    def load_user_data(username):
        """Carica dati utente - ora usa il database"""
        try:
            db = SupabaseDatabaseManager()
            return db.get_user(username)
        except Exception:
            return None
    
    @staticmethod
    def verify_user_password(username, password):
        """Verifica password utente - ora usa il database"""
        try:
            db = SupabaseDatabaseManager()
            user = db.get_user(username)
            if user:
                return PasswordManager.verify_password(password, user['password_hash'])
            return False
        except Exception:
            return False

# Classi placeholder per compatibilità - sostituisci con le tue classi originali
class PrivacyManager:
    """Placeholder - copia la tua classe originale qui"""
    @staticmethod
    def show_detailed_privacy_page():
        st.write("Privacy Manager - da implementare")

class FormComponents:
    """Placeholder - copia la tua classe originale qui"""
    @staticmethod
    def show_success_message_with_actions(message, action1_text, action1_key, action2_text, action2_key):
        st.success(message)
        col1, col2 = st.columns(2)
        with col1:
            if st.button(action1_text, key=action1_key):
                return "action1"
        with col2:
            if st.button(action2_text, key=action2_key):
                return "action2"
        return None
    
    @staticmethod
    def show_account_form():
        with st.form("account_form"):
            nome_conto = st.text_input("Nome del conto")
            descrizione_conto = st.text_area("Descrizione (opzionale)")
            tipo_conto = st.selectbox("Tipo di conto", ["Carta di credito", "Conto corrente", "PayPal", "Contanti", "Altro"])
            submitted = st.form_submit_button("Aggiungi Conto")
        return submitted, nome_conto, descrizione_conto, tipo_conto
    
    @staticmethod
    def show_change_password_form():
        with st.form("change_password_form"):
            current_password = st.text_input("Password corrente", type="password")
            new_password = st.text_input("Nuova password", type="password")
            confirm_new_password = st.text_input("Conferma nuova password", type="password")
            submitted = st.form_submit_button("Cambia Password")
        return submitted, current_password, new_password, confirm_new_password
    
    @staticmethod
    def show_expense_form(conti_options, tipo_form):
        if tipo_form == "giornaliera":
            with st.form("expense_form"):
                data = st.date_input("Data")
                categoria = st.selectbox("Categoria", ["Alimentari", "Trasporti", "Casa", "Salute", "Svago", "Altro"])
                descrizione = st.text_input("Descrizione")
                importo = st.number_input("Importo (€)", min_value=0.01, step=0.01)
                conto = st.selectbox("Conto", conti_options)
                submitted = st.form_submit_button("Aggiungi Spesa")
            return submitted, {
                'data': data,
                'categoria': categoria,
                'descrizione': descrizione,
                'importo': importo,
                'conto': conto
            }
        else:  # ricorrente
            with st.form("recurring_expense_form"):
                nome = st.text_input("Nome della spesa")
                categoria = st.selectbox("Categoria", ["Alimentari", "Trasporti", "Casa", "Salute", "Svago", "Altro"])
                importo = st.number_input("Importo (€)", min_value=0.01, step=0.01)
                frequenza = st.selectbox("Frequenza", ["Mensile", "Settimanale", "Annuale"])
                conto = st.selectbox("Conto", conti_options)
                submitted = st.form_submit_button("Aggiungi Spesa Ricorrente")
            return submitted, {
                'nome': nome,
                'categoria': categoria,
                'importo': importo,
                'frequenza': frequenza,
                'conto': conto
            }

class UIHelpers:
    """Placeholder - copia la tua classe originale qui"""
    @staticmethod
    def show_header_with_user_info(display_name, remaining_mins):
        st.title("💸 Gestione Spese Mensili")
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        
        with col1:
            st.write(f"👤 **Benvenuto, {display_name}!**")
            st.write(f"⏰ Sessione: {remaining_mins} min rimanenti")
        
        with col2:
            if st.button("🏦 Conti"):
                return "conti"
        with col3:
            if st.button("🔒 Password"):
                return "password"
        with col4:
            if st.button("🛡️ Privacy"):
                return "privacy"
        with col5:
            if st.button("🚪 Logout"):
                return "logout"
        return None
    
    @staticmethod
    def show_navigation_buttons():
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Aggiungi Spesa", use_container_width=True):
                return "aggiungi_spesa"
        with col2:
            if st.button("🗂️ Gestisci Spese", use_container_width=True):
                return "gestisci_spese"
        return None
    
    @staticmethod
    def show_month_year_selector():
        col1, col2 = st.columns(2)
        with col1:
            mese = st.selectbox("Mese", range(1, 13), format_func=lambda x: calendar.month_name[x])
        with col2:
            anno = st.selectbox("Anno", range(2020, 2030), index=datetime.now().year - 2020)
        return mese, anno
    
    @staticmethod
    def show_metrics(totale_giornaliere, totale_ricorrenti, totale):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Spese Giornaliere", f"€{totale_giornaliere:.2f}")
        with col2:
            st.metric("Spese Ricorrenti", f"€{totale_ricorrenti:.2f}")
        with col3:
            st.metric("Totale Mese", f"€{totale:.2f}")
    
    @staticmethod
    def show_sidebar_info(username, conti):
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Info Account")
        st.sidebar.write(f"👤 **Username:** {username}")
        st.sidebar.write(f"🏦 **Conti configurati:** {len(conti)}")
        
        if len(conti) == 0:
            if st.sidebar.button("🏦 Configura il tuo primo conto"):
                return "configura_conti"
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🛡️ Privacy & Sicurezza")
        if st.sidebar.button("📄 Dettagli Privacy"):
            return "dettagli_privacy"
        
        return None

class StateManager:
    """Placeholder - copia la tua classe originale qui"""
    @staticmethod
    def clear_user_session():
        keys_to_clear = ['authenticated', 'username', 'display_username', 
                        'spese_giornaliere', 'spese_ricorrenti', 'conti']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    @staticmethod
    def reset_form_fields():
        # Reset dei campi form se necessario
        pass

class LoginForm:
    """Placeholder - copia la tua classe originale qui"""
    @staticmethod
    def show_login_form():
        st.title("🔐 Accesso - Gestione Spese")
        
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Registrazione"])
        
        with tab1:
            LoginForm._show_login_tab()
        
        with tab2:
            LoginForm._show_registration_tab()
    
    @staticmethod
    def _show_login_tab():
        with st.form("login_form"):
            username = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Accedi")
        
        if submitted:
            if LoginAttemptTracker.is_locked_out(username):
                st.error("Account temporaneamente bloccato per troppi tentativi falliti")
                return
            
            success, display_name = UserAuthenticator.authenticate_user(username, password)
            if success:
                LoginAttemptTracker.reset_attempts(username)
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.display_username = display_name
                st.session_state.last_activity = datetime.now()
                st.success("Login effettuato con successo!")
                st.rerun()
            else:
                LoginAttemptTracker.record_failed_attempt(username)
                st.error("Credenziali non valide")
    
    @staticmethod
    def _show_registration_tab():
        with st.form("registration_form"):
            email = st.text_input("Email")
            display_name = st.text_input("Nome visualizzato (opzionale)")
            password = st.text_input(
                "Password", 
                type="password",
                help=f"Minimo {SecurityConfig.MIN_PASSWORD_LENGTH} caratteri con lettere maiuscole, minuscole, numeri e caratteri speciali."
            )
            confirm_password = st.text_input("Conferma Password", type="password")
            submitted = st.form_submit_button("Registrati")
        
        if submitted:
            if password != confirm_password:
                st.error("Le password non coincidono")
                return
            
            success, message = UserAuthenticator.register_user(email, password, display_name)
            if success:
                st.success(message)
                st.info("Ora puoi effettuare il login con le tue credenziali")
            else:
                st.error(message)
