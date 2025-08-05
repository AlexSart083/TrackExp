"""
Modulo per i componenti dell'interfaccia utente
Contiene tutte le funzioni relative a:
- Form di login e registrazione
- Disclaimer sulla privacy
- Componenti UI riutilizzabili
- Gestione dello stato dei form
"""

import streamlit as st
import time
import pandas as pd
from datetime import datetime
from auth_security import SecurityConfig, UserAuthenticator, LoginAttemptTracker

class PrivacyManager:
    """Gestione del disclaimer sulla privacy"""
    
    @staticmethod
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
    
    @staticmethod
    def show_detailed_privacy_page():
        """Mostra la pagina dettagliata sulla privacy"""
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
        
        st.info("""
        ### 🏠 **ALTERNATIVA PER MASSIMA PRIVACY:**
        
        **Vuoi che i dati rimangano solo sul tuo dispositivo?**
        
        1. 📥 Scarica il codice sorgente dal repository
        2. 💻 Installa Python e Streamlit sul tuo PC
        3. ▶️ Esegui l'app localmente con `streamlit run app.py`
        4. 🔒 Tutti i dati rimarranno solo sul tuo dispositivo
        
        In questo modo avrai **privacy totale** senza alcuna trasmissione di dati.
        """)

class LoginForm:
    """Gestione del form di login e registrazione"""
    
    @staticmethod
    def show_login_form():
        """Mostra il form di login/registrazione"""
        st.title("🔐 Accesso Sicuro - Gestione Spese Mensili")
        
        # Disclaimer Privacy prominente nella pagina di login
        PrivacyManager.show_privacy_disclaimer()
        
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Registrazione"])
        
        with tab1:
            LoginForm._show_login_tab()
        
        with tab2:
            LoginForm._show_registration_tab()
        
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
    
@staticmethod
    def _show_login_tab():
        """Tab per il login - versione semplificata"""
        st.subheader("Accedi al tuo account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Accedi")
            
            if login_submitted:
                if username and password:
                    # Sanitizza username direttamente
                    username_clean = username.strip().lower()
                    
                    success, message = UserAuthenticator.authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.username = username_clean
                        st.session_state.display_username = username
                        st.session_state.last_activity = time.time()
                        st.success("✅ Login effettuato con successo!")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ Inserisci username e password")
    
    @staticmethod
    def _show_registration_tab():
        """Tab per la registrazione"""
        st.subheader("Crea un nuovo account sicuro")
        with st.form("register_form"):
            new_username = st.text_input("Nuovo Username", 
                                       help="Minimo 3 caratteri. Solo lettere, numeri, underscore e trattini.")
            new_password = st.text_input("Nuova Password", type="password",
                                       help=f"Minimo {SecurityConfig.MIN_PASSWORD_LENGTH} caratteri con lettere maiuscole, minuscole, numeri e caratteri speciali.")
            confirm_password = st.text_input("Conferma Password", type="password")
            register_submitted = st.form_submit_button("Registrati")
            
            if register_submitted:
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        success, message = UserAuthenticator.register_user(new_username, new_password)
                        if success:
                            st.success(f"✅ {message}")
                            st.info("🎉 Ora puoi effettuare il login con le tue credenziali")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Le password non coincidono")
                else:
                    st.error("❌ Compila tutti i campi")

class FormComponents:
    """Componenti per i form"""
    
    @staticmethod
    def show_success_message_with_actions(message, action1_text, action1_key, action2_text, action2_key):
        """Mostra messaggio di successo con azioni"""
        st.success(f"✅ {message}")
        
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
        """Form per aggiungere un conto"""
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
            
            return submitted_conto, nome_conto, descrizione_conto, tipo_conto
    
    @staticmethod
    def show_expense_form(conti_options, form_type="giornaliera"):
        """Form per aggiungere spese"""
        form_key = f"form_spesa_{form_type}"
        
        with st.form(form_key):
            col1, col2 = st.columns(2)
            
            if form_type == "giornaliera":
                with col1:
                    data_spesa = st.date_input("Data", value=datetime.now().date())
                    categoria = st.selectbox("Categoria", 
                        ["Alimentari", "Trasporti", "Bollette", "Intrattenimento", 
                         "Salute", "Abbigliamento", "Casa", "Altro"])
                    conto_selezionato = st.selectbox("Conto di Pagamento", 
                        ["Nessuno"] + conti_options if conti_options != ["Nessun conto configurato"] else ["Nessuno"],
                        help="Seleziona il conto da cui è stata effettuata la spesa")
                
                with col2:
                    descrizione = st.text_input("Descrizione")
                    importo = st.number_input("Importo (€)", min_value=0.01, step=0.01)
                
                submitted = st.form_submit_button("💾 Aggiungi Spesa", use_container_width=True)
                
                return submitted, {
                    'data': data_spesa,
                    'categoria': categoria,
                    'descrizione': descrizione,
                    'importo': importo,
                    'conto': conto_selezionato
                }
            
            else:  # ricorrente
                with col1:
                    nome_ricorrente = st.text_input("Nome spesa")
                    categoria_ricorrente = st.selectbox("Categoria", 
                        ["Bollette", "Abbonamenti", "Assicurazioni", "Affitto", 
                         "Trasporti", "Altro"], key="cat_ricorrente")
                    conto_ricorrente = st.selectbox("Conto di Pagamento", 
                        ["Nessuno"] + conti_options if conti_options != ["Nessun conto configurato"] else ["Nessuno"],
                        help="Seleziona il conto da cui viene addebitata la spesa ricorrente",
                        key="conto_ric")
                
                with col2:
                    importo_ricorrente = st.number_input("Importo (€)", min_value=0.01, step=0.01, key="importo_ricorrente")
                    frequenza = st.selectbox("Frequenza", ["Settimanale", "Mensile", "Annuale"])
                
                submitted_ricorrente = st.form_submit_button("💾 Aggiungi Spesa Ricorrente", use_container_width=True)
                
                return submitted_ricorrente, {
                    'nome': nome_ricorrente,
                    'categoria': categoria_ricorrente,
                    'importo': importo_ricorrente,
                    'frequenza': frequenza,
                    'conto': conto_ricorrente
                }
    
    @staticmethod
    def show_change_password_form():
        """Form per cambiare password"""
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
                help=f"Minimo {SecurityConfig.MIN_PASSWORD_LENGTH} caratteri con lettere maiuscole, minuscole, numeri e caratteri speciali."
            )
            
            confirm_new_password = st.text_input(
                "Conferma Nuova Password", 
                type="password",
                help="Ripeti la nuova password per confermare"
            )
            
            change_submitted = st.form_submit_button("🔄 Cambia Password", use_container_width=True)
            
            return change_submitted, current_password, new_password, confirm_new_password

class UIHelpers:
    """Funzioni di aiuto per l'interfaccia utente"""
    
    @staticmethod
    def show_header_with_user_info(display_username, remaining_mins):
        """Mostra l'header con le informazioni utente"""
        col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 1, 1, 1, 1])
        
        with col1:
            st.title("💸 Gestione Spese Mensili")
        with col2:
            st.write(f"👤 **{display_username}**")
        with col3:
            st.write(f"⏱️ {remaining_mins}min")
        
        # Ritorna i pulsanti cliccati
        button_clicked = None
        with col4:
            if st.button("🏦 Conti"):
                button_clicked = "conti"
        with col5:
            if st.button("🔒 Password"):
                button_clicked = "password"
        with col6:
            if st.button("🛡️ Privacy"):
                button_clicked = "privacy"
        with col7:
            if st.button("🚪 Logout"):
                button_clicked = "logout"
        
        return button_clicked
    
    @staticmethod
    def show_navigation_buttons():
        """Mostra i pulsanti di navigazione principali"""
        col1, col2, col3 = st.columns([1, 1, 2])
        
        button_clicked = None
        with col1:
            if st.button("➕ Aggiungi Spesa", use_container_width=True):
                button_clicked = "aggiungi_spesa"
        with col2:
            if st.button("🗂️ Gestisci Spese", use_container_width=True):
                button_clicked = "gestisci_spese"
        
        return button_clicked
    
    @staticmethod
    def show_month_year_selector():
        """Mostra i selettori per mese e anno"""
        import calendar
        col1, col2 = st.columns(2)
        with col1:
            mese_selezionato = st.selectbox("Mese", range(1, 13), 
                format_func=lambda x: calendar.month_name[x],
                index=datetime.now().month - 1)
        with col2:
            anno_selezionato = st.selectbox("Anno", 
                range(2020, datetime.now().year + 2),
                index=datetime.now().year - 2020)
        
        return mese_selezionato, anno_selezionato
    
    @staticmethod
    def show_metrics(totale_giornaliere, totale_ricorrenti, totale_mese):
        """Mostra le metriche principali"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Spese Giornaliere", f"€{totale_giornaliere:.2f}")
        with col2:
            st.metric("Spese Ricorrenti", f"€{totale_ricorrenti:.2f}")
        with col3:
            st.metric("Totale Mese", f"€{totale_mese:.2f}")
    
    @staticmethod
    def show_sidebar_info(username, conti):
        """Mostra le informazioni nella sidebar"""
        st.sidebar.title("💾 Backup & Restore")
        st.sidebar.write(f"👤 **Utente:** {username}")
        
        # Info conti
        st.sidebar.markdown("---")
        st.sidebar.markdown("🏦 **I Tuoi Conti:**")
        if conti:
            for conto in conti[:3]:  # Mostra max 3 conti
                st.sidebar.markdown(f"• {conto['nome']}")
            if len(conti) > 3:
                st.sidebar.markdown(f"• ... e altri {len(conti) - 3}")
            st.sidebar.markdown(f"**Totale: {len(conti)} conti**")
        else:
            st.sidebar.markdown("• Nessun conto configurato")
            if st.sidebar.button("🏦 Configura Ora"):
                return "configura_conti"
        
        # Privacy disclaimer
        st.sidebar.markdown("---")
        st.sidebar.info("🔒 **PRIVACY**")
        st.sidebar.markdown("""
        **Noi sviluppatori NON raccogliamo le tue informazioni finanziarie**

        ⚠️ **App su Streamlit Cloud**: i dati sono sui server Streamlit

        💡 **Massima privacy**: scarica il codice e usalo localmente
        """)

        if st.sidebar.button("ℹ️ Dettagli Privacy"):
            return "dettagli_privacy"
        
        return None

class StateManager:
    """Gestione dello stato dell'applicazione"""
    
    @staticmethod
    def reset_form_fields():
        """Reset dei campi del form"""
        fields_to_reset = [
            'form_data', 'form_categoria', 'form_descrizione', 'form_importo',
            'spesa_aggiunta', 'spesa_ricorrente_aggiunta', 'conto_aggiunto',
            'password_changed'
        ]
        
        for field in fields_to_reset:
            if field in st.session_state:
                del st.session_state[field]
    
    @staticmethod
    def clear_user_session():
        """Pulisce la sessione utente"""
        fields_to_clear = [
            'authenticated', 'username', 'display_username',
            'spese_giornaliere', 'spese_ricorrenti', 'conti'
        ]
        
        for field in fields_to_clear:
            if field in st.session_state:
                del st.session_state[field]
        
        # Reset ai valori di default
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.display_username = None
        st.session_state.spese_giornaliere = []
        st.session_state.spese_ricorrenti = []
        st.session_state.conti = []
        st.session_state.current_page = "dashboard"
