# Configurazioni base dell'applicazione
APP_CONFIG = {
    # Limiti file
    "max_file_size": 5 * 1024 * 1024,  # 5MB per singolo file
    "max_total_files_size": 20 * 1024 * 1024,  # 20MB totali
    "max_files_number": 200,  # Numero massimo di file processabili
    
    # Token limits per le API
    "max_tokens_per_chunk": 4000,
    "max_total_tokens": 128000,
    
    # Configurazione regole
    "rules_config": {
        "allow_custom_rules": True,
        "max_custom_rules": 10,
        "save_rule_presets": True,
        "default_active_rules": {
            "code": ["no_omissions", "maintain_style"],
            "data": ["complete_processing", "show_insights"],
            "json": ["complete_processing", "structural_focus"]
        },
        "rules_persistence": True,  # Salva regole tra sessioni
        "allow_rule_combinations": True,  # Permette combinazioni di regole
        "max_active_rules": 15  # Numero massimo di regole attive contemporaneamente
    },
    
    # Tipi di file supportati
    "supported_file_types": [
        "py",    # Python
        "js",    # JavaScript
        "html",  # HTML
        "css",   # CSS
        "json",  # JSON
        "txt",   # Text
        "md",    # Markdown
        "yaml",  # YAML
        "yml",   # YAML
        "xml",   # XML
        "csv",   # CSV
        "ini",   # INI config
        "conf",  # Config
        "sh",    # Shell
        "bash",  # Bash
        "sql",   # SQL
        "zip"    # ZIP archives
    ],
    
    # Language mappings
    "language_mapping": {
        ".py": "python",
        ".js": "javascript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".xml": "xml",
        ".txt": "text",
        ".csv": "csv",
        ".ini": "ini",
        ".conf": "text",
        ".sh": "shell",
        ".bash": "shell",
        ".sql": "sql"
    },
    
    # UI Settings
    "ui_config": {
        "max_code_preview_lines": 50,
        "max_chat_history": 100,
        "auto_expand_code": True,
        "show_line_numbers": True,
        "show_rules_badge": True,
        "rules_badge_position": "top-right",
        "contextual_actions": True,
        "show_file_stats": True
    },
    
    # Analisi Settings
    "analysis_config": {
        "auto_suggest_rules": True,
        "analyze_imports": True,
        "analyze_dependencies": True,
        "detect_frameworks": True,
        "code_quality_checks": True,
        "security_checks": True,
        "performance_checks": True
    }
}

# Messaggi di errore standard
ERROR_MESSAGES = {
    "file_too_large": "File exceeds maximum size limit",
    "total_size_exceeded": "Total files size exceeds limit",
    "too_many_files": "Too many files uploaded",
    "unsupported_type": "File type not supported",
    "processing_error": "Error processing file",
    "invalid_zip": "Invalid ZIP file",
    "non_text_file": "Non-text file detected",
    "rules_error": {
        "too_many_rules": "Maximum number of active rules exceeded",
        "invalid_combination": "Invalid rule combination",
        "custom_rule_limit": "Maximum number of custom rules reached",
        "mandatory_rule_disabled": "Cannot disable mandatory rules"
    }
}