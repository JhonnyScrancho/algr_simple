import streamlit as st
from utils.code_formatter import format_code
from services.code_analyzer import CodeAnalyzer
import hashlib
from typing import Dict, Any

class CodeViewer:
    def __init__(self):
        self.code_analyzer = CodeAnalyzer()
        
    def _generate_unique_key(self, file_name: str, content: str, suffix: str = "") -> str:
        """Genera una chiave unica basata sul nome file e contenuto"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        base = f"{file_name}_{content_hash}".replace(".", "_").replace(" ", "_").lower()
        return f"{base}_{suffix}" if suffix else base
        
    def display_preview(self, code: str, language: str = None, file_name: str = ""):
        """Mostra una preview del codice con opzioni di analisi"""
        if not language:
            language = "python"  # default
            
        # Genera key unica per questa preview
        unique_key = self._generate_unique_key(file_name, code)
        
        # Toolbar con opzioni
        col1, col2 = st.columns(2)
        with col1:
            show_line_numbers = st.checkbox(
                "Line Numbers", 
                value=True,
                key=f"line_numbers_{unique_key}"
            )
        with col2:
            show_analysis = st.checkbox(
                "Show Analysis",
                key=f"analysis_{unique_key}"
            )
        
        # Display codice formattato
        formatted_code = format_code(code)
        st.code(formatted_code, language=language, line_numbers=show_line_numbers)
        
        # Se richiesta, mostra analisi
        if show_analysis:
            analysis = self.code_analyzer.analyze_code(code)
            
            # Stats in colonne
            cols = st.columns(3)
            with cols[0]:
                st.metric(
                    "Lines", 
                    analysis["stats"]["total_lines"],
                    key=f"stat_lines_{unique_key}"
                )
            with cols[1]:
                st.metric(
                    "Code", 
                    analysis["stats"]["code_lines"],
                    key=f"stat_code_{unique_key}"
                )
            with cols[2]:
                st.metric(
                    "Comments", 
                    analysis["stats"]["comment_lines"],
                    key=f"stat_comments_{unique_key}"
                )
            
            # Complessità in expander
            with st.expander("🔄 Complexity", key=f"complexity_{unique_key}"):
                comp_cols = st.columns(2)
                with comp_cols[0]:
                    st.metric(
                        "Cognitive Load",
                        analysis["complexity"]["cognitive_load"],
                        key=f"cognitive_{unique_key}"
                    )
                with comp_cols[1]:
                    st.metric(
                        "Nesting Depth",
                        analysis["complexity"]["nesting_depth"],
                        key=f"nesting_{unique_key}"
                    )
            
            # Issues e Suggestions
            if analysis["issues"]:
                with st.expander("⚠️ Issues", key=f"issues_{unique_key}"):
                    for idx, issue in enumerate(analysis["issues"]):
                        st.warning(issue, key=f"issue_{idx}_{unique_key}")
            
            if analysis["suggestions"]:
                with st.expander("💡 Suggestions", key=f"suggestions_{unique_key}"):
                    for idx, suggestion in enumerate(analysis["suggestions"]):
                        st.info(suggestion, key=f"suggestion_{idx}_{unique_key}")
    
    def display_code_with_analysis(self, code: str, analysis: dict = None, file_name: str = ""):
        """Mostra il codice con analisi dettagliata e rich UI"""
        # Genera key unica per questa visualizzazione
        unique_key = self._generate_unique_key(file_name, code, "detailed")
        
        # Mostra codice
        if code:
            st.code(format_code(code), line_numbers=True)
        
        if analysis:
            # Tab per differenti tipi di analisi
            tabs = st.tabs(["📊 Metrics", "🔍 Analysis", "⚠️ Issues", "💡 Suggestions"])
            
            # Tab Metrics
            with tabs[0]:
                # Statistiche base
                st.subheader("Code Statistics")
                stat_cols = st.columns(4)
                with stat_cols[0]:
                    st.metric(
                        "Total Lines",
                        analysis["stats"]["total_lines"],
                        key=f"det_total_lines_{unique_key}"
                    )
                with stat_cols[1]:
                    st.metric(
                        "Code Lines",
                        analysis["stats"]["code_lines"],
                        key=f"det_code_lines_{unique_key}"
                    )
                with stat_cols[2]:
                    st.metric(
                        "Comments",
                        analysis["stats"]["comment_lines"],
                        key=f"det_comments_{unique_key}"
                    )
                with stat_cols[3]:
                    st.metric(
                        "Avg Line Length",
                        f"{analysis['stats']['avg_line_length']:.1f}",
                        key=f"det_avg_length_{unique_key}"
                    )
            
            # Tab Analysis
            with tabs[1]:
                st.subheader("Complexity Analysis")
                comp_cols = st.columns(3)
                with comp_cols[0]:
                    st.metric(
                        "Cognitive Load",
                        analysis["complexity"]["cognitive_load"],
                        key=f"det_cognitive_{unique_key}"
                    )
                with comp_cols[1]:
                    st.metric(
                        "Max Nesting",
                        analysis["complexity"]["nesting_depth"],
                        key=f"det_nesting_{unique_key}"
                    )
                with comp_cols[2]:
                    st.metric(
                        "Branch Points",
                        analysis["complexity"].get("branches", 0),
                        key=f"det_branches_{unique_key}"
                    )
                
                # AST Analysis se disponibile
                if "functions" in analysis:
                    st.subheader("Code Structure")
                    struct_cols = st.columns(3)
                    with struct_cols[0]:
                        st.metric(
                            "Functions",
                            len(analysis["functions"]),
                            key=f"det_functions_{unique_key}"
                        )
                        if analysis["functions"]:
                            with st.expander("Function Details"):
                                for func in analysis["functions"]:
                                    st.markdown(f"**{func['name']}**")
                                    st.markdown(f"Arguments: {func['args']}")
                                    if func['has_docstring']:
                                        st.markdown("✅ Has docstring")
                                    else:
                                        st.markdown("❌ No docstring")
                                    
                    with struct_cols[1]:
                        st.metric(
                            "Classes",
                            len(analysis["classes"]),
                            key=f"det_classes_{unique_key}"
                        )
                        if analysis["classes"]:
                            with st.expander("Class Details"):
                                for cls in analysis["classes"]:
                                    st.markdown(f"**{cls['name']}**")
                                    st.markdown(f"Methods: {cls['methods']}")
                                    if cls['has_docstring']:
                                        st.markdown("✅ Has docstring")
                                    else:
                                        st.markdown("❌ No docstring")
                                    
                    with struct_cols[2]:
                        st.metric(
                            "Imports",
                            len(analysis["imports"]),
                            key=f"det_imports_{unique_key}"
                        )
                        if analysis["imports"]:
                            with st.expander("Import Details"):
                                for imp in analysis["imports"]:
                                    st.markdown(f"- {imp}")
            
            # Tab Issues
            with tabs[2]:
                if analysis["issues"]:
                    for i, issue in enumerate(analysis["issues"], 1):
                        with st.expander(f"Issue {i}", key=f"det_issue_{i}_{unique_key}"):
                            st.warning(issue)
                else:
                    st.success("No issues found!")
            
            # Tab Suggestions
            with tabs[3]:
                if analysis["suggestions"]:
                    for i, suggestion in enumerate(analysis["suggestions"], 1):
                        with st.expander(f"Suggestion {i}", key=f"det_suggestion_{i}_{unique_key}"):
                            st.info(suggestion)
                else:
                    st.success("No suggestions available!")
    
    def display_diff(self, old_code: str, new_code: str, language: str = None, file_name: str = ""):
        """Mostra il diff tra due versioni del codice"""
        if not language:
            language = "python"
            
        unique_key = self._generate_unique_key(file_name, old_code + new_code, "diff")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Original")
            st.code(old_code, language=language, line_numbers=True)
        with col2:
            st.subheader("Modified")
            st.code(new_code, language=language, line_numbers=True)
            
    def display_tree_view(self, files: list):
        """Mostra una vista ad albero dei file"""
        if not files:
            st.info("No files to display")
            return
            
        # Organizza file per cartelle
        file_tree = {}
        for file in files:
            path = file.get('path', '')
            if path not in file_tree:
                file_tree[path] = []
            file_tree[path].append(file)
            
        # Mostra struttura
        for path in sorted(file_tree.keys()):
            if path:
                st.markdown(f"**📁 {path}/**")
            for file in sorted(file_tree[path], key=lambda x: x['name']):
                unique_key = self._generate_unique_key(file['name'], file.get('content', ''), "tree")
                if st.button(f"📄 {file['name']}", key=f"tree_{unique_key}"):
                    self.display_preview(
                        file['content'],
                        file.get('language', 'text'),
                        file['name']
                    )