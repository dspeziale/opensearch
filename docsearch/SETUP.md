# DocSearch - Setup e Avvio con OpenSearch

## 📋 Prerequisiti

1. **OpenSearch** installato sul PC
2. **Python 3.9+**
3. **pip** per installare le dipendenze

## 🚀 Avvio Rapido

### 1. Avvia OpenSearch

Se OpenSearch non è già in esecuzione, avvialo:

```bash
# Se hai installato OpenSearch con tar.gz
cd /path/to/opensearch
./bin/opensearch

# Oppure se hai installato con Docker
docker run -d -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin@123" \
  opensearchproject/opensearch:latest

# Oppure se hai un servizio systemd
sudo systemctl start opensearch
```

**Verifica che OpenSearch sia attivo:**
```bash
curl -X GET "http://localhost:9200" -u admin:admin -k
```

Dovresti vedere una risposta JSON con le info del cluster.

### 2. Installa le Dipendenze Python

```bash
cd /home/user/opensearch/docsearch
pip install -r requirements.txt
```

**Note sulle dipendenze:**
- Se hai problemi con `pypff`, potrebbe richiedere librerie di sistema:
  ```bash
  sudo apt-get install libpff-dev  # Ubuntu/Debian
  ```

### 3. Configura il Sistema

Il file `.env` è già stato creato con la configurazione di default:
- OpenSearch: `localhost:9200`
- Credenziali: `admin/admin`
- Porta Flask: `5000`

**Se la tua installazione OpenSearch usa credenziali diverse**, modifica il file `.env`:
```bash
nano .env
```

### 4. Avvia DocSearch

```bash
python app.py
```

L'applicazione sarà disponibile su: **http://localhost:5000**

## 🔍 Verifica Installazione

1. **Verifica OpenSearch:**
   ```bash
   curl -XGET "http://localhost:9200/_cluster/health" -u admin:admin -k
   ```

2. **Verifica indice documenti:**
   ```bash
   curl -XGET "http://localhost:9200/documents" -u admin:admin -k
   ```

3. **Testa l'applicazione:**
   - Apri http://localhost:5000
   - Vai su "Carica Documenti"
   - Carica un file di test
   - Cerca il documento dalla homepage

## 📁 Formati File Supportati

Il sistema supporta **18 formati** diversi:

### Documenti
- ✅ PDF
- ✅ DOC/DOCX (Word)
- ✅ RTF (Rich Text Format)
- ✅ ODT (OpenDocument Text)
- ✅ TXT, MD (Markdown)

### Dati
- ✅ XLS/XLSX (Excel)
- ✅ CSV
- ✅ JSON
- ✅ XML

### Email
- ✅ MSG (Outlook Message)
- ✅ PST (Outlook Archive)

### Presentazioni
- ✅ PPTX (PowerPoint)

### Altri
- ✅ HTML
- ✅ ZIP (con estrazione contenuto)

## 🔧 Configurazione Avanzata

### Cambia Porta

Modifica nel file `.env`:
```env
PORT=8080
```

### Usa OpenSearch Remoto

Se hai OpenSearch su un server remoto:
```env
OPENSEARCH_HOST=192.168.1.100
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=your-password
```

### Abilita OpenAI (Opzionale)

Per risposte ancora più intelligenti:
```env
USE_OPENAI=true
OPENAI_API_KEY=sk-your-api-key
```

## 🐛 Risoluzione Problemi

### OpenSearch non si connette

**Errore:** `Connection refused`

**Soluzioni:**
1. Verifica che OpenSearch sia in esecuzione:
   ```bash
   ps aux | grep opensearch
   ```

2. Verifica la porta:
   ```bash
   netstat -tlnp | grep 9200
   ```

3. Controlla i log di OpenSearch:
   ```bash
   tail -f /path/to/opensearch/logs/opensearch.log
   ```

### Errore "SSL: CERTIFICATE_VERIFY_FAILED"

Se OpenSearch usa SSL auto-firmato, assicurati che nel file `.env` sia:
```env
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false
```

Oppure modifica `opensearch_manager.py` per disabilitare la verifica SSL.

### Memoria insufficiente

Se OpenSearch usa troppa memoria, puoi limitarla:
```bash
export OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m"
./bin/opensearch
```

### Dipendenze mancanti

Se hai errori con le librerie:
```bash
# Reinstalla tutto
pip install --force-reinstall -r requirements.txt

# Oppure installa una dipendenza specifica
pip install python-pptx
```

## 📊 Struttura Dati OpenSearch

Il sistema crea automaticamente l'indice `documents` con il seguente schema:

```json
{
  "filename": "documento.pdf",
  "extension": ".pdf",
  "type": "PDF Document",
  "content": "testo estratto...",
  "summary": "riassunto automatico...",
  "keywords": ["keyword1", "keyword2"],
  "tags": ["tag1", "tag2"],
  "metadata": {
    "size": 1024000,
    "path": "/path/to/file"
  },
  "indexed_at": "2025-11-10T10:00:00",
  "file_size": 1024000,
  "file_path": "/uploads/20251110_100000_documento.pdf"
}
```

## 🎯 Funzionalità Principali

### 1. Upload Singolo
- Carica un file alla volta
- Aggiungi tags personalizzati
- Estrazione automatica keywords

### 2. Upload Directory
- Carica intere cartelle
- Processa tutti i file supportati
- Applica tags globali

### 3. Ricerca Intelligente
- Ricerca full-text
- Filtro per tags
- Risposte con RAG (Retrieval Augmented Generation)
- Confidence scoring
- Suggerimenti correlati

### 4. Gestione Documenti
- Visualizza tutti i documenti
- Filtra per tipo
- Dettagli completi
- Elimina documenti

## 📝 Log e Debug

I log dell'applicazione vengono mostrati nella console. Per maggiori dettagli:

```python
# Modifica in app.py
logging.basicConfig(level=logging.DEBUG)
```

## 🔐 Sicurezza

**IMPORTANTE per produzione:**

1. Cambia `SECRET_KEY` nel file `.env`
2. Usa credenziali forti per OpenSearch
3. Abilita SSL su OpenSearch
4. Limita l'accesso alla porta 5000
5. Usa un reverse proxy (nginx/apache)

## 🆘 Supporto

- **Documentazione OpenSearch:** https://opensearch.org/docs/
- **Repository:** https://github.com/dspeziale/opensearch

---

**Buon utilizzo del sistema documentale! 🚀**
