# import streamlit as st
# from typing import Any, Dict, Optional

# def debug_file_state(location: str, files: Any = None, context: Optional[Dict] = None):
#     """Utility per logging dello stato dei file e del contesto"""
#     with st.expander(f"🔍 Debug Info: {location}", expanded=True):
#         st.markdown("---")
        
#         # Session State Check
#         st.markdown("### 📌 SESSION STATE:")
#         if hasattr(st.session_state, 'current_files'):
#             if st.session_state.current_files:
#                 st.info(f"current_files: {len(st.session_state.current_files)} files")
#                 for f in st.session_state.current_files[:2]:
#                     st.code(f"""
#                     - File: {f.get('name', 'N/A')}
#                     - Path: {f.get('path', 'N/A')}
#                     - Content Length: {len(f['content']) if 'content' in f else 'No content'}
#                     """)
#             else:
#                 st.warning("current_files: None/Empty")
#         else:
#             st.error("current_files: Not in session_state")

#         # Files Parameter Check
#         if files is not None:
#             st.markdown("### 📂 FILES PARAMETER:")
#             if isinstance(files, list):
#                 st.info(f"Files in list: {len(files)}")
#                 for f in files[:2]:
#                     if isinstance(f, dict):
#                         st.code(f"""
#                         - File: {f.get('name', 'N/A')}
#                         - Path: {f.get('path', 'N/A')}
#                         - Content Length: {len(f['content']) if 'content' in f else 'No content'}
#                         """)
#             else:
#                 st.warning(f"files type: {type(files)}")

#         # Context Check
#         if context is not None:
#             st.markdown("### 🔄 CONTEXT:")
#             for key in context:
#                 if key == 'available_files' and isinstance(context[key], list):
#                     st.info(f"available_files: {len(context[key])} files")
#                     for f in context[key][:2]:
#                         st.code(f"""
#                         - File: {f.get('name', 'N/A')}
#                         - Content Length: {len(f['content']) if 'content' in f else 'No content'}
#                         """)
#                 elif key == 'current_files' and isinstance(context[key], list):
#                     st.info(f"current_files: {len(context[key])} files")
#                     for f in context[key][:2]:
#                         st.code(f"""
#                         - File: {f.get('name', 'N/A')}
#                         - Content Length: {len(f['content']) if 'content' in f else 'No content'}
#                         """)
#                 else:
#                     st.info(f"{key}: {type(context[key])}")

# def debug_zip_processing(zip_content: Any, stage: str):
#     """Debug specifico per il processing ZIP"""
#     with st.expander(f"🔍 ZIP Processing: {stage}", expanded=True):
#         st.markdown("---")
        
#         if isinstance(zip_content, dict):
#             if 'files' in zip_content:
#                 files = zip_content['files']
#                 st.info(f"Files found: {len(files)}")
#                 for f in files[:2]:
#                     st.code(f"""
#                     - File: {f.get('name', 'N/A')}
#                     - Content Length: {len(f['content']) if 'content' in f else 'No content'}
#                     - Path: {f.get('path', 'N/A')}
#                     """)
            
#             if 'structure' in zip_content:
#                 st.markdown("### 📁 Structure:")
#                 for path, items in zip_content['structure'].items():
#                     st.markdown(f"**Directory:** {path or 'root'}")
#                     if isinstance(items, list):
#                         for item in items[:2]:
#                             if isinstance(item, dict):
#                                 st.code(f"- {item.get('name', 'N/A')}")