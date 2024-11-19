import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Any
import pytz
from pathlib import Path
import hashlib

class FirebaseChatPersistence:
    def __init__(self):
        # Inizializza Firebase solo se non è già stato fatto
        self.timezone = pytz.timezone('Europe/Rome')
        if not firebase_admin._apps:
            cred_dict = {
                "type": st.secrets["firebase"]["type"],
                "project_id": st.secrets["firebase"]["project_id"],
                "private_key_id": st.secrets["firebase"]["private_key_id"],
                "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["firebase"]["client_email"],
                "client_id": st.secrets["firebase"]["client_id"],
                "auth_uri": st.secrets["firebase"]["auth_uri"],
                "token_uri": st.secrets["firebase"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
    
    def _generate_file_hash(self, content: str) -> str:
        """Genera un hash del contenuto del file"""
        return hashlib.md5(content.encode()).hexdigest()

    def _get_current_timestamp(self) -> str:
        """Ottiene il timestamp corrente nel timezone italiano"""
        return datetime.now(self.timezone).isoformat()

    def get_all_chats(self) -> Dict:
        """Recupera tutte le chat"""
        try:
            chats = {}
            for doc in self.db.collection('chats').stream():
                chat_data = doc.to_dict()
                chats[doc.id] = {
                    "title": chat_data.get("title", "Nuova Chat"),
                    "created_at": chat_data.get("created_at", self._get_current_timestamp()),
                    "updated_at": chat_data.get("updated_at", self._get_current_timestamp()),
                    "files_count": len(chat_data.get("files", {}).get("versions", {}))
                }
            return {"chats": chats} if chats else {"chats": {}}
        except Exception as e:
            st.error(f"Errore nel recupero delle chat: {str(e)}")
            return {"chats": {}}

    def create_chat(self, title: str = "Nuova Chat") -> str:
        """Crea una nuova chat con struttura aggiornata"""
        try:
            current_time = self._get_current_timestamp()
            
            chat_data = {
                "title": title,
                "created_at": current_time,
                "updated_at": current_time,
                "messages": [],
                "files": {
                    "versions": {},  # Dizionario per versioni dei file
                    "structure": {},  # Struttura cartelle
                    "metadata": {}    # Metadata per ogni file
                }
            }
            
            doc_ref = self.db.collection('chats').document()
            doc_ref.set(chat_data)
            return doc_ref.id
            
        except Exception as e:
            st.error(f"Errore nella creazione della chat: {str(e)}")
            return ""

    def get_chat_messages(self, chat_id: str) -> List[Dict]:
        """Recupera i messaggi di una specifica chat"""
        try:
            doc = self.db.collection('chats').document(chat_id).get()
            if doc.exists:
                chat_data = doc.to_dict()
                return chat_data.get("messages", [])
            return []
        except Exception as e:
            st.error(f"Errore nel recupero dei messaggi: {str(e)}")
            return []

    def add_message(self, chat_id: str, role: str, content: str) -> bool:
        """Aggiunge un messaggio alla chat"""
        try:
            chat_ref = self.db.collection('chats').document(chat_id)
            
            if not chat_ref.get().exists:
                st.error("Chat non trovata")
                return False
            
            new_message = {
                "role": role,
                "content": content,
                "timestamp": self._get_current_timestamp()
            }
            
            chat_ref.update({
                "messages": firestore.ArrayUnion([new_message]),
                "updated_at": self._get_current_timestamp()
            })
            
            return True
        except Exception as e:
            st.error(f"Errore nell'aggiunta del messaggio: {str(e)}")
            return False

    def get_chat_files(self, chat_id: str) -> Dict:
        """Recupera i file della chat con versioni"""
        try:
            doc = self.db.collection('chats').document(chat_id).get()
            
            if not doc.exists:
                return {"content": [], "structure": {}, "metadata": {}}
            
            chat_data = doc.to_dict()
            files_data = chat_data.get("files", {})
            versions = files_data.get("versions", {})
            metadata = files_data.get("metadata", {})
            
            # Costruisci lista file con versione più recente
            current_files = []
            for file_name, versions_data in versions.items():
                if versions_data:
                    # Prendi la versione più recente
                    latest_version = max(versions_data.keys())
                    file_data = versions_data[latest_version]
                    file_data["name"] = file_name
                    file_data["version"] = latest_version
                    current_files.append(file_data)
            
            return {
                "content": current_files,
                "structure": files_data.get("structure", {}),
                "metadata": metadata
            }
            
        except Exception as e:
            st.error(f"Errore nel recupero dei file: {str(e)}")
            return {"content": [], "structure": {}, "metadata": {}}

    def add_files_to_chat(self, chat_id: str, files: List[Dict], structure: Dict = None) -> bool:
        """Aggiunge o aggiorna file nella chat con versioning"""
        try:
            chat_ref = self.db.collection('chats').document(chat_id)
            chat_doc = chat_ref.get()
            
            if not chat_doc.exists:
                return False
            
            chat_data = chat_doc.to_dict()
            files_data = chat_data.get("files", {})
            versions = files_data.get("versions", {})
            metadata = files_data.get("metadata", {})
            
            current_time = self._get_current_timestamp()
            updates = {"updated_at": current_time}
            
            for file in files:
                if not isinstance(file, dict) or 'name' not in file or 'content' not in file:
                    continue
                
                file_name = file['name']
                content_hash = self._generate_file_hash(file['content'])
                
                # Verifica se il file esiste e se il contenuto è cambiato
                if file_name in versions:
                    latest_version = max(versions[file_name].keys())
                    if versions[file_name][latest_version].get('hash') != content_hash:
                        # Contenuto diverso, crea nuova versione
                        new_version = str(int(latest_version) + 1)
                    else:
                        # Contenuto identico, salta
                        continue
                else:
                    # Nuovo file
                    new_version = "1"
                    versions[file_name] = {}
                
                # Prepara dati file
                file_data = {
                    "content": file['content'],
                    "hash": content_hash,
                    "size": len(file['content']),
                    "path": file.get('path', ''),
                    "language": file.get('language', 'text'),
                    "created_at": current_time
                }
                
                # Aggiorna versioni e metadata
                versions[file_name][new_version] = file_data
                metadata[file_name] = {
                    "current_version": new_version,
                    "total_versions": len(versions[file_name]),
                    "last_updated": current_time,
                    "size_history": {new_version: len(file['content'])}
                }
            
            # Aggiorna struttura se fornita
            if structure:
                updates["files.structure"] = structure
            
            # Aggiorna versioni e metadata
            updates["files.versions"] = versions
            updates["files.metadata"] = metadata
            
            chat_ref.update(updates)
            return True
                
        except Exception as e:
            st.error(f"Errore nell'aggiunta dei file: {str(e)}")
            return False

    def get_file_versions(self, chat_id: str, file_name: str) -> Dict:
        """Recupera tutte le versioni di un file specifico"""
        try:
            doc = self.db.collection('chats').document(chat_id).get()
            
            if not doc.exists:
                return {"versions": {}, "metadata": None}
            
            chat_data = doc.to_dict()
            files_data = chat_data.get("files", {})
            versions = files_data.get("versions", {}).get(file_name, {})
            metadata = files_data.get("metadata", {}).get(file_name)
            
            return {
                "versions": versions,
                "metadata": metadata
            }
            
        except Exception as e:
            st.error(f"Errore nel recupero delle versioni: {str(e)}")
            return {"versions": {}, "metadata": None}

    def remove_file_from_chat(self, chat_id: str, file_name: str) -> bool:
        """Rimuove un file e tutte le sue versioni"""
        try:
            chat_ref = self.db.collection('chats').document(chat_id)
            doc = chat_ref.get()
            
            if not doc.exists:
                return False
            
            chat_data = doc.to_dict()
            files_data = chat_data.get("files", {})
            versions = files_data.get("versions", {})
            metadata = files_data.get("metadata", {})
            
            # Rimuovi file da versioni e metadata
            if file_name in versions:
                versions.pop(file_name)
            if file_name in metadata:
                metadata.pop(file_name)
            
            # Aggiorna documento
            chat_ref.update({
                "files.versions": versions,
                "files.metadata": metadata,
                "updated_at": self._get_current_timestamp()
            })
            
            return True
            
        except Exception as e:
            st.error(f"Errore nella rimozione del file: {str(e)}")
            return False

    def add_image_to_chat(self, chat_id: str, image_data: Dict) -> bool:
        """Aggiunge un'immagine alla chat"""
        try:
            chat_ref = self.db.collection('chats').document(chat_id)
            doc = chat_ref.get()
            
            if not doc.exists:
                return False
            
            image_entry = {
                "data": image_data["base64"],
                "format": image_data["format"],
                "timestamp": self._get_current_timestamp()
            }
            
            chat_ref.update({
                "files.images": firestore.ArrayUnion([image_entry]),
                "updated_at": self._get_current_timestamp()
            })
            
            return True
        except Exception as e:
            st.error(f"Errore nell'aggiunta dell'immagine: {str(e)}")
            return False

    def update_chat_title(self, chat_id: str, new_title: str) -> bool:
        """Aggiorna il titolo della chat"""
        try:
            chat_ref = self.db.collection('chats').document(chat_id)
            doc = chat_ref.get()
            
            if not doc.exists:
                return False
            
            chat_ref.update({
                "title": new_title,
                "updated_at": self._get_current_timestamp()
            })
            return True
        except Exception as e:
            st.error(f"Errore nell'aggiornamento del titolo: {str(e)}")
            return False

    def delete_chat(self, chat_id: str) -> bool:
        """Elimina una chat e tutti i suoi dati"""
        try:
            chat_ref = self.db.collection('chats').document(chat_id)
            doc = chat_ref.get()
            
            if not doc.exists:
                return False
            
            chat_ref.delete()
            return True
        except Exception as e:
            st.error(f"Errore nell'eliminazione della chat: {str(e)}")
            return False