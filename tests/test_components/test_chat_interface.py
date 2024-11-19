import pytest
import streamlit as st
from components.chat_interface import ChatInterface

def test_chat_interface_init():
    chat = ChatInterface()
    assert chat is not None
    assert chat.llm_handler is not None

def test_display_messages(mock_streamlit):
    chat = ChatInterface()
    
    # Test con messaggio semplice
    st.session_state.messages = [{
        "role": "user",
        "content": "Test message"
    }]
    chat.display_messages()
    
    # Test con messaggio contenente codice
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Here's the code",
        "code": "def test(): pass",
        "language": "python"
    })
    chat.display_messages()

def test_handle_user_input(mock_streamlit, mock_llm_response, sample_file_content):
    chat = ChatInterface()
    
    # Test input semplice
    chat.handle_user_input("Test message")
    assert len(st.session_state.messages) > 0
    
    # Test input con contesto
    context = {"current_file": sample_file_content}
    chat.handle_user_input("Explain this code", context)
    
    last_message = st.session_state.messages[-1]
    assert last_message["role"] in ["user", "assistant"]

def test_determine_prompt_type():
    chat = ChatInterface()
    
    # Test vari tipi di prompt
    assert chat._determine_prompt_type("analyze this code") == "code_analysis"
    assert chat._determine_prompt_type("explain how this works") == "code_explanation"
    assert chat._determine_prompt_type("complete this function") == "code_completion"
    assert chat._determine_prompt_type("fix this bug") == "bug_finding"