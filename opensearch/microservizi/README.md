# Microservizio MSSQL Upload

Microservizio per caricare e aggiornare dati su tabelle Microsoft SQL Server (MSSQL).

## Caratteristiche

- **API REST** con FastAPI per operazioni CRUD
- **Script Python** per upload diretto o tramite API
- Supporto per operazioni: **INSERT**, **UPDATE**, **UPSERT**, **DELETE**
- Upload da file **CSV** o **JSON**
- Validazione dati con Pydantic
- Logging completo delle operazioni
- Configurazione tramite variabili d'ambiente

## Prerequisiti

### 1. SQL Server ODBC Driver

Il microservizio richiede il driver ODBC per SQL Server.

**Linux (Ubuntu/Debian):**
```bash
# Aggiungi repository Microsoft
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Installa driver
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

**macOS:**
```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew install msodbcsql17
```

**Windows:**
- Scarica e installa da: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

### 2. Python 3.8+

Assicurati di avere Python 3.8 o superiore installato.

## Installazione

### 1. Clona e installa dipendenze

```bash
cd opensearch/microservizi

# Crea virtual environment (consigliato)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt
```

### 2. Configura ambiente

```bash
# Copia file esempio
cp .env.example .env

# Modifica con i tuoi parametri
nano .env
```

Parametri in `.env`:
```env
MSSQL_SERVER=your-server.database.windows.net
MSSQL_DATABASE=your-database
MSSQL_USERNAME=your-username
MSSQL_PASSWORD=your-password
MSSQL_PORT=1433

API_PORT=8000
API_URL=http://localhost:8000
```

## Utilizzo

### Modalità 1: API REST

#### Avvia il server API

```bash
python api.py
```

Il server sarà disponibile su `http://localhost:8000`

#### Documetazione API interattiva

Apri nel browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### Esempi di chiamate API

**1. Health Check**
```bash
curl http://localhost:8000/health
```

**2. Inserimento dati**
```bash
curl -X POST "http://localhost:8000/api/v1/insert" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "employees",
    "data": [
      {
        "id": 1,
        "name": "Mario Rossi",
        "email": "mario.rossi@example.com",
        "department": "IT"
      },
      {
        "id": 2,
        "name": "Laura Bianchi",
        "email": "laura.bianchi@example.com",
        "department": "HR"
      }
    ]
  }'
```

**3. Aggiornamento dati**
```bash
curl -X POST "http://localhost:8000/api/v1/update" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "employees",
    "data": {
      "department": "Finance"
    },
    "where": {
      "id": 1
    }
  }'
```

**4. Upsert (inserisci o aggiorna)**
```bash
curl -X POST "http://localhost:8000/api/v1/upsert" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "employees",
    "primary_key": "id",
    "data": [
      {
        "id": 1,
        "name": "Mario Rossi",
        "email": "mario.rossi@newmail.com",
        "department": "IT"
      },
      {
        "id": 3,
        "name": "Giuseppe Verdi",
        "email": "giuseppe.verdi@example.com",
        "department": "Sales"
      }
    ]
  }'
```

**5. Upload CSV**
```bash
curl -X POST "http://localhost:8000/api/v1/upload-csv" \
  -F "file=@data.csv" \
  -F "table_name=employees" \
  -F "operation=upsert" \
  -F "primary_key=id"
```

**6. Eliminazione dati**
```bash
curl -X DELETE "http://localhost:8000/api/v1/delete?table_name=employees" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1
  }'
```

### Modalità 2: Script Python Diretto

#### Upload da CSV (connessione diretta)

```bash
python mssql_uploader.py \
  --mode direct \
  --operation insert \
  --table employees \
  --csv-file data.csv \
  --server your-server.database.windows.net \
  --database your-database \
  --username your-username \
  --password your-password
```

#### Upload da CSV (tramite API)

```bash
python mssql_uploader.py \
  --mode api \
  --operation upsert \
  --table employees \
  --csv-file data.csv \
  --primary-key id \
  --api-url http://localhost:8000
```

#### Upload da JSON

```bash
python mssql_uploader.py \
  --mode direct \
  --operation insert \
  --table employees \
  --json-file data.json
```

### Modalità 3: Utilizzo Programmatico

#### Connessione diretta

```python
from mssql_uploader import MSSQLUploader

# Inizializza uploader
uploader = MSSQLUploader(
    server="your-server.database.windows.net",
    database="your-database",
    username="your-username",
    password="your-password"
)

# Connetti
uploader.connect()

# Inserisci dati
data = [
    {"id": 1, "name": "Mario Rossi", "email": "mario@example.com"},
    {"id": 2, "name": "Laura Bianchi", "email": "laura@example.com"}
]
uploader.insert_data("employees", data)

# Aggiorna dati
uploader.update_data(
    table_name="employees",
    data={"department": "IT"},
    where={"id": 1}
)

# Upsert
uploader.upsert_data(
    table_name="employees",
    data=data,
    primary_key="id"
)

# Carica da CSV
uploader.load_from_csv(
    csv_file="data.csv",
    table_name="employees",
    operation="upsert",
    primary_key="id"
)

# Disconnetti
uploader.disconnect()
```

#### Tramite API Client

```python
from mssql_uploader import MSSQLAPIClient

# Inizializza client
client = MSSQLAPIClient(api_url="http://localhost:8000")

# Inserisci dati
data = [
    {"id": 1, "name": "Mario Rossi", "email": "mario@example.com"}
]
result = client.insert_data("employees", data)
print(result)

# Upsert
result = client.upsert_data(
    table_name="employees",
    data=data,
    primary_key="id"
)

# Upload CSV
result = client.upload_csv(
    csv_file="data.csv",
    table_name="employees",
    operation="upsert",
    primary_key="id"
)
```

## Struttura File

```
opensearch/microservizi/
├── api.py                  # Microservizio FastAPI
├── mssql_uploader.py       # Script upload/client
├── requirements.txt        # Dipendenze Python
├── .env.example           # Esempio configurazione
└── README.md              # Documentazione
```

## Esempi di Dati

### File CSV (data.csv)
```csv
id,name,email,department
1,Mario Rossi,mario.rossi@example.com,IT
2,Laura Bianchi,laura.bianchi@example.com,HR
3,Giuseppe Verdi,giuseppe.verdi@example.com,Sales
```

### File JSON (data.json)
```json
[
  {
    "id": 1,
    "name": "Mario Rossi",
    "email": "mario.rossi@example.com",
    "department": "IT"
  },
  {
    "id": 2,
    "name": "Laura Bianchi",
    "email": "laura.bianchi@example.com",
    "department": "HR"
  }
]
```

## Creare Tabella di Test

```sql
CREATE TABLE employees (
    id INT PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(100) NOT NULL,
    department NVARCHAR(50)
);
```

## Docker Deployment (Opzionale)

### Dockerfile

Crea un file `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Installa ODBC driver
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "api.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  mssql-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MSSQL_SERVER=${MSSQL_SERVER}
      - MSSQL_DATABASE=${MSSQL_DATABASE}
      - MSSQL_USERNAME=${MSSQL_USERNAME}
      - MSSQL_PASSWORD=${MSSQL_PASSWORD}
      - MSSQL_PORT=1433
      - API_PORT=8000
    restart: unless-stopped
```

### Avvia con Docker

```bash
# Build
docker-compose build

# Avvia
docker-compose up -d

# Logs
docker-compose logs -f
```

## Troubleshooting

### Errore: "Driver not found"

Assicurati di aver installato il driver ODBC. Verifica con:
```bash
odbcinst -q -d
```

Dovresti vedere `ODBC Driver 17 for SQL Server` nell'elenco.

### Errore di connessione

1. Verifica che SQL Server accetti connessioni remote
2. Controlla il firewall sulla porta 1433
3. Verifica username e password
4. Per Azure SQL, assicurati che l'IP sia nella whitelist

### Errore di timeout

Aumenta il timeout nella stringa di connessione:
```python
pyodbc.connect(conn_str, timeout=60)
```

## Sicurezza

- **NON committare** file `.env` con credenziali
- Usa variabili d'ambiente per le credenziali in produzione
- Considera l'uso di Azure Key Vault o simili per gestire segreti
- Abilita SSL/TLS per connessioni in produzione
- Limita accesso all'API con autenticazione (es. API keys, OAuth2)

## Performance

### Batch Insert

Per inserimenti di grandi quantità di dati, considera l'uso di:
```python
cursor.fast_executemany = True
cursor.executemany(query, data)
```

### Connection Pooling

Per applicazioni ad alto traffico, implementa connection pooling.

## Licenza

MIT

## Supporto

Per problemi o domande, apri una issue nel repository.
