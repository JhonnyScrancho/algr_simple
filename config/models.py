from pathlib import Path
import re
from typing import Dict, Any, List, Set, Optional

# Regole di analisi per tipo di contenuto
ANALYSIS_RULES = {
    "code": {
        "default": [
            "no_omissions",
            "no_overengineering",
            "maintain_style",
            "practical_improvements",
            "actual_code_focus"
        ],
        "description": {
            "no_omissions": "Non omettere parti di codice usando (...)",
            "no_overengineering": "No sovra-ingegnerizzazione non richiesta",
            "maintain_style": "Mantieni lo stile e l'approccio esistente",
            "practical_improvements": "Solo miglioramenti pratici e concreti",
            "actual_code_focus": "Focus sul codice effettivo, no speculazioni"
        },
        "mandatory": [
            "no_omissions",
            "maintain_style"
        ]
    },
    "conversation": {
        "default": [
            "natural_flow",
            "context_awareness",
            "appropriate_tone"
        ],
        "description": {
            "natural_flow": "Mantieni un flusso naturale della conversazione",
            "context_awareness": "Considera il contesto della discussione",
            "appropriate_tone": "Usa un tono appropriato al contesto"
        },
        "mandatory": [
            "natural_flow",
            "context_awareness"
        ]
    },
    "data": {
        "default": [
            "complete_analysis",
            "show_insights",
            "statistical_relevance",
            "practical_visualization"
        ],
        "description": {
            "complete_analysis": "Mostra tutti gli step dell'analisi",
            "show_insights": "Evidenzia pattern e insights significativi",
            "statistical_relevance": "Includi rilevanza statistica",
            "practical_visualization": "Suggerisci visualizzazioni utili"
        },
        "mandatory": [
            "complete_analysis",
            "show_insights"
        ]
    },
    "json": {
        "default": [
            "complete_processing",
            "show_transformations",
            "structural_focus",
            "optimization_suggestions"
        ],
        "description": {
            "complete_processing": "Processing completo dei dati",
            "show_transformations": "Mostra trasformazioni dati",
            "structural_focus": "Focus sulla struttura dati",
            "optimization_suggestions": "Suggerimenti di ottimizzazione"
        },
        "mandatory": [
            "complete_processing",
            "structural_focus"
        ]
    }
}

# Preset di regole predefiniti aggiornati
RULE_PRESETS = {
    "conversational": {
        "name": "Conversational Mode",
        "description": "Ottimizzato per conversazioni naturali",
        "enabled_rules": {
            "conversation": ["natural_flow", "context_awareness", "appropriate_tone"]
        }
    },
    "technical": {
        "name": "Technical Analysis",
        "description": "Analisi tecnica approfondita",
        "enabled_rules": {
            "code": ["no_omissions", "maintain_style", "practical_improvements"],
            "data": ["complete_analysis", "show_insights"]
        }
    },
    "full_stack": {
        "name": "Full Stack Analysis",
        "description": "Analisi completa per applicazioni full stack",
        "enabled_rules": {
            "code": ["no_omissions", "maintain_style", "practical_improvements"],
            "data": ["complete_analysis", "show_insights"],
            "api": ["security_check", "performance_check"]
        }
    },
    "data_pipeline": {
        "name": "Data Pipeline",
        "description": "Analisi focalizzata sul processing dati",
        "enabled_rules": {
            "data": ["complete_analysis", "show_insights", "statistical_relevance"],
            "json": ["complete_processing", "show_transformations"],
            "config": ["validation_check", "security_check"]
        }
    }
}

# Sistema di prompt migliorato
SYSTEM_PROMPTS = {
    "conversational": """Mantieni una conversazione naturale e contestuale.
    - Rispondi in modo appropriato al contesto
    - Usa un tono colloquiale quando appropriato
    - Evita analisi tecniche non richieste
    - Mantieni il flusso della conversazione""",
    
    "general": "Analizza il contenuto fornendo una risposta dettagliata e utile.",
    
    "code_analysis": """Analizza il codice considerando:
    1. Struttura e organizzazione del codice
    2. Potenziali problemi di sicurezza ({security_concerns})
    3. Performance e ottimizzazioni ({performance_tips})
    4. Best practices per {language}
    5. Suggerimenti per migliorare la manutenibilità
    6. Analisi della complessità ciclomatica
    7. Identificazione di design pattern utilizzati
    
    Se sono presenti più file, analizza anche:
    1. Dipendenze tra i file
    2. Coerenza dello stile di codifica
    3. Possibili problemi di integrazione
    4. Suggerimenti per una migliore organizzazione""",
    
    "code_explanation": """Spiega il codice evidenziando:
    1. Funzionamento generale e scopo
    2. Flusso di esecuzione
    3. Pattern e tecniche utilizzate
    4. Punti chiave e decisioni implementative
    5. Strutture dati e algoritmi utilizzati
    
    Se il codice è parte di un progetto più ampio:
    1. Relazioni con altri componenti
    2. Ruolo nel contesto generale
    3. Interazioni con altre parti del sistema""",
    
    "data_analysis": """Analizza i dati considerando:
    1. Struttura e formato dei dati
    2. Statistiche descrittive chiave
    3. Pattern e tendenze evidenti
    4. Anomalie o outliers
    5. Correlazioni tra campi
    6. Qualità e completezza dei dati
    
    Se sono presenti più file:
    1. Relazioni tra i dataset
    2. Coerenza dei dati
    3. Possibili integrazioni
    4. Suggerimenti per ottimizzazione""",
}

# Configurazione modelli aggiornata
MODELS_CONFIG = {
    "claude-3-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "model_id": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 0.95,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "conversation_mode": True
    },
    "gpt-4": {
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "model_id": "gpt-4-0125-preview",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 0.95,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "conversation_mode": True
    },
    "deepseek-chat": {
        "name": "DeepSeek Chat",
        "provider": "deepseek",
        "model_id": "deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 0.95,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "conversation_mode": True
    }
}

def determine_content_type(content: str, context: Optional[Dict] = None) -> str:
    """Determina il tipo di contenuto in modo più accurato"""
    # Check per conversazione
    if _is_conversational(content):
        return 'conversation'
    
    # Check per codice
    if contains_code(content):
        return 'code'
    
    # Check per dati strutturati
    if _contains_structured_data(content):
        return 'data'
    
    # Check basato sul contesto
    if context:
        if 'file_type' in context:
            return _map_file_type_to_content_type(context['file_type'])
        if 'available_files' in context:
            return _determine_type_from_files(context['available_files'])
    
    return 'general'

def _is_conversational(content: str) -> bool:
    """Determina se il contenuto è una conversazione normale"""
    # Pattern tipici di conversazione
    conversation_patterns = [
        r'\b(ciao|salve|hey|hi)\b',
        r'\?$',
        r'\b(grazie|prego|per favore)\b',
        r'^(come|cosa|quando|dove|perché|chi)\b'
    ]
    
    content_lower = content.lower()
    
    # Check lunghezza e pattern
    if len(content.split()) < 15:  # Messaggi brevi
        for pattern in conversation_patterns:
            if re.search(pattern, content_lower):
                return True
    
    # Check tecnicismi
    technical_indicators = [
        r'\b(function|class|def|var|let|const)\b',
        r'```',
        r'\b(analizza|ottimizza|debug)\b'
    ]
    
    for indicator in technical_indicators:
        if re.search(indicator, content_lower):
            return False
    
    return True

def contains_code(content: str) -> bool:
    """Verifica se il contenuto contiene codice"""
    code_patterns = [
        # Blocchi di codice
        r'```[\w]*\n[\s\S]*?\n```',
        
        # Dichiarazioni comuni
        r'\b(function|class|def|var|let|const)\b\s+\w+',
        
        # Import/require
        r'\b(import|require|from)\b\s+[\w\s,{}]+',
        
        # Sintassi comune
        r'[\w\s]*\([^\)]*\)\s*{',
        r'=>',
        r'\b(if|for|while|switch)\b\s*\(',
        
        # Tags HTML/XML
        r'<[\w\s="\']*>.*?</[\w\s]*>',
        
        # Indentazione significativa
        r'^\s{2,}[\w]+'
    ]
    
    for pattern in code_patterns:
        if re.search(pattern, content, re.MULTILINE):
            return True
    
    return False

def _contains_structured_data(content: str) -> bool:
    """Verifica se il contenuto contiene dati strutturati"""
    data_patterns = [
        # JSON-like
        r'{[\s\S]*".*?"[\s\S]*}',
        r'\[[\s\S]*{.*?}[\s\S]*\]',
        
        # CSV-like
        r'(?:\w+,){2,}\w+(?:\n|$)',
        
        # YAML-like
        r'^\w+:\s*\n(?:\s{2,}-\s+.*\n)+',
        
        # Tabular data
        r'\|\s*[\w\s]+\s*\|.*\|'
    ]
    
    for pattern in data_patterns:
        if re.search(pattern, content, re.MULTILINE):
            return True
    
    return False

def _map_file_type_to_content_type(file_type: str) -> str:
    """Mappa il tipo di file al tipo di contenuto"""
    mappings = {
        'py': 'code',
        'js': 'code',
        'ts': 'code',
        'java': 'code',
        'cpp': 'code',
        'json': 'data',
        'csv': 'data',
        'yaml': 'data',
        'yml': 'data',
        'xml': 'data'
    }
    return mappings.get(file_type.lower(), 'general')

def _determine_type_from_files(files: List[Dict]) -> str:
    """Determina il tipo di contenuto dai file disponibili"""
    for file in files:
        ext = Path(file.get('name', '')).suffix.lower().lstrip('.')
        content_type = _map_file_type_to_content_type(ext)
        if content_type != 'general':
            return content_type
    return 'general'

def get_active_rules(content_type: str, preset: Optional[str] = None) -> Set[str]:
    """Ottiene le regole attive per il tipo di contenuto e preset"""
    # Ottieni regole obbligatorie
    mandatory_rules = set(ANALYSIS_RULES.get(content_type, {}).get("mandatory", []))
    
    # Aggiungi regole dal preset se specificato
    if preset and preset in RULE_PRESETS:
        preset_rules = set()
        for rule_type, rules in RULE_PRESETS[preset]["enabled_rules"].items():
            if rule_type == content_type:
                preset_rules.update(rules)
        return mandatory_rules.union(preset_rules)
    
    # Usa regole default
    default_rules = set(ANALYSIS_RULES.get(content_type, {}).get("default", []))
    return mandatory_rules.union(default_rules)

def select_system_prompt(context: Dict) -> str:
    """Seleziona e personalizza il prompt di sistema appropriato"""
    content_type = determine_content_type(
        context.get('content', ''),
        context
    )
    
    if content_type == 'conversation':
        return SYSTEM_PROMPTS['conversational']
    
    prompt_type = context.get('type', 'general')
    base_prompt = SYSTEM_PROMPTS.get(prompt_type, SYSTEM_PROMPTS['general'])
    
    # Personalizza per codice
    if content_type == 'code' and "available_files" in context:
        language = None
        for file in context["available_files"]:
            ext = Path(file["name"]).suffix.lower()
            if ext in {'.py': 'Python', '.js': 'JavaScript', '.html': 'HTML',
                      '.css': 'CSS', '.cpp': 'C++', '.java': 'Java'}.keys():
                language = {'.py': 'Python', '.js': 'JavaScript', '.html': 'HTML',
                          '.css': 'CSS', '.cpp': 'C++', '.java': 'Java'}[ext]
                break
        
        if language:
            base_prompt = base_prompt.format(
                language=language,
                security_concerns=get_security_concerns(language),
                performance_tips=get_performance_tips(language)
            )
    
    return base_prompt

def get_security_concerns(language: str) -> str:
    """Restituisce problemi di sicurezza specifici per linguaggio"""
    concerns = {
        'Python': 'injection SQL, deserializzazione non sicura, gestione input non sanitizzato',
        'JavaScript': 'XSS, CSRF, injection DOM, gestione incorretta async',
        'HTML': 'XSS, CSRF, clickjacking, content security policy',
        'CSS': 'information disclosure, CSS injection','C++': 'buffer overflow, memory leaks, integer overflow',
        'Java': 'serializzazione non sicura, SSRF, path traversal'
    }
    return concerns.get(language, 'problemi comuni di sicurezza')

def get_performance_tips(language: str) -> str:
    """Restituisce suggerimenti performance specifici per linguaggio"""
    tips = {
        'Python': 'uso generator, ottimizzazione loop, gestione memoria',
        'JavaScript': 'debouncing, throttling, ottimizzazione DOM',
        'HTML': 'lazy loading, ottimizzazione rendering',
        'CSS': 'ottimizzazione selettori, performance animazioni',
        'C++': 'ottimizzazione memoria, uso reference, move semantics',
        'Java': 'garbage collection, thread pooling, caching'
    }
    return tips.get(language, 'ottimizzazioni generali')

def merge_rule_sets(rule_sets: List[str]) -> Set[str]:
    """Unisce più set di regole mantenendo le regole obbligatorie"""
    merged_rules = set()
    for rule_set in rule_sets:
        if rule_set in ANALYSIS_RULES:
            # Aggiungi regole obbligatorie
            merged_rules.update(ANALYSIS_RULES[rule_set].get("mandatory", []))
            # Aggiungi regole default
            merged_rules.update(ANALYSIS_RULES[rule_set].get("default", []))
    return merged_rules

def suggest_rules(context: dict) -> List[str]:
    """Suggerisce regole basate sul contesto"""
    suggested_rules = []
    
    # Analizza input utente
    if 'user_input' in context:
        content_type = determine_content_type(context['user_input'], context)
        if content_type == 'conversation':
            suggested_rules.append('conversation')
        elif content_type == 'code':
            suggested_rules.append('code')
        elif content_type == 'data':
            suggested_rules.append('data')
    
    # Analizza file disponibili
    if "available_files" in context:
        extensions = [Path(f["name"]).suffix.lower() for f in context["available_files"]]
        
        # Regole per codice
        if any(ext in {'.py', '.js', '.html', '.css', '.cpp', '.java'} for ext in extensions):
            if 'code' not in suggested_rules:
                suggested_rules.append("code")
        
        # Regole per dati
        if any(ext in {'.json', '.csv', '.yaml', '.yml'} for ext in extensions):
            if 'data' not in suggested_rules:
                suggested_rules.append("data")
        
        # Regole per configurazione
        if any(ext in {'.yml', '.yaml', '.conf', '.ini', '.env'} for ext in extensions):
            suggested_rules.append("config")
    
    return suggested_rules

def build_interaction_prompt(context: Dict[str, Any]) -> str:
    """Costruisce un prompt di interazione ottimizzato"""
    content_type = determine_content_type(
        context.get('content', ''),
        context
    )
    
    prompt_sections = []
    
    # Base prompt
    if content_type == 'conversation':
        prompt_sections.append(SYSTEM_PROMPTS['conversational'])
    else:
        prompt_sections.append(select_system_prompt(context))
    
    # Regole attive
    active_rules = context.get('active_rules', set())
    if active_rules:
        prompt_sections.append("\nRegole attive:")
        for rule_type in ANALYSIS_RULES:
            type_rules = active_rules.intersection(ANALYSIS_RULES[rule_type]['default'])
            if type_rules:
                for rule in type_rules:
                    description = ANALYSIS_RULES[rule_type]['description'].get(rule)
                    if description:
                        prompt_sections.append(f"- {description}")
    
    # Contesto file
    if 'available_files' in context and context['available_files']:
        prompt_sections.append("\nFile disponibili:")
        for file in context['available_files']:
            prompt_sections.append(f"- {file['name']} ({file.get('language', 'unknown')})")
    
    # Struttura progetto
    if 'project_structure' in context and context['project_structure']:
        prompt_sections.append("\nStruttura progetto:")
        for path, files in context['project_structure'].items():
            if path:
                prompt_sections.append(f"\n📁 {path}/")
            for file in files:
                prompt_sections.append(f"  └─ {file.get('name', 'Unknown file')}")
    
    # Memoria conversazione
    if 'conversation_history' in context:
        prompt_sections.append("\nContesto conversazione:")
        for message in context['conversation_history'][-3:]:  # Ultimi 3 messaggi
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            prompt_sections.append(f"{role}: {content}")
    
    return "\n".join(prompt_sections)

def get_model_specific_prompt(model_name: str, content_type: str, context: Dict[str, Any] = None) -> str:
    """Ottiene un prompt specifico per il modello e tipo di contenuto"""
    if not context:
        context = {}
    
    # Verifica se il modello supporta la modalità conversazione
    model_config = MODELS_CONFIG.get(model_name, {})
    if model_config.get('conversation_mode') and content_type == 'conversation':
        return SYSTEM_PROMPTS['conversational']
    
    # Costruisci prompt completo
    return build_interaction_prompt(
        {**context, 'content_type': content_type}
    )

def get_model_defaults(model_id: str) -> Dict[str, Any]:
    """Restituisce le configurazioni di default per un modello"""
    return MODELS_CONFIG.get(model_id, MODELS_CONFIG["claude-3-sonnet"])

# Funzioni di utilità per la gestione dei prompt
def sanitize_prompt(prompt: str) -> str:
    """Sanitizza il prompt rimuovendo caratteri problematici"""
    # Rimuovi caratteri di controllo
    prompt = ''.join(char for char in prompt if ord(char) >= 32)
    # Normalizza spazi
    prompt = ' '.join(prompt.split())
    return prompt.strip()

def truncate_prompt(prompt: str, max_length: int = 4000) -> str:
    """Tronca il prompt mantenendo la coerenza"""
    if len(prompt) <= max_length:
        return prompt
    
    # Trova un punto di interruzione sicuro
    safe_end = prompt.rfind('\n', 0, max_length)
    if safe_end == -1:
        safe_end = prompt.rfind('. ', 0, max_length)
    if safe_end == -1:
        safe_end = prompt.rfind(' ', 0, max_length)
    if safe_end == -1:
        safe_end = max_length
    
    return prompt[:safe_end] + "\n[Testo troncato per lunghezza]"

def format_code_prompt(prompt: str) -> str:
    """Formatta un prompt contenente codice"""
    if not contains_code(prompt):
        return prompt
    
    # Assicura che i blocchi di codice siano ben formattati
    lines = prompt.split('\n')
    formatted_lines = []
    in_code_block = False
    
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            formatted_lines.append(line)
        elif in_code_block:
            # Preserva l'indentazione nel codice
            formatted_lines.append(line)
        else:
            # Normalizza il testo fuori dai blocchi di codice
            formatted_lines.append(line.strip())
    
    return '\n'.join(formatted_lines)

# Export delle funzioni principali
__all__ = [
    'MODELS_CONFIG',
    'ANALYSIS_RULES',
    'RULE_PRESETS',
    'SYSTEM_PROMPTS',
    'determine_content_type',
    'contains_code',
    'get_active_rules',
    'merge_rule_sets',
    'suggest_rules',
    'select_system_prompt',
    'get_security_concerns',
    'get_performance_tips',
    'get_model_defaults',
    'get_model_specific_prompt',
    'build_interaction_prompt',
    'sanitize_prompt',
    'truncate_prompt',
    'format_code_prompt'
]