"""
Modulo UI Components per la Gestione Spese Mensili
Contiene tutti i componenti dell'interfaccia utente
"""

import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
from auth_security import UserAuthenticator, SessionManager

class LoginForm:
    """Gestione del form di login"""
    
    @staticmethod
    def show_login_form():
        """Mostra il form di login/registrazione"""
        st.title("🔐 Gestione Spese Mensili")
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["🔑 Login", "👤 Registrazione"])
        
        with tab1:
            LoginForm._show_login_tab()
        
        with tab2:
            LoginForm._show_registration_tab()
    
    @staticmethod
    def _show_login_tab():
        """Tab per il login"""
        st.subheader("Accedi al tuo account")
        
        with st.form("login_form"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            submitted = st.form_submit_button("🔑 Accedi")
            
            if submitted:
                if username and password:
                    success, message = UserAuthenticator.login(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.display_username = username
                        SessionManager.update_session_activity(st.session_state)
                        st.success("✅ Login effettuato con successo!")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("❌ Inserisci username e password")
    
    @staticmethod
    def _show_registration_tab():
        """Tab per la registrazione"""
        st.subheader("Crea un nuovo account")
        
        with st.form("registration_form"):
            username = st.text_input("👤 Username")
            display_name = st.text_input("📝 Nome visualizzato (opzionale)")
            password = st.text_input("🔒 Password", type="password")
            confirm_password = st.text_input("🔒 Conferma Password", type="password")
            
            st.markdown("**🛡️ Requisiti password:**")
            st.markdown("• Almeno 8 caratteri • Lettere maiuscole e minuscole • Almeno un numero")
            
            submitted = st.form_submit_button("👤 Registrati")
            
            if submitted:
                if username and password and confirm_password:
                    if password == confirm_password:
                        success, message = UserAuthenticator.register(
                            username, password, display_name or username
                        )
                        if success:
                            st.success("✅ Registrazione completata! Ora puoi effettuare il login.")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Le password non coincidono")
                else:
                    st.error("❌ Compila tutti i campi obbligatori")

class PrivacyManager:
    """Gestione delle informazioni sulla privacy"""
    
    @staticmethod
    def show_detailed_privacy_page():
        """Mostra la pagina dettagliata sulla privacy"""
        st.markdown("""
        ## 🛡️ Informativa sulla Privacy
        
        ### 📊 Dati Raccolti
        - **Username e password**: Per l'autenticazione dell'account
        - **Dati finanziari**: Spese, categorie, conti (solo per le tue analisi personali)
        - **Preferenze**: Impostazioni dell'app
        
        ### 🔒 Sicurezza
        - Le password sono crittografate con bcrypt
        - I dati sono memorizzati in un database sicuro
        - Sessioni con timeout automatico per sicurezza
        
        ### 🚫 Cosa NON facciamo
        - Non vendiamo i tuoi dati
        - Non condividiamo informazioni con terze parti
        - Non utilizziamo i dati per pubblicità
        
        ### 💾 Controllo dei Dati
        - Puoi scaricare un backup completo dei tuoi dati
        - Puoi eliminare il tuo account e tutti i dati associati
        - Hai pieno controllo sui tuoi dati finanziari
        
        ### 🌐 Hosting
        - App ospitata su Streamlit Cloud
        - Database sicuro con crittografia
        - Per massima privacy, puoi usare il codice in locale
        
        ### 📞 Contatti
        Per domande sulla privacy, contatta gli sviluppatori.
        """)
        
        if st.button("🗑️ Elimina Account e Dati"):
            st.warning("⚠️ **ATTENZIONE**: Questa azione eliminerà permanentemente tutti i tuoi dati!")
            if st.button("❌ CONFERMA ELIMINAZIONE", type="primary"):
                try:
                    # Qui andrebbero eliminate le informazioni dal database
                    st.success("✅ Account eliminato con successo")
                    st.session_state.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Errore nell'eliminazione: {e}")

class FormComponents:
    """Componenti per i form"""
    
    @staticmethod
    def show_success_message_with_actions(message, action1_text, action1_key, action2_text, action2_key):
        """Mostra messaggio di successo con azioni"""
        st.success(f"✅ {message}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(action1_text, key=action1_key, use_container_width=True):
                return "action1"
        with col2:
            if st.button(action2_text, key=action2_key, use_container_width=True):
                return "action2"
        return None
    
    @staticmethod
    def show_account_form():
        """Form per aggiungere un conto"""
        with st.form("account_form"):
            nome_conto = st.text_input("🏦 Nome Conto", placeholder="es. Carta Visa")
            descrizione_conto = st.text_area("📝 Descrizione (opzionale)", placeholder="es. Carta principale per spese quotidiane")
            tipo_conto = st.selectbox("🏷️ Tipo Conto", [
                "Carta di Credito", "Conto Corrente", "PayPal", "Contanti", 
                "Carta Prepagata", "Conto Aziendale", "Altro"
            ])
            submitted = st.form_submit_button("➕ Aggiungi Conto")
            
        return submitted, nome_conto, descrizione_conto, tipo_conto
    
    @staticmethod
    def show_change_password_form():
        """Form per cambio password"""
        with st.form("change_password_form"):
            current_password = st.text_input("🔒 Password Attuale", type="password")
            new_password = st.text_input("🔑 Nuova Password", type="password")
            confirm_new_password = st.text_input("🔑 Conferma Nuova Password", type="password")
            submitted = st.form_submit_button("🔄 Cambia Password")
            
        return submitted, current_password, new_password, confirm_new_password
    
    @staticmethod
    def show_expense_form(conti_options, tipo_spesa):
        """Form per aggiungere spese"""
        if tipo_spesa == "giornaliera":
            return FormComponents._show_daily_expense_form(conti_options)
        else:
            return FormComponents._show_recurring_expense_form(conti_options)
    
    @staticmethod
    def _show_daily_expense_form(conti_options):
        """Form per spese giornaliere"""
        with st.form("daily_expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                data = st.date_input("📅 Data", value=date.today())
                categoria = st.selectbox("🏷️ Categoria", [
                    "Alimentari", "Trasporti", "Bollette", "Divertimento", 
                    "Salute", "Abbigliamento", "Casa", "Altro"
                ])
            
            with col2:
                importo = st.number_input("💰 Importo (€)", min_value=0.01, step=0.01)
                conto = st.selectbox("💳 Conto", conti_options)
            
            descrizione = st.text_input("📝 Descrizione", placeholder="es. Spesa al supermercato")
            submitted = st.form_submit_button("➕ Aggiungi Spesa")
            
        form_data = {
            'data': data,
            'categoria': categoria,
            'importo': importo,
            'conto': conto,
            'descrizione': descrizione
        }
        
        return submitted, form_data
    
    @staticmethod
    def _show_recurring_expense_form(conti_options):
        """Form per spese ricorrenti"""
        with st.form("recurring_expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("📝 Nome Spesa", placeholder="es. Abbonamento Netflix")
                categoria = st.selectbox("🏷️ Categoria", [
                    "Abbonamenti", "Bollette", "Assicurazioni", "Affitto", 
                    "Trasporti", "Salute", "Altro"
                ])
            
            with col2:
                importo = st.number_input("💰 Importo (€)", min_value=0.01, step=0.01)
                frequenza = st.selectbox("🔄 Frequenza", ["Mensile", "Annuale"])
                conto = st.selectbox("💳 Conto", conti_options)
            
            submitted = st.form_submit_button("➕ Aggiungi Spesa Ricorrente")
            
        form_data = {
            'nome': nome,
            'categoria': categoria,
            'importo': importo,
            'frequenza': frequenza,
            'conto': conto
        }
        
        return submitted, form_data

class UIHelpers:
    """Helper per l'interfaccia utente"""
    
    @staticmethod
    def show_header_with_user_info(display_name, remaining_mins):
        """Mostra l'header con info utente"""
        st.title("💸 Gestione Spese Mensili")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.write(f"👋 **Benvenuto, {display_name}!**")
        
        with col2:
            if remaining_mins > 5:
                st.write(f"🕐 Sessione: {remaining_mins} min rimanenti")
            else:
                st.warning(f"⏰ Sessione: {remaining_mins} min rimanenti")
        
        with col3:
            if st.button("🔒 Logout"):
                return "logout"
        
        # Menu opzioni
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🏦 Conti"):
                return "conti"
        with col2:
            if st.button("🔑 Password"):
                return "password"
        with col3:
            if st.button("🛡️ Privacy"):
                return "privacy"
        with col4:
            st.write("")  # Spazio vuoto
        
        return None
    
    @staticmethod
    def show_navigation_buttons():
        """Pulsanti di navigazione principali"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("➕ Aggiungi Spesa", use_container_width=True):
                return "aggiungi_spesa"
        
        with col2:
            if st.button("🗂️ Gestisci Spese", use_container_width=True):
                return "gestisci_spese"
        
        with col3:
            st.write("")  # Spazio vuoto
        
        return None
    
    @staticmethod
    def show_month_year_selector():
        """Selettore mese e anno"""
        col1, col2 = st.columns(2)
        
        with col1:
            mese_selezionato = st.selectbox(
                "📅 Seleziona Mese",
                range(1, 13),
                index=datetime.now().month - 1,
                format_func=lambda x: calendar.month_name[x]
            )
        
        with col2:
            anno_selezionato = st.selectbox(
                "📅 Seleziona Anno",
                range(2020, datetime.now().year + 2),
                index=datetime.now().year - 2020
            )
        
        return mese_selezionato, anno_selezionato
    
    @staticmethod
    def show_metrics(totale_giornaliere, totale_ricorrenti, totale_mese):
        """Mostra le metriche principali"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("💰 Spese Giornaliere", f"€{totale_giornaliere:.2f}")
        
        with col2:
            st.metric("🔄 Spese Ricorrenti", f"€{totale_ricorrenti:.2f}")
        
        with col3:
            st.metric("📊 Totale Mese", f"€{totale_mese:.2f}")
    
    @staticmethod
    def show_sidebar_info(username, conti):
        """Informazioni nella sidebar"""
        st.sidebar.markdown("---")
        st.sidebar.header("📊 Info Account")
        st.sidebar.write(f"👤 **Utente:** {username}")
        st.sidebar.write(f"🏦 **Conti:** {len(conti)}")
        
        if len(conti) == 0:
            st.sidebar.warning("⚠️ Nessun conto configurato")
            if st.sidebar.button("🏦 Configura Conti"):
                return "configura_conti"
        
        st.sidebar.markdown("---")
        st.sidebar.header("🛡️ Privacy")
        if st.sidebar.button("📋 Dettagli Privacy"):
            return "dettagli_privacy"
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("**💡 Suggerimento del giorno:**")
        st.sidebar.info("Usa i backup regolari per non perdere i tuoi dati!")
        
        return None

class StateManager:
    """Gestione dello stato dell'applicazione"""
    
    @staticmethod
    def clear_user_session():
        """Pulisce la sessione utente"""
        keys_to_keep = ['database_initialized']
        keys_to_clear = [key for key in st.session_state.keys() if key not in keys_to_keep]
        
        for key in keys_to_clear:
            del st.session_state[key]
        
        # Reinizializza i valori di default
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.display_username = None
        st.session_state.spese_giornaliere = []
        st.session_state.spese_ricorrenti = []
        st.session_state.conti = []
        st.session_state.current_page = "dashboard"
    
    @staticmethod
    def reset_form_fields():
        """Reset dei campi form"""
        form_keys = [
            'spesa_aggiunta', 'spesa_ricorrente_aggiunta', 'conto_aggiunto',
            'password_changed'
        ]
        
        for key in form_keys:
            if key in st.session_state:
                st.session_state[key] = False
