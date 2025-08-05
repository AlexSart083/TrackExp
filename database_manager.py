"""
Fixed Database Manager per integrazione con Supabase PostgreSQL
"""

import streamlit as st
import psycopg2
import psycopg2.extras
import json
from datetime import datetime
import bcrypt

class SupabaseDatabaseManager:
    """Manager per database Supabase PostgreSQL"""
    
    def __init__(self):
        self.db_url = st.secrets["database"]["url"]
    
    def get_connection(self):
        """Ottieni connessione al database"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            st.error(f"Errore connessione database: {e}")
            raise e
    
    def init_database(self):
        """Inizializza le tabelle se non esistono"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Tabella utenti
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username VARCHAR(255) PRIMARY KEY,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabella spese giornaliere
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spese_giornaliere (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    data DATE NOT NULL,
                    categoria VARCHAR(255) NOT NULL,
                    descrizione TEXT NOT NULL,
                    importo DECIMAL(10,2) NOT NULL,
                    conto VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
                )
            """)
            
            # Tabella spese ricorrenti
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spese_ricorrenti (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    nome VARCHAR(255) NOT NULL,
                    categoria VARCHAR(255) NOT NULL,
                    importo DECIMAL(10,2) NOT NULL,
                    frequenza VARCHAR(100) NOT NULL,
                    conto VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
                )
            """)
            
            # Tabella conti
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conti (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    nome VARCHAR(255) NOT NULL,
                    descrizione TEXT,
                    tipo VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE
                )
            """)
            
            # Indici per performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_spese_giornaliere_username ON spese_giornaliere (username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_spese_giornaliere_data ON spese_giornaliere (data)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_spese_ricorrenti_username ON spese_ricorrenti (username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conti_username ON conti (username)")
            
            conn.commit()
            st.success("✅ Database inizializzato correttamente!")
            
        except Exception as e:
            conn.rollback()
            st.error(f"Errore inizializzazione database: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def save_user(self, username, password_hash, display_name=None):
        """Salva un nuovo utente"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (%s, %s, %s)",
                (username, password_hash, display_name)
            )
            conn.commit()
            return True
        except psycopg2.IntegrityError:
            conn.rollback()
            return False  # Username già esistente
        except Exception as e:
            conn.rollback()
            st.error(f"Errore salvataggio utente: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    # Alias per compatibilità con il codice esistente
    def create_user(self, username, password_hash, display_name=None):
        """Alias per save_user per compatibilità"""
        return self.save_user(username, password_hash, display_name)
    
    def user_exists(self, username):
        """Controlla se un utente esiste"""
        user_data = self.get_user(username)
        return user_data is not None
    
    def get_user(self, username):
        """Recupera dati utente"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute(
                "SELECT username, password_hash, display_name FROM users WHERE username = %s",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            st.error(f"Errore recupero utente: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def update_user_password(self, username, new_password_hash):
        """Aggiorna password utente"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (new_password_hash, username)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            st.error(f"Errore aggiornamento password: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def save_expense_data(self, username, spese_giornaliere, spese_ricorrenti, conti):
        """Salva tutti i dati delle spese per un utente"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Cancella dati esistenti per questo utente
            cursor.execute("DELETE FROM spese_giornaliere WHERE username = %s", (username,))
            cursor.execute("DELETE FROM spese_ricorrenti WHERE username = %s", (username,))
            cursor.execute("DELETE FROM conti WHERE username = %s", (username,))
            
            # Inserisci spese giornaliere
            for spesa in spese_giornaliere:
                # Assicurati che il conto non sia 'Nessuno'
                conto_value = spesa.get('conto')
                if conto_value == 'Nessuno':
                    conto_value = None
                    
                cursor.execute(
                    "INSERT INTO spese_giornaliere (username, data, categoria, descrizione, importo, conto) VALUES (%s, %s, %s, %s, %s, %s)",
                    (username, spesa['data'], spesa['categoria'], spesa['descrizione'], spesa['importo'], conto_value)
                )
            
            # Inserisci spese ricorrenti
            for spesa in spese_ricorrenti:
                # Assicurati che il conto non sia 'Nessuno'
                conto_value = spesa.get('conto')
                if conto_value == 'Nessuno':
                    conto_value = None
                    
                cursor.execute(
                    "INSERT INTO spese_ricorrenti (username, nome, categoria, importo, frequenza, conto) VALUES (%s, %s, %s, %s, %s, %s)",
                    (username, spesa['nome'], spesa['categoria'], spesa['importo'], spesa['frequenza'], conto_value)
                )
            
            # Inserisci conti
            for conto in conti:
                cursor.execute(
                    "INSERT INTO conti (username, nome, descrizione, tipo) VALUES (%s, %s, %s, %s)",
                    (username, conto['nome'], conto.get('descrizione'), conto['tipo'])
                )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Errore salvataggio dati: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def load_expense_data(self, username):
        """Carica tutti i dati delle spese per un utente"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Carica spese giornaliere
            cursor.execute(
                "SELECT data, categoria, descrizione, importo, conto FROM spese_giornaliere WHERE username = %s ORDER BY data DESC",
                (username,)
            )
            spese_giornaliere = [
                {
                    'data': str(row['data']),  # Converte date in string
                    'categoria': row['categoria'], 
                    'descrizione': row['descrizione'],
                    'importo': float(row['importo']),  # Converte Decimal in float
                    'conto': row['conto']
                } for row in cursor.fetchall()
            ]
            
            # Carica spese ricorrenti
            cursor.execute(
                "SELECT nome, categoria, importo, frequenza, conto FROM spese_ricorrenti WHERE username = %s",
                (username,)
            )
            spese_ricorrenti = [
                {
                    'nome': row['nome'],
                    'categoria': row['categoria'],
                    'importo': float(row['importo']),
                    'frequenza': row['frequenza'],
                    'conto': row['conto']
                } for row in cursor.fetchall()
            ]
            
            # Carica conti
            cursor.execute(
                "SELECT nome, descrizione, tipo, created_at FROM conti WHERE username = %s ORDER BY created_at",
                (username,)
            )
            conti = [
                {
                    'nome': row['nome'],
                    'descrizione': row['descrizione'],
                    'tipo': row['tipo'],
                    'creato_il': row['created_at'].isoformat() if row['created_at'] else datetime.now().isoformat()
                } for row in cursor.fetchall()
            ]
            
            return spese_giornaliere, spese_ricorrenti, conti
            
        except Exception as e:
            st.error(f"Errore caricamento dati: {e}")
            return [], [], []
        finally:
            cursor.close()
            conn.close()

    def get_user_count(self):
        """Conta il numero totale di utenti registrati"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            st.error(f"Errore conteggio utenti: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

# Classe di utilità per gestione password sicura
class PasswordManager:
    """Gestione sicura delle password con bcrypt"""
    
    @staticmethod
    def hash_password(password):
        """Hash della password con bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password, hashed):
        """Verifica password con hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def is_strong_password(password):
        """Verifica forza password"""
        if len(password) < 8:
            return False, "La password deve essere lunga almeno 8 caratteri"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*(),.?\":{}|<>" for c in password)
        
        if not has_upper:
            return False, "La password deve contenere almeno una lettera maiuscola"
        if not has_lower:
            return False, "La password deve contenere almeno una lettera minuscola"
        if not has_digit:
            return False, "La password deve contenere almeno un numero"
        if not has_special:
            return False, "La password deve contenere almeno un carattere speciale"
        
        return True, "Password sicura"
