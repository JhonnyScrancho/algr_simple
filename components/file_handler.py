import streamlit as st
from pathlib import Path
import zipfile
import io
import os
import re
import json
import ast
import hashlib
from datetime import datetime
import pytz
from typing import Dict, Any, List, Set, Optional, Tuple
from config.settings import APP_CONFIG

class FileHandler:
    def __init__(self):
        self.max_single_file_size = APP_CONFIG["max_file_size"]
        self.max_total_size = APP_CONFIG["max_total_files_size"]
        self.max_files = APP_CONFIG["max_files_number"]
        self.supported_extensions = APP_CONFIG["supported_file_types"]
        self.app_config = APP_CONFIG
        self.timezone = pytz.timezone('Europe/Rome')

    def _generate_file_hash(self, content: str) -> str:
        """Genera hash del contenuto del file"""
        return hashlib.md5(content.encode()).hexdigest()

    def _get_current_timestamp(self) -> str:
        """Ottiene timestamp corrente in timezone italiano"""
        return datetime.now(self.timezone).isoformat()

    def handle_uploaded_files(self, uploaded_files, existing_files: List[Dict] = None) -> Dict[str, Any]:
        """Gestisce file caricati con supporto versioning"""
        try:
            if not uploaded_files:
                return {"success": False, "error": "Nessun file caricato"}

            # Inizializza strutture dati
            processed_files = []
            file_versions = {}
            total_size = 0
            file_structure = {"": []}
            
            # Gestisci file esistenti
            if existing_files:
                for file in existing_files:
                    if isinstance(file, dict) and 'content' in file:
                        path = file.get('path', '')
                        if path not in file_structure:
                            file_structure[path] = []
                        file_structure[path].append({
                            "name": file.get('name', 'unknown'),
                            "size": file.get('size', 0),
                            "type": "file",
                            "version": file.get('version', '1')
                        })
                        total_size += file.get('size', 0)
                        processed_files.append(file)
            
            # Processa nuovi file
            for uploaded_file in uploaded_files:
                try:
                    # Valida file
                    validation = self._validate_file(uploaded_file)
                    if not validation["success"]:
                        st.warning(validation["error"])
                        continue
                    
                    # Verifica dimensione totale
                    new_total_size = total_size + uploaded_file.size
                    if new_total_size > self.max_total_size:
                        return {
                            "success": False,
                            "error": f"Dimensione totale supera {self.max_total_size/1024/1024:.1f}MB"
                        }
                    
                    # Processa il file
                    if uploaded_file.name.lower().endswith('.zip'):
                        result = self._process_zip(uploaded_file, existing_files)
                        
                        if not result.get("success"):
                            st.warning(f"Errore nel processare lo ZIP {uploaded_file.name}: {result.get('error')}")
                            continue
                        
                        if 'files' in result:
                            # Verifica numero massimo file
                            if len(processed_files) + len(result['files']) > self.max_files:
                                st.warning(f"Troppi file nel ZIP (limite: {self.max_files})")
                                continue
                            
                            # Gestisci ogni file dello ZIP
                            for file in result['files']:
                                process_result = self._process_file_with_version(
                                    file,
                                    processed_files,
                                    file_versions
                                )
                                
                                if process_result["success"]:
                                    new_file = process_result["file"]
                                    path = new_file.get('path', '')
                                    
                                    if path not in file_structure:
                                        file_structure[path] = []
                                        
                                    file_structure[path].append({
                                        "name": new_file['name'],
                                        "size": new_file['size'],
                                        "type": "file",
                                        "version": new_file.get('version', '1')
                                    })
                                    
                                    processed_files.append(new_file)
                                    total_size += new_file['size']
                                else:
                                    st.warning(process_result["error"])
                    
                    else:
                        # Processa file singolo
                        result = self._process_single_file(uploaded_file)
                        if not result.get("success"):
                            st.warning(f"Errore nel processare {uploaded_file.name}: {result.get('error')}")
                            continue
                        
                        # Gestisci versioning
                        process_result = self._process_file_with_version(
                            result,
                            processed_files,
                            file_versions
                        )
                        
                        if process_result["success"]:
                            new_file = process_result["file"]
                            path = new_file.get('path', '')
                            
                            if path not in file_structure:
                                file_structure[path] = []
                                
                            file_structure[path].append({
                                "name": new_file['name'],
                                "size": new_file['size'],
                                "type": "file",
                                "version": new_file.get('version', '1')
                            })
                            
                            processed_files.append(new_file)
                            total_size += new_file['size']
                        else:
                            st.warning(process_result["error"])
                
                except Exception as e:
                    st.error(f"Errore nel processare il file {uploaded_file.name}: {str(e)}")
                    continue
            
            if not processed_files:
                return {"success": False, "error": "Nessun file processato correttamente"}
            
            # Ordina struttura e file
            file_structure = self._sort_structure(file_structure)
            processed_files = self._sort_files(processed_files)
            
            # Analisi dei file processati
            try:
                content_analysis = self._analyze_content(processed_files)
            except Exception as e:
                st.warning(f"Errore nell'analisi dei file: {str(e)}")
                content_analysis = {}
            
            return {
                "success": True,
                "files": processed_files,
                "structure": file_structure,
                "versions": file_versions,
                "file_count": len(processed_files),
                "total_size": total_size,
                "analysis": content_analysis
            }
                    
        except Exception as e:
            st.error(f"Errore generale nell'elaborazione: {str(e)}")
            return {
                "success": False,
                "error": f"Errore elaborazione: {str(e)}"
            }

    def _process_file_with_version(
        self,
        file: Dict,
        existing_files: List[Dict],
        file_versions: Dict
    ) -> Dict[str, Any]:
        """Processa un file gestendo il versioning"""
        try:
            if not isinstance(file, dict) or 'name' not in file or 'content' not in file:
                return {"success": False, "error": "Dati file non validi"}

            file_name = file['name']
            content_hash = self._generate_file_hash(file['content'])
            
            # Cerca file esistente
            existing_file = None
            for ef in existing_files:
                if ef.get('name') == file_name and ef.get('path', '') == file.get('path', ''):
                    existing_file = ef
                    break
            
            if existing_file:
                # File esistente, verifica contenuto
                existing_hash = self._generate_file_hash(existing_file['content'])
                if existing_hash == content_hash:
                    return {"success": False, "error": f"File {file_name} non modificato"}
                
                # Contenuto diverso, crea nuova versione
                current_version = existing_file.get('version', '1')
                new_version = str(int(current_version) + 1)
                
                file['version'] = new_version
                file['previous_version'] = current_version
                file['hash'] = content_hash
                
                if file_name not in file_versions:
                    file_versions[file_name] = {}
                file_versions[file_name][new_version] = file
                
            else:
                # Nuovo file
                file['version'] = '1'
                file['hash'] = content_hash
                
                if file_name not in file_versions:
                    file_versions[file_name] = {}
                file_versions[file_name]['1'] = file
            
            return {"success": True, "file": file}
            
        except Exception as e:
            return {"success": False, "error": f"Errore nel processing: {str(e)}"}

    def _process_zip(self, zip_file, existing_files: List[Dict] = None) -> Dict[str, Any]:
        """Processa file ZIP mantenendo la struttura cartelle"""
        try:
            processed_files = []
            total_size = 0
            structure = {"": []}
            file_versions = {}

            with zipfile.ZipFile(io.BytesIO(zip_file.read())) as z:
                # Filtra file validi
                valid_files = [
                    f for f in z.namelist()
                    if not (f.endswith('/') or  
                        f.startswith('__') or  
                        '/.' in f or  
                        f.startswith('.'))
                ]

                # Filtra per estensioni supportate
                valid_files = [f for f in valid_files 
                            if Path(f).suffix.lower().lstrip('.') in self.supported_extensions]

                # Processa ogni file valido
                for file_path in valid_files:
                    try:
                        # Leggi contenuto
                        content = z.read(file_path).decode('utf-8')
                        size = len(content)
                        
                        # Verifica dimensione
                        if size > self.max_single_file_size:
                            st.warning(f"File {file_path} ignorato: troppo grande")
                            continue
                        
                        # Gestisci path in modo sicuro
                        path_parts = Path(file_path).parts
                        file_name = path_parts[-1]
                        
                        # Gestisci directory
                        dir_path = ""
                        if len(path_parts) > 1:
                            dir_path = str(Path(*path_parts[:-1]))
                        
                        # Crea struttura directory
                        if dir_path not in structure:
                            structure[dir_path] = []
                        
                        # Prepara file info
                        file_ext = Path(file_name).suffix.lower()
                        file_info = {
                            "name": file_name,
                            "content": content,
                            "size": size,
                            "path": dir_path,
                            "language": self.app_config["language_mapping"].get(file_ext, "text"),
                            "hash": self._generate_file_hash(content)
                        }
                        
                        # Gestisci versioning
                        if existing_files:
                            process_result = self._process_file_with_version(
                                file_info,
                                existing_files,
                                file_versions
                            )
                            
                            if process_result["success"]:
                                file_info = process_result["file"]
                            else:
                                continue
                        else:
                            file_info['version'] = '1'
                            if file_name not in file_versions:
                                file_versions[file_name] = {}
                            file_versions[file_name]['1'] = file_info
                        
                        structure[dir_path].append({
                            "name": file_name,
                            "size": size,
                            "type": "file",
                            "version": file_info['version']
                        })
                        
                        processed_files.append(file_info)
                        total_size += size
                        
                    except UnicodeDecodeError:
                        st.warning(f"File {file_path} ignorato: non è un file di testo")
                        continue
                    except Exception as e:
                        st.warning(f"Errore nel processare {file_path}: {str(e)}")
                        continue
                
                if not processed_files:
                    return {
                        "success": False,
                        "error": "Nessun file valido trovato nel ZIP"
                    }
                
                return {
                    "success": True,
                    "files": processed_files,
                    "structure": structure,
                    "versions": file_versions,
                    "total_size": total_size
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nell'elaborazione ZIP: {str(e)}"
            }
    
    def _process_single_file(self, file) -> Dict[str, Any]:
        """Processa singolo file"""
        try:
            # Verifica dimensione
            if file.size > self.max_single_file_size:
                return {
                    "success": False,
                    "error": f"File troppo grande (max {self.max_single_file_size/1024/1024:.1f}MB)"
                }
            
            # Verifica estensione
            file_extension = Path(file.name).suffix.lower().lstrip('.')
            if file_extension not in self.supported_extensions:
                return {
                    "success": False,
                    "error": f"Tipo file non supportato: {file_extension}"
                }
            
            # Leggi contenuto
            content = file.read().decode('utf-8')
            
            return {
                "success": True,
                "name": file.name,
                "content": content,
                "size": file.size,
                "path": "",  # root directory
                "language": APP_CONFIG["language_mapping"].get(f".{file_extension}", "text"),
                "hash": self._generate_file_hash(content)
            }
            
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": "File non testuale o codifica non supportata"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore file: {str(e)}"
            }

    def _validate_file(self, file) -> Dict[str, Any]:
        """Valida un file prima del processing"""
        try:
            # Verifica dimensione
            if file.size > self.max_single_file_size:
                return {
                    "success": False,
                    "error": f"File troppo grande (max {self.max_single_file_size/1024/1024:.1f}MB)"
                }
            
            # Verifica estensione per file non-ZIP
            if not file.name.lower().endswith('.zip'):
                file_extension = Path(file.name).suffix.lower().lstrip('.')
                if file_extension not in self.supported_extensions:
                    return {
                        "success": False,"error": f"Tipo file non supportato: {file_extension}"
                    }
            
            # Verifica percorso sicuro
            if any(part.startswith('.') for part in Path(file.name).parts):
                return {
                    "success": False,
                    "error": "Percorso file non valido"
                }
                
            return {"success": True}
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore validazione: {str(e)}"
            }

    def _analyze_content(self, files: List[Dict]) -> Dict[str, Any]:
        """Analizza contenuto dei file per suggerire regole e contesto"""
        try:
            analysis = {
                'types': set(),
                'suggested_rules': set(),
                'project_type': None,
                'languages': set(),
                'frameworks': set()
            }
            
            if not files:
                return analysis
                
            # Analisi estensioni e contenuto
            for file in files:
                # Verifica file valido
                if not isinstance(file, dict) or 'name' not in file:
                    continue
                    
                # Estrai estensione
                ext = Path(file['name']).suffix.lower()
                
                # Analisi codice
                if ext in {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.cs'}:
                    analysis['types'].add('code')
                    analysis['suggested_rules'].update([
                        'no_omissions',
                        'maintain_style',
                        'practical_improvements'
                    ])
                    
                    # Aggiungi linguaggio
                    analysis['languages'].add(ext.lstrip('.'))
                    
                    # Check specifici per linguaggio
                    if ext == '.py' and 'content' in file:
                        self._analyze_python_specific(file, analysis)
                    elif ext in {'.js', '.ts', '.jsx', '.tsx'} and 'content' in file:
                        self._analyze_javascript_specific(file, analysis)
                
                # Analisi dati
                elif ext in {'.json', '.csv', '.yaml', '.yml'}:
                    analysis['types'].add('data')
                    analysis['suggested_rules'].update([
                        'complete_processing',
                        'show_insights',
                        'data_quality'
                    ])
                    
                    if ext == '.json' and 'content' in file:
                        self._analyze_json_specific(file, analysis)
                
                # Analisi config
                elif ext in {'.conf', '.ini', '.env'}:
                    analysis['types'].add('config')
                    analysis['suggested_rules'].add('config_validation')
            
            # Determina tipo progetto
            if self._is_web_project(files):
                analysis['project_type'] = 'web'
                analysis['suggested_rules'].update(['frontend', 'api_security'])
            elif self._is_data_project(files):
                analysis['project_type'] = 'data'
                analysis['suggested_rules'].update(['data_validation', 'data_quality'])
            elif self._is_backend_project(files):
                analysis['project_type'] = 'backend'
                analysis['suggested_rules'].update(['code_security', 'api_design'])

            # Converti set in liste per json serialization
            return {
                'types': list(analysis['types']),
                'suggested_rules': list(analysis['suggested_rules']),
                'project_type': analysis['project_type'],
                'languages': list(analysis['languages']),
                'frameworks': list(analysis['frameworks'])
            }

        except Exception as e:
            st.warning(f"Errore nell'analisi del contenuto: {str(e)}")
            return {
                'types': [],
                'suggested_rules': [],
                'project_type': None,
                'languages': [],
                'frameworks': []
            }

    def _analyze_python_specific(self, file: Dict, analysis: Dict):
        """Analisi specifica per file Python"""
        try:
            if not file.get('content'):
                return
                
            content = file['content'].lower()
            
            # Check per test
            if ('test' in file['name'].lower() or 
                'pytest' in content or 
                'unittest' in content):
                analysis['suggested_rules'].add('test_coverage')
            
            # Check per framework
            frameworks = {
                'django': 'Django',
                'flask': 'Flask',
                'fastapi': 'FastAPI',
                'streamlit': 'Streamlit',
                'pytorch': 'PyTorch',
                'tensorflow': 'TensorFlow'
            }
            
            for fw_key, fw_name in frameworks.items():
                if fw_key in content:
                    analysis['frameworks'].add(fw_name)

        except Exception as e:
            st.warning(f"Errore nell'analisi Python: {str(e)}")

    def _analyze_javascript_specific(self, file: Dict, analysis: Dict):
        """Analisi specifica per file JavaScript/TypeScript"""
        try:
            if not file.get('content'):
                return
                
            content = file['content'].lower()
            
            # Check per framework
            if 'react' in content or 'useState' in content or 'useEffect' in content:
                analysis['frameworks'].add('React')
                analysis['suggested_rules'].add('react_best_practices')
            elif 'vue' in content or 'createapp' in content:
                analysis['frameworks'].add('Vue')
                analysis['suggested_rules'].add('vue_best_practices')
            elif 'angular' in content or '@component' in content:
                analysis['frameworks'].add('Angular')
                analysis['suggested_rules'].add('angular_best_practices')

        except Exception as e:
            st.warning(f"Errore nell'analisi JavaScript: {str(e)}")

    def _analyze_json_specific(self, file: Dict, analysis: Dict):
        """Analisi specifica per file JSON"""
        try:
            if not file.get('content'):
                return
                
            content = json.loads(file['content'])
            if isinstance(content, list) and len(content) > 0:
                analysis['suggested_rules'].add('data_structure_analysis')
            elif isinstance(content, dict) and len(content) > 0:
                if file['name'] == 'package.json':
                    if 'dependencies' in content:
                        for dep in content['dependencies']:
                            if dep.lower() in ['react', 'vue', '@angular/core']:
                                analysis['frameworks'].add(dep.capitalize())
                analysis['suggested_rules'].add('config_validation')
        except json.JSONDecodeError:
            pass
        except Exception as e:
            st.warning(f"Errore nell'analisi JSON: {str(e)}")

    def _is_web_project(self, files: List[Dict]) -> bool:
        """Determina se il progetto è di tipo web"""
        try:
            if not files:
                return False
                
            web_indicators = {'.html', '.css', '.js', '.jsx', '.vue', '.ts', '.tsx'}
            frameworks = {'react', 'vue', 'angular', 'svelte', 'next', 'nuxt'}
            
            # Verifica estensioni
            for file in files:
                if not isinstance(file, dict) or 'name' not in file:
                    continue
                ext = Path(file['name']).suffix.lower()
                if ext in web_indicators:
                    return True
                    
                # Verifica contenuto per framework
                if file.get('content'):
                    content = file['content'].lower()
                    if any(fw in content for fw in frameworks):
                        return True
            
            return False
            
        except Exception as e:
            st.warning(f"Errore nel determinare il tipo di progetto web: {str(e)}")
            return False

    def _is_data_project(self, files: List[Dict]) -> bool:
        """Determina se il progetto è di tipo data analysis"""
        try:
            if not files:
                return False
                
            data_indicators = {'.csv', '.json', '.yaml', '.yml', '.xml'}
            data_libs = {'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'plotly'}
            
            for file in files:
                if not isinstance(file, dict) or 'name' not in file:
                    continue
                    
                ext = Path(file['name']).suffix.lower()
                if ext in data_indicators:
                    return True
                    
                if ext == '.py' and file.get('content'):
                    content = file['content'].lower()
                    if any(lib in content for lib in data_libs):
                        return True
            
            return False
            
        except Exception as e:
            st.warning(f"Errore nel determinare il tipo di progetto data: {str(e)}")
            return False

    def _is_backend_project(self, files: List[Dict]) -> bool:
        """Determina se il progetto è di tipo backend"""
        try:
            if not files:
                return False
                
            backend_indicators = {'.py', '.java', '.php', '.rb', '.go', '.rs'}
            backend_frameworks = {'django', 'flask', 'fastapi', 'express', 'spring', 'laravel'}
            
            for file in files:
                if not isinstance(file, dict) or 'name' not in file:
                    continue
                    
                ext = Path(file['name']).suffix.lower()
                if ext in backend_indicators:
                    return True
                    
                if file.get('content'):
                    content = file['content'].lower()
                    if any(fw in content for fw in backend_frameworks):
                        return True
            
            return False
            
        except Exception as e:
            st.warning(f"Errore nel determinare il tipo di progetto backend: {str(e)}")
            return False

    def _sort_structure(self, structure: Dict) -> Dict:
        """Ordina la struttura cartelle"""
        sorted_structure = {}
        # Ordina le chiavi (percorsi)
        for path in sorted(structure.keys()):
            # Ordina i file in ogni cartella
            sorted_structure[path] = sorted(
                structure[path],
                key=lambda x: (x["type"], x["name"].lower())
            )
        return sorted_structure
    
    def _sort_files(self, files: List) -> List:
        """Ordina la lista dei file"""
        return sorted(
            files,
            key=lambda x: (x.get("path", ""), x["name"].lower())
        )