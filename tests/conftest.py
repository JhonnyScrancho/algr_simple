import pytest
import streamlit as st
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock di base per Streamlit"""
    # Simula st.session_state
    if not hasattr(st, 'session_state'):
        class SessionState(dict):
            def __init__(self):
                self.messages = []
                self.current_file = None
                self.model = "claude-3-sonnet"
                self.code_analysis = {}
                self.settings = {
                    'theme': 'light',
                    'show_line_numbers': True,
                    'auto_analyze': True
                }
        st.session_state = SessionState()

@pytest.fixture
def sample_python_code():
    """Fixture per codice Python di esempio"""
    return """
def calculate_sum(numbers):
    \"\"\"Calculate sum of numbers.\"\"\"
    total = 0
    for num in numbers:
        total += num
    return total

def process_data(data, threshold=0):
    \"\"\"Process data with threshold.\"\"\"
    results = []
    for item in data:
        if item > threshold:
            results.append(item * 2)
    return results
    """

@pytest.fixture
def sample_file_content():
    """Fixture per contenuto file"""
    return {
        "name": "test.py",
        "content": "def test(): pass",
        "language": "python",
        "extension": ".py",
        "success": True
    }

@pytest.fixture
def mock_llm_response():
    """Fixture per risposta LLM"""
    return {
        "role": "assistant",
        "content": "Here's the explanation...",
        "code": "def example(): pass",
        "language": "python"
    }