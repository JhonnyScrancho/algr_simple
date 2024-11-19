import streamlit as st
from pygments import highlight
from pygments.formatters import get_formatter_by_name
from pygments.lexers import get_lexer_by_name, Python3Lexer
from config.settings import APP_CONFIG

def format_code(code: str, language: str = "python") -> str:
    """Formatta il codice per la visualizzazione"""
    try:
        # Se il codice è vuoto, ritorna stringa vuota
        if not code:
            return ""
        
        # Se non viene specificato il linguaggio, usa Python come default
        if not language:
            language = "python"
        
        # Rimuovi spazi extra all'inizio e alla fine
        code = code.strip()
        
        # Formattazione base per migliorare leggibilità
        lines = code.split('\n')
        formatted_lines = []
        current_indent = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Gestione indentazione
            if stripped.startswith(('class ', 'def ', 'if ', 'for ', 'while ')):
                formatted_lines.append('    ' * current_indent + stripped)
                current_indent += 1
            elif stripped.startswith(('return', 'break', 'continue', 'pass')):
                current_indent = max(0, current_indent - 1)
                formatted_lines.append('    ' * current_indent + stripped)
            else:
                formatted_lines.append('    ' * current_indent + stripped)
        
        return '\n'.join(formatted_lines)
        
    except Exception as e:
        st.error(f"Error formatting code: {str(e)}")
        return code

def get_code_segments(code: str) -> dict:
    """Estrae segmenti significativi del codice"""
    try:
        segments = {
            'imports': [],
            'classes': [],
            'functions': [],
            'main_code': []
        }
        
        lines = code.split('\n')
        current_segment = 'main_code'
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith(('import ', 'from ')):
                segments['imports'].append(line)
            elif stripped.startswith('class '):
                segments['classes'].append(line)
            elif stripped.startswith('def '):
                segments['functions'].append(line)
            else:
                segments[current_segment].append(line)
                
        return segments
        
    except Exception as e:
        st.error(f"Error segmenting code: {str(e)}")
        return {}