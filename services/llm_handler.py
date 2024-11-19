from abc import ABC, abstractmethod
import streamlit as st
import anthropic
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator, Union
from config.models import (
    MODELS_CONFIG,
    SYSTEM_PROMPTS,
    determine_content_type,
    select_system_prompt
)

class LLMProvider(ABC):
    """Interfaccia base per i provider LLM"""
    
    @abstractmethod
    def initialize(self, api_key: str, **kwargs):
        """Inizializza il provider con le credenziali necessarie"""
        pass
    
    @abstractmethod
    def get_response(self, prompt: str, context: dict = None) -> dict:
        """Ottiene una risposta completa dal modello"""
        pass
    
    @abstractmethod
    def get_streaming_response(self, prompt: str, context: dict = None) -> Generator[str, None, None]:
        """Ottiene una risposta in streaming dal modello"""
        pass

class AnthropicProvider(LLMProvider):
    """Implementazione del provider Anthropic Claude"""
    
    def initialize(self, api_key: str, **kwargs):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_config = kwargs.get('model_config', {})
    
    def get_response(self, prompt: str, context: dict = None) -> dict:
        try:
            system = select_system_prompt(context) if context else SYSTEM_PROMPTS['general']
            messages = [{"role": "user", "content": prompt}]
            
            # Handle image if present
            if context and 'image' in context:
                messages[0]["content"] = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": context['image']
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            
            response = self.client.messages.create(
                model=self.model_config.get('model_id'),
                max_tokens=self.model_config.get('max_tokens', 4096),
                temperature=self.model_config.get('temperature', 0.7),
                top_p=self.model_config.get('top_p', 0.95),
                system=system,
                messages=messages
            )
            
            if response and hasattr(response, 'content'):
                if isinstance(response.content, list) and response.content:
                    if hasattr(response.content[0], 'text'):
                        return {
                            "role": "assistant",
                            "content": response.content[0].text,
                            "timestamp": datetime.now().isoformat()
                        }
            
            return {
                "role": "assistant",
                "content": "Risposta non valida dal modello.",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "role": "assistant",
                "content": f"Errore nella richiesta: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_streaming_response(self, prompt: str, context: dict = None) -> Generator[str, None, None]:
        try:
            system = select_system_prompt(context) if context else SYSTEM_PROMPTS['general']
            messages = [{"role": "user", "content": prompt}]
            
            # Handle image in streaming
            if context and 'image' in context:
                messages[0]["content"] = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": context['image']
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            
            with self.client.messages.stream(
                model=self.model_config.get('model_id'),
                max_tokens=self.model_config.get('max_tokens', 4096),
                temperature=self.model_config.get('temperature', 0.7),
                top_p=self.model_config.get('top_p', 0.95),
                system=system,
                messages=messages
            ) as stream:
                for chunk in stream:
                    if hasattr(chunk, 'delta'):
                        if hasattr(chunk.delta, 'content'):
                            for content_block in chunk.delta.content:
                                if hasattr(content_block, 'text'):
                                    yield content_block.text
                    elif hasattr(chunk, 'message'):
                        for content in chunk.message.content:
                            if hasattr(content, 'text'):
                                yield content.text
                            elif isinstance(content, str):
                                yield content
                                
        except Exception as e:
            yield f"Errore nello streaming: {str(e)}"

class DeepseekProvider(LLMProvider):
    """Implementazione del provider Deepseek"""
    
    def initialize(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.model_config = kwargs.get('model_config', {})
    
    def get_response(self, prompt: str, context: dict = None) -> dict:
        try:
            system = select_system_prompt(context) if context else SYSTEM_PROMPTS['general']
            messages = []
            
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_config.get('model_id'),
                "messages": messages,
                "max_tokens": self.model_config.get('max_tokens', 4096),
                "temperature": self.model_config.get('temperature', 0.7),
                "top_p": self.model_config.get('top_p', 0.95),
                "presence_penalty": self.model_config.get('presence_penalty', 0.0),
                "frequency_penalty": self.model_config.get('frequency_penalty', 0.0)
            }
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            response_data = response.json()
            if 'choices' in response_data and response_data['choices']:
                content = response_data['choices'][0].get('message', {}).get('content', '')
                return {
                    "role": "assistant",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "role": "assistant",
                "content": "Risposta non valida dal modello.",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "role": "assistant",
                "content": f"Errore nella richiesta: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_streaming_response(self, prompt: str, context: dict = None) -> Generator[str, None, None]:
        try:
            system = select_system_prompt(context) if context else SYSTEM_PROMPTS['general']
            messages = []
            
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_config.get('model_id'),
                "messages": messages,
                "max_tokens": self.model_config.get('max_tokens', 4096),
                "temperature": self.model_config.get('temperature', 0.7),
                "top_p": self.model_config.get('top_p', 0.95),
                "presence_penalty": self.model_config.get('presence_penalty', 0.0),
                "frequency_penalty": self.model_config.get('frequency_penalty', 0.0),
                "stream": True
            }
            
            with requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                stream=True
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            json_response = json.loads(line.decode('utf-8').replace('data: ', ''))
                            if 'choices' in json_response:
                                chunk = json_response['choices'][0].get('delta', {}).get('content', '')
                                if chunk:
                                    yield chunk
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            yield f"Errore nello streaming: {str(e)}"

class LLMHandler:
    """Gestore principale per le interazioni con i modelli LLM"""
    
    def __init__(self, default_model: str = "claude-3-sonnet"):
        # Inizializza lista per i log
        if 'debug_logs' not in st.session_state:
            st.session_state.debug_logs = []
        
        self.providers: Dict[str, LLMProvider] = {
            "anthropic": AnthropicProvider(),
            "deepseek": DeepseekProvider()
        }
        self.current_provider = None
        self.model_name = default_model
        self.initialize_model(default_model)
        self.max_context_length = 200000

    def _log(self, message: str):
        """Aggiunge un messaggio ai log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.debug_logs.append(f"[{timestamp}] {message}")
        # Mantieni solo gli ultimi 50 messaggi
        if len(st.session_state.debug_logs) > 50:
            st.session_state.debug_logs = st.session_state.debug_logs[-50:]

    def initialize_model(self, model_name: str):
        """Inizializza il provider appropriato per il modello selezionato"""
        self._log(f"🔄 Inizializzazione modello: {model_name}")
        self._log(f"Provider corrente: {st.session_state.get('current_provider', 'none')}")
        
        try:
            if model_name not in MODELS_CONFIG:
                self._log(f"⚠️ Modello {model_name} non supportato, uso Claude 3 Sonnet")
                model_name = "claude-3-sonnet"
            
            model_config = MODELS_CONFIG[model_name]
            provider_name = model_config["provider"]
            self._log(f"Provider richiesto: {provider_name}")
            
            # Ottieni la chiave API appropriata
            api_key = None
            if provider_name == "anthropic":
                if "ANTHROPIC_API_KEY" not in st.secrets:
                    self._log("❌ Chiave API Anthropic mancante")
                    return False
                api_key = st.secrets["ANTHROPIC_API_KEY"]
                self._log("✓ Chiave API Anthropic trovata")
            elif provider_name == "deepseek":
                if "DEEPSEEK_API_KEY" not in st.secrets:
                    self._log("❌ Chiave API DeepSeek mancante")
                    return False
                api_key = st.secrets["DEEPSEEK_API_KEY"]
                self._log("✓ Chiave API DeepSeek trovata")
                
                # Test chiave DeepSeek
                if not api_key or api_key.strip() == "":
                    self._log("❌ Chiave API DeepSeek non valida")
                    return False
                self._log("✓ Chiave API DeepSeek valida")
            else:
                self._log(f"❌ Provider {provider_name} non supportato")
                return False
            
            # Verifica provider
            if provider_name not in self.providers:
                self._log(f"❌ Provider {provider_name} non inizializzato")
                return False
            
            # Inizializza il provider
            self._log(f"Inizializzazione provider {provider_name}...")
            self.current_provider = self.providers[provider_name]
            self.current_provider.initialize(api_key, model_config=model_config)
            self.model_name = model_name
            
            # Aggiorna session state
            old_provider = st.session_state.get('current_provider', 'none')
            old_model = st.session_state.get('model', 'none')
            
            st.session_state.model = model_name
            st.session_state.current_provider = provider_name
            
            self._log(f"✓ Cambio provider: {old_provider} -> {provider_name}")
            self._log(f"✓ Cambio modello: {old_model} -> {model_name}")
            
            return True

        except Exception as e:
            self._log(f"❌ Errore nell'inizializzazione del modello: {str(e)}")
            if self.model_name != "claude-3-sonnet":
                self._log("⚠️ Tentativo di fallback su Claude...")
                return self.initialize_model("claude-3-sonnet")
            return False

    def get_response(self, prompt: str, context: dict = None) -> dict:
        """Ottiene una risposta dal modello corrente"""
        self._log(f"Provider attuale: {st.session_state.get('current_provider')}")
        self._log(f"Modello attuale: {st.session_state.get('model')}")
        
        if not self.current_provider:
            self._log("❌ Nessun provider inizializzato")
            return {
                "role": "assistant",
                "content": "Errore: nessun provider disponibile.",
                "timestamp": datetime.now().isoformat()
            }

        # Corretto mapping del provider atteso dal modello corrente
        model_name = st.session_state.get('model', self.model_name)
        expected_provider = MODELS_CONFIG[model_name]["provider"]
        current_provider = st.session_state.get("current_provider", "anthropic")
        
        self._log(f"Provider atteso dal modello {model_name}: {expected_provider}")
        self._log(f"Provider attualmente in uso: {current_provider}")
        
        if current_provider != expected_provider:
            self._log(f"⚠️ Cambio provider necessario da {current_provider} a {expected_provider}")
            success = self.initialize_model(model_name)
            if not success:
                self._log("❌ Cambio provider fallito")
                return {
                    "role": "assistant",
                    "content": "Errore nel cambio del modello.",
                    "timestamp": datetime.now().isoformat()
                }
            self._log(f"✓ Provider cambiato con successo a {expected_provider}")
        
        return self.current_provider.get_response(prompt, context)

    def get_streaming_response(self, prompt: str, context: dict = None) -> Generator[str, None, None]:
        """Ottiene una risposta in streaming dal modello corrente"""
        self._log(f"Provider attuale: {st.session_state.get('current_provider')}")
        self._log(f"Modello attuale: {st.session_state.get('model')}")
        
        if not self.current_provider:
            yield "Errore: nessun provider inizializzato."
            return

        # Corretto mapping del provider atteso dal modello corrente
        model_name = st.session_state.get('model', self.model_name)
        expected_provider = MODELS_CONFIG[model_name]["provider"]
        current_provider = st.session_state.get("current_provider", "anthropic")
        
        self._log(f"Provider atteso dal modello {model_name}: {expected_provider}")
        self._log(f"Provider attualmente in uso: {current_provider}")
        
        if current_provider != expected_provider:
            self._log(f"⚠️ Cambio provider necessario da {current_provider} a {expected_provider}")
            success = self.initialize_model(model_name)
            if not success:
                self._log("❌ Cambio provider fallito")
                yield "Errore nel cambio del modello."
                return
            self._log(f"✓ Provider cambiato con successo a {expected_provider}")
        
        yield from self.current_provider.get_streaming_response(prompt, context)

    def get_model_parameters(self) -> dict:
        """Ottiene i parametri correnti del modello"""
        model_config = MODELS_CONFIG.get(self.model_name, {})
        
        # Parametri base supportati da tutti i provider
        params = {
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 4096),
            'top_p': model_config.get('top_p', 0.95),
        }
        
        # Aggiungi parametri specifici per Deepseek
        if model_config.get('provider') == 'deepseek':
            params.update({
                'presence_penalty': model_config.get('presence_penalty', 0.0),
                'frequency_penalty': model_config.get('frequency_penalty', 0.0)
            })
        
        return params
    
    def update_model_parameters(self, parameters: dict):
        """Aggiorna i parametri del modello corrente"""
        model_config = MODELS_CONFIG.get(self.model_name, {})
        
        # Filtra i parametri validi per il provider corrente
        valid_params = {
            k: v for k, v in parameters.items()
            if k in self.get_model_parameters()
        }
        
        model_config.update(valid_params)