import pytest
from utils.code_formatter import format_code

def test_format_code():
    test_code = """
def test_function():
    return "test"
    """
    
    formatted = format_code(test_code)
    assert formatted is not None
    assert isinstance(formatted, str)
    
def test_format_empty_code():
    assert format_code("") == ""
    
def test_format_invalid_code():
    invalid_code = "def test_function(:"  # Sintassi invalida
    formatted = format_code(invalid_code)
    assert formatted is not None