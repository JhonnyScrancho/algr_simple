import streamlit as st
from datetime import datetime
import pytz
from zoneinfo import ZoneInfo
import time
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Generator, Union
from dataclasses import dataclass
import difflib

from services.llm_handler import LLMHandler
from services.code_analyzer import CodeAnalyzer, AnalysisResult
from services.firebase_persistence import FirebaseChatPersistence
from components.image_handler import ImageHandler
from components.file_handler import FileHandler
from components.code_viewer import CodeViewer
from config.models import (
    ANALYSIS_RULES,
    MODELS_CONFIG,
    determine_content_type,
    get_active_rules,
    suggest_rules,
    merge_rule_sets,
    contains_code
)

@dataclass
class MessageContext:
    """Contesto di un messaggio"""
    content_type: str
    active_rules: Set[str]
    available_files: Optional[List[Dict]] = None
    current_file: Optional[Dict] = None
    analysis_result: Optional[AnalysisResult] = None
    version_changes: Optional[Dict] = None
    image_data: Optional[Dict] = None
    
@dataclass
class ChatState:
    """Stato della chat"""
    current_chat_id: str
    messages: List[Dict]
    files: List[Dict]
    file_structure: Dict
    file_versions: Dict
    images: List[Dict]
    conversation_history: List[Dict]
    is_processing: bool = False
    should_stop: bool = False
    current_response: str = ""
    temp_image: Optional[Any] = None

class ChatInterface:
    def __init__(self, persistence: Optional[FirebaseChatPersistence] = None):
        """Inizializza l'interfaccia chat"""
        self.llm_handler = LLMHandler()
        self.code_analyzer = CodeAnalyzer()
        self.image_handler = ImageHandler()
        self.chat_persistence = persistence or FirebaseChatPersistence()
        self.file_handler = FileHandler()
        self.code_viewer = CodeViewer()
        self.timezone = pytz.timezone('Europe/Rome')
        
        # Inizializza stato
        self._initialize_chat_state()
        
        # Cache per analisi
        self._analysis_cache: Dict[str, AnalysisResult] = {}
        self._context_cache: Dict[str, MessageContext] = {}
        
    def _initialize_chat_state(self):
        """Inizializza o recupera lo stato della chat"""
        try:
            if not hasattr(st.session_state, 'chat_state'):
                # Recupera o crea chat iniziale
                chats = self.chat_persistence.get_all_chats()
                if not chats.get('chats'):
                    chat_id = self.chat_persistence.create_chat()
                    if not chat_id:
                        raise Exception("Errore nella creazione della chat iniziale")
                    st.session_state.chats = self.chat_persistence.get_all_chats()
                else:
                    chat_id = next(iter(chats['chats']))
                
                # Recupera dati chat
                messages = self.chat_persistence.get_chat_messages(chat_id)
                files_data = self.chat_persistence.get_chat_files(chat_id)
                
                # Crea stato iniziale
                st.session_state.chat_state = ChatState(
                    current_chat_id=chat_id,
                    messages=messages or [],
                    files=files_data.get('content', []),
                    file_structure=files_data.get('structure', {}),
                    file_versions=files_data.get('versions', {}),
                    images=files_data.get('images', []),
                    conversation_history=[]
                )
            
            # Inizializza memoria conversazione se non presente
            if not hasattr(st.session_state, 'conversation_memory'):
                st.session_state.conversation_memory = {
                    'messages': [],
                    'max_length': st.session_state.get('memory_length', 3)
                }
            
        except Exception as e:
            st.error(f"Errore nell'inizializzazione dello stato: {str(e)}")
            raise

    def _get_current_timestamp(self) -> str:
        """Ottiene il timestamp corrente nel timezone italiano"""
        return datetime.now(self.timezone).isoformat()

    def _format_timestamp(self, timestamp: str) -> str:
        """Formatta il timestamp per la visualizzazione"""
        try:
            if '+' not in timestamp and 'Z' not in timestamp:
                dt = datetime.fromisoformat(timestamp)
                dt = dt.replace(tzinfo=pytz.UTC)
            else:
                timestamp = timestamp.replace('Z', '+00:00')
                dt = datetime.fromisoformat(timestamp)
            
            dt_italy = dt.astimezone(self.timezone)
            return dt_italy.strftime("%d-%m-%y %H:%M")
            
        except Exception as e:
            st.error(f"Errore nella formattazione del timestamp: {str(e)}")
            return timestamp

    def _update_conversation_memory(self, message: Dict):
        """Aggiorna la memoria della conversazione"""
        memory = st.session_state.conversation_memory
        
        # Aggiungi nuovo messaggio
        memory['messages'].append(message)
        
        # Mantieni solo gli ultimi N messaggi
        max_length = memory.get('max_length', 3)
        if len(memory['messages']) > max_length:
            memory['messages'] = memory['messages'][-max_length:]

    def _get_conversation_context(self) -> str:
        """Ottiene il contesto della conversazione dalla memoria"""
        memory = st.session_state.conversation_memory
        if not memory['messages']:
            return ""
        
        context = []
        for msg in memory['messages']:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, dict):
                content = content.get('content', '')
            context.append(f"{role}: {content}")
        
        return "\n".join(context)

    def _detect_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Rileva e estrae blocchi di codice dal testo"""
        code_blocks = []
        
        # Pattern per blocchi con linguaggio
        pattern_with_lang = r'```(\w+)?\n(.*?)\n```'
        # Pattern per blocchi senza linguaggio
        pattern_without_lang = r'```\n?(.*?)\n?```'
        
        # Cerca blocchi con linguaggio
        matches_with_lang = re.finditer(pattern_with_lang, text, re.DOTALL)
        for match in matches_with_lang:
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            code_blocks.append({
                "language": language,
                "code": code,
                "original": match.group(0)
            })
        
        # Cerca blocchi senza linguaggio
        matches_without_lang = re.finditer(pattern_without_lang, text, re.DOTALL)
        for match in matches_without_lang:
            # Verifica che non sia già stato trovato
            if not any(block['original'] == match.group(0) for block in code_blocks):
                code = match.group(1).strip()
                language = self._guess_language(code)
                code_blocks.append({
                    "language": language,
                    "code": code,
                    "original": match.group(0)
                })
        
        return code_blocks

    def _guess_language(self, code: str) -> str:
        """Cerca di determinare il linguaggio del codice"""
        code = code.strip().lower()
        
        # Indicatori per linguaggio
        indicators = {
            'python': [
                ('def ', 3),
                ('class ', 3),
                ('import ', 2),
                ('from ', 2),
                ('@', 1),
                ('if __name__', 3),
                ('.py', 2),
                ('print(', 1),
                ('return ', 1),
                ('#', 1),
                ('self.', 2),
                ('elif ', 2),
                ('None', 1),
                ('True', 1),
                ('False', 1),
                ('try:', 2),
                ('except:', 2),
                ('with ', 2)
            ],
            'javascript': [
                ('function ', 3),
                ('const ', 2),
                ('let ', 2),
                ('var ', 2),
                ('=>', 3),
                ('document.', 3),
                ('window.', 3),
                ('.js', 2),
                ('console.log(', 2),
                ('===', 2),
                ('!==', 2),
                ('undefined', 2)
            ],
            'html': [
                ('<html', 3),
                ('<body', 2),
                ('<div', 2),
                ('<p>', 1),
                ('<script', 2),
                ('<head', 2),
                ('<style', 2),
                ('<link', 1),
                ('<meta', 1),
                ('</div>', 2)
            ],
            'css': [
                ('{', 1),
                ('margin:', 2),
                ('padding:', 2),
                ('color:', 2),
                ('background:', 2),
                ('font-', 2),
                ('border:', 2),
                ('@media', 3),
                ('#', 1),
                ('.class', 1),
                ('px;', 2),
                ('em;', 2),
                ('rem;', 2)
            ],
            'sql': [
                ('select ', 3),
                ('from ', 2),
                ('where ', 2),
                ('insert into', 3),
                ('update ', 2),
                ('delete from', 3),
                ('create table', 3),
                ('join ', 2),
                ('group by', 2),
                ('order by', 2)
            ]
        }
        
        # Calcola punteggi
        scores = {lang: 0 for lang in indicators}
        for lang, indicators_list in indicators.items():
            for indicator, weight in indicators_list:
                occurrences = code.count(indicator)
                scores[lang] += occurrences * weight
        
        # Gestione casi speciali
        if scores['python'] > 0 and '{' in code:
            python_indicators = sum(1 for ind, _ in indicators['python'] if ind in code)
            if python_indicators >= 3:
                scores['python'] += 2
        
        # Se nessun punteggio significativo
        max_score = max(scores.values())
        if max_score == 0:
            if ('    ' in code or '\t' in code) and (':' in code or 'def' in code or 'class' in code):
                return 'python'
        
        # Trova linguaggio con punteggio più alto
        max_score = max(scores.values())
        if max_score > 0:
            candidates = [lang for lang, score in scores.items() if score == max_score]
            if len(candidates) > 1 and 'python' in candidates:
                if any(ind in code for ind, _ in indicators['python']):
                    return 'python'
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return 'text'

    def _looks_like_code(self, text: str) -> bool:
        """Verifica se il testo sembra essere codice"""
        indicators = [
            '    ',
            '\t',
            '()',
            '{',
            ';',
            'function',
            'class',
            'def ',
            'return',
            'import',
            'var ',
            'let ',
            'const '
        ]
        
        lines = text.split('\n')
        if len(lines) < 2:
            return False
            
        score = 0
        for indicator in indicators:
            if indicator in text:
                score += 1
                
        return score >= 2
    
    def format_message_with_code(self, message: str) -> Dict:
        """Formatta un messaggio con eventuali blocchi di codice"""
        code_blocks = self._detect_code_blocks(message)
        
        if code_blocks:
            formatted_message = message
            for i, block in enumerate(code_blocks):
                formatted_message = formatted_message.replace(
                    block['original'],
                    f"\n[Codice Blocco {i+1}]\n"
                )
            
            return {
                "content": formatted_message.strip(),
                "code_blocks": code_blocks
            }
        
        if len(message.split('\n')) > 1 and self._looks_like_code(message):
            language = self._guess_language(message)
            return {
                "content": f"[Codice {language}]",
                "code_blocks": [{
                    "language": language,
                    "code": message,
                    "original": message
                }]
            }
        
        return {"content": message}

    def _prepare_context(self, prompt: str, files: Optional[List[Dict]] = None, current_file: Optional[Dict] = None, image_data: Optional[Dict] = None) -> MessageContext:
        """Prepara il contesto per un messaggio"""
        content_type = determine_content_type(prompt)
        
        # Formatta i file per l'LLM
        formatted_files = []
        if files:
            for file in files:
                if isinstance(file, dict) and 'content' in file:
                    # Limita la dimensione del contenuto per evitare problemi di token
                    content = file['content'][:100000] if len(file['content']) > 100000 else file['content']
                    formatted_files.append({
                        'name': file.get('name', 'unknown'),
                        'content': content,
                        'language': file.get('language', 'text'),
                        'path': file.get('path', '')
                    })
        
        # Suggerisci regole base sul contenuto
        suggested_rules = suggest_rules({
            'content': prompt,
            'available_files': formatted_files,
            'current_file': current_file
        })
        
        # Merge con regole attive
        active_rules = merge_rule_sets(suggested_rules)
        
        context = MessageContext(
            content_type=content_type,
            active_rules=active_rules,
            available_files=formatted_files,
            current_file=current_file,
            image_data=image_data
        )
        
        return context

    def _generate_content_hash(self, content: str) -> str:
        """Genera hash del contenuto per caching"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()

    def _analyze_version_changes(self, file: Dict) -> Optional[Dict]:
        """Analizza cambiamenti tra versioni del file"""
        if not file.get('name'):
            return None
            
        chat_id = st.session_state.chat_state.current_chat_id
        versions = self.chat_persistence.get_file_versions(
            chat_id,
            file['name']
        )
        
        if not versions.get('versions'):
            return None
        
        # Ottieni versione corrente e precedente
        version_numbers = sorted(versions['versions'].keys())
        if len(version_numbers) < 2:
            return None
            
        current_version = versions['versions'][version_numbers[-1]]
        previous_version = versions['versions'][version_numbers[-2]]
        
        # Analizza differenze
        differ = difflib.Differ()
        current_lines = current_version['content'].splitlines()
        previous_lines = previous_version['content'].splitlines()
        
        diff = list(differ.compare(previous_lines, current_lines))
        
        changes = {
            "version_from": version_numbers[-2],
            "version_to": version_numbers[-1],
            "lines_added": len([l for l in diff if l.startswith('+ ')]),
            "lines_removed": len([l for l in diff if l.startswith('- ')]),
            "lines_modified": len([l for l in diff if l.startswith('? ')]),
            "diff_summary": self._generate_diff_summary(diff),
            "timestamp": current_version.get('created_at')
        }
        
        return changes

    def _generate_diff_summary(self, diff: List[str]) -> List[str]:
        """Genera riassunto delle modifiche"""
        summary = []
        current_block = []
        
        for line in diff:
            if line.startswith('? '):
                continue
                
            if line.startswith(('+ ', '- ')):
                current_block.append(line)
            else:
                if current_block:
                    block_summary = self._summarize_change_block(current_block)
                    if block_summary:
                        summary.append(block_summary)
                    current_block = []
        
        if current_block:
            block_summary = self._summarize_change_block(current_block)
            if block_summary:
                summary.append(block_summary)
        
        return summary

    def _summarize_change_block(self, block: List[str]) -> Optional[str]:
        """Riassume un blocco di modifiche"""
        if not block:
            return None
            
        additions = [l[2:] for l in block if l.startswith('+ ')]
        deletions = [l[2:] for l in block if l.startswith('- ')]
        
        patterns = {
            r'def\s+(\w+)': "funzione",
            r'class\s+(\w+)': "classe",
            r'import\s+(\w+)': "import",
            r'return\s+': "return statement",
            r'if\s+': "condizione",
            r'for\s+': "loop",
            r'while\s+': "loop",
            r'try:': "gestione errori"
        }
        
        for pattern, description in patterns.items():
            for line in additions:
                match = re.search(pattern, line)
                if match:
                    if match.groups():
                        return f"Aggiunto {description} '{match.group(1)}'"
                    return f"Aggiunto {description}"
                    
            for line in deletions:
                match = re.search(pattern, line)
                if match:
                    if match.groups():
                        return f"Rimosso {description} '{match.group(1)}'"
                    return f"Rimosso {description}"
        
        if len(block) == 1:
            return f"Modificata una linea"
        return f"Modificate {len(block)} linee"

    def handle_uploaded_files(self, uploaded_files) -> bool:
        """Gestisce i file caricati"""
        if not uploaded_files:
            return False
            
        try:
            chat_id = st.session_state.chat_state.current_chat_id
            current_files = st.session_state.chat_state.files
            
            result = self.file_handler.handle_uploaded_files(
                uploaded_files,
                current_files
            )
            
            if not result.get('success'):
                return False

            # Aggiorna stato locale
            st.session_state.chat_state.files = result['files']
            st.session_state.chat_state.file_structure = result['structure']
            
            if 'versions' in result:
                st.session_state.chat_state.file_versions.update(
                    result['versions']
                )
            
            # Salva in Firebase
            return self.chat_persistence.add_files_to_chat(
                chat_id,
                result['files'],
                result['structure']
            )

        except Exception as e:
            st.error(f"Errore nel caricamento dei file: {str(e)}")
            return False
        
    def handle_user_input(self, prompt: str, context: Dict = None):
        """Gestisce l'input dell'utente e genera la risposta"""
        try:
            chat_state = st.session_state.chat_state
            
            # Prepara contesto esteso
            files = None
            if hasattr(chat_state, 'files') and chat_state.files:
                # Assicurati che i file siano nel formato corretto
                files = [{
                    'name': f.get('name', ''),
                    'content': f.get('content', ''),
                    'language': f.get('language', 'text'),
                    'path': f.get('path', ''),
                    'version': f.get('version', '1')
                } for f in chat_state.files if isinstance(f, dict)]
            
            # Se c'è un file specifico nel contesto, usalo
            current_file = context.get('current_file') if context else None
            image_data = None
            
            # Gestione immagine temporanea
            if hasattr(st.session_state, 'temp_image') and st.session_state.temp_image:
                image_result = self.image_handler.process_image(st.session_state.temp_image)
                if image_result['success']:
                    image_data = image_result
                    if not self.chat_persistence.add_image_to_chat(
                        chat_state.current_chat_id,
                        image_result
                    ):
                        st.error("Errore nel salvataggio dell'immagine")
                st.session_state.temp_image = None
            
            # Prepara contesto del messaggio
            message_context = self._prepare_context(
                prompt,
                files,  # Passa i file formattati
                current_file,
                image_data
            )
            
            # Aggiungi messaggio utente con contesto files
            user_message = {
                "role": "user",
                "content": prompt,
                "timestamp": self._get_current_timestamp(),
                "context": {
                    "content_type": message_context.content_type,
                    "active_rules": list(message_context.active_rules),
                    "files": files  # Includi i file nel contesto del messaggio
                }
            }
            
            success = self.chat_persistence.add_message(
                chat_state.current_chat_id,
                "user",
                user_message
            )
            
            if not success:
                st.error("Errore nel salvataggio del messaggio")
                return

            # Aggiorna memoria conversazione
            self._update_conversation_memory(user_message)
            
            # Mostra messaggio utente
            with st.chat_message("user"):
                st.write(prompt)

            # Gestisci risposta
            with st.chat_message("assistant"):
                # ... resto del codice della funzione ...

                # Prepara contesto per LLM con i file formattati
                llm_context = {
                    "content_type": message_context.content_type,
                    "active_rules": message_context.active_rules,
                    "conversation_mode": st.session_state.conversation_mode,
                    "conversation_style": st.session_state.conversation_style,
                    "conversation_history": self._get_conversation_context(),
                    "available_files": files,  # Usa i file formattati
                }

                if current_file:
                    llm_context["current_file"] = current_file
                
                if message_context.analysis_result:
                    llm_context["code_analysis"] = message_context.analysis_result
                
                if message_context.version_changes:
                    llm_context["version_changes"] = message_context.version_changes
                
                if image_data:
                    llm_context["image"] = image_data["base64"]

                    # Debug log per verifica contesto
                    st.session_state.debug_logs.append(f"LLM Context Keys: {list(llm_context.keys())}")
                    if "available_files" in llm_context:
                        st.session_state.debug_logs.append(f"Files in context: {len(llm_context['available_files'])}")
                    
                    # Ottieni risposta in streaming
                    accumulated_response = []
                    for partial_response in self.llm_handler.get_streaming_response(
                        prompt,
                        llm_context
                    ):
                        if chat_state.should_stop:
                            thinking_placeholder.empty()
                            message_placeholder.error("Elaborazione interrotta")
                            return
                        
                        if isinstance(partial_response, str):
                            accumulated_response.append(partial_response)
                            current_text = "".join(accumulated_response)
                            
                            # Formatta risposta
                            formatted_message = self.format_message_with_code(current_text)
                            if isinstance(formatted_message, dict):
                                message_placeholder.markdown(formatted_message["content"])
                                # Mostra blocchi codice
                                if "code_blocks" in formatted_message:
                                    for i, block in enumerate(formatted_message["code_blocks"]):
                                        with st.expander(f"Codice {i+1}", expanded=True):
                                            st.code(block["code"], language=block["language"])
                            else:
                                message_placeholder.markdown(current_text)
                    
                    final_response = "".join(accumulated_response)
                    
                    # Salva risposta completa
                    if final_response.strip():
                        assistant_message = {
                            "role": "assistant",
                            "content": final_response,
                            "timestamp": self._get_current_timestamp(),
                            "context": {
                                "content_type": message_context.content_type,
                                "active_rules": list(message_context.active_rules),
                                "files": message_context.available_files  # Mantieni il contesto dei file
                            }
                        }
                        
                        success = self.chat_persistence.add_message(
                            chat_state.current_chat_id,
                            "assistant",
                            assistant_message
                        )
                        
                        if not success:
                            st.error("Errore nel salvataggio della risposta")
                        
                        # Aggiorna memoria conversazione
                        self._update_conversation_memory(assistant_message)
                        
                except Exception as e:
                    st.error(f"Errore nell'elaborazione: {str(e)}")
                    st.session_state.debug_logs.append(f"Error in message processing: {str(e)}")
                finally:
                    chat_state.is_processing = False
                    chat_state.should_stop = False
                    chat_state.current_response = ""
                    # Rimuovi il messaggio "thinking" e il pulsante di stop
                    thinking_placeholder.empty()
                    stop_button_placeholder.empty()
                        
        except Exception as e:
            st.error(f"Errore nella gestione dell'input: {str(e)}")
            st.session_state.debug_logs.append(f"Error in input handling: {str(e)}")

    def display_messages(self):
        """Visualizza i messaggi della chat corrente"""
        try:
            chat_state = st.session_state.chat_state
            messages = self.chat_persistence.get_chat_messages(
                chat_state.current_chat_id
            )
            
            if not messages:
                return
                
            for message in messages:
                if not isinstance(message, dict) or 'role' not in message:
                    continue
                    
                with st.chat_message(message["role"]):
                    # Estrai il contenuto correttamente
                    content = message.get('content', '')
                    
                    # Gestisci il caso in cui content è un dizionario
                    if isinstance(content, dict):
                        actual_content = content.get('content', '')
                        # Formatta solo se è una stringa
                        if isinstance(actual_content, str):
                            formatted_message = self.format_message_with_code(actual_content)
                    else:
                        # Formatta solo se content è una stringa
                        if isinstance(content, str):
                            formatted_message = self.format_message_with_code(content)
                        else:
                            formatted_message = {'content': str(content)}

                    # Visualizza il contenuto
                    if isinstance(formatted_message, dict):
                        st.markdown(formatted_message["content"])
                        if "code_blocks" in formatted_message:
                            for i, block in enumerate(formatted_message["code_blocks"]):
                                with st.expander(f"Codice {i+1}", expanded=True):
                                    st.code(block["code"], language=block["language"])
                    else:
                        st.markdown(str(formatted_message))
                    
                    # Timestamp
                    if 'timestamp' in message:
                        st.caption(f"Inviato: {self._format_timestamp(message['timestamp'])}")
                    
        except Exception as e:
            st.error(f"Errore nella visualizzazione dei messaggi: {str(e)}")
            # Debug info
            if 'message' in locals():
                st.error(f"Contenuto del messaggio problematico: {type(message.get('content'))} - {message.get('content')}")

    import streamlit as st

    def display_chat_sidebar(self):
        """Visualizza la sidebar delle chat"""
        with st.sidebar:
            chat_state = st.session_state.chat_state

            # Pulsante per creare una nuova chat
            if st.button("➕ Nuova Chat", use_container_width=True):
                chat_id = self.chat_persistence.create_chat()
                if chat_id:
                    st.session_state.chats = self.chat_persistence.get_all_chats()
                    chat_state.current_chat_id = chat_id
                    # Reset dello stato
                    chat_state.files = []
                    chat_state.file_structure = {}
                    chat_state.file_versions = {}
                    chat_state.images = []
                    chat_state.conversation_history = []
                    st.rerun()

            # Lista delle chat esistenti
            chats = st.session_state.chats.get("chats", {})

            # Stile CSS per i pulsanti orizzontali
            st.markdown("""
                <style>
                .button-container {
                    display: flex;
                    gap: 0.5rem;
                    margin-top: 0.5rem;
                }
                .button-container .stButton > button {
                    flex: 1;
                    padding: 0.2rem 0.5rem;
                    font-size: 1rem;
                }
                </style>
                """, unsafe_allow_html=True)

            for chat_id, chat_info in chats.items():
                # Determina se è la chat corrente
                is_current = chat_id == chat_state.current_chat_id
                container_style = f"""
                    padding: 0.5rem;
                    border-radius: 0.5rem;
                    background-color: {'rgba(0, 0, 0, 0.05)' if is_current else 'transparent'};
                    margin-bottom: 0.5rem;
                """

                # Inizio del container per la chat
                st.markdown(f"<div style='{container_style}'>", unsafe_allow_html=True)

                # Titolo della chat modificabile
                chat_title = chat_info.get("title", "Nuova Chat")
                new_title = st.text_input(
                    "",
                    value=chat_title,
                    key=f"title_{chat_id}",
                    label_visibility="collapsed"
                )

                if new_title != chat_title:
                    self.chat_persistence.update_chat_title(chat_id, new_title)
                    st.session_state.chats = self.chat_persistence.get_all_chats()

                # Informazioni sulla chat
                info_list = []
                if "updated_at" in chat_info:
                    info_list.append(f"🕒 {self._format_timestamp(chat_info['updated_at'])}")

                messages = self.chat_persistence.get_chat_messages(chat_id)
                if messages:
                    info_list.append(f"💬 {len(messages)} messaggi")

                files_data = self.chat_persistence.get_chat_files(chat_id)
                if files_data and files_data.get('content'):
                    info_list.append(f"📎 {len(files_data['content'])} file")

                if info_list:
                    st.caption(" | ".join(info_list))

                # Azioni per la chat
                # Container per i pulsanti
                col1, col2 = st.columns(2)
                
                # Pulsante per selezionare la chat
                with col1:
                    if st.button("🔄 Seleziona", key=f"select_{chat_id}", use_container_width=True):
                        chat_state.current_chat_id = chat_id
                        # Carica i dati della chat
                        chat_data = self.chat_persistence.get_chat_files(chat_id)
                        if chat_data:
                            chat_state.files = chat_data.get('content', [])
                            chat_state.file_structure = chat_data.get('structure', {})
                            chat_state.file_versions = chat_data.get('versions', {})
                            chat_state.images = chat_data.get('images', [])
                        st.rerun()

                # Pulsante per eliminare la chat (non per la chat corrente)
                with col2:
                    if len(chats) > 1 and not is_current:
                        if st.button("🗑️ Elimina", key=f"delete_{chat_id}", use_container_width=True):
                            if self.delete_chat(chat_id):
                                st.rerun()

                # Fine del container per la chat
                st.markdown("</div>", unsafe_allow_html=True)

                # Anteprima dei file in un expander
                if files_data and files_data.get('content'):
                    with st.expander("📂 File", expanded=False):
                        self._display_chat_files(
                            files_data['content'],
                            files_data.get('structure', {}),
                            files_data.get('versions', {})
                        )


    def _display_chat_files(self, files: List[Dict], structure: Dict, versions: Dict):
        """Visualizza i file della chat con struttura e versioni"""
        if not files:
            return
            
        # Mostra struttura cartelle se presente
        if structure:
            for path, items in structure.items():
                if path:
                    st.markdown(f"**📁 {path}/**")
                for item in items:
                    if isinstance(item, dict):
                        file_name = item.get('name', 'Unknown file')
                        version = item.get('version', '1')
                        st.markdown(f"└─ 📄 {file_name} (v{version})")
        
        # Lista file con preview
        for file in files:
            if not isinstance(file, dict) or 'name' not in file:
                continue
                
            with st.expander(f"📄 {file['name']}", expanded=False):
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    # File info
                    st.caption(f"Versione: {file.get('version', '1')}")
                    if 'size' in file:
                        st.caption(f"Dimensione: {file['size']/1024:.1f}KB")
                    
                    # Preview contenuto
                    if file.get('content'):
                        file_ext = Path(file['name']).suffix.lower()
                        language = self.file_handler.app_config["language_mapping"].get(file_ext, "text")
                        st.code(
                            file['content'][:500] + "..." if len(file['content']) > 500 else file['content'],
                            language=language,
                            line_numbers=True
                        )
                
                with col2:
                    # Azioni file
                    if versions and file['name'] in versions:
                        version_count = len(versions[file['name']])
                        st.caption(f"📝 {version_count} versioni")
                        
                        if version_count > 1:
                            if st.button("🔄 Diff", key=f"diff_{file['name']}", help="Mostra differenze"):
                                version_changes = self._analyze_version_changes(file)
                                if version_changes:
                                    st.json(version_changes)
                    
                    if st.button("🗑️", key=f"delete_file_{file['name']}", help="Rimuovi file"):
                        if self.chat_persistence.remove_file_from_chat(
                            st.session_state.chat_state.current_chat_id,
                            file['name']
                        ):
                            st.session_state.chat_state.files = None
                            st.rerun()

    def delete_chat(self, chat_id: str) -> bool:
        """Elimina una chat"""
        try:
            # Ottieni tutte le chat
            chats = st.session_state.chats.get("chats", {})
            
            # Non permettere eliminazione ultima chat
            if len(chats) <= 1:
                st.error("Non puoi eliminare l'ultima chat")
                return False
            
            # Elimina chat
            if self.chat_persistence.delete_chat(chat_id):
                chat_state = st.session_state.chat_state
                
                # Se era la chat corrente, passa alla prima disponibile
                if chat_id == chat_state.current_chat_id:
                    # Rimuovi chat eliminata
                    chats.pop(chat_id, None)
                    # Prendi primo ID rimanente
                    next_chat_id = next(iter(chats))
                    chat_state.current_chat_id = next_chat_id
                    
                    # Aggiorna dati chat corrente
                    chat_data = self.chat_persistence.get_chat_files(next_chat_id)
                    if chat_data:
                        chat_state.files = chat_data.get('content', [])
                        chat_state.file_structure = chat_data.get('structure', {})
                        chat_state.file_versions = chat_data.get('versions', {})
                        chat_state.images = chat_data.get('images', [])
                    
                # Aggiorna lista chat
                st.session_state.chats = self.chat_persistence.get_all_chats()
                return True
                
            return False
            
        except Exception as e:
            st.error(f"Errore nell'eliminazione della chat: {str(e)}")
            return False        


    def display_contextual_actions(self, file_info: Optional[Dict] = None):
        """Mostra azioni contestuali basate sul contenuto"""
        if not file_info and not hasattr(st.session_state, 'chat_state'):
            return
            
        chat_state = st.session_state.chat_state
        
        # Determina tipo di file
        if file_info:
            files_to_analyze = [file_info]
        else:
            files_to_analyze = chat_state.files
        
        if not files_to_analyze:
            return
        
        content_types = set()
        for file in files_to_analyze:
            ext = Path(file['name']).suffix.lower()
            if ext in {'.py', '.js', '.html', '.css', '.cpp', '.java'}:
                content_types.add('code')
            elif ext == '.json':
                content_types.add('json')
            elif ext in {'.csv', '.xlsx'}:
                content_types.add('data')
        
        if not content_types:
            return
        
        st.write("🔍 Azioni disponibili:")
        cols = st.columns(len(content_types))
        
        for i, content_type in enumerate(content_types):
            with cols[i]:
                if content_type == 'code':
                    self._display_code_actions(file_info)
                elif content_type in {'json', 'data'}:
                    self._display_data_actions(file_info)

    def _display_code_actions(self, file_info: Optional[Dict] = None):
        """Mostra azioni specifiche per il codice"""
        context = {"current_file": file_info} if file_info else {}
        
        if st.button("📝 Review Completa", use_container_width=True):
            self.handle_user_input(
                "Esegui una review completa del codice",
                {"type": "code_analysis", **context}
            )
        
        if st.button("🐛 Trova Bug", use_container_width=True):
            self.handle_user_input(
                "Cerca potenziali bug e problemi nel codice",
                {"type": "bug_finding", **context}
            )
        
        if st.button("📚 Spiega Codice", use_container_width=True):
            self.handle_user_input(
                "Spiega in dettaglio cosa fa questo codice",
                {"type": "code_explanation", **context}
            )
        
        if st.button("💡 Migliora Codice", use_container_width=True):
            self.handle_user_input(
                "Suggerisci miglioramenti pratici per questo codice",
                {"type": "code_improvement", **context}
            )
        
        if file_info and st.session_state.version_tracking:
            if st.button("📝 Storia Modifiche", use_container_width=True):
                version_changes = self._analyze_version_changes(file_info)
                if version_changes:
                    with st.expander("📜 Storia Modifiche", expanded=True):
                        st.json(version_changes)

    def _display_data_actions(self, file_info: Optional[Dict] = None):
        """Mostra azioni specifiche per i dati"""
        context = {"current_file": file_info} if file_info else {}
        
        if st.button("📊 Analisi Dati", use_container_width=True):
            self.handle_user_input(
                "Esegui un'analisi completa dei dati",
                {"type": "data_analysis", **context}
            )
        
        if st.button("🔍 Trova Pattern", use_container_width=True):
            self.handle_user_input(
                "Identifica pattern e correlazioni nei dati",
                {"type": "data_analysis", **context}
            )
        
        if st.button("📈 Suggerisci Visualizzazioni", use_container_width=True):
            self.handle_user_input(
                "Suggerisci visualizzazioni utili per questi dati",
                {"type": "data_visualization", **context}
            )
        
        if file_info and st.session_state.auto_analysis:
            if st.button("🔄 Analisi Automatica", use_container_width=True):
                self.handle_user_input(
                    f"Analizza automaticamente il file {file_info['name']}",
                    {"type": "auto_analysis", **context}
                )

    def _get_file_preview(self, file: Dict, max_lines: int = 10) -> str:
        """Ottiene preview del contenuto del file"""
        if not file.get('content'):
            return ""
            
        lines = file['content'].split('\n')
        if len(lines) <= max_lines:
            return file['content']
            
        return '\n'.join(lines[:max_lines]) + f"\n... [altri {len(lines) - max_lines} linee]"

    def _get_file_info(self, file: Dict) -> Dict[str, Any]:
        """Ottiene informazioni dettagliate sul file"""
        info = {
            "name": file.get('name', 'Unknown'),
            "size": len(file.get('content', '')),
            "lines": len(file.get('content', '').split('\n')),
            "type": Path(file.get('name', '')).suffix.lower(),
            "version": file.get('version', '1')
        }
        
        if file.get('path'):
            info["path"] = file['path']
            
        if file.get('language'):
            info["language"] = file['language']
            
        return info

    def _format_file_size(self, size: int) -> str:
        """Formatta dimensione file in formato leggibile"""
        for unit in ['B', 'KB', 'MB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}GB"            