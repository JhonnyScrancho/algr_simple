# Developer AI Assistant

Una chat AI per sviluppatori basata su Streamlit e Claude-3.

## Setup

1. Clona il repository
```bash
git clone <repository-url>
cd project
```

2. Crea e attiva un ambiente virtuale
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

3. Installa le dipendenze
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Per sviluppo/test
```

4. Configura le variabili d'ambiente
```bash
cp .env.example .env
# Modifica .env con le tue chiavi API
```

5. Avvia l'applicazione
```bash
streamlit run app.py
```

## Struttura del Progetto

```
project/
├── app.py                 # Applicazione principale
├── components/           # Componenti UI
├── services/            # Logica di business
├── utils/              # Utility
├── config/            # Configurazioni
├── static/            # Asset statici
└── tests/             # Test suite
```

## Testing

Esegui i test con:
```bash
pytest
```

## Licenza

MIT