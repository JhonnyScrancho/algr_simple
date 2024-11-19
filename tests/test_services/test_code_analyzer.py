import pytest
from services.code_analyzer import CodeAnalyzer

def test_analyze_code(sample_python_code):
    analyzer = CodeAnalyzer()
    analysis = analyzer.analyze_code(sample_python_code)
    
    # Verifica presenza campi base
    assert "issues" in analysis
    assert "suggestions" in analysis
    assert "stats" in analysis
    assert "complexity" in analysis
    
    # Verifica statistiche
    stats = analysis["stats"]
    assert stats["total_lines"] > 0
    assert stats["code_lines"] > 0
    
    # Verifica complessità
    complexity = analysis["complexity"]
    assert "cognitive_load" in complexity
    assert "nesting_depth" in complexity

def test_get_code_stats(sample_python_code):
    analyzer = CodeAnalyzer()
    stats = analyzer._get_code_stats(sample_python_code)
    
    assert stats["total_lines"] > 0
    assert stats["empty_lines"] >= 0
    assert stats["code_lines"] > 0
    assert stats["comment_lines"] >= 0
    assert stats["avg_line_length"] > 0

def test_analyze_ast(sample_python_code):
    analyzer = CodeAnalyzer()
    tree = ast.parse(sample_python_code)
    ast_analysis = analyzer._analyze_ast(tree)
    
    assert "functions" in ast_analysis
    assert len(ast_analysis["functions"]) == 2  # Due funzioni nel sample code
    assert "classes" in ast_analysis
    assert "imports" in ast_analysis

def test_empty_code():
    analyzer = CodeAnalyzer()
    analysis = analyzer.analyze_code("")
    
    assert analysis["stats"]["total_lines"] == 0
    assert not analysis["issues"]
    assert not analysis["suggestions"]