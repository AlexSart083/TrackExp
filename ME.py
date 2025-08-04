import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import calendar
import plotly.express as px
import plotly.graph_objects as go

# Configurazione della pagina
st.set_page_config(
    page_title="Gestione Spese Mensili",
    page_icon="💰",
    layout="wide"
)

# File per il salvataggio dei dati
DATA_FILE = "spese_data.json"

# Inizializzazione dello stato della sessione
if 'spese_giornaliere' not in st.session_state:
    st.session_state.spese_giornaliere = []
if 'spese_ricorrenti' not in st.session_state:
    st.session_state.spese_ricorrenti = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"

# Funzioni per il salvataggio e caricamento dei dati
def salva_dati():
    """Salva i dati in un file JSON"""
    data = {
        'spese_giornaliere': st.session_state.spese_giornaliere,
        'spese_ricorrenti': st.session_state.spese_ricorrenti
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
        except Exception as e:
            st.error(f"Errore nel caricamento dei dati: {e}")

def carica_backup(file_content):
    """Carica i dati da un file di backup"""
    try:
        data = json.loads(file_content)
        st.session_state.spese_giornaliere = data.get('spese_giornaliere', [])
        st.session_state.spese_ricorrenti = data.get('spese_ricorrenti', [])
        salva_dati()
        return True
    except Exception as e:
        st.error(f"Errore nel caricamento del backup: {e}")
        return False

def aggiungi_spesa_giornaliera(data, categoria, descrizione, importo):
    """Aggiunge una spesa giornaliera"""
    spesa = {
        'data': data.strftime('%Y-%m-%d'),
        'categoria': categoria,
        'descrizione': descrizione,
        'importo': float(importo)
    }
    st.session_state.spese_giornaliere.append(spesa)
    salva_dati()

def aggiungi_spesa_ricorrente(nome, categoria, importo, frequenza):
    """Aggiunge una spesa ricorrente"""
    spesa = {
        'nome': nome,
        'categoria': categoria,
        'importo': float(importo),
        'frequenza': frequenza
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

# Carica i dati all'avvio
carica_dati()

# Titolo principale
st.title("💰 Gestione Spese Mensili")

# DASHBOARD (ex Resoconto Mensile)
if st.session_state.current_page == "dashboard":
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
    
    # Grafici
    if spese_mese or st.session_state.spese_ricorrenti:
        col1, col2 = st.columns(2)
        
        with col1:
            # Grafico spese per categoria (spese giornaliere)
            if spese_mese:
                df_categorie = pd.DataFrame(spese_mese)
                spese_per_categoria = df_categorie.groupby('categoria')['importo'].sum().reset_index()
                
                fig = px.pie(spese_per_categoria, values='importo', names='categoria', 
                           title="Spese Giornaliere per Categoria")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nessuna spesa giornaliera per questo mese")
        
        with col2:
            # Grafico andamento giornaliero
            if spese_mese:
                df_giornaliero = pd.DataFrame(spese_mese)
                df_giornaliero['data'] = pd.to_datetime(df_giornaliero['data'])
                spese_per_giorno = df_giornaliero.groupby('data')['importo'].sum().reset_index()
                
                fig = px.line(spese_per_giorno, x='data', y='importo', 
                            title="Andamento Spese Giornaliere")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nessun dato per il grafico giornaliero")
    
    # Dettaglio spese del mese
    if spese_mese:
        st.subheader("Dettaglio Spese Giornaliere")
        df_mese = pd.DataFrame(spese_mese)
        df_mese['data'] = pd.to_datetime(df_mese['data']).dt.strftime('%d/%m/%Y')
        
        # Raggruppa per categoria
        spese_per_categoria = df_mese.groupby('categoria')['importo'].sum().reset_index()
        spese_per_categoria = spese_per_categoria.sort_values('importo', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Spese per categoria:**")
            for _, row in spese_per_categoria.iterrows():
                st.write(f"• {row['categoria']}: €{row['importo']:.2f}")
        
        with col2:
            fig = px.bar(spese_per_categoria, x='categoria', y='importo',
                        title="Spese per Categoria")
            st.plotly_chart(fig, use_container_width=True)
        
        # Tabella dettagliata
        st.subheader("Elenco Completo Spese Giornaliere")
        st.dataframe(df_mese, use_container_width=True)
    
    # Mostra spese ricorrenti se presenti
    if st.session_state.spese_ricorrenti:
        st.subheader("Spese Ricorrenti Attive")
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
                'Importo Mensile': f"€{importo_mensile:.2f}"
            })
        
        if ricorrenti_df:
            st.dataframe(pd.DataFrame(ricorrenti_df), use_container_width=True)

# AGGIUNGI SPESA
elif st.session_state.current_page == "aggiungi_spesa":
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.header("➕ Aggiungi Nuova Spesa")
    
    tab1, tab2 = st.tabs(["Spesa Giornaliera", "Spesa Ricorrente"])
    
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
            
            with col2:
                descrizione = st.text_input("Descrizione")
                importo = st.number_input("Importo (€)", min_value=0.01, step=0.01)
            
            submitted = st.form_submit_button("Aggiungi Spesa")
            
            if submitted:
                if descrizione and importo > 0:
                    aggiungi_spesa_giornaliera(data_spesa, categoria, descrizione, importo)
                    st.session_state.spesa_aggiunta = True
                    st.rerun()
                else:
                    st.error("Compila tutti i campi correttamente!")
    
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
            
            with col2:
                importo_ricorrente = st.number_input("Importo (€)", min_value=0.01, step=0.01, key="importo_ricorrente")
                frequenza = st.selectbox("Frequenza", ["Settimanale", "Mensile", "Annuale"])
            
            submitted_ricorrente = st.form_submit_button("Aggiungi Spesa Ricorrente")
            
            if submitted_ricorrente:
                if nome_ricorrente and importo_ricorrente > 0:
                    aggiungi_spesa_ricorrente(nome_ricorrente, categoria_ricorrente, importo_ricorrente, frequenza)
                    st.session_state.spesa_ricorrente_aggiunta = True
                    st.rerun()
                else:
                    st.error("Compila tutti i campi correttamente!")

# GESTISCI SPESE
elif st.session_state.current_page == "gestisci_spese":
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🏠 Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    st.header("🗂️ Gestisci Spese")
    
    tab1, tab2 = st.tabs(["Spese Giornaliere", "Spese Ricorrenti"])
    
    with tab1:
        st.subheader("Spese Giornaliere")
        
        if st.session_state.spese_giornaliere:
            df = pd.DataFrame(st.session_state.spese_giornaliere)
            df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
            
            # Filtri
            col1, col2 = st.columns(2)
            with col1:
                categorie_filtro = st.multiselect("Filtra per categoria", 
                    df['categoria'].unique(), default=df['categoria'].unique())
            with col2:
                mese_filtro = st.selectbox("Filtra per mese", 
                    ["Tutti"] + [calendar.month_name[i] for i in range(1, 13)])
            
            # Applica filtri
            df_filtrato = df[df['categoria'].isin(categorie_filtro)]
            if mese_filtro != "Tutti":
                mese_num = list(calendar.month_name).index(mese_filtro)
                df_filtrato = df_filtrato[pd.to_datetime(df_filtrato['data'], format='%d/%m/%Y').dt.month == mese_num]
            
            # Mostra tabella con opzione di eliminazione
            st.write("**Clicca sull'icona del cestino per eliminare una spesa**")
            for idx, spesa in df_filtrato.iterrows():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 2, 1])
                with col1:
                    st.write(spesa['data'])
                with col2:
                    st.write(spesa['categoria'])
                with col3:
                    st.write(spesa['descrizione'])
                with col4:
                    st.write(f"€{spesa['importo']:.2f}")
                with col5:
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
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                with col1:
                    st.write(spesa['nome'])
                with col2:
                    st.write(spesa['categoria'])
                with col3:
                    st.write(f"€{spesa['importo']:.2f}")
                with col4:
                    st.write(spesa['frequenza'])
                with col5:
                    if st.button("🗑️", key=f"del_r_{idx}"):
                        elimina_spesa_ricorrente(idx)
                        st.success("Spesa ricorrente eliminata!")
                        st.rerun()
        else:
            st.info("Nessuna spesa ricorrente registrata.")

# Sidebar con funzioni di backup
st.sidebar.title("💾 Backup & Restore")

# Download backup
if st.sidebar.button("📥 Scarica Backup"):
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            st.sidebar.download_button(
                label="Download JSON",
                data=f.read(),
                file_name=f"backup_spese_{datetime.now().strftime('%Y%m%d')}.json",
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
st.sidebar.markdown("💡 **Suggerimenti:**")
st.sidebar.markdown("• Fai backup regolari dei tuoi dati")
st.sidebar.markdown("• I dati vengono salvati automaticamente")
st.sidebar.markdown(f"• File corrente: {DATA_FILE}")
