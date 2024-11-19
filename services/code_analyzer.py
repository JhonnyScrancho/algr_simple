import streamlit as st
import ast
import re
import difflib
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AnalysisResult:
    """Struttura dati per risultati analisi"""
    stats: Dict[str, Any]
    complexity: Dict[str, int]
    issues: List[str]
    suggestions: List[str]
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    imports: List[str]
    dependencies: List[str]
    version_changes: Optional[Dict[str, Any]] = None

class CodeAnalyzer:
    def __init__(self):
        self.previous_analyses = {}
        
    def analyze_code(self, code: str, file_info: Optional[Dict] = None, active_rules: Set[str] = None) -> AnalysisResult:
        """Analizza il codice fornendo risultati dettagliati"""
        try:
            # Inizializza risultato
            result = AnalysisResult(
                stats=self._get_code_stats(code),
                complexity=self._analyze_complexity(code),
                issues=[],
                suggestions=[],
                functions=[],
                classes=[],
                imports=[],
                dependencies=[]
            )
            
            # Analisi AST se il codice è Python
            try:
                tree = ast.parse(code)
                ast_analysis = self._analyze_ast(tree, active_rules)
                result.functions = ast_analysis['functions']
                result.classes = ast_analysis['classes']
                result.imports = ast_analysis['imports']
                result.dependencies = ast_analysis['dependencies']
                
                # Aggiungi issues e suggestions dall'analisi AST
                result.issues.extend(ast_analysis.get('issues', []))
                result.suggestions.extend(ast_analysis.get('suggestions', []))
            except SyntaxError:
                result.issues.append("Il codice contiene errori di sintassi")
            except Exception as e:
                result.issues.append(f"Errore nell'analisi AST: {str(e)}")
            
            # Analisi stile e pattern
            style_issues = self._analyze_style(code)
            result.issues.extend(style_issues)
            
            # Pattern e best practices
            pattern_analysis = self._analyze_patterns(code)
            result.issues.extend(pattern_analysis['issues'])
            result.suggestions.extend(pattern_analysis['suggestions'])
            
            # Analisi sicurezza
            security_issues = self._analyze_security(code, file_info)
            result.issues.extend(security_issues)
            
            # Analisi incrementale se disponibile versione precedente
            if file_info and 'name' in file_info:
                prev_analysis = self.previous_analyses.get(file_info['name'])
                if prev_analysis:
                    version_changes = self._analyze_changes(code, prev_analysis, file_info)
                    result.version_changes = version_changes
            
            # Salva analisi corrente
            if file_info and 'name' in file_info:
                self.previous_analyses[file_info['name']] = {
                    'code': code,
                    'analysis': result
                }
            
            return result
            
        except Exception as e:
            st.error(f"Errore durante l'analisi del codice: {str(e)}")
            return AnalysisResult(
                stats={},
                complexity={'cognitive_load': 0, 'nesting_depth': 0},
                issues=["Errore durante l'analisi"],
                suggestions=[],
                functions=[],
                classes=[],
                imports=[],
                dependencies=[]
            )
    
    def _get_code_stats(self, code: str) -> Dict[str, Any]:
        """Calcola statistiche dettagliate del codice"""
        lines = code.split('\n')
        stats = {
            "total_lines": len(lines),
            "empty_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "docstring_lines": 0,
            "avg_line_length": 0,
            "max_line_length": 0,
            "imports_count": 0,
            "classes_count": 0,
            "functions_count": 0
        }
        
        total_length = 0
        in_docstring = False
        docstring_quotes = 0
        
        for line in lines:
            stripped = line.strip()
            length = len(line)
            
            # Aggiorna lunghezze
            if length > 0:
                total_length += length
                stats["max_line_length"] = max(stats["max_line_length"], length)
            
            # Conta docstring
            if '"""' in line or "'''" in line:
                docstring_quotes += line.count('"""') + line.count("'''")
                in_docstring = docstring_quotes % 2 != 0
                if not stripped[3:].strip():  # Solo quotes
                    continue
            
            # Classifica linea
            if not stripped:
                stats["empty_lines"] += 1
            elif in_docstring:
                stats["docstring_lines"] += 1
            elif stripped.startswith('#'):
                stats["comment_lines"] += 1
            else:
                stats["code_lines"] += 1
                # Conta elementi base
                if stripped.startswith('import ') or stripped.startswith('from '):
                    stats["imports_count"] += 1
                elif stripped.startswith('class '):
                    stats["classes_count"] += 1
                elif stripped.startswith('def '):
                    stats["functions_count"] += 1
        
        # Calcola media
        non_empty_lines = stats["total_lines"] - stats["empty_lines"]
        if non_empty_lines > 0:
            stats["avg_line_length"] = total_length / non_empty_lines
        
        return stats
    
    def _analyze_complexity(self, code: str) -> Dict[str, int]:
        """Analizza la complessità del codice"""
        try:
            tree = ast.parse(code)
        except:
            return {"cognitive_load": 0, "nesting_depth": 0, "branches": 0}
        
        complexity = {
            "cognitive_load": 0,
            "nesting_depth": 0,
            "branches": 0,
            "max_method_complexity": 0,
            "total_complexity": 0
        }
        
        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_depth = 0
                self.max_depth = 0
                self.branches = 0
                self.cognitive_load = 0
                
            def visit_FunctionDef(self, node):
                self.cognitive_load += 1
                self.generic_visit(node)
                
            def visit_ClassDef(self, node):
                self.cognitive_load += 1
                self.generic_visit(node)
                
            def visit_If(self, node):
                self.branches += 1
                self.cognitive_load += 1
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
                
            def visit_For(self, node):
                self.branches += 1
                self.cognitive_load += 2
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
                
            def visit_While(self, node):
                self.branches += 1
                self.cognitive_load += 2
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
                
            def visit_Try(self, node):
                self.branches += len(node.handlers) + 1
                self.cognitive_load += 1
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
        
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        
        complexity["cognitive_load"] = visitor.cognitive_load
        complexity["nesting_depth"] = visitor.max_depth
        complexity["branches"] = visitor.branches
        complexity["total_complexity"] = (
            visitor.cognitive_load +
            visitor.max_depth * 2 +
            visitor.branches
        )
        
        return complexity
    
    def _analyze_ast(self, tree: ast.AST, active_rules: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Analisi dettagliata basata su AST"""
        analysis = {
            "functions": [],
            "classes": [],
            "imports": [],
            "dependencies": [],
            "issues": [],
            "suggestions": []
        }
        
        class ASTAnalyzer(ast.NodeVisitor):
            def __init__(self, analysis_dict, active_rules):
                self.analysis = analysis_dict
                self.active_rules = active_rules or set()
                self.current_class = None
                self.current_function = None
                self.local_names = set()
                self.undefined_names = set()
                
            def visit_FunctionDef(self, node):
                func_analysis = {
                    "name": node.name,
                    "args": len(node.args.args),
                    "kwargs": len(node.args.kwonlyargs),
                    "defaults": len(node.args.defaults),
                    "has_varargs": node.args.vararg is not None,
                    "has_kwargs": node.args.kwarg is not None,
                    "docstring": ast.get_docstring(node),
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "returns": self._get_return_annotation(node),
                    "complexity": self._analyze_function_complexity(node),
                    "calls": [],
                    "attributes": [],
                    "local_vars": []
                }
                
                # Analisi di qualità
                if not func_analysis["docstring"] and "maintain_style" in self.active_rules:
                    self.analysis["issues"].append(
                        f"Function {node.name} missing docstring"
                    )
                
                if func_analysis["args"] > 5 and "practical_improvements" in self.active_rules:
                    self.analysis["suggestions"].append(
                        f"Consider reducing number of arguments in {node.name}"
                    )
                
                prev_function = self.current_function
                self.current_function = func_analysis
                self.local_names = set()
                
                self.generic_visit(node)
                
                func_analysis["local_vars"] = list(self.local_names)
                self.analysis["functions"].append(func_analysis)
                self.current_function = prev_function
            
            def visit_ClassDef(self, node):
                class_analysis = {
                    "name": node.name,
                    "bases": [self._get_name(b) for b in node.bases],
                    "docstring": ast.get_docstring(node),
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "methods": [],
                    "attributes": []
                }
                
                if not class_analysis["docstring"] and "maintain_style" in self.active_rules:
                    self.analysis["issues"].append(
                        f"Class {node.name} missing docstring"
                    )
                
                prev_class = self.current_class
                self.current_class = class_analysis
                
                self.generic_visit(node)
                
                self.analysis["classes"].append(class_analysis)
                self.current_class = prev_class
            
            def visit_Import(self, node):
                for name in node.names:
                    self.analysis["imports"].append(name.name)
                    if name.asname:
                        self.local_names.add(name.asname)
                    else:
                        self.local_names.add(name.name.split('.')[0])
            
            def visit_ImportFrom(self, node):
                module = node.module if node.module else ''
                for name in node.names:
                    full_name = f"{module}.{name.name}" if module else name.name
                    self.analysis["imports"].append(full_name)
                    if name.asname:
                        self.local_names.add(name.asname)
                    else:
                        self.local_names.add(name.name)
            
            def visit_Call(self, node):
                call_name = self._get_call_name(node)
                if call_name and self.current_function:
                    self.current_function["calls"].append(call_name)
                self.generic_visit(node)
            
            def visit_Attribute(self, node):
                attr_name = self._get_attribute_name(node)
                if attr_name:
                    if self.current_class:
                        self.current_class["attributes"].append(attr_name)
                    elif self.current_function:
                        self.current_function["attributes"].append(attr_name)
                self.generic_visit(node)
            
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    self.local_names.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    if node.id not in self.local_names and node.id not in {'self', 'cls'}:
                        self.undefined_names.add(node.id)
                self.generic_visit(node)
            
            def _get_decorator_name(self, node):
                if isinstance(node, ast.Name):
                    return node.id
                elif isinstance(node, ast.Call):
                    return self._get_call_name(node)
                elif isinstance(node, ast.Attribute):
                    return self._get_attribute_name(node)
                return "unknown_decorator"
            
            def _get_return_annotation(self, node):
                if node.returns:
                    return ast.unparse(node.returns)
                return None
            
            def _analyze_function_complexity(self, node):
                visitor = ComplexityVisitor()
                visitor.visit(node)
                return {
                    "cognitive_load": visitor.cognitive_load,
                    "nesting_depth": visitor.max_depth,
                    "branches": visitor.branches
                }
            
            def _get_call_name(self, node):
                if isinstance(node.func, ast.Name):
                    return node.func.id
                elif isinstance(node.func, ast.Attribute):
                    return self._get_attribute_name(node.func)
                return None
            
            def _get_attribute_name(self, node):
                parts = []
                current = node
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                return '.'.join(reversed(parts))
            
            def _get_name(self, node):
                if isinstance(node, ast.Name):
                    return node.id
                elif isinstance(node, ast.Attribute):
                    return self._get_attribute_name(node)
                return "unknown"
        
        analyzer = ASTAnalyzer(analysis, active_rules)
        analyzer.visit(tree)
        
        # Analisi dipendenze
        analysis["dependencies"] = self._analyze_dependencies(analysis["imports"])
        
        return analysis
    
    def _analyze_style(self, code: str) -> List[str]:
        """Analizza lo stile del codice"""
        issues = []
        lines = code.split('\n')
        
        # Check indentazione
        indent_sizes = set()
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indent_sizes.add(indent)
        
        if len(indent_sizes) > 1:
            issues.append(f"Indentazione inconsistente: trovate dimensioni {indent_sizes}")
        
        # Check lunghezza linee
        for i, line in enumerate(lines, 1):
            if len(line) > 79:  # PEP 8
                issues.append(f"Linea {i} troppo lunga ({len(line)} caratteri)")
        
        # Check naming conventions
        names = re.findall(r'\b(?:def|class)\s+(\w+)', code)
        
        snake_case = sum(1 for n in names if re.match(r'^[a-z_][a-z0-9_]*$', n))
        camel_case = sum(1 for n in names if re.match(r'^[A-Z][a-zA-Z0-9]*$', n))
        
        if snake_case and camel_case:
            issues.append("Mixing di convenzioni di naming (snake_case e CamelCase)")
        
        # Check spazi attorno agli operatori
        operator_regex = r'[^=!<>]=[^=]|[+\-*/<>]=?'
        for i, line in enumerate(lines, 1):
            for match in re.finditer(operator_regex, line):
                op = match.group()
                if not (op.startswith(' ') and op.endswith(' ')):
                    issues.append(f"Linea {i}: spazi mancanti attorno all'operatore '{op.strip()}'")
        
        return issues
    
    def _analyze_patterns(self, code: str) -> Dict[str, List[str]]:
        """Analizza pattern e suggerisce miglioramenti"""
        analysis = {
            "issues": [],
            "suggestions": []
        }
        
        # Check per anti-patterns comuni
        patterns = {
            r'except:\s*pass': (
                "issues",
                "Bare except clause con pass trovata - gestire le eccezioni specifiche"
            ),
            r'except Exception as e:\s*pass': (
                "issues",
                "Eccezione generale catturata e ignorata"
            ),
            r'while True:.*break': (
                "suggestions",
                "Consider replacing 'while True' with a more explicit condition"
            ),
            r'global\s+\w+': (
                "suggestions",
                "Uso di variabili globali - considerare refactoring per miglior design"
            ),
            r'print\s*\(': (
                "suggestions",
                "Uso di print statements - considerare logging per codice di produzione"
            ),
            r'\[i\s+for\s+i\s+in': (
                "suggestions",
                "List comprehension poco chiara - considerare nomi più descrittivi"
            ),
            r'\.sort\(.*lambda': (
                "suggestions",
                "Uso di lambda in sort - considerare operator.itemgetter o methodcaller"
            ),
        }
        
        for pattern, (category, message) in patterns.items():
            if re.search(pattern, code):
                analysis[category].append(message)
        
        # Check per pattern di performance
        performance_patterns = {
            r'\+\s*str\(': (
                "String concatenation inefficiente - usare join() o f-strings"
            ),
            r'range\(len\(': (
                "Uso di range(len()) - considerare enumerate()"
            ),
            r'\[.*\]\s*\*\s*\d+': (
                "List multiplication può essere inefficiente per grandi liste"
            ),
            r'dict\(\[\(.*\)\]\)': (
                "Creazione dict inefficiente - usare dict comprehension"
            )
        }
        
        for pattern, message in performance_patterns.items():
            if re.search(pattern, code):
                analysis["suggestions"].append(message)
        
        return analysis
    
    def _analyze_security(self, code: str, file_info: Optional[Dict]) -> List[str]:
        """Analizza potenziali problemi di sicurezza"""
        issues = []
        
        # Determina il tipo di file
        file_type = "unknown"
        if file_info and 'name' in file_info:
            ext = Path(file_info['name']).suffix.lower()
            if ext == '.py':
                file_type = "python"
            elif ext in {'.js', '.ts'}:
                file_type = "javascript"
            elif ext == '.html':
                file_type = "html"
        
        # Pattern di sicurezza per tipo di file
        security_patterns = {
            "python": {
                r'eval\s*\(': "Uso di eval() - rischio di code injection",
                r'exec\s*\(': "Uso di exec() - rischio di code injection",
                r'subprocess\.': "Uso di subprocess - verificare input sanitization",
                r'input\s*\(': "Uso di input() - verificare input validation",
                r'os\.system\s*\(': "Uso di os.system() - rischio di command injection",
                r'pickle\.': "Uso di pickle - rischio deserializzazione non sicura",
                r'yaml\.load\s*\(': "Uso di yaml.load() - usare yaml.safe_load()",
                r'\.raw_input\s*\(': "Uso di raw_input() - verificare input validation"
            },
            "javascript": {
                r'eval\s*\(': "Uso di eval() - rischio di code injection",
                r'innerHTML': "Uso di innerHTML - rischio XSS",
                r'document\.write\s*\(': "Uso di document.write() - rischio XSS",
                r'localStorage\.': "Uso di localStorage - verificare dati sensibili",
                r'new\s+Function\s*\(': "Uso di new Function() - rischio code injection"
            },
            "html": {
                r'on\w+\s*=': "Event handler inline - rischio XSS",
                r'javascript:': "JavaScript URI - rischio XSS",
                r'<script\s+src=([\'"])(?!https:)': "Script non HTTPS - rischio MITM"
            }
        }
        
        # Controlla pattern specifici per tipo di file
        if file_type in security_patterns:
            for pattern, message in security_patterns[file_type].items():
                if re.search(pattern, code):
                    issues.append(message)
        
        # Pattern generici di sicurezza
        generic_patterns = {
            r'password\s*=': "Password in chiaro nel codice",
            r'api_key\s*=': "API key in chiaro nel codice",
            r'secret\s*=': "Secret in chiaro nel codice",
            r'token\s*=': "Token in chiaro nel codice"
        }
        
        for pattern, message in generic_patterns.items():
            if re.search(pattern, code):
                issues.append(message)
        
        return issues
    
    def _analyze_changes(self, current_code: str, previous: Dict, file_info: Dict) -> Dict[str, Any]:
        """Analizza cambiamenti tra versioni del codice"""
        changes = {
            "lines_added": 0,
            "lines_removed": 0,
            "lines_modified": 0,
            "complexity_delta": 0,
            "significant_changes": [],
            "breaking_changes": [],
            "diff_summary": []
        }
        
        # Confronto linee
        current_lines = current_code.splitlines()
        previous_lines = previous['code'].splitlines()
        
        differ = difflib.Differ()
        diff = list(differ.compare(previous_lines, current_lines))
        
        for line in diff:
            if line.startswith('+ '):
                changes["lines_added"] += 1
            elif line.startswith('- '):
                changes["lines_removed"] += 1
            elif line.startswith('? '):
                changes["lines_modified"] += 1
        
        # Analisi complessità
        try:
            current_complexity = self._analyze_complexity(current_code)
            previous_complexity = previous['analysis'].complexity
            
            complexity_delta = (
                current_complexity['cognitive_load'] - 
                previous_complexity['cognitive_load']
            )
            changes["complexity_delta"] = complexity_delta
            
            if abs(complexity_delta) > 5:
                changes["significant_changes"].append(
                    f"Significativo cambio di complessità: {complexity_delta}"
                )
        except Exception as e:
            changes["significant_changes"].append(
                f"Errore nell'analisi della complessità: {str(e)}"
            )
        
        # Analisi funzioni e classi
        try:
            current_tree = ast.parse(current_code)
            previous_tree = ast.parse(previous['code'])
            
            current_funcs = {
                node.name: node 
                for node in ast.walk(current_tree) 
                if isinstance(node, ast.FunctionDef)
            }
            previous_funcs = {
                node.name: node 
                for node in ast.walk(previous_tree) 
                if isinstance(node, ast.FunctionDef)
            }
            
            # Check funzioni rimosse/modificate
            for name, node in previous_funcs.items():
                if name not in current_funcs:
                    changes["breaking_changes"].append(f"Funzione rimossa: {name}")
                else:
                    # Confronta signature
                    prev_args = len(node.args.args)
                    curr_args = len(current_funcs[name].args.args)
                    if prev_args != curr_args:
                        changes["breaking_changes"].append(
                            f"Signature cambiata per {name}: "
                            f"da {prev_args} a {curr_args} argomenti"
                        )
            
            # Check nuove funzioni
            for name in current_funcs:
                if name not in previous_funcs:
                    changes["significant_changes"].append(f"Nuova funzione: {name}")
        
        except Exception as e:
            changes["significant_changes"].append(
                f"Errore nell'analisi delle funzioni: {str(e)}"
            )
        
        # Genera riassunto diff
        changes["diff_summary"] = self._generate_diff_summary(diff)
        
        return changes
    
    def _analyze_dependencies(self, imports: List[str]) -> List[str]:
        """Analizza e classifica le dipendenze"""
        dependencies = []
        standard_lib = {
            'os', 'sys', 're', 'math', 'datetime', 'collections', 'json',
            'random', 'time', 'pathlib', 'typing', 'abc', 'logging'
        }
        
        for imp in imports:
            base_module = imp.split('.')[0]
            if base_module not in standard_lib:
                dependencies.append(imp)
        
        return dependencies
    
    def _generate_diff_summary(self, diff: List[str]) -> List[str]:
        """Genera un riassunto delle modifiche"""
        summary = []
        current_block = []
        
        for line in diff:
            if line.startswith('? '):
                continue
                
            if line.startswith(('+ ', '- ')):
                current_block.append(line)
            else:
                if current_block:
                    # Analizza blocco corrente
                    block_summary = self._summarize_change_block(current_block)
                    if block_summary:
                        summary.append(block_summary)
                    current_block = []
        
        # Gestisci ultimo blocco
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
        
        # Pattern comuni
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
            # Check modifiche
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
        
        # Summary generico
        if len(block) == 1:
            return f"Modificata una linea"
        return f"Modificate {len(block)} linee"

# Classe per tracciare le modifiche del codice
@dataclass
class CodeChange:
    """Rappresenta una modifica al codice"""
    type: str  # 'add', 'remove', 'modify'
    line_number: int
    original_line: Optional[str]
    new_line: Optional[str]
    description: str