import streamlit as st
import os
from pathlib import Path
from typing import Dict

def load_env_variables() -> Dict[str, str]:
    """Carica e valida le variabili d'ambiente necessarie"""
    required_vars = [
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY"
    ]
    
    env_vars = {}
    missing_vars = []
    
    # Verifica la presenza delle variabili richieste
    for var in required_vars:
        value = st.secrets.get(var)
        if value:
            env_vars[var] = value
        else:
            missing_vars.append(var)
    
    # Se mancano variabili richieste, mostra warning ma continua con quelle disponibili
    if missing_vars:
        st.warning(f"Optional environment variables missing: {', '.join(missing_vars)}")
    
    return env_vars

def get_project_root() -> Path:
    """Ottiene il percorso root del progetto"""
    return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def initialize_environment():
    """Inizializza l'ambiente dell'applicazione"""
    # Carica variabili d'ambiente
    env_vars = load_env_variables()
    
    # Imposta configurazioni base se non presenti in session_state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.env = env_vars
        st.session_state.project_root = str(get_project_root())
        
        # Impostazioni default
        if 'settings' not in st.session_state:
            st.session_state.settings = {
                'theme': 'light',
                'show_line_numbers': True,
                'auto_analyze': True
            }
    
    return env_vars