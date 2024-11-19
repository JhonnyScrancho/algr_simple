import pytest
from services.llm_handler import LLMHandler

def test_llm_handler_init():
    handler = LLMHandler()
    assert handler.model_name == "claude-3-sonnet"
    assert handler.current_model is not None

@pytest.mark.asyncio
async def test_get_response(mock_llm_response):
    handler = LLMHandler()
    response = await handler.get_response("Test prompt")
    
    assert "role" in response
    assert "content" in response
    assert response["role"] == "assistant"

@pytest.mark.asyncio
async def test_get_response_with_context(sample_python_code):
    handler = LLMHandler()
    context = {
        "type": "code_analysis",
        "code": sample_python_code
    }
    
    response = await handler.get_response("Analyze this code", context)
    assert "role" in response
    assert "content" in response
    assert len(response["content"]) > 0

def test_retry_mechanism():
    handler = LLMHandler()
    
    # Simula errore temporaneo
    handler.client.messages.create.side_effect = [
        Exception("Temporary error"),
        {"content": [{"text": "Success"}]}
    ]
    
    response = handler.get_response("Test retry")
    assert response["content"] == "Success"