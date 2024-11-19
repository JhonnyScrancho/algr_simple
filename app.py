import os
import sys
from pathlib import Path

# Aggiungi la directory root del progetto al PYTHONPATH
project_root = Path(__file__).parent
sys.path.append(str(project_root))

import streamlit as st
from components.chat_interface import ChatInterface
from components.code_viewer import CodeViewer
from components.file_handler import FileHandler
from components.settings_ui import SettingsUI 
from services.firebase_persistence import FirebaseChatPersistence
from services.llm_handler import LLMHandler
from config.models import MODELS_CONFIG
from config.settings import APP_CONFIG


def initialize_session_state():
    """Inizializza lo stato della sessione"""
    if 'model' not in st.session_state:
        st.session_state.model = list(MODELS_CONFIG.keys())[0]
    
    if 'llm_handler' not in st.session_state:
        try:
            st.session_state.llm_handler = LLMHandler(st.session_state.model)
        except Exception as e:
            st.error(f"Errore nell'inizializzazione dell'LLM handler: {str(e)}")
            st.session_state.llm_handler = None
            return False
    
    if 'chat_persistence' not in st.session_state:
        try:
            st.session_state.chat_persistence = FirebaseChatPersistence()
        except Exception as e:
            st.error(f"Errore nell'inizializzazione di Firebase: {str(e)}")
            return False
    
    # Inizializza le chat se non esistono
    if 'chats' not in st.session_state:
        try:
            chats = st.session_state.chat_persistence.get_all_chats()
            st.session_state.chats = chats
            
            # Se non ci sono chat, creane una nuova
            if not chats.get('chats'):
                new_chat_id = st.session_state.chat_persistence.create_chat()
                if new_chat_id:
                    st.session_state.current_chat_id = new_chat_id
                    # Ricarica le chat dopo la creazione
                    st.session_state.chats = st.session_state.chat_persistence.get_all_chats()
                else:
                    st.error("Errore nella creazione della chat iniziale")
                    return False
            else:
                # Usa la prima chat esistente come corrente
                st.session_state.current_chat_id = next(iter(chats['chats']))
        except Exception as e:
            st.error(f"Errore nell'inizializzazione delle chat: {str(e)}")
            return False
    
    if 'current_files' not in st.session_state:
        st.session_state.current_files = None
    
    if 'is_processing' not in st.session_state:
        st.session_state.is_processing = False
    
    if 'should_stop' not in st.session_state:
        st.session_state.should_stop = False
        
    if 'temp_image' not in st.session_state:
        st.session_state.temp_image = None
        
    # Inizializza stato di processing
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = {
            'is_processing': False,
            'last_update': None,
            'file_count': 0
        }
        
    return True

def main():
    st.set_page_config(
        page_title="Allegro",
        page_icon="👲🏿",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Carica CSS
    try:
        with open('static/css/main.css', 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Errore nel caricamento del CSS: {str(e)}")
        st.markdown("""
            <style>
            .stApp {
                max-width: 1200px;
                margin: 0 auto;
            }
            </style>
        """, unsafe_allow_html=True)
    
    if not initialize_session_state():
        st.error("Errore nell'inizializzazione dell'applicazione")
        st.stop()
        return
    
    # Inizializza le impostazioni UI
    settings_ui = SettingsUI()
    settings_ui.initialize_session_state()
    
    chat_interface = ChatInterface(persistence=st.session_state.chat_persistence)
    
    # Sidebar più compatta e organizzata
    with st.sidebar:
        # Settings section
        st.subheader("⚙️ Settings")
        settings_ui.display_sidebar_settings()
        
        # Image upload section
        st.subheader("📷 Immagine")
        uploaded_file = st.file_uploader(
            "Carica immagine",
            type=['png', 'jpg', 'jpeg'],
            key="chat_image_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            st.image(uploaded_file, width=200)
            st.session_state.temp_image = uploaded_file
            if st.button("🗑️ Rimuovi", key="remove_image", use_container_width=True):
                st.session_state.temp_image = None
                st.rerun()
        
        # Files section
        st.subheader("📁 Files")
        uploaded_files = st.file_uploader(
            "Carica files",
            type=APP_CONFIG["supported_file_types"],
            accept_multiple_files=True,
            help="Limit 200MB per file • PY, JS, HTML, CSS, JSON, TXT, MD, YAML, YML, XML, CSV, INI, CONF, SH, BASH, SQL, ZIP, HTM",
            label_visibility="collapsed",
            key="file_uploader"
        )
        
        if uploaded_files:
            try:
                # with st.spinner("Processing files..."):
                #     st.write("🚀 Inizio processing files...")
                    
                #     # Stato pre-processing
                #     st.write("📊 Stato iniziale:")
                #     st.write({
                #         'has_files': hasattr(st.session_state, 'current_files'),
                #         'files_count': len(st.session_state.current_files) if hasattr(st.session_state, 'current_files') and st.session_state.current_files else 0
                #     })
                    
                    file_handler = FileHandler()
                    result = file_handler.handle_uploaded_files(uploaded_files)
                    
                    if result.get('success'):
                        st.success(f"📁 Caricati {result['file_count']} file")
                        
                        # Verifica post-processing
                        # st.write("📊 Stato finale:")
                        # st.write({
                        #     'has_files': hasattr(st.session_state, 'current_files'),
                        #     'files_count': len(st.session_state.current_files) if hasattr(st.session_state, 'current_files') and st.session_state.current_files else 0,
                        #     'processed_count': result['file_count']
                        # })
                        
                        if 'files' in result:
                            st.session_state.current_files = result['files']
                            st.session_state.file_structure = result.get('structure', {})
                            
                            # Verifica finale post-assegnazione
                            # st.write("✅ Verifica finale:")
                            # st.write(f"Files in session state: {len(st.session_state.current_files) if st.session_state.current_files else 'None'}")
                            
                            # Struttura progetto in expander
                            with st.expander("📂 Struttura Progetto", expanded=True):
                                if 'structure' in result:
                                    for path, files in result['structure'].items():
                                        if path:
                                            st.markdown(f"**📁 {path}/**")
                                        if isinstance(files, list):
                                            for file in files:
                                                try:
                                                    if isinstance(file, dict):
                                                        filename = file.get('name', 'Unknown file')
                                                    elif isinstance(file, str):
                                                        filename = file
                                                    else:
                                                        continue
                                                    st.markdown(f"└─ 📄 {filename}")
                                                except Exception as e:
                                                    st.warning(f"Errore nella visualizzazione del file: {str(e)}")
                            
                            # Anteprime file e azioni contestuali in expander
                            with st.expander("👁️ Anteprima Files"):
                                code_viewer = CodeViewer()
                                valid_files = [f for f in result['files'] if isinstance(f, dict) and 'name' in f]
                                
                                if valid_files:
                                    # Tabs per file
                                    file_tabs = st.tabs([f"📄 {f['name']}" for f in valid_files])
                                    for tab, file in zip(file_tabs, valid_files):
                                        with tab:
                                            try:
                                                file_ext = Path(file['name']).suffix.lower()
                                                language = APP_CONFIG["language_mapping"].get(file_ext, "text")
                                                
                                                # Azioni contestuali per tipo file
                                                if language in ['python', 'javascript', 'typescript']:
                                                    st.write("🔍 Azioni disponibili:")
                                                    cols = st.columns(4)
                                                    with cols[0]:
                                                        if st.button("📝 Review", key=f"review_{file['name']}", use_container_width=True):
                                                            chat_interface.handle_user_input(
                                                                f"Analizza il file {file['name']}",
                                                                {"type": "code_analysis", "current_file": file}
                                                            )
                                                    with cols[1]:
                                                        if st.button("🐛 Bug Check", key=f"bug_{file['name']}", use_container_width=True):
                                                            chat_interface.handle_user_input(
                                                                f"Trova bug in {file['name']}",
                                                                {"type": "bug_finding", "current_file": file}
                                                            )
                                                elif file_ext in ['.json', '.csv']:
                                                    st.write("📊 Analisi Dati:")
                                                    cols = st.columns(3)
                                                    with cols[0]:
                                                        if st.button("📈 Analizza", key=f"analyze_{file['name']}", use_container_width=True):
                                                            chat_interface.handle_user_input(
                                                                f"Analizza i dati in {file['name']}",
                                                                {"type": "data_analysis", "current_file": file}
                                                            )
                                                
                                                code_viewer.display_preview(
                                                    code=file['content'],
                                                    language=language,
                                                    file_name=file['name']
                                                )
                                            except Exception as e:
                                                st.error(f"Errore nella visualizzazione dell'anteprima: {str(e)}")
                    else:
                        st.error(result.get('error', 'Errore nel caricamento dei file'))
                        
            except Exception as e:
                st.error(f"Errore inaspettato durante il processing: {str(e)}")
        
        # Chat management
        st.subheader("💭 Chat")
        chat_interface.display_chat_sidebar()

        # Debug section
        #if st.checkbox("🔍 Show Debug Info"):
        #    st.write("### Debug Info")
        #    if hasattr(st.session_state, 'current_files'):
         #       st.write(f"📁 Files caricati: {len(st.session_state.current_files) if st.session_state.current_files else 'None'}")
         #   else:
        #        st.write("❌ No files in session state")
                
        #    st.write("### Processing Status")
         #   st.write(st.session_state.processing_status)

    # Area principale
    st.title("Allegro 👲🏿")
    
    if st.session_state.llm_handler is not None:
        st.caption(f"🤖 {MODELS_CONFIG[st.session_state.model]['name']}")
        if st.session_state.current_files:
            st.caption(f"📁 {len(st.session_state.current_files)} files caricati")
    
    # Chat interface
    if st.session_state.llm_handler is not None:
        # Area messaggi
        chat_interface.display_messages()
        
        # Input chat in basso
        if prompt := st.chat_input("Scrivi un messaggio..."):
            context = {
                'current_files': st.session_state.current_files,
                'model': st.session_state.model,
                'model_config': MODELS_CONFIG[st.session_state.model]
            } if st.session_state.current_files else {
                'model': st.session_state.model,
                'model_config': MODELS_CONFIG[st.session_state.model]
            }
            chat_interface.handle_user_input(prompt, context)
    else:
        st.warning("Sistema non inizializzato correttamente. Ricarica la pagina.")

if __name__ == "__main__":
    main()