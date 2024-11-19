import streamlit as st
from typing import List, Set, Dict, Any, Optional
from config.models import (
    MODELS_CONFIG, 
    ANALYSIS_RULES, 
    RULE_PRESETS,
    get_active_rules,
    determine_content_type
)

class SettingsUI:
    def __init__(self):
        self.models_config = MODELS_CONFIG
        self.analysis_rules = ANALYSIS_RULES
        self.rule_presets = RULE_PRESETS

    def initialize_session_state(self):
        """Inizializza lo stato della sessione per le impostazioni"""
        # Regole
        if 'active_rules' not in st.session_state:
            st.session_state.active_rules = {
                rule_type: set(rules["mandatory"]) 
                for rule_type, rules in self.analysis_rules.items()
            }
        
        # Conversazione
        if 'conversation_mode' not in st.session_state:
            st.session_state.conversation_mode = True
        
        if 'memory_length' not in st.session_state:
            st.session_state.memory_length = 3
            
        if 'conversation_style' not in st.session_state:
            st.session_state.conversation_style = "Bilanciato"
        
        # Files
        if 'version_tracking' not in st.session_state:
            st.session_state.version_tracking = True
            
        if 'diff_strategy' not in st.session_state:
            st.session_state.diff_strategy = "Smart"
            
        if 'change_threshold' not in st.session_state:
            st.session_state.change_threshold = 10
        
        # Analisi
        if 'auto_analysis' not in st.session_state:
            st.session_state.auto_analysis = True
            
        if 'analysis_depth' not in st.session_state:
            st.session_state.analysis_depth = "Standard"
            
        if 'analysis_checks' not in st.session_state:
            st.session_state.analysis_checks = [
                "Sicurezza",
                "Performance",
                "Stile"
            ]
        
        # Preview
        if 'preview_mode' not in st.session_state:
            st.session_state.preview_mode = "Semplice"
            
        if 'preview_lines' not in st.session_state:
            st.session_state.preview_lines = 50
            
        if 'syntax_highlight' not in st.session_state:
            st.session_state.syntax_highlight = True
            
        if 'line_numbers' not in st.session_state:
            st.session_state.line_numbers = True

    def display_sidebar_settings(self):
        """Mostra tutte le impostazioni nella sidebar"""
        # Settings Tabs
        tabs = st.tabs([
            "🤖 Modello", 
            "⚙️ Regole",
            "💬 Conversazione",
            "📂 File"
        ])
        
        # Tab Modello
        with tabs[0]:
            self._display_model_settings()
            
        # Tab Regole
        with tabs[1]:
            self._display_rules_settings()
            
        # Tab Conversazione
        with tabs[2]:
            self._display_conversation_settings()
            
        # Tab File
        with tabs[3]:
            self._display_file_settings()

        # Debug logs
        if 'debug_logs' in st.session_state:
            with st.expander("🔍 Debug Logs", expanded=False):
                logs = st.session_state.debug_logs
                if logs:
                    st.code('\n'.join(logs), language='text')
                else:
                    st.info("Nessun log disponibile")
                if st.button("🗑️ Pulisci Log"):
                    st.session_state.debug_logs = []
                    st.rerun()

    def _display_model_settings(self):
        """Mostra impostazioni del modello"""
        # Model selector
        available_models = list(MODELS_CONFIG.keys())
        current_model_index = available_models.index(st.session_state.model)
        model_display_names = {
            model_id: config["name"] 
            for model_id, config in MODELS_CONFIG.items()
        }
        display_names = [
            model_display_names[model_id] 
            for model_id in available_models
        ]
        
        selected_display_name = st.selectbox(
            "Modello",
            options=display_names,
            index=current_model_index,
            key="model_selector"
        )
        
        # Aggiorna modello se cambiato
        selected_model = next(
            model_id for model_id, name in model_display_names.items() 
            if name == selected_display_name
        )
        
        if selected_model != st.session_state.model:
            st.session_state.model = selected_model
            try:
                st.session_state.llm_handler.initialize_model(selected_model)
            except Exception as e:
                st.error(f"Errore nel cambio del modello: {str(e)}")
                st.rerun()
        
        # Parametri modello in expander
        with st.expander("🎛️ Parametri Modello", expanded=False):
            current_params = st.session_state.llm_handler.get_model_parameters()
            
            new_params = {}
            
            # Temperature
            new_params['temperature'] = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=current_params['temperature'],
                step=0.1,
                help="Controlla la creatività delle risposte"
            )
            
            # Top P
            new_params['top_p'] = st.slider(
                "Top P",
                min_value=0.0,
                max_value=1.0,
                value=current_params['top_p'],
                step=0.05,
                help="Controlla la diversità delle risposte"
            )
            
            # Max Tokens
            new_params['max_tokens'] = st.slider(
                "Max Tokens",
                min_value=1,
                max_value=4096,
                value=current_params['max_tokens'],
                step=100,
                help="Lunghezza massima della risposta"
            )
            
            # Presence Penalty
            if 'presence_penalty' in current_params:
                new_params['presence_penalty'] = st.slider(
                    "Presence Penalty",
                    min_value=-2.0,
                    max_value=2.0,
                    value=current_params.get('presence_penalty', 0.0),
                    step=0.1,
                    help="Penalizza la ripetizione di token"
                )
            
            # Frequency Penalty    
            if 'frequency_penalty' in current_params:
                new_params['frequency_penalty'] = st.slider(
                    "Frequency Penalty",
                    min_value=-2.0,
                    max_value=2.0,
                    value=current_params.get('frequency_penalty', 0.0),
                    step=0.1,
                    help="Penalizza la ripetizione di frasi"
                )
            
            # Pulsanti azione
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Salva", use_container_width=True):
                    st.session_state.llm_handler.update_model_parameters(new_params)
                    st.success("Parametri salvati")
                    
            with col2:
                if st.button("🔄 Reset", use_container_width=True):
                    default_params = {
                        'temperature': MODELS_CONFIG[st.session_state.model].get('temperature', 0.7),
                        'max_tokens': MODELS_CONFIG[st.session_state.model].get('max_tokens', 4096),
                        'top_p': MODELS_CONFIG[st.session_state.model].get('top_p', 0.95),
                        'presence_penalty': MODELS_CONFIG[st.session_state.model].get('presence_penalty', 0.0),
                        'frequency_penalty': MODELS_CONFIG[st.session_state.model].get('frequency_penalty', 0.0),
                    }
                    st.session_state.llm_handler.update_model_parameters(default_params)
                    st.success("Parametri resettati")
                    st.rerun()

    def _display_rules_settings(self):
        """Mostra impostazioni delle regole"""
        # Preset selector
        preset_options = ["Custom"] + list(RULE_PRESETS.keys())
        selected_preset = st.selectbox(
            "🔍 Preset Regole",
            options=preset_options,
            help="Preset predefiniti di regole"
        )
        
        if selected_preset != "Custom":
            preset_info = RULE_PRESETS[selected_preset]
            st.info(preset_info["description"])
            
            if st.button("Applica Preset", key=f"apply_{selected_preset}", use_container_width=True):
                for rule_type, rules in preset_info["enabled_rules"].items():
                    if rule_type in st.session_state.active_rules:
                        st.session_state.active_rules[rule_type] = set(rules)
                st.success(f"Preset {selected_preset} applicato")
                st.rerun()
        
        # Regole per tipo
        for rule_type, rules_info in ANALYSIS_RULES.items():
            with st.expander(f"📋 Regole {rule_type.title()}", expanded=False):
                self._display_rule_type_settings(rule_type, rules_info)

    def _display_rule_type_settings(self, rule_type: str, rules_info: dict):
        """Mostra impostazioni per un tipo specifico di regole"""
        # Regole obbligatorie
        st.caption("🔒 Regole Obbligatorie")
        for rule in rules_info["mandatory"]:
            st.info(f"✓ {rules_info['description'][rule]}")
        
        # Regole opzionali
        st.caption("🔓 Regole Opzionali")
        optional_rules = [
            r for r in rules_info["default"] 
            if r not in rules_info["mandatory"]
        ]
        
        for rule in optional_rules:
            enabled = rule in st.session_state.active_rules[rule_type]
            if st.checkbox(
                rules_info["description"][rule],
                value=enabled,
                key=f"{rule_type}_{rule}"
            ):
                st.session_state.active_rules[rule_type].add(rule)
            else:
                st.session_state.active_rules[rule_type].discard(rule)

    def _display_conversation_settings(self):
        """Mostra impostazioni conversazione"""
        # Modalità conversazione
        st.caption("💭 Modalità Conversazione")
        
        conversation_mode = st.toggle(
            "Abilita modalità conversazione",
            value=st.session_state.get('conversation_mode', True),
            help="Ottimizza il modello per conversazioni naturali"
        )
        
        if conversation_mode != st.session_state.get('conversation_mode'):
            st.session_state.conversation_mode = conversation_mode
            if conversation_mode:
                # Attiva regole conversazione
                st.session_state.active_rules['conversation'] = set(
                    ANALYSIS_RULES['conversation']['default']
                )
            else:
                # Disattiva regole conversazione
                st.session_state.active_rules['conversation'] = set(
                    ANALYSIS_RULES['conversation']['mandatory']
                )
        
        # Memoria conversazione
        st.caption("🧠 Memoria Conversazione")
        
        memory_length = st.slider(
            "Lunghezza memoria (messaggi)",
            min_value=1,
            max_value=10,
            value=st.session_state.get('memory_length', 3),
            help="Numero di messaggi precedenti da considerare"
        )
        
        if memory_length != st.session_state.get('memory_length'):
            st.session_state.memory_length = memory_length
        
        # Stile conversazione
        st.caption("🎨 Stile Conversazione")
        
        conversation_style = st.select_slider(
            "Stile risposta",
            options=["Conciso", "Bilanciato", "Dettagliato"],
            value=st.session_state.get('conversation_style', "Bilanciato"),
            help="Controlla il livello di dettaglio delle risposte"
        )
        
        if conversation_style != st.session_state.get('conversation_style'):
            st.session_state.conversation_style = conversation_style

    def _display_file_settings(self):
        """Mostra impostazioni gestione file"""
        # Versioning
        st.caption("📝 Versioning")
        
        version_tracking = st.toggle(
            "Abilita tracking versioni",
            value=st.session_state.get('version_tracking', True),
            help="Mantieni storia delle modifiche ai file"
        )
        
        if version_tracking != st.session_state.get('version_tracking'):
            st.session_state.version_tracking = version_tracking
        
        if version_tracking:
            # Impostazioni versioning
            with st.expander("⚙️ Impostazioni Versioning", expanded=False):
                # Strategia diff
                diff_strategy = st.radio(
                    "Strategia diff",
                    options=["Completa", "Smart", "Minima"],
                    index=1,
                    help="Controlla il livello di dettaglio del tracking modifiche"
                )
                
                if diff_strategy != st.session_state.get('diff_strategy'):
                    st.session_state.diff_strategy = diff_strategy
                
                # Threshold modifiche
                change_threshold = st.slider(
                    "Soglia modifiche (%)",
                    min_value=1,
                    max_value=100,
                    value=st.session_state.get('change_threshold', 10),
                    help="Percentuale minima di modifiche per nuova versione"
                )
                
                if change_threshold != st.session_state.get('change_threshold'):
                    st.session_state.change_threshold = change_threshold
        
        # Auto-analisi
        st.caption("🔍 Analisi Automatica")
        
        auto_analysis = st.toggle(
            "Analisi automatica file",
            value=st.session_state.get('auto_analysis', True),
            help="Analizza automaticamente i file caricati"
        )
        
        if auto_analysis != st.session_state.get('auto_analysis'):
            st.session_state.auto_analysis = auto_analysis
        
        if auto_analysis:
            # Impostazioni analisi
            with st.expander("⚙️ Impostazioni Analisi", expanded=False):
                # Profondità analisi
                analysis_depth = st.select_slider(
                    "Profondità analisi",
                    options=["Base", "Standard", "Approfondita"],
                    value=st.session_state.get('analysis_depth', "Standard"),
                    help="Controlla il livello di dettaglio dell'analisi"
                )
                
                if analysis_depth != st.session_state.get('analysis_depth'):
                    st.session_state.analysis_depth = analysis_depth
                
                # Check specifici
                st.multiselect(
                    "Check da eseguire",
                    options=[
                        "Sicurezza",
                        "Performance",
                        "Stile",
                        "Complessità",
                        "Dipendenze"
                    ],
                    default=st.session_state.get('analysis_checks', [
                        "Sicurezza",
                        "Performance",
                        "Stile"
                    ]),
                    key="analysis_checks"
                )
        
        # Preview file
        st.caption("👁️ Preview File")
        
        preview_mode = st.radio(
            "Modalità preview",
            options=["Semplice", "Avanzata"],
            help="Controlla la visualizzazione dei file"
        )
        
        if preview_mode != st.session_state.get('preview_mode'):
            st.session_state.preview_mode = preview_mode
        
        if preview_mode == "Avanzata":
            # Impostazioni preview avanzata
            with st.expander("⚙️ Impostazioni Preview", expanded=False):
                st.number_input(
                    "Linee preview",
                    min_value=10,
                    max_value=100,
                    value=st.session_state.get('preview_lines', 50),
                    step=10,
                    key="preview_lines"
                )
                
                st.checkbox(
                    "Syntax highlighting",
                    value=st.session_state.get('syntax_highlight', True),
                    key="syntax_highlight"
                )
                
                st.checkbox(
                    "Numeri linea",
                    value=st.session_state.get('line_numbers', True),
                    key="line_numbers"
                )

    def get_current_settings(self) -> Dict[str, Any]:
        """Ottiene tutte le impostazioni correnti"""
        return {
            # Modello
            "model": st.session_state.model,
            "model_params": st.session_state.llm_handler.get_model_parameters(),
            
            # Regole
            "active_rules": {
                rule_type: list(rules)
                for rule_type, rules in st.session_state.active_rules.items()
            },
            
            # Conversazione
            "conversation_mode": st.session_state.conversation_mode,
            "memory_length": st.session_state.memory_length,
            "conversation_style": st.session_state.conversation_style,
            
            # Files
            "version_tracking": st.session_state.version_tracking,
            "diff_strategy": st.session_state.diff_strategy,
            "change_threshold": st.session_state.change_threshold,
            
            # Analisi
            "auto_analysis": st.session_state.auto_analysis,
            "analysis_depth": st.session_state.analysis_depth,
            "analysis_checks": st.session_state.analysis_checks,
            
            # Preview
            "preview_mode": st.session_state.preview_mode,
            "preview_lines": st.session_state.preview_lines,
            "syntax_highlight": st.session_state.syntax_highlight,
            "line_numbers": st.session_state.line_numbers
        }

    def save_settings(self, settings: Dict[str, Any]):
        """Salva tutte le impostazioni"""
        if 'model' in settings:
            st.session_state.model = settings['model']
        if 'model_params' in settings and hasattr(st.session_state, 'llm_handler'):
            st.session_state.llm_handler.update_model_parameters(settings['model_params'])
        
        if 'active_rules' in settings:
            st.session_state.active_rules = {
                rule_type: set(rules)
                for rule_type, rules in settings['active_rules'].items()
            }
        
        for key in [
            'conversation_mode', 'memory_length', 'conversation_style',
            'version_tracking', 'diff_strategy', 'change_threshold',
            'auto_analysis', 'analysis_depth', 'analysis_checks',
            'preview_mode', 'preview_lines', 'syntax_highlight', 'line_numbers'
        ]:
            if key in settings:
                setattr(st.session_state, key, settings[key])

    def reset_settings(self):
        """Resetta tutte le impostazioni ai valori default"""
        # Modello
        st.session_state.model = list(MODELS_CONFIG.keys())[0]
        if hasattr(st.session_state, 'llm_handler'):
            st.session_state.llm_handler.initialize_model(st.session_state.model)
        
        # Inizializza tutto da zero
        self.initialize_session_state()

    def export_settings(self) -> Dict[str, Any]:
        """Esporta le impostazioni in formato serializzabile"""
        settings = self.get_current_settings()
        
        # Converti set in liste per json
        if 'active_rules' in settings:
            settings['active_rules'] = {
                rule_type: list(rules)
                for rule_type, rules in settings['active_rules'].items()
            }
        
        return settings

    def import_settings(self, settings: Dict[str, Any]):
        """Importa impostazioni da formato serializzato"""
        # Converti liste in set per regole
        if 'active_rules' in settings:
            settings['active_rules'] = {
                rule_type: set(rules)
                for rule_type, rules in settings['active_rules'].items()
            }
        
        self.save_settings(settings)

    # Esporta solo le funzioni necessarie
    __all__ = [
        'display_sidebar_settings',
        'initialize_session_state', 
        'initialize_rules',
        'get_current_settings',
        'save_settings',
        'reset_settings',
        'export_settings',
        'import_settings'
    ]