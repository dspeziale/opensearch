#!/usr/bin/env python3
"""
Script per aggiornare le impostazioni dell'indice OpenSearch
per supportare documenti grandi con highlighting
"""

import os
from opensearchpy import OpenSearch
from opensearchpy.exceptions import RequestError

# Configurazione
OPENSEARCH_HOST = os.getenv('OPENSEARCH_HOST', 'localhost')
OPENSEARCH_PORT = int(os.getenv('OPENSEARCH_PORT', 9200))
OPENSEARCH_USER = os.getenv('OPENSEARCH_USER', 'admin')
OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', 'admin')

def main():
    print("🔧 Aggiornamento impostazioni indice OpenSearch...")

    # Connetti a OpenSearch
    client = OpenSearch(
        hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False
    )

    index_name = 'documents'

    try:
        # Verifica che l'indice esista
        if not client.indices.exists(index=index_name):
            print(f"❌ Indice '{index_name}' non trovato!")
            print("💡 Avvia l'applicazione una volta per creare l'indice")
            return

        print(f"✅ Indice '{index_name}' trovato")

        # Chiudi l'indice temporaneamente
        print("📦 Chiusura indice per aggiornamento...")
        client.indices.close(index=index_name)

        # Aggiorna le impostazioni
        print("⚙️  Aggiornamento impostazioni highlighting...")
        settings = {
            'index': {
                'highlight.max_analyzed_offset': 10000000  # 10MB
            }
        }

        client.indices.put_settings(
            index=index_name,
            body=settings
        )

        # Riapri l'indice
        print("🔓 Riapertura indice...")
        client.indices.open(index=index_name)

        # Verifica le impostazioni
        current_settings = client.indices.get_settings(index=index_name)
        max_offset = current_settings[index_name]['settings']['index'].get('highlight', {}).get('max_analyzed_offset', 'default (1000000)')

        print(f"\n✅ Aggiornamento completato con successo!")
        print(f"📊 Nuovo limite highlighting: {max_offset} caratteri")
        print("\n💡 Ora puoi cercare anche nei documenti grandi senza errori")

    except RequestError as e:
        print(f"❌ Errore durante l'aggiornamento: {e}")
        print("\n💡 Prova a ricreare l'indice con:")
        print("   python -c 'from opensearch_manager import OpenSearchManager; osm = OpenSearchManager(); osm.create_index(force=True)'")
        print("   ⚠️  ATTENZIONE: questo cancellerà tutti i documenti!")

    except Exception as e:
        print(f"❌ Errore: {e}")

        # Assicurati che l'indice sia riaperto
        try:
            client.indices.open(index=index_name)
            print("🔓 Indice riaperto dopo errore")
        except:
            pass

if __name__ == '__main__':
    main()
