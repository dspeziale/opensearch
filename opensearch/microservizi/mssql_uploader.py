"""
Script Python per caricare/aggiornare tabelle MSSQL
Può lavorare sia direttamente con il database che tramite API
"""

import pyodbc
import pandas as pd
import requests
import json
import os
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MSSQLUploader:
    """Classe per gestire upload/update su MSSQL"""

    def __init__(
        self,
        server: str,
        database: str,
        username: str,
        password: str,
        port: int = 1433
    ):
        """
        Inizializza uploader MSSQL

        Args:
            server: Server MSSQL
            database: Nome database
            username: Username
            password: Password
            port: Porta (default 1433)
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.connection = None

    def connect(self):
        """Crea connessione al database"""
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password}"
            )

            self.connection = pyodbc.connect(conn_str, timeout=30)
            logger.info(f"Connesso a {self.server}/{self.database}")
            return True

        except Exception as e:
            logger.error(f"Errore connessione: {str(e)}")
            return False

    def disconnect(self):
        """Chiude connessione"""
        if self.connection:
            self.connection.close()
            logger.info("Connessione chiusa")

    def insert_data(self, table_name: str, data: List[Dict[str, Any]]) -> int:
        """
        Inserisce dati in una tabella

        Args:
            table_name: Nome tabella
            data: Lista di dizionari con i dati

        Returns:
            Numero di righe inserite
        """
        if not self.connection:
            raise Exception("Nessuna connessione attiva")

        try:
            cursor = self.connection.cursor()

            # Costruzione query
            columns = list(data[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            columns_str = ','.join([f"[{col}]" for col in columns])

            insert_query = f"INSERT INTO [{table_name}] ({columns_str}) VALUES ({placeholders})"

            # Inserimento batch
            rows_inserted = 0
            for row in data:
                values = [row[col] for col in columns]
                cursor.execute(insert_query, values)
                rows_inserted += 1

            self.connection.commit()
            cursor.close()

            logger.info(f"Inseriti {rows_inserted} record in {table_name}")
            return rows_inserted

        except Exception as e:
            logger.error(f"Errore inserimento: {str(e)}")
            self.connection.rollback()
            raise

    def update_data(
        self,
        table_name: str,
        data: Dict[str, Any],
        where: Dict[str, Any]
    ) -> int:
        """
        Aggiorna dati in una tabella

        Args:
            table_name: Nome tabella
            data: Dati da aggiornare
            where: Condizioni WHERE

        Returns:
            Numero di righe aggiornate
        """
        if not self.connection:
            raise Exception("Nessuna connessione attiva")

        try:
            cursor = self.connection.cursor()

            # Costruzione query UPDATE
            set_clause = ','.join([f"[{col}]=?" for col in data.keys()])
            where_clause = ' AND '.join([f"[{col}]=?" for col in where.keys()])

            update_query = f"UPDATE [{table_name}] SET {set_clause} WHERE {where_clause}"

            values = list(data.values()) + list(where.values())
            cursor.execute(update_query, values)

            rows_updated = cursor.rowcount
            self.connection.commit()
            cursor.close()

            logger.info(f"Aggiornati {rows_updated} record in {table_name}")
            return rows_updated

        except Exception as e:
            logger.error(f"Errore aggiornamento: {str(e)}")
            self.connection.rollback()
            raise

    def upsert_data(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        primary_key: str
    ) -> Dict[str, int]:
        """
        Inserisce o aggiorna dati (UPSERT)

        Args:
            table_name: Nome tabella
            data: Lista di dizionari con i dati
            primary_key: Nome colonna chiave primaria

        Returns:
            Dizionario con conteggi inserimenti e aggiornamenti
        """
        if not self.connection:
            raise Exception("Nessuna connessione attiva")

        try:
            cursor = self.connection.cursor()

            rows_inserted = 0
            rows_updated = 0

            for row in data:
                # Verifica esistenza
                check_query = f"SELECT COUNT(*) FROM [{table_name}] WHERE [{primary_key}]=?"
                cursor.execute(check_query, row[primary_key])
                exists = cursor.fetchone()[0] > 0

                if exists:
                    # UPDATE
                    columns = [col for col in row.keys() if col != primary_key]
                    set_clause = ','.join([f"[{col}]=?" for col in columns])
                    update_query = f"UPDATE [{table_name}] SET {set_clause} WHERE [{primary_key}]=?"

                    values = [row[col] for col in columns] + [row[primary_key]]
                    cursor.execute(update_query, values)
                    rows_updated += 1
                else:
                    # INSERT
                    columns = list(row.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    columns_str = ','.join([f"[{col}]" for col in columns])
                    insert_query = f"INSERT INTO [{table_name}] ({columns_str}) VALUES ({placeholders})"

                    values = [row[col] for col in columns]
                    cursor.execute(insert_query, values)
                    rows_inserted += 1

            self.connection.commit()
            cursor.close()

            logger.info(f"Upsert: {rows_inserted} inseriti, {rows_updated} aggiornati")

            return {
                "inserted": rows_inserted,
                "updated": rows_updated
            }

        except Exception as e:
            logger.error(f"Errore upsert: {str(e)}")
            self.connection.rollback()
            raise

    def delete_data(self, table_name: str, where: Dict[str, Any]) -> int:
        """
        Elimina dati da una tabella

        Args:
            table_name: Nome tabella
            where: Condizioni WHERE

        Returns:
            Numero di righe eliminate
        """
        if not self.connection:
            raise Exception("Nessuna connessione attiva")

        try:
            cursor = self.connection.cursor()

            # Costruzione query DELETE
            where_clause = ' AND '.join([f"[{col}]=?" for col in where.keys()])
            delete_query = f"DELETE FROM [{table_name}] WHERE {where_clause}"

            values = list(where.values())
            cursor.execute(delete_query, values)

            rows_deleted = cursor.rowcount
            self.connection.commit()
            cursor.close()

            logger.info(f"Eliminati {rows_deleted} record da {table_name}")
            return rows_deleted

        except Exception as e:
            logger.error(f"Errore eliminazione: {str(e)}")
            self.connection.rollback()
            raise

    def load_from_csv(
        self,
        csv_file: str,
        table_name: str,
        operation: str = "insert",
        primary_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Carica dati da CSV in tabella

        Args:
            csv_file: Path del file CSV
            table_name: Nome tabella destinazione
            operation: insert, update, o upsert
            primary_key: Chiave primaria per upsert

        Returns:
            Risultato dell'operazione
        """
        try:
            # Leggi CSV
            df = pd.read_csv(csv_file)
            data = df.to_dict('records')

            logger.info(f"Letti {len(data)} record da {csv_file}")

            # Esegui operazione
            if operation == "insert":
                rows = self.insert_data(table_name, data)
                return {"inserted": rows}

            elif operation == "upsert":
                if not primary_key:
                    raise ValueError("primary_key richiesto per upsert")
                return self.upsert_data(table_name, data, primary_key)

            else:
                raise ValueError(f"Operazione non supportata: {operation}")

        except Exception as e:
            logger.error(f"Errore caricamento CSV: {str(e)}")
            raise

    def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict]:
        """
        Esegue query personalizzata

        Args:
            query: Query SQL
            params: Parametri query (opzionale)

        Returns:
            Risultati query
        """
        if not self.connection:
            raise Exception("Nessuna connessione attiva")

        try:
            cursor = self.connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Se è una SELECT, ritorna risultati
            if query.strip().upper().startswith("SELECT"):
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                cursor.close()
                return results
            else:
                # Per INSERT/UPDATE/DELETE
                self.connection.commit()
                rows_affected = cursor.rowcount
                cursor.close()
                return [{"rows_affected": rows_affected}]

        except Exception as e:
            logger.error(f"Errore esecuzione query: {str(e)}")
            self.connection.rollback()
            raise


class MSSQLAPIClient:
    """Client per interagire con API MSSQL"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Inizializza client API

        Args:
            api_url: URL base dell'API
        """
        self.api_url = api_url.rstrip('/')

    def insert_data(self, table_name: str, data: List[Dict[str, Any]]) -> Dict:
        """Inserisce dati tramite API"""
        url = f"{self.api_url}/api/v1/insert"
        payload = {
            "table_name": table_name,
            "data": data,
            "operation": "insert"
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def update_data(
        self,
        table_name: str,
        data: Dict[str, Any],
        where: Dict[str, Any]
    ) -> Dict:
        """Aggiorna dati tramite API"""
        url = f"{self.api_url}/api/v1/update"
        payload = {
            "table_name": table_name,
            "data": data,
            "where": where
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def upsert_data(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        primary_key: str
    ) -> Dict:
        """Upsert dati tramite API"""
        url = f"{self.api_url}/api/v1/upsert"
        payload = {
            "table_name": table_name,
            "data": data,
            "operation": "upsert",
            "primary_key": primary_key
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def upload_csv(
        self,
        csv_file: str,
        table_name: str,
        operation: str = "insert",
        primary_key: Optional[str] = None
    ) -> Dict:
        """Carica CSV tramite API"""
        url = f"{self.api_url}/api/v1/upload-csv"

        with open(csv_file, 'rb') as f:
            files = {'file': f}
            params = {
                'table_name': table_name,
                'operation': operation
            }
            if primary_key:
                params['primary_key'] = primary_key

            response = requests.post(url, files=files, params=params)
            response.raise_for_status()
            return response.json()


def main():
    """Esempio di utilizzo da linea di comando"""
    parser = argparse.ArgumentParser(description='MSSQL Uploader')

    parser.add_argument('--mode', choices=['direct', 'api'], default='direct',
                        help='Modalità di connessione')
    parser.add_argument('--operation', choices=['insert', 'update', 'upsert', 'delete'],
                        default='insert', help='Operazione da eseguire')

    # Parametri database
    parser.add_argument('--server', default=os.getenv('MSSQL_SERVER', 'localhost'))
    parser.add_argument('--database', default=os.getenv('MSSQL_DATABASE', 'testdb'))
    parser.add_argument('--username', default=os.getenv('MSSQL_USERNAME', 'sa'))
    parser.add_argument('--password', default=os.getenv('MSSQL_PASSWORD', ''))
    parser.add_argument('--port', type=int, default=int(os.getenv('MSSQL_PORT', '1433')))

    # Parametri API
    parser.add_argument('--api-url', default=os.getenv('API_URL', 'http://localhost:8000'))

    # Parametri operazione
    parser.add_argument('--table', required=True, help='Nome tabella')
    parser.add_argument('--csv-file', help='File CSV da caricare')
    parser.add_argument('--json-file', help='File JSON da caricare')
    parser.add_argument('--primary-key', help='Chiave primaria per upsert')

    args = parser.parse_args()

    try:
        if args.mode == 'direct':
            # Connessione diretta
            uploader = MSSQLUploader(
                server=args.server,
                database=args.database,
                username=args.username,
                password=args.password,
                port=args.port
            )

            if not uploader.connect():
                logger.error("Impossibile connettersi al database")
                return

            # Carica dati
            if args.csv_file:
                result = uploader.load_from_csv(
                    csv_file=args.csv_file,
                    table_name=args.table,
                    operation=args.operation,
                    primary_key=args.primary_key
                )
                logger.info(f"Risultato: {result}")

            elif args.json_file:
                with open(args.json_file, 'r') as f:
                    data = json.load(f)

                if args.operation == 'insert':
                    rows = uploader.insert_data(args.table, data)
                    logger.info(f"Inseriti {rows} record")

                elif args.operation == 'upsert':
                    if not args.primary_key:
                        logger.error("--primary-key richiesto per upsert")
                        return
                    result = uploader.upsert_data(args.table, data, args.primary_key)
                    logger.info(f"Risultato: {result}")

            uploader.disconnect()

        else:
            # Tramite API
            client = MSSQLAPIClient(api_url=args.api_url)

            if args.csv_file:
                result = client.upload_csv(
                    csv_file=args.csv_file,
                    table_name=args.table,
                    operation=args.operation,
                    primary_key=args.primary_key
                )
                logger.info(f"Risultato: {result}")

            elif args.json_file:
                with open(args.json_file, 'r') as f:
                    data = json.load(f)

                if args.operation == 'insert':
                    result = client.insert_data(args.table, data)
                elif args.operation == 'upsert':
                    if not args.primary_key:
                        logger.error("--primary-key richiesto per upsert")
                        return
                    result = client.upsert_data(args.table, data, args.primary_key)

                logger.info(f"Risultato: {result}")

    except Exception as e:
        logger.error(f"Errore: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
