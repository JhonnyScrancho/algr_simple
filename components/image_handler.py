import base64
from PIL import Image
from io import BytesIO
import streamlit as st

class ImageHandler:
    """Gestisce il caricamento e l'elaborazione delle immagini per i modelli LLM"""
    
    def __init__(self):
        self.supported_formats = ['png', 'jpg', 'jpeg']
        self.max_image_size = 5 * 1024 * 1024  # 5MB
    
    def process_image(self, uploaded_file) -> dict:
        """Processa l'immagine caricata"""
        if uploaded_file.size > self.max_image_size:
            return {
                "success": False,
                "error": f"Immagine troppo grande (max {self.max_image_size/1024/1024}MB)"
            }
        
        try:
            # Leggi l'immagine con PIL
            image = Image.open(uploaded_file)
            
            # Converti in JPEG se necessario
            if image.format != 'JPEG':
                rgb_im = image.convert('RGB')
                img_byte_arr = BytesIO()
                rgb_im.save(img_byte_arr, format='JPEG', quality=85)
                img_byte_arr = img_byte_arr.getvalue()
            else:
                img_byte_arr = uploaded_file.getvalue()
            
            # Codifica in base64
            base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
            
            return {
                "success": True,
                "base64": base64_image,
                "format": "jpeg",
                "size": len(img_byte_arr)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nel processare l'immagine: {str(e)}"
            }