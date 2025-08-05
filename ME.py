"""
App principale per la Gestione Spese Mensili - Versione Refactored
Utilizza i moduli separati per una migliore organizzazione del codice
"""

import streamlit as st
import pandas as pd
import calendar
import time
from datetime import datetime, date
from database_manager import SupabaseDatabaseManager
import plotly.express as px

# Import dei moduli personalizzati
from auth_security import (
    SecurityConfig, UserAuthenticator, SessionManager, 
    FileManager, LoginAttemptTracker
)
from expense_manager import (
    AccountManager, ExpenseManager, ExpenseCalculator, 
    DataManager, ExpenseFormatter, ExpenseFilter
)
from ui_components import (
    LoginForm, PrivacyManager, FormComponents, UIHelpers, StateManager
)

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Spese Mensili",
    page_icon="💸",
    layout="wide"
)

class ExpenseApp:
    """Classe principale dell'applicazione"""
    
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Inizializza lo stato della sessione"""
        default_values = {
            'authenticated': False,
            'username': None,
            'display_username': None,
            'spese_giornaliere': [],
            'spese_ricorrenti': [],
            'conti': [],
            'current_page': "dashboard"
        }
        
        for key, value in default_values.items():
            if key not in st.session_state:
                st.session_state[key] = value
        def initialize_database(self):
            """Inizializza il database al primo avvio"""
            if 'database_initialized' not in st.session_state:
                try:
                    with st.spinner("🔄 Connessione al database..."):
                        db = SupabaseDatabaseManager()
                        db.init_database()
                        st.session_state.database_initialized = True
                        
                        # Mostra statistiche database nella sidebar
                        user_count = db.get_user_count()
                        if user_count > 0:
                            st.sidebar.success(f"🗄️ Database connesso! ({user_count} utenti registrati)")
                        else:
                            st.sidebar.info("🗄️ Database connesso! Nessun utente registrato")
                            
                except Exception as e:
                    st.error(f"❌ Errore connessione database: {e}")
                    st.error("**Verifica la configurazione nei Secrets:**")
                    st.code("""
        [database]
        url = "postgresql://postgres:CUeAjYUmdwpjZjd0@db.eyxvgdmagmvcgbxadhnb.supabase.co:5432/postgres"
        
        [encryption] 
        secret_key = "fSEDqIau4R27THxBKpAz5Ey1cC6Ygb0b"
        
        [auth]
        session_timeout_minutes = 30
                    """)
                    st.stop()                
    
    def check_authentication(self):
        """Controlla l'autenticazione e il timeout della sessione"""
        # Controllo timeout sessione
        if st.session_state.authenticated and SessionManager.check_session_timeout(st.session_state):
            StateManager.clear_user_session()
            st.error("🕐 Sessione scaduta per inattività. Effettua nuovamente il login.")
            st.rerun()
        
        # Se non autenticato, mostra il form di login
        if not st.session_state.authenticated:
            LoginForm.show_login_form()
            st.stop()
    
    def load_user_data(self):
        """Carica i dati specifici dell'utente"""
        try:
            spese_g, spese_r, conti = DataManager.carica_dati(st.session_state.username)
            st.session_state.spese_giornaliere = spese_g
            st.session_state.spese_ricorrenti = spese_r
            st.session_state.conti = conti
        except Exception as e:
            st.error(f"Errore nel caricamento dei dati: {e}")
    
    def save_user_data(self):
        """Salva i dati dell'utente"""
        try:
            DataManager.salva_dati(
                st.session_state.username,
                st.session_state.spese_giornaliere,
                st.session_state.spese_ricorrenti,
                st.session_state.conti
            )
        except Exception as e:
            st.error(f"Errore nel salvataggio dei dati: {e}")
    
    def show_header(self):
        """Mostra l'header dell'applicazione"""
        remaining_mins = SessionManager.get_remaining_session_time(st.session_state)
        display_name = st.session_state.display_username or st.session_state.username
        
        button_clicked = UIHelpers.show_header_with_user_info(display_name, remaining_mins)
        
        if button_clicked == "conti":
            st.session_state.current_page = "gestisci_conti"
            st.rerun()
        elif button_clicked == "password":
            st.session_state.current_page = "change_password"
            st.rerun()
        elif button_clicked == "privacy":
            st.session_state.current_page = "privacy_info"
            st.rerun()
        elif button_clicked == "logout":
            StateManager.clear_user_session()
            st.success("🔒 Logout effettuato con successo!")
            st.rerun()
    
    def show_manage_accounts_page(self):
        """Pagina gestione conti"""
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
            if st.session_state.get('conto_aggiunto', False):
                action = FormComponents.show_success_message_with_actions(
                    "Conto aggiunto con successo!",
                    "➕ Aggiungi altro conto", "altro_conto",
                    "📋 Visualizza conti", "visualizza_conti"
                )
                if action:
                    st.session_state.conto_aggiunto = False
                    st.rerun()
                st.stop()
            
            submitted, nome_conto, descrizione_conto, tipo_conto = FormComponents.show_account_form()
            
            if submitted:
                if nome_conto.strip():
                    # Controlla se esiste già un conto con lo stesso nome
                    nomi_esistenti = [conto['nome'].lower() for conto in st.session_state.conti]
                    if nome_conto.lower() in nomi_esistenti:
                        st.error("❌ Esiste già un conto con questo nome!")
                    else:
                        AccountManager.aggiungi_conto(
                            st.session_state.conti, 
                            nome_conto.strip(), 
                            descrizione_conto.strip(), 
                            tipo_conto
                        )
                        self.save_user_data()
                        st.session_state.conto_aggiunto = True
                        st.rerun()
                else:
                    st.error("❌ Il nome del conto è obbligatorio!")
        
        with tab2:
            self._show_accounts_list()
    
    def _show_accounts_list(self):
        """Mostra la lista dei conti"""
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
                        success, message = AccountManager.elimina_conto(
                            st.session_state.conti,
                            st.session_state.spese_giornaliere,
                            st.session_state.spese_ricorrenti,
                            idx
                        )
                        if success:
                            self.save_user_data()
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
    
    def show_privacy_page(self):
        """Pagina informazioni privacy"""
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🏠 Dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
        
        st.header("🛡️ Informazioni sulla Privacy")
        st.write(f"👤 **Utente:** {st.session_state.display_username}")
        st.markdown("---")
        
        PrivacyManager.show_detailed_privacy_page()
    
    def show_change_password_page(self):
        """Pagina cambio password"""
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🏠 Dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
        
        st.header("🔒 Cambia Password")
        st.write(f"👤 **Utente:** {st.session_state.display_username}")
        
        # Controllo per messaggio di successo
        if st.session_state.get('password_changed', False):
            st.success("✅ Password cambiata con successo!")
            st.info("🔒 Per sicurezza, effettua un nuovo login")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔑 Vai al Login", key="go_to_login"):
                    StateManager.clear_user_session()
                    st.session_state.password_changed = False
                    st.rerun()
            with col2:
                if st.button("🏠 Torna alla Dashboard", key="back_to_dashboard"):
                    st.session_state.current_page = "dashboard"
                    st.session_state.password_changed = False
                    st.rerun()
            st.stop()
        
        st.markdown("---")
        
        submitted, current_password, new_password, confirm_new_password = FormComponents.show_change_password_form()
        
        if submitted:
            if current_password and new_password and confirm_new_password:
                if new_password == confirm_new_password:
                    success, message = UserAuthenticator.change_password(
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
    
    def show_dashboard(self):
        """Dashboard principale"""
        # Pulsanti di navigazione
        button_clicked = UIHelpers.show_navigation_buttons()
        
        if button_clicked == "aggiungi_spesa":
            st.session_state.current_page = "aggiungi_spesa"
            st.rerun()
        elif button_clicked == "gestisci_spese":
            st.session_state.current_page = "gestisci_spese"
            st.rerun()
        
        st.markdown("---")
        
        # Dashboard - Resoconto Mensile
        st.header("📈 Dashboard - Resoconto Mensile")
        
        # Selezione mese e anno
        mese_selezionato, anno_selezionato = UIHelpers.show_month_year_selector()
        
        # Calcola spese per il mese selezionato
        spese_mese = ExpenseCalculator.filtra_spese_per_mese(
            st.session_state.spese_giornaliere, mese_selezionato, anno_selezionato
        )
        totale_giornaliere_mese = sum(spesa['importo'] for spesa in spese_mese)
        totale_ricorrenti_mese = ExpenseCalculator.calcola_spese_ricorrenti_mensili(
            st.session_state.spese_ricorrenti
        )
        totale_mese = totale_giornaliere_mese + totale_ricorrenti_mese
        
        # Mostra il resoconto
        st.subheader(f"Resoconto per {calendar.month_name[mese_selezionato]} {anno_selezionato}")
        UIHelpers.show_metrics(totale_giornaliere_mese, totale_ricorrenti_mese, totale_mese)
        
        # Spese per Conto
        self._show_expenses_by_account(mese_selezionato, anno_selezionato)
        
        # Elenco e dettaglio spese
        self._show_expense_details(spese_mese)
        
        # Spese ricorrenti
        self._show_recurring_expenses()
    
    def _show_expenses_by_account(self, mese, anno):
        """Mostra le spese per conto"""
        st.subheader("💳 Spese per Conto")
        
        if st.session_state.conti:
            spese_per_conto = ExpenseCalculator.calcola_spese_per_conto(
                st.session_state.spese_giornaliere,
                st.session_state.spese_ricorrenti,
                mese, anno
            )
            
            if spese_per_conto:
                # Mostra la tabella
                df_conti = ExpenseFormatter.format_tabella_spese_per_conto(spese_per_conto)
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
    
    def _show_expense_details(self, spese_mese):
        """Mostra i dettagli delle spese"""
        if spese_mese:
            st.subheader("📋 Elenco Completo Spese Giornaliere")
            df_mese = ExpenseFormatter.format_spese_giornaliere_for_display(spese_mese)
            st.dataframe(df_mese, use_container_width=True)
            
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
        else:
            st.info("📝 Nessuna spesa giornaliera per questo mese")
    
    def _show_recurring_expenses(self):
        """Mostra le spese ricorrenti"""
        if st.session_state.spese_ricorrenti:
            st.subheader("🔄 Spese Ricorrenti Attive")
            df_ricorrenti = ExpenseFormatter.format_spese_ricorrenti_for_display(
                st.session_state.spese_ricorrenti
            )
            st.dataframe(df_ricorrenti, use_container_width=True)
    
    def show_add_expense_page(self):
        """Pagina aggiungi spese"""
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
            self._show_daily_expense_form()
        
        with tab2:
            self._show_recurring_expense_form()
    
    def _show_daily_expense_form(self):
        """Form per spese giornaliere"""
        st.subheader("Spesa Giornaliera")
        
        # Controllo per messaggio di successo
        if st.session_state.get('spesa_aggiunta', False):
            action = FormComponents.show_success_message_with_actions(
                "Spesa aggiunta correttamente!",
                "➕ Aggiungi altra spesa", "altra_giornaliera",
                "🏠 Torna alla Dashboard", "dashboard_giornaliera"
            )
            if action == "action1":
                st.session_state.spesa_aggiunta = False
                StateManager.reset_form_fields()
                st.rerun()
            elif action == "action2":
                st.session_state.spesa_aggiunta = False
                st.session_state.current_page = "dashboard"
                StateManager.reset_form_fields()
                st.rerun()
            st.stop()
        
        conti_options = AccountManager.get_conti_options(st.session_state.conti)
        submitted, form_data = FormComponents.show_expense_form(conti_options, "giornaliera")
        
        if submitted:
            if form_data['descrizione'] and form_data['importo'] > 0:
                conto_finale = None if form_data['conto'] == "Nessuno" else form_data['conto']
                ExpenseManager.aggiungi_spesa_giornaliera(
                    st.session_state.spese_giornaliere,
                    form_data['data'],
                    form_data['categoria'],
                    form_data['descrizione'],
                    form_data['importo'],
                    conto_finale
                )
                self.save_user_data()
                st.session_state.spesa_aggiunta = True
                st.rerun()
            else:
                st.error("❌ Compila tutti i campi correttamente!")
    
    def _show_recurring_expense_form(self):
        """Form per spese ricorrenti"""
        st.subheader("Spesa Ricorrente")
        
        # Controllo per messaggio di successo
        if st.session_state.get('spesa_ricorrente_aggiunta', False):
            action = FormComponents.show_success_message_with_actions(
                "Spesa ricorrente aggiunta correttamente!",
                "➕ Aggiungi altra spesa ricorrente", "altra_ricorrente",
                "🏠 Torna alla Dashboard", "dashboard_ricorrente"
            )
            if action == "action1":
                st.session_state.spesa_ricorrente_aggiunta = False
                StateManager.reset_form_fields()
                st.rerun()
            elif action == "action2":
                st.session_state.spesa_ricorrente_aggiunta = False
                st.session_state.current_page = "dashboard"
                StateManager.reset_form_fields()
                st.rerun()
            st.stop()
        
        conti_options = AccountManager.get_conti_options(st.session_state.conti)
        submitted, form_data = FormComponents.show_expense_form(conti_options, "ricorrente")
        
        if submitted:
            if form_data['nome'] and form_data['importo'] > 0:
                conto_finale = None if form_data['conto'] == "Nessuno" else form_data['conto']
                ExpenseManager.aggiungi_spesa_ricorrente(
                    st.session_state.spese_ricorrenti,
                    form_data['nome'],
                    form_data['categoria'],
                    form_data['importo'],
                    form_data['frequenza'],
                    conto_finale
                )
                self.save_user_data()
                st.session_state.spesa_ricorrente_aggiunta = True
                st.rerun()
            else:
                st.error("❌ Compila tutti i campi correttamente!")
    
    def show_manage_expenses_page(self):
        """Pagina gestisci spese"""
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🏠 Dashboard"):
                st.session_state.current_page = "dashboard"
                st.rerun()
        
        st.header("🗂️ Gestisci Spese")
        
        tab1, tab2 = st.tabs(["💰 Spese Giornaliere", "🔄 Spese Ricorrenti"])
        
        with tab1:
            self._show_manage_daily_expenses()
        
        with tab2:
            self._show_manage_recurring_expenses()
    
    def _show_manage_daily_expenses(self):
        """Gestione spese giornaliere"""
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
                conti_unici = df['conto'].fillna('Non specificato').unique()
                conto_filtro = st.multiselect("Filtra per conto",
                    conti_unici, default=conti_unici)
            
            # Applica filtri
            df_filtrato = ExpenseFilter.applica_filtri_spese_giornaliere(
                df, categorie_filtro, mese_filtro, conto_filtro
            )
            
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
                        ExpenseManager.elimina_spesa_giornaliera(
                            st.session_state.spese_giornaliere, idx
                        )
                        self.save_user_data()
                        st.success("Spesa eliminata!")
                        st.rerun()
            
            st.write(f"**Totale visualizzato: €{df_filtrato['importo'].sum():.2f}**")
        else:
            st.info("Nessuna spesa giornaliera registrata.")
    
    def _show_manage_recurring_expenses(self):
        """Gestione spese ricorrenti"""
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
                        ExpenseManager.elimina_spesa_ricorrente(
                            st.session_state.spese_ricorrenti, idx
                        )
                        self.save_user_data()
                        st.success("Spesa ricorrente eliminata!")
                        st.rerun()
        else:
            st.info("Nessuna spesa ricorrente registrata.")
    
    def show_sidebar(self):
        """Mostra la sidebar"""
        st.sidebar.title("💾 Backup & Restore")
        st.sidebar.write(f"👤 **Utente:** {st.session_state.username}")
        
        # Download backup
        if st.sidebar.button("📥 Scarica Backup"):
            try:
                backup_data = DataManager.esporta_dati_per_backup(st.session_state.username)
                if backup_data:
                    st.sidebar.download_button(
                        label="Download JSON",
                        data=backup_data,
                        file_name=f"backup_spese_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
                else:
                    st.sidebar.error("Nessun file di dati trovato!")
            except Exception as e:
                st.sidebar.error(f"Errore nell'esportazione: {e}")
        
        # Upload backup
        st.sidebar.markdown("**📤 Carica Backup**")
        uploaded_file = st.sidebar.file_uploader("Seleziona file backup", type=['json'])
        
        if uploaded_file is not None:
            file_content = uploaded_file.read().decode('utf-8')
            if st.sidebar.button("Ripristina Backup"):
                try:
                    spese_g, spese_r, conti = DataManager.carica_backup(file_content)
                    st.session_state.spese_giornaliere = spese_g
                    st.session_state.spese_ricorrenti = spese_r
                    st.session_state.conti = conti
                    self.save_user_data()
                    st.sidebar.success("✅ Backup ripristinato con successo!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ Errore nel ripristino del backup: {e}")
        
        # Info sulla sidebar
        sidebar_action = UIHelpers.show_sidebar_info(st.session_state.username, st.session_state.conti)
        if sidebar_action == "configura_conti":
            st.session_state.current_page = "gestisci_conti"
            st.rerun()
        elif sidebar_action == "dettagli_privacy":
            st.session_state.current_page = "privacy_info"
            st.rerun()
    
    def run(self):
        """Avvia l'applicazione"""
        # Controlla autenticazione
        self.initialize_database()
        
        self.check_authentication()
        
        # Carica dati utente
        self.load_user_data()
        
        # Mostra header
        self.show_header()
        
        # Router delle pagine
        if st.session_state.current_page == "gestisci_conti":
            self.show_manage_accounts_page()
        elif st.session_state.current_page == "privacy_info":
            self.show_privacy_page()
        elif st.session_state.current_page == "change_password":
            self.show_change_password_page()
        elif st.session_state.current_page == "aggiungi_spesa":
            self.show_add_expense_page()
        elif st.session_state.current_page == "gestisci_spese":
            self.show_manage_expenses_page()
        else:  # dashboard
            self.show_dashboard()
        
        # Mostra sidebar
        self.show_sidebar()
        
        # Footer
        st.markdown("<p style='text-align: center; color: gray;'>Created by AS with the supervision of KIM😼</p>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-size: 0.8em;'>🔒 <strong>Privacy:</strong> Noi sviluppatori non raccogliamo le tue informazioni finanziarie. App ospitata su Streamlit Cloud - per massima privacy usa il codice localmente.</p>", unsafe_allow_html=True)

# Avvio dell'applicazione
if __name__ == "__main__":
    app = ExpenseApp()
    app.run()
