import streamlit as st
import ast
from typing import List, Dict

class DocGenerator:
    def generate_docstring(self, code: str) -> str:
        """Genera documentazione per il codice Python"""
        try:
            tree = ast.parse(code)
            docs = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Raccogli informazioni sulla funzione
                    func_info = {
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'returns': self._get_return_type(node),
                        'docstring': ast.get_docstring(node) or 'No documentation available'
                    }
                    
                    # Genera docstring
                    doc = self._format_docstring(func_info)
                    docs.append(doc)
                    
            return '\n\n'.join(docs) if docs else "No functions found to document"
            
        except Exception as e:
            st.error(f"Error generating documentation: {str(e)}")
            return "Error generating documentation"
    
    def _get_return_type(self, node: ast.FunctionDef) -> str:
        """Cerca di determinare il tipo di ritorno"""
        # Controlla annotations
        if node.returns:
            return ast.unparse(node.returns)
            
        # Cerca return statements
        returns = []
        for n in ast.walk(node):
            if isinstance(n, ast.Return) and n.value:
                returns.append(n.value)
                
        if returns:
            types = set()
            for ret in returns:
                if isinstance(ret, ast.Num):
                    types.add('number')
                elif isinstance(ret, ast.Str):
                    types.add('str')
                elif isinstance(ret, ast.List):
                    types.add('list')
                elif isinstance(ret, ast.Dict):
                    types.add('dict')
            
            return ' or '.join(types) if types else 'unknown'
            
        return 'None'
    
    def _format_docstring(self, func_info: Dict) -> str:
        """Formatta la docstring in stile Google"""
        doc = [f'def {func_info["name"]}({", ".join(func_info["args"])}):\n    """']
        
        # Descrizione dalla docstring esistente
        if func_info['docstring'] != 'No documentation available':
            doc.append(f'    {func_info["docstring"]}\n')
        
        # Arguments
        if func_info['args']:
            doc.append('    Args:')
            for arg in func_info['args']:
                doc.append(f'        {arg}: Description of {arg}')
        
        # Returns
        doc.append('\n    Returns:')
        doc.append(f'        {func_info["returns"]}: Description of return value')
        
        doc.append('    """')
        return '\n'.join(doc)