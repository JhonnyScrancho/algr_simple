import pytest
from components.code_viewer import CodeViewer

def test_code_viewer_init():
    viewer = CodeViewer()
    assert viewer is not None

def test_display_preview():
    viewer = CodeViewer()
    test_code = """
    def test_function():
        return "test"
    """
    
    # Test base preview
    viewer.display_preview(test_code, "python")
    
    # Test senza specificare il linguaggio
    viewer.display_preview(test_code)