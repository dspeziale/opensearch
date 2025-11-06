"""
Microservizio API per caricare/aggiornare tabelle MSSQL
Utilizza FastAPI per esporre endpoint REST
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uvicorn
import pyodbc
import pandas as pd
import os
from datetime import datetime
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inizializzazione FastAPI
app = FastAPI(
    title="MSSQL Upload API",
    description="Microservizio per caricare e aggiornare dati su MSSQL",
    version="1.0.0"
)


# Modelli Pydantic per validazione
class DatabaseConfig(BaseModel):
    server: str = Field(..., description="Server MSSQL")
    database: str = Field(..., description="Nome database")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    port: int = Field(default=1433, description="Porta MSSQL")


class TableData(BaseModel):
    table_name: str = Field(..., description="Nome tabella")
    data: List[Dict[str, Any]] = Field(..., description="Dati da inserire")
    operation: str = Field(default="insert", description="Operazione: insert, update, upsert")
    primary_key: Optional[str] = Field(None, description="Chiave primaria per update/upsert")


class UpdateData(BaseModel):
    table_name: str = Field(..., description="Nome tabella")
    data: Dict[str, Any] = Field(..., description="Dati da aggiornare")
    where: Dict[str, Any] = Field(..., description="Condizioni WHERE")


# Gestione connessioni al database
def get_connection(config: DatabaseConfig):
    """Crea connessione al database MSSQL"""
    try:
        # Stringa di connessione per pyodbc
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config.server},{config.port};"
            f"DATABASE={config.database};"
            f"UID={config.username};"
            f"PWD={config.password}"
        )

        connection = pyodbc.connect(conn_str, timeout=30)
        logger.info(f"Connessione stabilita con {config.server}/{config.database}")
        return connection
    except Exception as e:
        logger.error(f"Errore connessione database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore connessione: {str(e)}")


def get_connection_from_env():
    """Ottiene connessione usando variabili d'ambiente"""
    config = DatabaseConfig(
        server=os.getenv("MSSQL_SERVER", "localhost"),
        database=os.getenv("MSSQL_DATABASE", "testdb"),
        username=os.getenv("MSSQL_USERNAME", "sa"),
        password=os.getenv("MSSQL_PASSWORD", ""),
        port=int(os.getenv("MSSQL_PORT", "1433"))
    )
    return get_connection(config)


# Endpoint API
@app.get("/")
async def root():
    """Endpoint di test"""
    return {
        "message": "MSSQL Upload API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_connection_from_env()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post("/api/v1/insert")
async def insert_data(table_data: TableData, config: Optional[DatabaseConfig] = None):
    """
    Inserisce dati in una tabella MSSQL

    Args:
        table_data: Dati della tabella e record da inserire
        config: Configurazione database (opzionale, usa env se non fornita)
    """
    try:
        # Connessione
        if config:
            conn = get_connection(config)
        else:
            conn = get_connection_from_env()

        cursor = conn.cursor()

        # Costruzione query INSERT
        columns = list(table_data.data[0].keys())
        placeholders = ','.join(['?' for _ in columns])
        columns_str = ','.join([f"[{col}]" for col in columns])

        insert_query = f"INSERT INTO [{table_data.table_name}] ({columns_str}) VALUES ({placeholders})"

        # Inserimento dati
        rows_inserted = 0
        for row in table_data.data:
            values = [row[col] for col in columns]
            cursor.execute(insert_query, values)
            rows_inserted += 1

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Inseriti {rows_inserted} record in {table_data.table_name}")

        return {
            "status": "success",
            "table": table_data.table_name,
            "rows_inserted": rows_inserted,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Errore inserimento dati: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/update")
async def update_data(update_data: UpdateData, config: Optional[DatabaseConfig] = None):
    """
    Aggiorna dati in una tabella MSSQL

    Args:
        update_data: Dati da aggiornare e condizioni WHERE
        config: Configurazione database (opzionale)
    """
    try:
        # Connessione
        if config:
            conn = get_connection(config)
        else:
            conn = get_connection_from_env()

        cursor = conn.cursor()

        # Costruzione query UPDATE
        set_clause = ','.join([f"[{col}]=?" for col in update_data.data.keys()])
        where_clause = ' AND '.join([f"[{col}]=?" for col in update_data.where.keys()])

        update_query = f"UPDATE [{update_data.table_name}] SET {set_clause} WHERE {where_clause}"

        # Valori per la query
        values = list(update_data.data.values()) + list(update_data.where.values())

        cursor.execute(update_query, values)
        rows_affected = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Aggiornati {rows_affected} record in {update_data.table_name}")

        return {
            "status": "success",
            "table": update_data.table_name,
            "rows_updated": rows_affected,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Errore aggiornamento dati: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/upsert")
async def upsert_data(table_data: TableData, config: Optional[DatabaseConfig] = None):
    """
    Inserisce o aggiorna dati (UPSERT/MERGE)

    Args:
        table_data: Dati da inserire/aggiornare con chiave primaria
        config: Configurazione database (opzionale)
    """
    if not table_data.primary_key:
        raise HTTPException(
            status_code=400,
            detail="primary_key è richiesto per operazione upsert"
        )

    try:
        # Connessione
        if config:
            conn = get_connection(config)
        else:
            conn = get_connection_from_env()

        cursor = conn.cursor()

        rows_inserted = 0
        rows_updated = 0

        for row in table_data.data:
            # Verifica se il record esiste
            check_query = f"SELECT COUNT(*) FROM [{table_data.table_name}] WHERE [{table_data.primary_key}]=?"
            cursor.execute(check_query, row[table_data.primary_key])
            exists = cursor.fetchone()[0] > 0

            if exists:
                # UPDATE
                columns = [col for col in row.keys() if col != table_data.primary_key]
                set_clause = ','.join([f"[{col}]=?" for col in columns])
                update_query = f"UPDATE [{table_data.table_name}] SET {set_clause} WHERE [{table_data.primary_key}]=?"

                values = [row[col] for col in columns] + [row[table_data.primary_key]]
                cursor.execute(update_query, values)
                rows_updated += 1
            else:
                # INSERT
                columns = list(row.keys())
                placeholders = ','.join(['?' for _ in columns])
                columns_str = ','.join([f"[{col}]" for col in columns])
                insert_query = f"INSERT INTO [{table_data.table_name}] ({columns_str}) VALUES ({placeholders})"

                values = [row[col] for col in columns]
                cursor.execute(insert_query, values)
                rows_inserted += 1

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Upsert completato: {rows_inserted} inseriti, {rows_updated} aggiornati")

        return {
            "status": "success",
            "table": table_data.table_name,
            "rows_inserted": rows_inserted,
            "rows_updated": rows_updated,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Errore upsert dati: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    table_name: str = None,
    operation: str = "insert",
    primary_key: Optional[str] = None
):
    """
    Carica dati da file CSV in tabella MSSQL

    Args:
        file: File CSV da caricare
        table_name: Nome tabella destinazione
        operation: insert, update, o upsert
        primary_key: Chiave primaria per upsert
    """
    try:
        # Leggi CSV
        contents = await file.read()

        # Salva temporaneamente
        temp_file = f"/tmp/{file.filename}"
        with open(temp_file, "wb") as f:
            f.write(contents)

        # Leggi con pandas
        df = pd.read_csv(temp_file)

        # Converti in lista di dizionari
        data = df.to_dict('records')

        # Crea TableData
        table_data = TableData(
            table_name=table_name or file.filename.replace('.csv', ''),
            data=data,
            operation=operation,
            primary_key=primary_key
        )

        # Esegui operazione appropriata
        if operation == "insert":
            result = await insert_data(table_data)
        elif operation == "upsert":
            result = await upsert_data(table_data)
        else:
            raise HTTPException(status_code=400, detail="Operazione non supportata")

        # Rimuovi file temporaneo
        os.remove(temp_file)

        return result

    except Exception as e:
        logger.error(f"Errore upload CSV: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/delete")
async def delete_data(
    table_name: str,
    where: Dict[str, Any],
    config: Optional[DatabaseConfig] = None
):
    """
    Elimina record da una tabella

    Args:
        table_name: Nome tabella
        where: Condizioni WHERE per eliminazione
        config: Configurazione database (opzionale)
    """
    try:
        # Connessione
        if config:
            conn = get_connection(config)
        else:
            conn = get_connection_from_env()

        cursor = conn.cursor()

        # Costruzione query DELETE
        where_clause = ' AND '.join([f"[{col}]=?" for col in where.keys()])
        delete_query = f"DELETE FROM [{table_name}] WHERE {where_clause}"

        values = list(where.values())
        cursor.execute(delete_query, values)
        rows_deleted = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Eliminati {rows_deleted} record da {table_name}")

        return {
            "status": "success",
            "table": table_name,
            "rows_deleted": rows_deleted,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Errore eliminazione dati: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Avvia server
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
