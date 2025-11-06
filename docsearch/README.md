# 🔍 DocSearch - Sistema di Documentazione Intelligente

Sistema avanzato di gestione e ricerca documentale con **OpenSearch** e **AI** per risposte intelligenti.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![OpenSearch](https://img.shields.io/badge/OpenSearch-2.11-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Caratteristiche

- 🧠 **Ricerca Intelligente** - Usa linguaggio naturale per cercare nei documenti
- 🤖 **RAG (Retrieval Augmented Generation)** - Risposte intelligenti con percorsi di approfondimento
- 📄 **Multi-formato** - Supporta PDF, Word, Excel, HTML, Markdown, TXT, CSV
- ⚡ **Indicizzazione Automatica** - Upload e indicizzazione in un click
- 🎯 **Estrazione Keywords** - Keywords estratte automaticamente
- 📊 **Summary Automatico** - Ogni documento viene riassunto
- 🎨 **Interfaccia AdminLTE** - UI moderna e responsive
- 🔄 **Full-text Search** - Ricerca ottimizzata con OpenSearch

## 🎬 Demo

### Homepage con Ricerca Intelligente
- Form di ricerca con suggerimenti
- Risposta intelligente con confidenza
- Percorso di approfondimento step-by-step
- Suggerimenti per ricerche correlate
- Lista documenti rilevanti con highlights

### Upload Documenti
- Drag & drop o selezione file
- Progress bar upload
- Parsing automatico multi-formato
- Indicizzazione immediata

### Gestione Documenti
- Lista tutti i documenti indicizzati
- Filtri per tipo e nome
- Visualizzazione dettagli
- Eliminazione documenti

## 🚀 Quick Start

### Prerequisiti

- Python 3.9+
- Docker & Docker Compose (per OpenSearch)
- 2GB RAM minimo

### 1. Clone Repository

```bash
cd docsearch/
```

### 2. Avvia OpenSearch con Docker

```bash
docker-compose up -d opensearch
```

Verifica che OpenSearch sia avviato:
```bash
curl http://localhost:9200
```

### 3. Configura Environment

```bash
cp .env.example .env
```

Modifica `.env` se necessario (opzionale):
```bash
nano .env
```

### 4. Installa Dipendenze

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Avvia Applicazione

```bash
./run.sh
```

Oppure manualmente:
```bash
python app.py
```

### 6. Apri Browser

Vai su: **http://localhost:5000**

🎉 **Fatto!** Ora puoi caricare documenti e iniziare a cercare!

## 📁 Struttura Progetto

```
docsearch/
├── app.py                      # Applicazione Flask principale
├── document_parser.py          # Parser multi-formato
├── opensearch_manager.py       # Manager OpenSearch
├── rag_engine.py              # Motore RAG per risposte intelligenti
├── config.py                  # Configurazione
├── requirements.txt           # Dipendenze Python
├── docker-compose.yml         # OpenSearch Docker setup
├── run.sh                     # Script avvio rapido
├── .env.example               # Template configurazione
│
├── templates/                 # Templates HTML
│   ├── base.html             # Template base AdminLTE
│   ├── index.html            # Homepage ricerca
│   ├── upload.html           # Upload documenti
│   ├── documents.html        # Lista documenti
│   ├── about.html            # Info
│   ├── 404.html              # Not found
│   └── 500.html              # Server error
│
└── static/                    # File statici
    └── uploads/              # Documenti caricati
```

## 📚 Formati Supportati

| Formato | Estensioni | Descrizione |
|---------|-----------|-------------|
| **PDF** | `.pdf` | Portable Document Format |
| **Word** | `.doc`, `.docx` | Microsoft Word |
| **Excel** | `.xls`, `.xlsx` | Microsoft Excel |
| **CSV** | `.csv` | Comma Separated Values |
| **HTML** | `.html`, `.htm` | Pagine Web |
| **Markdown** | `.md` | Markdown |
| **Text** | `.txt` | Plain Text |
| **Outlook** | `.msg` | Singoli messaggi email Outlook |
| **Outlook** | `.pst` | Archivi Outlook (inbox, folders) |

## 🎯 Come Funziona

### 1. Upload Documento

```python
# L'utente carica un file tramite web UI
POST /api/upload
```

### 2. Parsing

```python
# DocumentParser estrae il contenuto
parser = DocumentParser()
parsed = parser.parse(file_path)

# Output:
{
    'content': 'testo estratto...',
    'keywords': ['keyword1', 'keyword2', ...],
    'summary': 'breve riassunto...',
    'metadata': {...}
}
```

### 3. Indicizzazione

```python
# OpenSearchManager indicizza in OpenSearch
opensearch = OpenSearchManager()
opensearch.index_document(parsed)
```

### 4. Ricerca

```python
# Ricerca full-text con fuzzy matching
results = opensearch.search("come installare opensearch")
```

### 5. RAG Response

```python
# RAG Engine genera risposta intelligente
rag = RAGEngine()
response = rag.generate_answer(SearchContext(
    query=query,
    results=results
))

# Output:
{
    'answer': 'risposta dettagliata...',
    'confidence': 0.85,
    'sources': [...],
    'flow': ['step1', 'step2', ...],
    'suggestions': ['cerca anche...', ...]
}
```

## 🔧 Configurazione Avanzata

### Variabili Environment (.env)

```bash
# Flask
SECRET_KEY=your-secret-key
DEBUG=false
PORT=5000

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=admin

# OpenAI (opzionale - per risposte ancora più intelligenti)
USE_OPENAI=true
OPENAI_API_KEY=sk-...

# Upload
MAX_UPLOAD_SIZE_MB=50
```

### OpenAI Integration

Per abilitare risposte ancora più intelligenti con GPT:

1. Ottieni API key da: https://platform.openai.com/api-keys

2. Configura `.env`:
```bash
USE_OPENAI=true
OPENAI_API_KEY=sk-your-key-here
```

3. Riavvia applicazione

### Production Deployment

#### Con Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Con Nginx (reverse proxy)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 API Endpoints

### Ricerca

```bash
POST /api/search
Content-Type: application/json

{
    "query": "come installare opensearch",
    "size": 10,
    "use_rag": true
}
```

### Upload

```bash
POST /api/upload
Content-Type: multipart/form-data

file: <binary>
```

### Lista Documenti

```bash
GET /api/documents?page=1&size=20
```

### Dettagli Documento

```bash
GET /api/document/<doc_id>
```

### Elimina Documento

```bash
DELETE /api/document/<doc_id>
```

### Statistiche

```bash
GET /api/statistics
```

## 🎨 Personalizzazione UI

L'interfaccia usa **AdminLTE 3** Light Mode. Per personalizzare:

1. Modifica `templates/base.html` per cambiare layout
2. Aggiungi CSS custom in `static/css/`
3. Modifica colori nei template individuali

## 🧪 Testing

### Test DocumentParser

```bash
cd docsearch/
python document_parser.py
```

### Test OpenSearch Manager

```bash
python opensearch_manager.py
```

### Test RAG Engine

```bash
python rag_engine.py
```

## 📈 Performance

- **Parsing**: ~1-2 secondi per documento (dipende da dimensione)
- **Indicizzazione**: ~100ms per documento
- **Ricerca**: ~50-200ms (dipende da corpus size)
- **RAG Response**: ~500ms senza OpenAI, ~2s con OpenAI

## 🐛 Troubleshooting

### OpenSearch non si connette

```bash
# Verifica che OpenSearch sia running
docker ps | grep opensearch

# Verifica logs
docker logs docsearch-opensearch

# Riavvia
docker-compose restart opensearch
```

### Errore upload file

- Verifica dimensione file < 50MB
- Verifica formato supportato
- Controlla permessi cartella `static/uploads/`

### Parsing fallisce

- Alcuni PDF con protezione potrebbero non essere leggibili
- File Word molto vecchi (.doc) potrebbero non essere supportati
- Prova a convertire il file in formato più recente

## 🤝 Contributing

Contributi benvenuti!

1. Fork il progetto
2. Crea branch feature (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 TODO / Future Features

- [ ] Supporto OCR per PDF scansionati
- [ ] Ricerca semantica con embeddings
- [ ] Multi-tenancy con utenti
- [ ] Export risultati ricerca (PDF, Excel)
- [ ] API REST completa con autenticazione
- [ ] Supporto più lingue (NLP multilingua)
- [ ] Dashboard analytics
- [ ] Scheduled re-indexing
- [ ] Integrazione con storage cloud (S3, GCS)
- [ ] Mobile app

## 📄 License

MIT License - see LICENSE file

## 👤 Author

Creato con ❤️ per fornire ricerca documentale intelligente e user-friendly

---

## 🎓 Learn More

- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [AdminLTE Documentation](https://adminlte.io/docs/)
- [RAG Systems](https://www.pinecone.io/learn/retrieval-augmented-generation/)

## 💬 Support

Per domande o supporto:
- Apri una Issue su GitHub
- Consulta la pagina About nell'applicazione

---

**Buona ricerca! 🚀**
