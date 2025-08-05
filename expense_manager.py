"""
Modulo per la gestione delle spese e dei conti
Contiene tutte le funzioni relative a:
- Gestione spese giornaliere
- Gestione spese ricorrenti
- Gestione conti
- Calcoli e filtri
- Backup e restore
"""

import json
import os
import pandas as pd
from datetime import datetime
from auth_security import FileManager

class AccountManager:
    """Gestione dei conti di pagamento"""
    
    @staticmethod
    def aggiungi_conto(conti_list, nome, descrizione, tipo_conto="Personale"):
        """Aggiunge un nuovo conto"""
        conto = {
            'id': len(conti_list) + 1,
            'nome': nome,
            'descrizione': descrizione,
            'tipo': tipo_conto,
            'creato_il': datetime.now().isoformat()
        }
        conti_list.append(conto)
        return True
    
    @staticmethod
    def elimina_conto(conti_list, spese_giornaliere, spese_ricorrenti, indice):
        """Elimina un conto"""
        if 0 <= indice < len(conti_list):
            conto_eliminato = conti_list[indice]
            
            # Verifica se il conto è utilizzato in qualche spesa
            conto_nome = conto_eliminato['nome']
            spese_con_conto = [s for s in spese_giornaliere if s.get('conto') == conto_nome]
            spese_ricorrenti_con_conto = [s for s in spese_ricorrenti if s.get('conto') == conto_nome]
            
            if spese_con_conto or spese_ricorrenti_con_conto:
                return False, f"Impossibile eliminare il conto '{conto_nome}'. È utilizzato in {len(spese_con_conto)} spese giornaliere e {len(spese_ricorrenti_con_conto)} spese ricorrenti."
            
            conti_list.pop(indice)
            return True, "Conto eliminato con successo"
        return False, "Errore nell'eliminazione del conto"
    
    @staticmethod
    def get_conti_options(conti_list):
        """Restituisce le opzioni dei conti per i selectbox"""
        if not conti_list:
            return ["Nessun conto configurato"]
        return [conto['nome'] for conto in conti_list]

class ExpenseManager:
    """Gestione delle spese"""
    
    @staticmethod
    def aggiungi_spesa_giornaliera(spese_list, data, categoria, descrizione, importo, conto=None):
        """Aggiunge una spesa giornaliera"""
        spesa = {
            'data': data.strftime('%Y-%m-%d'),
            'categoria': categoria,
            'descrizione': descrizione,
            'importo': float(importo),
            'conto': conto
        }
        spese_list.append(spesa)
    
    @staticmethod
    def aggiungi_spesa_ricorrente(spese_list, nome, categoria, importo, frequenza, conto=None):
        """Aggiunge una spesa ricorrente"""
        spesa = {
            'nome': nome,
            'categoria': categoria,
            'importo': float(importo),
            'frequenza': frequenza,
            'conto': conto
        }
        spese_list.append(spesa)
    
    @staticmethod
    def elimina_spesa_giornaliera(spese_list, indice):
        """Elimina una spesa giornaliera"""
        if 0 <= indice < len(spese_list):
            spese_list.pop(indice)
            return True
        return False
    
    @staticmethod
    def elimina_spesa_ricorrente(spese_list, indice):
        """Elimina una spesa ricorrente"""
        if 0 <= indice < len(spese_list):
            spese_list.pop(indice)
            return True
        return False

class ExpenseCalculator:
    """Calcoli e analisi delle spese"""
    
    @staticmethod
    def calcola_spese_ricorrenti_mensili(spese_ricorrenti):
        """Calcola il totale delle spese ricorrenti per un mese specifico"""
        totale = 0
        for spesa in spese_ricorrenti:
            if spesa['frequenza'] == 'Mensile':
                totale += spesa['importo']
            elif spesa['frequenza'] == 'Settimanale':
                # Approssimazione: 4.33 settimane per mese
                totale += spesa['importo'] * 4.33
            elif spesa['frequenza'] == 'Annuale':
                totale += spesa['importo'] / 12
        return totale
    
    @staticmethod
    def filtra_spese_per_mese(spese_giornaliere, mese, anno):
        """Filtra le spese giornaliere per mese e anno"""
        spese_filtrate = []
        for spesa in spese_giornaliere:
            data_spesa = datetime.strptime(spesa['data'], '%Y-%m-%d')
            if data_spesa.month == mese and data_spesa.year == anno:
                spese_filtrate.append(spesa)
        return spese_filtrate
    
    @staticmethod
    def calcola_spese_per_conto(spese_giornaliere, spese_ricorrenti, mese, anno):
        """Calcola le spese per conto per un mese specifico"""
        spese_mese = ExpenseCalculator.filtra_spese_per_mese(spese_giornaliere, mese, anno)
        
        # Raggruppa spese giornaliere per conto
        spese_per_conto = {}
        for spesa in spese_mese:
            conto = spesa.get('conto', 'Non specificato')
            if conto not in spese_per_conto:
                spese_per_conto[conto] = {'giornaliere': 0, 'ricorrenti': 0}
            spese_per_conto[conto]['giornaliere'] += spesa['importo']
        
        # Aggiungi spese ricorrenti per conto
        for spesa in spese_ricorrenti:
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

class DataManager:
    """Gestione del salvataggio e caricamento dei dati"""
    
    @staticmethod
    def salva_dati(username, spese_giornaliere, spese_ricorrenti, conti):
        """Salva i dati in un file JSON specifico per utente"""
        data_file = FileManager.get_user_data_file(username)
        data = {
            'spese_giornaliere': spese_giornaliere,
            'spese_ricorrenti': spese_ricorrenti,
            'conti': conti
        }
        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            raise Exception(f"Errore nel salvataggio dei dati: {e}")
    
    @staticmethod
    def carica_dati(username):
        """Carica i dati dal file JSON se esiste"""
        data_file = FileManager.get_user_data_file(username)
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return (
                        data.get('spese_giornaliere', []),
                        data.get('spese_ricorrenti', []),
                        data.get('conti', [])
                    )
            except Exception as e:
                raise Exception(f"Errore nel caricamento dei dati: {e}")
        return [], [], []
    
    @staticmethod
    def carica_backup(file_content):
        """Carica i dati da un file di backup"""
        try:
            data = json.loads(file_content)
            return (
                data.get('spese_giornaliere', []),
                data.get('spese_ricorrenti', []),
                data.get('conti', [])
            )
        except Exception as e:
            raise Exception(f"Errore nel caricamento del backup: {e}")
    
    @staticmethod
    def esporta_dati_per_backup(username):
        """Esporta i dati per il backup"""
        data_file = FileManager.get_user_data_file(username)
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                raise Exception(f"Errore nell'esportazione del backup: {e}")
        return None

class ExpenseFormatter:
    """Formattazione e visualizzazione delle spese"""
    
    @staticmethod
    def format_spese_giornaliere_for_display(spese_giornaliere):
        """Formatta le spese giornaliere per la visualizzazione"""
        if not spese_giornaliere:
            return pd.DataFrame()
        
        df = pd.DataFrame(spese_giornaliere)
        df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
        
        # Riordina le colonne
        cols_order = ['data', 'categoria', 'descrizione', 'importo', 'conto']
        df = df.reindex(columns=cols_order)
        df.columns = ['Data', 'Categoria', 'Descrizione', 'Importo', 'Conto']
        
        # Gestisci valori None per il conto
        df['Conto'] = df['Conto'].fillna('Non specificato')
        
        return df
    
    @staticmethod
    def format_spese_ricorrenti_for_display(spese_ricorrenti):
        """Formatta le spese ricorrenti per la visualizzazione"""
        if not spese_ricorrenti:
            return pd.DataFrame()
        
        ricorrenti_df = []
        for spesa in spese_ricorrenti:
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
        
        return pd.DataFrame(ricorrenti_df)
    
    @staticmethod
    def format_tabella_spese_per_conto(spese_per_conto):
        """Formatta la tabella delle spese per conto"""
        if not spese_per_conto:
            return pd.DataFrame()
        
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
        tabella_conti.sort(
            key=lambda x: float(x['Totale'].replace('€', '').replace(',', '.')), 
            reverse=True
        )
        
        return pd.DataFrame(tabella_conti)

class ExpenseFilter:
    """Filtri per le spese"""
    
    @staticmethod
    def applica_filtri_spese_giornaliere(df, categorie_filtro, mese_filtro, conti_filtro):
        """Applica filtri alle spese giornaliere"""
        if df.empty:
            return df
        
        # Filtro per categoria
        df_filtrato = df[df['categoria'].isin(categorie_filtro)]
        
        # Filtro per mese
        if mese_filtro != "Tutti":
            import calendar
            mese_num = list(calendar.month_name).index(mese_filtro)
            df_filtrato = df_filtrato[
                pd.to_datetime(df_filtrato['data'], format='%d/%m/%Y').dt.month == mese_num
            ]
        
        # Filtro per conto
        df_filtrato = df_filtrato[
            df_filtrato['conto'].fillna('Non specificato').isin(conti_filtro)
        ]
        
        return df_filtrato
