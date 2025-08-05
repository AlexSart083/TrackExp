import streamlit as st
import pandas as pd
import json
import os
import hashlib
import secrets
import time
from datetime import datetime, date
import calendar
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import re

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Spese Mensili",
    page_icon="💸",
    layout="wide"
)

# Configurazioni di sicurezza
SECURITY_CONFIG = {
    'MIN_PASSWORD_LENGTH': 8,
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_DURATION': 300,  # 5 minuti in secondi
    'SESSION_TIMEOUT': 3600,  # 1 ora in secondi
    'SALT_LENGTH': 32,
    'HASH_ITERATIONS': 100000
}

# Funzioni di sicurezza avanzate
def generate_salt():
    """Genera un salt casuale per l'hashing della password"""
    return secrets.token_hex(SECURITY_CONFIG['SALT_LENGTH'])

def hash_password_secure(password, salt):
    """Hash sicuro della password con salt e PBKDF2"""
    return hashlib.pbkdf2_hmac('sha256', 
                              password.encode('utf-8'), 
                              salt.encode('utf-8'), 
                              SECURITY_CONFIG['HASH_ITERATIONS']).hex()

def validate_password_strength(password):
    """Valida la forza della password"""
    if len(password) < SECURITY_CONFIG['MIN_PASSWORD_LENGTH']:
        return False, f"La password deve essere di almeno {SECURITY_CONFIG['MIN_PASSWORD_LENGTH']} caratteri"
    
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

def sanitize_username(username):
    """Sanitizza il nome utente"""
    # Rimuove caratteri non alfanumerici eccetto underscore e trattini
    return re.sub(r'[^a-zA-Z0-9_-]', '', username)

def get_secure_data_dir():
    """Crea e restituisce la directory sicura per i dati"""
    data_dir = Path("secure_data")
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_user_data_file(username):
    """Genera il percorso sicuro del file dati specifico per utente"""
    username_clean = sanitize_username(username)
    data_dir = get_secure_data_dir()
    return str(data_dir / f"spese_data_{username_clean}.json")

def get_users_file():
    """Restituisce il percorso del file utenti sicuro"""
    data_dir = get_secure_data_dir()
    return str(data_dir / "users_secure.json")

def get_login_attempts_file():
    """Restituisce il percorso del file per il tracking dei tentativi di login"""
    data_dir = get_secure_data_dir()
    return str(data_dir / "login_attempts.json")

def load_login_attempts():
    """Carica i tentativi di login"""
    attempts_file = get_login_attempts_file()
    if os.path.exists(attempts_file):
        try:
            with open(attempts_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_login_attempts(attempts_data):
    """Salva i tentativi di login"""
    attempts_file = get_login_attempts_file()
    try:
        with open(attempts_file, 'w') as f:
            json.dump(attempts_data, f)
    except Exception as e:
        st.error(f"Errore nel salvare i tentativi di login: {e}")

def is_account_locked(username):
    """Controlla se l'account è bloccato"""
    attempts_data = load_login_attempts()
    username_clean = sanitize_username(username)
    
    if username_clean not in attempts_data:
        return False, 0
    
    user_attempts = attempts_data[username_clean]
    
    # Se non ci sono abbastanza tentativi falliti, non è bloccato
    if user_attempts.get('failed_attempts', 0) < SECURITY_CONFIG['MAX_LOGIN_ATTEMPTS']:
        return False, 0
    
    # Controlla se il tempo di blocco è scaduto
    last_attempt = user_attempts.get('last_attempt', 0)
    current_time = time.time()
    
    if current_time - last_attempt > SECURITY_CONFIG['LOCKOUT_DURATION']:
        # Reset dei tentativi se il tempo di blocco è scaduto
        attempts_data[username_clean] = {'failed_attempts': 0, 'last_attempt': 0}
        save_login_attempts(attempts_data)
        return False, 0
    
    remaining_time = SECURITY_CONFIG['LOCKOUT_DURATION'] - (current_time - last_attempt)
    return True, int(remaining_time)

def record_failed_login(username):
    """Registra un tentativo di login fallito"""
    attempts_data = load_login_attempts()
    username_clean = sanitize_username(username)
    
    if username_clean not in attempts_data:
        attempts_data[username_clean] = {'failed_attempts': 0, 'last_attempt': 0}
    
    attempts_data[username_clean]['failed_attempts'] += 1
    attempts_data[username_clean]['last_attempt'] = time.time()
    
    save_login_attempts(attempts_data)

def record_successful_login(username):
    """Registra un login riuscito (reset dei tentativi falliti)"""
    attempts_data = load_login_attempts()
    username_clean = sanitize_username(username)
    
    if username_clean in attempts_data:
        attempts_data[username_clean] = {'failed_attempts': 0, 'last_attempt': 0}
        save_login_attempts(attempts_data)

def check_session_timeout():
    """Controlla se la sessione è scaduta"""
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
        return False
    
    current_time = time.time()
    if current_time - st.session_state.last_activity > SECURITY_CONFIG['SESSION_TIMEOUT']:
        return True
    
    # Aggiorna l'ultimo tempo di attività
    st.session_state.last_activity = current_time
    return False

def authenticate_user(username, password):
    """Autentica l'utente con sicurezza migliorata"""
    users_file = get_users_file()
    username_clean = sanitize_username(username)
    
    # Controlla se l'account è bloccato
    is_locked, remaining_time = is_account_locked(username_clean)
    if is_locked:
        return False, f"Account bloccato. Riprova tra {remaining_time} secondi."
    
    # Se il file utenti non esiste, crealo vuoto
    if not os.path.exists(users_file):
        with open(users_file, 'w') as f:
            json.dump({}, f)
        record_failed_login(username_clean)
        return False, "Credenziali non valide"
    
    try:
        with open(users_file, 'r') as f:
            users = json.load(f)
        
        if username_clean in users:
            user_data = users[username_clean]
            stored_hash = user_data['password_hash']
            salt = user_data['salt']
            
            # Verifica la password
            password_hash = hash_password_secure(password, salt)
            if password_hash == stored_hash:
                record_successful_login(username_clean)
                return True, "Login effettuato con successo"
            else:
                record_failed_login(username_clean)
                return False, "Credenziali non valide"
        else:
            record_failed_login(username_clean)
            return False, "Credenziali non valide"
    except Exception as e:
        st.error(f"Errore durante l'autenticazione: {e}")
        return False, "Errore del sistema"

def register_user(username, password):
    """Registra un nuovo utente con sicurezza migliorata"""
    users_file = get_users_file()
    username_clean = sanitize_username(username)
    
    # Validazione username
    if len(username_clean) < 3:
        return False, "L'username deve essere di almeno 3 caratteri alfanumerici"
    
    if username != username_clean:
        return False, "L'username può contenere solo lettere, numeri, underscore e trattini"
    
    # Validazione password
    is_valid, message = validate_password_strength(password)
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
    salt = generate_salt()
    password_hash = hash_password_secure(password, salt)
    
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

def change_password(username, old_password, new_password):
    """Cambia la password dell'utente"""
    # Verifica la password attuale
    is_valid, message = authenticate_user(username, old_password)
    if not is_valid:
        return False, "Password attuale non corretta"
    
    # Valida la nuova password
    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        return False, message
    
    users_file = get_users_file()
    username_clean = sanitize_username(username)
    
    try:
        with open(users_file, 'r') as f:
            users = json.load(f)
        
        # Genera nuovo salt e hash
        salt = generate_salt()
        password_hash = hash_password_secure(new_password, salt)
        
        # Aggiorna la password
        users[username_clean]['password_hash'] = password_hash
        users[username_clean]['salt'] = salt
        users[username_clean]['password_changed_at'] = datetime.now().isoformat()
        
        with open(users_file, 'w') as f:
            json.dump(users, f, indent=2)
            
        return True, "Password cambiata con successo"
        
    except Exception as e:
        return False, f"Errore durante il cambio password: {e}"

def show_privacy_disclaimer():
    """Mostra il disclaimer sulla privacy"""
    st.info("""
    🔒 **INFORMATIVA PRIVACY**
    
    **Privacy e sicurezza dei tuoi dati finanziari:**
    
    • ✅ **Noi sviluppatori NON raccogliamo** le tue informazioni personali o finanziarie
    • ✅ **NON condividiamo** i tuoi dati con terze parti
    • ✅ **Password crittografate** con algoritmi di sicurezza avanzati (PBKDF2)  
    • ✅ **File separati per utente** - isolamento completo tra account
    • ✅ **Nessun tracking comportamentale** da parte nostra
    
    ⚠️ **Importante**: Questa app è ospitata su Streamlit Cloud. I dati vengono salvati sui server di Streamlit/Snowflake secondo le loro politiche di privacy.
    
    📋 **Raccomandazione**: Per dati estremamente sensibili, considera di scaricare il codice e usarlo localmente.
    """)

def login_form():
    """Form di login/registrazione con sicurezza migliorata"""
    st.title("🔐 Accesso Sicuro - Gestione Spese Mensili")
    
    # Disclaimer Privacy prominente nella pagina di login
    show_privacy_disclaimer()
    
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Registrazione"])
    
    with tab1:
        st.subheader("Accedi al tuo account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Accedi")
            
            if login_submitted:
                if username and password:
                    username_clean = sanitize_username(username)
                    
                    # Controlla se l'account è bloccato
                    is_locked, remaining_time = is_account_locked(username_clean)
                    if is_locked:
                        st.error(f"🚫 Account bloccato per troppi tentativi falliti. Riprova tra {remaining_time} secondi.")
                    else:
                        success, message = authenticate_user(username, password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.username = username_clean
                            st.session_state.display_username = username
                            st.session_state.last_activity = time.time()
                            st.success("✅ Login effettuato con successo!")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                            
                            # Mostra informazioni sui tentativi rimanenti
                            attempts_data = load_login_attempts()
                            if username_clean in attempts_data:
                                failed_attempts = attempts_data[username_clean].get('failed_attempts', 0)
                                remaining_attempts = SECURITY_CONFIG['MAX_LOGIN_ATTEMPTS'] - failed_attempts
                                if remaining_attempts > 0:
                                    st.warning(f"⚠️ Tentativi rimanenti: {remaining_attempts}")
                else:
                    st.error("❌ Inserisci username e password")
    
    with tab2:
        st.subheader("Crea un nuovo account sicuro")
        with st.form("register_form"):
            new_username = st.text_input("Nuovo Username", 
                                       help="Minimo 3 caratteri. Solo lettere, numeri, underscore e trattini.")
            new_password = st.text_input("Nuova Password", type="password",
                                       help=f"Minimo {SECURITY_CONFIG['MIN_PASSWORD_LENGTH']} caratteri con lettere maiuscole, minuscole, numeri e caratteri speciali.")
            confirm_password = st.text_input("Conferma Password", type="password")
            register_submitted = st.form_submit_button("Registrati")
            
            if register_submitted:
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        success, message = register_user(new_username, new_password)
                        if success:
                            st.success(f"✅ {message}")
                            st.info("🎉 Ora puoi effettuare il login con le tue credenziali")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Le password non coincidono")
                else:
                    st.error("❌ Compila tutti i campi")
    
    st.markdown("---")
    st.info("""
    🛡️ **Sicurezza Migliorata:**
    • Password robuste obbligatorie
    • Protezione contro attacchi brute force
    • Blocco account temporaneo dopo tentativi falliti
    • Timeout automatico della sessione
    • Crittografia avanzata delle password
    • Dati utente isolati e protetti
    """)

# Inizializzazione dello stato della sessione
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'display_username' not in st.session_state:
    st.session_state.display_username = None
if 'spese_giornaliere' not in st.session_state:
    st.session_state.spese_giornaliere = []
if 'spese_ricorrenti' not in st.session_state:
    st.session_state.spese_ricorrenti = []
if 'conti' not in st.session_state:
    st.session_state.conti = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"

# Controllo timeout sessione
if st.session_state.authenticated and check_session_timeout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.display_username = None
    st.session_state.spese_giornaliere = []
    st.session_state.spese_ricorrenti = []
    st.session_state.conti = []
    st.session_state.current_page = "dashboard"
    st.error("🕐 Sessione scaduta per inattività. Effettua nuovamente il login.")
    st.rerun()

# Se non autenticato, mostra il form di login
if not st.session_state.authenticated:
    login_form()
    st.stop()

# Se arrivati qui, l'utente è autenticato
DATA_FILE = get_user_data_file(st.session_state.username)

# NUOVE FUNZIONI PER LA GESTIONE DEI CONTI
def aggiungi_conto(nome, descrizione, tipo_conto="Personale"):
    """Aggiunge un nuovo conto"""
    conto = {
        'id': len(st.session_state.conti) + 1,
        'nome': nome,
        'descrizione': descrizione,
        'tipo': tipo_conto,
        'creato_il': datetime.now().isoformat()
    }
    st.session_state.conti.append(conto)
    salva_dati()
    return True

def elimina_conto(indice):
    """Elimina un conto"""
    if 0 <= indice < len(st.session_state.conti):
        conto_eliminato = st.session_state.conti[indice]
        
        # Verifica se il conto è utilizzato in qualche spesa
        conto_nome = conto_eliminato['nome']
        spese_con_conto = [s for s in st.session_state.spese_giornaliere if s.get('conto') == conto_nome]
        spese_ricorrenti_con_conto = [s for s in st.session_state.spese_ricorrenti if s.get('conto') == conto_nome]
        
        if spese_con_conto or spese_ricorrenti_con_conto:
            return False, f"Impossibile eliminare il conto '{conto_nome}'. È utilizzato in {len(spese_con_conto)} spese giornaliere e {len(spese_ricorrenti_con_conto)} spese ricorrenti."
        
        st.session_state.conti.pop(indice)
        salva_dati()
        return True, "Conto eliminato con successo"
    return False, "Errore nell'eliminazione del conto"

def get_conti_options():
    """Restituisce le opzioni dei conti per i selectbox"""
    if not st.session_state.conti:
        return ["Nessun conto configurato"]
    return [conto['nome'] for conto in st.session_state.conti]

def calcola_spese_per_conto(mese, anno):
    """Calcola le spese per conto per un mese specifico"""
    spese_mese = filtra_spese_per_mese(mese, anno)
    totale_ricorrenti_mese = calcola_spese_ricorrenti_mensili(mese, anno)
    
    # Raggruppa spese giornaliere per conto
    spese_per_conto = {}
    for spesa in spese_mese:
        conto = spesa.get('conto', 'Non specificato')
        if conto not in spese_per_conto:
            spese_per_conto[conto] = {'giornaliere': 0, 'ricorrenti': 0}
        spese_per_conto[conto]['giornaliere'] += spesa['importo']
    
    # Aggiungi spese ricorrenti per conto
    for spesa in st.session_state.spese_ricorrenti:
        conto = spesa.get('conto', 'Non specificato')
        if conto not in spese_per_conto:
            spese_per_conto[conto] = {'giornaliere': 0, 'ricorrenti': 0}
        
        importo_mensile = spesa['importo']
        if spesa['frequenza'] == 'Settimanale':
            importo_mensile *= 4.33
        elif spesa['frequenza'] == 'Annuale':
            importo_mensile /= 12
            
        spese_per_conto[conto]['ricorrenti'] += importo_mensile
    
    return spese_per_conto

# Funzioni per il salvataggio e caricamento dei dati (aggiornate per includere i conti)
def salva_dati():
    """Salva i dati in un file JSON specifico per utente"""
    data = {
        'spese_giornaliere': st.session_state.spese_giornaliere,
        'spese_ricorrenti': st.session_state.spese_ricorrenti,
        'conti': st.session_state.conti  # NUOVO: salva anche i conti
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

def carica_dati():
    """Carica i dati dal file JSON se esiste"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.spese_giornaliere = data.get('spese_giornaliere', [])
                st.session_state.spese_ricorrenti = data.get('spese_ricorrenti', [])
                st.session_state.conti = data.get('conti', [])  # NUOVO: carica anche i conti
        except Exception as e:
            st.error(f"Errore nel caricamento dei dati: {e}")

def carica_backup(file_content):
    """Carica i dati da un file di backup"""
    try:
        data = json.loads(file_content)
        st.session_state.spese_giornaliere = data.get('spese_giornaliere', [])
        st.session_state.spese_ricorrenti = data.get('spese_ricorrenti', [])
        st.session_state.conti = data.get('conti', [])  # NUOVO: carica anche i conti dal backup
        salva_dati()
        return True
    except Exception as e:
        st.error(f"Errore nel caricamento del backup: {e}")
        return False

def aggiungi_spesa_giornaliera(data, categoria, descrizione, importo, conto=None):
    """Aggiunge una spesa giornaliera (aggiornata per includere il conto)"""
    spesa = {
        'data': data.strftime('%Y-%m-%d'),
        'categoria': categoria,
        'descrizione': descrizione,
        'importo': float(importo),
        'conto': conto  # NUOVO: campo conto
    }
    st.session_state.spese_giornaliere.append(spesa)
    salva_dati()

def aggiungi_spesa_ricorrente(nome, categoria, importo, frequenza, conto=None):
    """Aggiunge una spesa ricorrente (aggiornata per includere il conto)"""
    spesa = {
        'nome': nome,
        'categoria': categoria,
        'importo': float(importo),
        'frequenza': frequenza,
        'conto': conto  # NUOVO: campo conto
    }
    st.session_state.spese_ricorrenti.append(spesa)
    salva_dati()

def elimina_spesa_giornaliera(indice):
    """Elimina una spesa giornaliera"""
    if 0 <= indice < len(st.session_state.spese_giornaliere):
        st.session_state.spese_giornaliere.pop(indice)
        salva_dati()

def elimina_spesa_ricorrente(indice):
    """Elimina una spesa ricorrente"""
    if 0 <= indice < len(st.session_state.spese_ricorrenti):
        st.session_state.spese_ricorrenti.pop(indice)
        salva_dati()

def calcola_spese_ricorrenti_mensili(mese, anno):
    """Calcola il totale delle spese ricorrenti per un mese specifico"""
    totale = 0
    for spesa in st.session_state.spese_ricorrenti:
        if spesa['frequenza'] == 'Mensile':
            totale += spesa['importo']
        elif spesa['frequenza'] == 'Settimanale':
            # Approssimazione: 4.33 settimane per mese
            totale += spesa['importo'] * 4.33
        elif spesa['frequenza'] == 'Annuale':
            totale += spesa['importo'] / 12
    return totale

def filtra_spese_per_mese(mese, anno):
    """Filtra le spese giornaliere per mese e anno"""
    spese_filtrate = []
    for spesa in st.session_state.spese_giornaliere:
        data_spesa = datetime.strptime(spesa['data'], '%Y-%m-%d')
        if data_spesa.month == mese and data_spesa.year == anno:
            spese_filtrate.append(spesa)
    return spese_filtrate

def reset_form_fields():
    """Reset dei campi del form"""
    if 'form_data' in st.session_state:
        st.session_state.form_data = None
    if 'form_categoria' in st.session_state:
        st.session_state.form_categoria = 0
    if 'form_descrizione' in st.session_state:
        st.session_state.form_descrizione = ""
    if 'form_importo' in st.session_state:
        st.session_state.form_importo = 0.01

# Carica i dati all'avvio (specifici per utente)
carica_dati()

# Header con info utente sicuro e logout
col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 1, 1, 1, 1])
with col1:
    st.title("💸 Gestione Spese Mensili")
with col2:
    display_name = st.session_state.display_username or st.session_state.username
    st.write(f"👤 **{display_name}**")
with col3:
    # Mostra tempo rimanente sessione
    if 'last_activity' in st.session_state:
        remaining = SECURITY_CONFIG['SESSION_TIMEOUT'] - (time.time() - st.session_state.last_activity)
        remaining_mins = int(remaining / 60)
        st.write(f"⏱️ {remaining_mins}min")
with col4:
    if st.button("🏦 Conti"):
        st.session_state.current_page = "gestisci_conti"
        st.rerun()
with col5:
    if st.button("🔒 Password"):
        st.session_state.current_page = "change_password"
        st.rerun()
with col6:
    if st.button("🛡️ Privacy"):
        st.session_state.current_page = "privacy_info"
        st.rerun()
with col7:
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.display_username = None
        st.session_state.spese_giornaliere = []
        st.session_state.spese_ricorrenti = []
        st.session_state.conti = []
        st.session_state.current_page = "dashboard"
        st.success("🔒 Logout effettuato con successo!")
        st.rerun()

# NUOVA PAGINA: GESTIONE CONTI
if st.session_state.current_page == "gestisci_conti":
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.header("🏦 Gestisci Conti")
    st.write(f"👤 **Utente:** {st.session_state.display_username}")
    
    tab1, tab2 = st.tabs(["➕ Aggiungi Conto", "📋 Visualizza Conti"])
    
    with tab1:
        st.subheader("Aggiungi Nuovo Conto")
        
        # Controllo per messaggio di successo
        if 'conto_aggiunto' in st.session_state and st.session_state.conto_aggiunto:
            st.success("✅ Conto aggiunto con successo!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Aggiungi altro conto", key="altro_conto"):
                    st.session_state.conto_aggiunto = False
                    st.rerun()
            with col2:
                if st.button("📋 Visualizza conti", key="visualizza_conti"):
                    st.session_state.conto_aggiunto = False
                    st.rerun()
            
            st.stop()
        
        with st.form("form_nuovo_conto"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_conto = st.text_input(
                    "Nome Conto *", 
                    placeholder="es. Carta Principale, Conto Corrente, PayPal...",
                    help="Nome identificativo del conto"
                )
                tipo_conto = st.selectbox(
                    "Tipo Conto", 
                    ["Personale", "Aziendale", "Famiglia", "Risparmi", "Investimenti", "Altro"]
                )
            
            with col2:
                descrizione_conto = st.text_area(
                    "Descrizione", 
                    placeholder="es. Carta di credito principale per spese quotidiane",
                    help="Descrizione opzionale del conto"
                )
            
            submitted_conto = st.form_submit_button("💾 Aggiungi Conto", use_container_width=True)
            
            if submitted_conto:
                if nome_conto.strip():
                    # Controlla se esiste già un conto con lo stesso nome
                    nomi_esistenti = [conto['nome'].lower() for conto in st.session_state.conti]
                    if nome_conto.lower() in nomi_esistenti:
                        st.error("❌ Esiste già un conto con questo nome!")
                    else:
                        aggiungi_conto(nome_conto.strip(), descrizione_conto.strip(), tipo_conto)
                        st.session_state.conto_aggiunto = True
                        st.rerun()
                else:
                    st.error("❌ Il nome del conto è obbligatorio!")
    
    with tab2:
        st.subheader("I Tuoi Conti")
        
        if st.session_state.conti:
            st.write("**Clicca sull'icona del cestino per eliminare un conto**")
            st.warning("⚠️ **Attenzione**: Non puoi eliminare un conto che è utilizzato in una o più spese.")
            
            for idx, conto in enumerate(st.session_state.conti):
                col1, col2, col3, col4, col5 = st.columns([3, 2, 4, 2, 1])
                
                with col1:
                    st.write(f"**{conto['nome']}**")
                with col2:
                    st.write(f"_{conto['tipo']}_")
                with col3:
                    if conto['descrizione']:
                        st.write(conto['descrizione'])
                    else:
                        st.write("_Nessuna descrizione_")
                with col4:
                    data_creazione = datetime.fromisoformat(conto['creato_il']).strftime('%d/%m/%Y')
                    st.write(f"🕐 {data_creazione}")
                with col5:
                    if st.button("🗑️", key=f"del_conto_{idx}"):
                        success, message = elimina_conto(idx)
                        if success:
                            st.success("Conto eliminato!")
                            st.rerun()
                        else:
                            st.error(message)
            
            st.markdown("---")
            st.info(f"📊 **Totale conti configurati:** {len(st.session_state.conti)}")
        else:
            st.info("🏦 Nessun conto configurato. Aggiungi il tuo primo conto!")
            st.markdown("""
            **Suggerimenti per i conti:**
            - Carta di credito principale
            - Conto corrente
            - PayPal
            - Contanti
            - Carta prepagata
            - Conto aziendale
            """)

# PAGINA INFORMAZIONI PRIVACY
elif st.session_state.current_page == "privacy_info":
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.header("🛡️ Informazioni sulla Privacy")
    st.write(f"👤 **Utente:** {st.session_state.display_username}")
    
    st.markdown("---")
    
    st.success("""
    ## 🔒 PRIVACY E SICUREZZA DEI TUOI DATI
    
    **Cosa garantiamo noi sviluppatori** riguardo alla privacy dei tuoi dati finanziari.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### ✅ **LE NOSTRE GARANZIE:**
        
        🚫 **Zero raccolta dati da parte nostra**
        • Non raccogliamo informazioni personali
        • Non monitoriamo le tue attività finanziarie
        • Non condividiamo dati con terze parti
        
        🔐 **Sicurezza implementata**
        • Password crittografate con PBKDF2
        • Salt univoci per ogni utente
        • Isolamento completo tra utenti
        
        📁 **File separati per utente**
        • Ogni utente ha file completamente isolati
        • Impossibilità di accesso incrociato
        • Backup personali e privati
        """)
    
    with col2:
        st.markdown("""
        ### ⚠️ **IMPORTANTE - STREAMLIT CLOUD:**
        
        📍 **Hosting esterno:**
        • App ospitata sui server Streamlit/Snowflake
        • I dati vengono salvati sui loro server
        • Soggetti alle politiche privacy di Streamlit
        
        🔗 **Connessioni di rete:**
        • Trasmissione dati cifrata (HTTPS)
        • Comunicazione con server Streamlit
        • Download librerie esterne
        
        💡 **Per massima privacy:**
        • Scarica il codice dal nostro repository
        • Esegui l'app localmente sul tuo PC
        • Tutti i dati rimarranno solo da te
        """)
    
    st.markdown("---")
    
    st.warning("""
    ### 📋 **DICHIARAZIONE TRASPARENTE**
    
    **Noi sviluppatori dichiariamo che:**
    
    ✅ **NON raccogliamo** le tue informazioni finanziarie personali
    ✅ **NON monitoriamo** le tue spese o abitudini
    ✅ **NON condividiamo** i tuoi dati con terze parti
    ✅ **NON abbiamo accesso** ai contenuti dei tuoi file di spesa
    
    ⚠️ **Tuttavia, questa app è ospitata su Streamlit Cloud**, quindi:
    • I tuoi dati vengono salvati sui server di Streamlit/Snowflake
    • Sono soggetti alle [politiche privacy di Streamlit](https://streamlit.io/privacy-policy)
    • Per massima privacy, usa l'app localmente scaricando il codice
    """)
    
    st.markdown("---")
    
    st.info("""
    ### 🏠 **ALTERNATIVA PER MASSIMA PRIVACY:**
    
    **Vuoi che i dati rimangano solo sul tuo dispositivo?**
    
    1. 📥 Scarica il codice sorgente dal repository
    2. 💻 Installa Python e Streamlit sul tuo PC
    3. ▶️ Esegui l'app localmente con `streamlit run app.py`
    4. 🔒 Tutti i dati rimarranno solo sul tuo dispositivo
    
    In questo modo avrai **privacy totale** senza alcuna trasmissione di dati.
    """)

# PAGINA CAMBIO PASSWORD
elif st.session_state.current_page == "change_password":
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.header("🔒 Cambia Password")
    st.write(f"👤 **Utente:** {st.session_state.display_username}")
    
    # Controllo per messaggio di successo
    if 'password_changed' in st.session_state and st.session_state.password_changed:
        st.success("✅ Password cambiata con successo!")
        st.info("🔒 Per sicurezza, effettua un nuovo login")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔑 Vai al Login", key="go_to_login"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.display_username = None
                st.session_state.spese_giornaliere = []
                st.session_state.spese_ricorrenti = []
                st.session_state.conti = []
                st.session_state.current_page = "dashboard"
                st.session_state.password_changed = False
                st.rerun()
        with col2:
            if st.button("🏠 Torna alla Dashboard", key="back_to_dashboard"):
                st.session_state.current_page = "dashboard"
                st.session_state.password_changed = False
                st.rerun()
        
        st.stop()
    
    st.markdown("---")
    
    with st.form("change_password_form"):
        st.subheader("Modifica la tua password")
        
        current_password = st.text_input(
            "Password Attuale", 
            type="password",
            help="Inserisci la tua password attuale per confermare l'identità"
        )
        
        new_password = st.text_input(
            "Nuova Password",
            type="password",
            help=f"Minimo {SECURITY_CONFIG['MIN_PASSWORD_LENGTH']} caratteri con lettere maiuscole, minuscole, numeri e caratteri speciali."
        )
        
        confirm_new_password = st.text_input(
            "Conferma Nuova Password", 
            type="password",
            help="Ripeti la nuova password per confermare"
        )
        
        change_submitted = st.form_submit_button("🔄 Cambia Password", use_container_width=True)
        
        if change_submitted:
            if current_password and new_password and confirm_new_password:
                if new_password == confirm_new_password:
                    success, message = change_password(
                        st.session_state.username,
                        current_password,
                        new_password
                    )
                    if success:
                        st.session_state.password_changed = True
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ Le nuove password non coincidono")
            else:
                st.error("❌ Compila tutti i campi")
    
    st.markdown("---")
    st.info("""
    🛡️ **Consigli per una password sicura:**
    • Usa almeno 8 caratteri
    • Includi lettere maiuscole e minuscole
    • Aggiungi almeno un numero
    • Usa caratteri speciali (!@#$%^&*(),.?":{}|<>)
    • Non utilizzare informazioni personali
    • Non riutilizzare password di altri account
    """)

# DASHBOARD (ex Resoconto Mensile) - AGGIORNATA CON TABELLA SPESE PER CONTO
elif st.session_state.current_page == "dashboard":
    # Pulsanti di navigazione
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("➕ Aggiungi Spesa", use_container_width=True):
            st.session_state.current_page = "aggiungi_spesa"
            st.rerun()
    
    with col2:
        if st.button("🗂️ Gestisci Spese", use_container_width=True):
            st.session_state.current_page = "gestisci_spese"
            st.rerun()
    
    st.markdown("---")

    # Dashboard - Resoconto Mensile
    st.header("📈 Dashboard - Resoconto Mensile")
    
    # Selezione mese e anno
    col1, col2 = st.columns(2)
    with col1:
        mese_selezionato = st.selectbox("Mese", range(1, 13), 
            format_func=lambda x: calendar.month_name[x],
            index=datetime.now().month - 1)
    with col2:
        anno_selezionato = st.selectbox("Anno", 
            range(2020, datetime.now().year + 2),
            index=datetime.now().year - 2020)
    
    # Calcola spese per il mese selezionato
    spese_mese = filtra_spese_per_mese(mese_selezionato, anno_selezionato)
    totale_giornaliere_mese = sum(spesa['importo'] for spesa in spese_mese)
    totale_ricorrenti_mese = calcola_spese_ricorrenti_mensili(mese_selezionato, anno_selezionato)
    totale_mese = totale_giornaliere_mese + totale_ricorrenti_mese
    
    # Mostra il resoconto
    st.subheader(f"Resoconto per {calendar.month_name[mese_selezionato]} {anno_selezionato}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Spese Giornaliere", f"€{totale_giornaliere_mese:.2f}")
    with col2:
        st.metric("Spese Ricorrenti", f"€{totale_ricorrenti_mese:.2f}")
    with col3:
        st.metric("Totale Mese", f"€{totale_mese:.2f}")
    
    # NUOVA SEZIONE: Spese per Conto
    st.subheader("💳 Spese per Conto")
    
    if st.session_state.conti:
        spese_per_conto = calcola_spese_per_conto(mese_selezionato, anno_selezionato)
        
        if spese_per_conto:
            # Crea DataFrame per la tabella
            tabella_conti = []
            for conto, importi in spese_per_conto.items():
                totale_conto = importi['giornaliere'] + importi['ricorrenti']
                tabella_conti.append({
                    'Conto': conto,
                    'Spese Giornaliere': f"€{importi['giornaliere']:.2f}",
                    'Spese Ricorrenti': f"€{importi['ricorrenti']:.2f}",
                    'Totale': f"€{totale_conto:.2f}"
                })
            
            # Ordina per totale decrescente
            tabella_conti.sort(key=lambda x: float(x['Totale'].replace('€', '').replace(',', '.')), reverse=True)
            
            # Mostra la tabella
            df_conti = pd.DataFrame(tabella_conti)
            st.dataframe(df_conti, use_container_width=True)
            
            # Grafico spese per conto
            if len(spese_per_conto) > 1:
                dati_grafico = []
                for conto, importi in spese_per_conto.items():
                    totale_conto = importi['giornaliere'] + importi['ricorrenti']
                    if totale_conto > 0:
                        dati_grafico.append({'Conto': conto, 'Importo': totale_conto})
                
                if dati_grafico:
                    df_grafico = pd.DataFrame(dati_grafico)
                    fig = px.pie(df_grafico, values='Importo', names='Conto', 
                               title="Distribuzione Spese per Conto")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📝 Nessuna spesa registrata per questo mese con i conti configurati.")
    else:
        st.warning("🏦 **Nessun conto configurato!** Vai su 'Conti' per configurare i tuoi conti di pagamento.")
        if st.button("🏦 Configura Conti Ora"):
            st.session_state.current_page = "gestisci_conti"
            st.rerun()
    
    # Elenco Completo Spese Giornaliere (prima sezione)
    if spese_mese:
        st.subheader("📋 Elenco Completo Spese Giornaliere")
        df_mese = pd.DataFrame(spese_mese)
        df_mese['data'] = pd.to_datetime(df_mese['data']).dt.strftime('%d/%m/%Y')
        # Riordina le colonne per mostrare anche il conto
        cols_order = ['data', 'categoria', 'descrizione', 'importo', 'conto']
        df_mese = df_mese.reindex(columns=cols_order)
        df_mese.columns = ['Data', 'Categoria', 'Descrizione', 'Importo', 'Conto']
        st.dataframe(df_mese, use_container_width=True)
    else:
        st.info("📝 Nessuna spesa giornaliera per questo mese")
    
    # Dettaglio Spese Giornaliere (seconda sezione con grafici)
    if spese_mese:
        st.subheader("📊 Dettaglio Spese Giornaliere")
        
        # Raggruppa per categoria
        df_categorie = pd.DataFrame(spese_mese)
        spese_per_categoria = df_categorie.groupby('categoria')['importo'].sum().reset_index()
        spese_per_categoria = spese_per_categoria.sort_values('importo', ascending=False)
        
        # Grafico spese per categoria
        fig = px.pie(spese_per_categoria, values='importo', names='categoria', 
                   title="Spese per Categoria")
        st.plotly_chart(fig, use_container_width=True)
        
        # Lista spese per categoria
        st.write("**Riassunto per categoria:**")
        for _, row in spese_per_categoria.iterrows():
            st.write(f"• {row['categoria']}: €{row['importo']:.2f}")
    
    # Mostra spese ricorrenti se presenti
    if st.session_state.spese_ricorrenti:
        st.subheader("🔄 Spese Ricorrenti Attive")
        ricorrenti_df = []
        for spesa in st.session_state.spese_ricorrenti:
            importo_mensile = spesa['importo']
            if spesa['frequenza'] == 'Settimanale':
                importo_mensile *= 4.33
            elif spesa['frequenza'] == 'Annuale':
                importo_mensile /= 12
            
            ricorrenti_df.append({
                'Nome': spesa['nome'],
                'Categoria': spesa['categoria'],
                'Importo Originale': f"€{spesa['importo']:.2f}",
                'Frequenza': spesa['frequenza'],
                'Conto': spesa.get('conto', 'Non specificato'),
                'Importo Mensile': f"€{importo_mensile:.2f}"
            })
        
        if ricorrenti_df:
            st.dataframe(pd.DataFrame(ricorrenti_df), use_container_width=True)

# AGGIUNGI SPESA - AGGIORNATA CON SELEZIONE CONTO
elif st.session_state.current_page == "aggiungi_spesa":
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.header("➕ Aggiungi Nuova Spesa")
    
    # Controllo se ci sono conti configurati
    if not st.session_state.conti:
        st.warning("⚠️ **Nessun conto configurato!** Configura almeno un conto prima di aggiungere spese.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏦 Configura Conti", use_container_width=True):
                st.session_state.current_page = "gestisci_conti"
                st.rerun()
        with col2:
            st.info("Puoi comunque aggiungere spese, ma non sarà specificato il conto di pagamento.")
    
    tab1, tab2 = st.tabs(["💰 Spesa Giornaliera", "🔄 Spesa Ricorrente"])
    
    with tab1:
        st.subheader("Spesa Giornaliera")
        
        # Controllo per messaggio di successo
        if 'spesa_aggiunta' in st.session_state and st.session_state.spesa_aggiunta:
            st.success("✅ Spesa aggiunta correttamente!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Aggiungi altra spesa", key="altra_giornaliera"):
                    st.session_state.spesa_aggiunta = False
                    reset_form_fields()
                    st.rerun()
            with col2:
                if st.button("🏠 Torna alla Dashboard", key="dashboard_giornaliera"):
                    st.session_state.spesa_aggiunta = False
                    st.session_state.current_page = "dashboard"
                    reset_form_fields()
                    st.rerun()
            
            st.stop()
        
        with st.form("form_spesa_giornaliera"):
            col1, col2 = st.columns(2)
            
            with col1:
                data_spesa = st.date_input("Data", value=date.today())
                categoria = st.selectbox("Categoria", 
                    ["Alimentari", "Trasporti", "Bollette", "Intrattenimento", 
                     "Salute", "Abbigliamento", "Casa", "Altro"])
                # NUOVO: Selezione conto
                opzioni_conti = get_conti_options()
                conto_selezionato = st.selectbox("Conto di Pagamento", 
                    ["Nessuno"] + opzioni_conti if opzioni_conti != ["Nessun conto configurato"] else ["Nessuno"],
                    help="Seleziona il conto da cui è stata effettuata la spesa")
            
            with col2:
                descrizione = st.text_input("Descrizione")
                importo = st.number_input("Importo (€)", min_value=0.01, step=0.01)
            
            submitted = st.form_submit_button("💾 Aggiungi Spesa", use_container_width=True)
            
            if submitted:
                if descrizione and importo > 0:
                    conto_finale = None if conto_selezionato == "Nessuno" else conto_selezionato
                    aggiungi_spesa_giornaliera(data_spesa, categoria, descrizione, importo, conto_finale)
                    st.session_state.spesa_aggiunta = True
                    st.rerun()
                else:
                    st.error("❌ Compila tutti i campi correttamente!")
    
    with tab2:
        st.subheader("Spesa Ricorrente")
        
        # Controllo per messaggio di successo
        if 'spesa_ricorrente_aggiunta' in st.session_state and st.session_state.spesa_ricorrente_aggiunta:
            st.success("✅ Spesa ricorrente aggiunta correttamente!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Aggiungi altra spesa ricorrente", key="altra_ricorrente"):
                    st.session_state.spesa_ricorrente_aggiunta = False
                    reset_form_fields()
                    st.rerun()
            with col2:
                if st.button("🏠 Torna alla Dashboard", key="dashboard_ricorrente"):
                    st.session_state.spesa_ricorrente_aggiunta = False
                    st.session_state.current_page = "dashboard"
                    reset_form_fields()
                    st.rerun()
            
            st.stop()
        
        with st.form("form_spesa_ricorrente"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_ricorrente = st.text_input("Nome spesa")
                categoria_ricorrente = st.selectbox("Categoria", 
                    ["Bollette", "Abbonamenti", "Assicurazioni", "Affitto", 
                     "Trasporti", "Altro"], key="cat_ricorrente")
                # NUOVO: Selezione conto per spese ricorrenti
                opzioni_conti = get_conti_options()
                conto_ricorrente = st.selectbox("Conto di Pagamento", 
                    ["Nessuno"] + opzioni_conti if opzioni_conti != ["Nessun conto configurato"] else ["Nessuno"],
                    help="Seleziona il conto da cui viene addebitata la spesa ricorrente",
                    key="conto_ric")
            
            with col2:
                importo_ricorrente = st.number_input("Importo (€)", min_value=0.01, step=0.01, key="importo_ricorrente")
                frequenza = st.selectbox("Frequenza", ["Settimanale", "Mensile", "Annuale"])
            
            submitted_ricorrente = st.form_submit_button("💾 Aggiungi Spesa Ricorrente", use_container_width=True)
            
            if submitted_ricorrente:
                if nome_ricorrente and importo_ricorrente > 0:
                    conto_finale = None if conto_ricorrente == "Nessuno" else conto_ricorrente
                    aggiungi_spesa_ricorrente(nome_ricorrente, categoria_ricorrente, importo_ricorrente, frequenza, conto_finale)
                    st.session_state.spesa_ricorrente_aggiunta = True
                    st.rerun()
                else:
                    st.error("❌ Compila tutti i campi correttamente!")

# GESTISCI SPESE - AGGIORNATA PER MOSTRARE ANCHE I CONTI
elif st.session_state.current_page == "gestisci_spese":
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.header("🗂️ Gestisci Spese")
    
    tab1, tab2 = st.tabs(["💰 Spese Giornaliere", "🔄 Spese Ricorrenti"])
    
    with tab1:
        st.subheader("Spese Giornaliere")
        
        if st.session_state.spese_giornaliere:
            df = pd.DataFrame(st.session_state.spese_giornaliere)
            df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
            
            # Filtri
            col1, col2, col3 = st.columns(3)
            with col1:
                categorie_filtro = st.multiselect("Filtra per categoria", 
                    df['categoria'].unique(), default=df['categoria'].unique())
            with col2:
                mese_filtro = st.selectbox("Filtra per mese", 
                    ["Tutti"] + [calendar.month_name[i] for i in range(1, 13)])
            with col3:
                # NUOVO: Filtro per conto
                conti_unici = df['conto'].fillna('Non specificato').unique()
                conto_filtro = st.multiselect("Filtra per conto",
                    conti_unici, default=conti_unici)
            
            # Applica filtri
            df_filtrato = df[df['categoria'].isin(categorie_filtro)]
            if mese_filtro != "Tutti":
                mese_num = list(calendar.month_name).index(mese_filtro)
                df_filtrato = df_filtrato[pd.to_datetime(df_filtrato['data'], format='%d/%m/%Y').dt.month == mese_num]
            
            # Applica filtro conto
            df_filtrato = df_filtrato[df_filtrato['conto'].fillna('Non specificato').isin(conto_filtro)]
            
            # Mostra tabella con opzione di eliminazione
            st.write("**Clicca sull'icona del cestino per eliminare una spesa**")
            for idx, spesa in df_filtrato.iterrows():
                col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 3, 2, 2, 1])
                with col1:
                    st.write(spesa['data'])
                with col2:
                    st.write(spesa['categoria'])
                with col3:
                    st.write(spesa['descrizione'])
                with col4:
                    st.write(f"€{spesa['importo']:.2f}")
                with col5:
                    conto_display = spesa.get('conto', 'Non specificato')
                    if pd.isna(conto_display) or conto_display is None:
                        conto_display = 'Non specificato'
                    st.write(conto_display)
                with col6:
                    if st.button("🗑️", key=f"del_g_{idx}"):
                        elimina_spesa_giornaliera(idx)
                        st.success("Spesa eliminata!")
                        st.rerun()
            
            st.write(f"**Totale visualizzato: €{df_filtrato['importo'].sum():.2f}**")
        else:
            st.info("Nessuna spesa giornaliera registrata.")
    
    with tab2:
        st.subheader("Spese Ricorrenti")
        
        if st.session_state.spese_ricorrenti:
            st.write("**Clicca sull'icona del cestino per eliminare una spesa ricorrente**")
            for idx, spesa in enumerate(st.session_state.spese_ricorrenti):
                col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 2, 2, 1])
                with col1:
                    st.write(spesa['nome'])
                with col2:
                    st.write(spesa['categoria'])
                with col3:
                    st.write(f"€{spesa['importo']:.2f}")
                with col4:
                    st.write(spesa['frequenza'])
                with col5:
                    conto_display = spesa.get('conto', 'Non specificato')
                    if pd.isna(conto_display) or conto_display is None:
                        conto_display = 'Non specificato'
                    st.write(conto_display)
                with col6:
                    if st.button("🗑️", key=f"del_r_{idx}"):
                        elimina_spesa_ricorrente(idx)
                        st.success("Spesa ricorrente eliminata!")
                        st.rerun()
        else:
            st.info("Nessuna spesa ricorrente registrata.")

# Sidebar con funzioni di backup (specifiche per utente)
st.sidebar.title("💾 Backup & Restore")
st.sidebar.write(f"👤 **Utente:** {st.session_state.username}")

# Download backup
if st.sidebar.button("📥 Scarica Backup"):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            st.sidebar.download_button(
                label="Download JSON",
                data=f.read(),
                file_name=f"backup_spese_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
    else:
        st.sidebar.error("Nessun file di dati trovato!")

# Upload backup
st.sidebar.markdown("**📤 Carica Backup**")
uploaded_file = st.sidebar.file_uploader("Seleziona file backup", type=['json'])

if uploaded_file is not None:
    file_content = uploaded_file.read().decode('utf-8')
    if st.sidebar.button("Ripristina Backup"):
        if carica_backup(file_content):
            st.sidebar.success("✅ Backup ripristinato con successo!")
            st.rerun()
        else:
            st.sidebar.error("❌ Errore nel ripristino del backup!")

st.sidebar.markdown("---")
st.sidebar.markdown("🔒 **Sicurezza:**")
st.sidebar.markdown("• I tuoi dati sono privati")
st.sidebar.markdown("• File personale isolato")
st.sidebar.markdown(f"• File: spese_data_{st.session_state.username}.json")

# Info conti nella sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("🏦 **I Tuoi Conti:**")
if st.session_state.conti:
    for conto in st.session_state.conti[:3]:  # Mostra max 3 conti
        st.sidebar.markdown(f"• {conto['nome']}")
    if len(st.session_state.conti) > 3:
        st.sidebar.markdown(f"• ... e altri {len(st.session_state.conti) - 3}")
    st.sidebar.markdown(f"**Totale: {len(st.session_state.conti)} conti**")
else:
    st.sidebar.markdown("• Nessun conto configurato")
    if st.sidebar.button("🏦 Configura Ora"):
        st.session_state.current_page = "gestisci_conti"
        st.rerun()

# Disclaimer Privacy nella sidebar
st.sidebar.markdown("---")
st.sidebar.info("🔒 **PRIVACY**")
st.sidebar.markdown("""
**Noi sviluppatori NON raccogliamo le tue informazioni finanziarie**

⚠️ **App su Streamlit Cloud**: i dati sono sui server Streamlit

💡 **Massima privacy**: scarica il codice e usalo localmente
""")

if st.sidebar.button("ℹ️ Dettagli Privacy"):
    st.session_state.current_page = "privacy_info"
    st.rerun()

st.markdown("<p style='text-align: center; color: gray;'>Created by AS with the supervision of KIM😼</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray; font-size: 0.8em;'>🔒 <strong>Privacy:</strong> Noi sviluppatori non raccogliamo le tue informazioni finanziarie. App ospitata su Streamlit Cloud - per massima privacy usa il codice localmente.</p>", unsafe_allow_html=True)
