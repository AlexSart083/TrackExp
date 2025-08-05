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
