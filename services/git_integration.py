import streamlit as st
from git import Repo
from pathlib import Path

class GitIntegration:
    def __init__(self):
        self.repo = None
    
    def init_repo(self, path: str) -> bool:
        """Inizializza o carica un repository Git"""
        try:
            self.repo = Repo(path)
            return True
        except:
            try:
                self.repo = Repo.init(path)
                return True
            except Exception as e:
                st.error(f"Errore nell'inizializzazione del repository: {str(e)}")
                return False
    
    def get_status(self) -> dict:
        """Ottiene lo stato del repository"""
        if not self.repo:
            return {"error": "Repository non inizializzato"}
        
        try:
            return {
                "branch": self.repo.active_branch.name,
                "modified": [item.a_path for item in self.repo.index.diff(None)],
                "untracked": self.repo.untracked_files
            }
        except Exception as e:
            return {"error": f"Errore nel recupero dello stato: {str(e)}"}