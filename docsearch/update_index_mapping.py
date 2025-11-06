#!/usr/bin/env python3
"""
Script per aggiornare il mapping dell'indice OpenSearch SENZA perdere dati
Usa il reindex API per copiare i dati in un nuovo indice con mapping corretto
"""

import os
import sys
import time
from opensearch_manager import OpenSearchManager

def main():
    print("=" * 60)
    print("🔄 Aggiornamento Mapping OpenSearch (CON preservazione dati)")
    print("=" * 60)
    print("\nQuesto script aggiornerà il mapping dell'indice")
    print("mantenendo tutti i documenti esistenti.")
    print("\nProcesso:")
    print("1. Crea un nuovo indice con mapping corretto")
    print("2. Copia tutti i documenti dal vecchio al nuovo indice")
    print("3. Elimina il vecchio indice")
    print("4. Ricrea l'indice principale con i dati copiati")
    print("=" * 60)

    response = input("\nVuoi continuare? (scrivi 'SI'): ")

    if response.strip().upper() != 'SI':
        print("\n❌ Operazione annullata.")
        sys.exit(0)

    print("\n🔄 Connessione a OpenSearch...")

    try:
        manager = OpenSearchManager(
            host=os.getenv('OPENSEARCH_HOST', 'localhost'),
            port=int(os.getenv('OPENSEARCH_PORT', 9200)),
            username=os.getenv('OPENSEARCH_USER', 'admin'),
            password=os.getenv('OPENSEARCH_PASSWORD', 'admin')
        )

        print("✅ Connesso a OpenSearch")

        # Mostra statistiche attuali
        stats = manager.get_statistics()
        print(f"\n📊 Statistiche attuali:")
        print(f"   - Documenti totali: {stats['total_documents']}")
        print(f"   - Dimensione totale: {stats['total_size'] / 1024:.2f} KB")

        if stats['total_documents'] == 0:
            print("\n⚠️  Nessun documento presente. Meglio ricreare l'indice direttamente.")
            print("   Esegui: python recreate_index.py")
            sys.exit(0)

        temp_index = 'documents_temp'
        original_index = 'documents'

        # Step 1: Crea indice temporaneo con mapping corretto
        print(f"\n1️⃣  Creazione indice temporaneo: {temp_index}...")

        # Mapping completo
        mapping = {
            'settings': {
                'number_of_shards': 1,
                'number_of_replicas': 0,
                'analysis': {
                    'analyzer': {
                        'document_analyzer': {
                            'type': 'custom',
                            'tokenizer': 'standard',
                            'filter': ['lowercase', 'asciifolding', 'stop', 'snowball']
                        }
                    }
                }
            },
            'mappings': {
                'properties': {
                    'filename': {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}},
                    'extension': {'type': 'keyword'},
                    'type': {'type': 'keyword'},
                    'content': {'type': 'text', 'analyzer': 'document_analyzer'},
                    'summary': {'type': 'text', 'analyzer': 'document_analyzer'},
                    'keywords': {'type': 'keyword'},
                    'tags': {'type': 'keyword'},  # ← FIX: keyword per aggregazioni
                    'metadata': {'type': 'object', 'enabled': True},
                    'indexed_at': {'type': 'date'},
                    'file_size': {'type': 'long'},
                    'file_path': {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}},
                    'is_attachment': {'type': 'boolean'},
                    'parent_document_id': {'type': 'keyword'},
                    'parent_filename': {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}}
                }
            }
        }

        # Elimina indice temp se esiste
        if manager.client.indices.exists(index=temp_index):
            manager.client.indices.delete(index=temp_index)

        manager.client.indices.create(index=temp_index, body=mapping)
        print("   ✅ Indice temporaneo creato")

        # Step 2: Reindex (copia documenti)
        print(f"\n2️⃣  Copia documenti da {original_index} a {temp_index}...")

        reindex_body = {
            'source': {'index': original_index},
            'dest': {'index': temp_index}
        }

        result = manager.client.reindex(body=reindex_body, wait_for_completion=True)

        copied_docs = result['created']
        print(f"   ✅ Copiati {copied_docs} documenti")

        # Step 3: Elimina indice originale
        print(f"\n3️⃣  Eliminazione indice originale: {original_index}...")
        manager.client.indices.delete(index=original_index)
        print("   ✅ Indice originale eliminato")

        # Step 4: Crea nuovo indice originale
        print(f"\n4️⃣  Creazione nuovo indice: {original_index}...")
        manager.client.indices.create(index=original_index, body=mapping)
        print("   ✅ Nuovo indice creato")

        # Step 5: Copia da temp a originale
        print(f"\n5️⃣  Copia documenti da {temp_index} a {original_index}...")

        reindex_body = {
            'source': {'index': temp_index},
            'dest': {'index': original_index}
        }

        result = manager.client.reindex(body=reindex_body, wait_for_completion=True)
        final_docs = result['created']
        print(f"   ✅ Copiati {final_docs} documenti")

        # Step 6: Elimina indice temp
        print(f"\n6️⃣  Pulizia indice temporaneo...")
        manager.client.indices.delete(index=temp_index)
        print("   ✅ Indice temporaneo eliminato")

        # Verifica finale
        print("\n7️⃣  Verifica finale...")
        time.sleep(1)
        new_stats = manager.get_statistics()
        print(f"   ✅ Documenti nell'indice: {new_stats['total_documents']}")

        if new_stats['total_documents'] == stats['total_documents']:
            print("\n" + "=" * 60)
            print("✅ SUCCESSO! Mapping aggiornato senza perdita di dati!")
            print("=" * 60)
            print(f"\n📊 Documenti preservati: {new_stats['total_documents']}")
            print("\n🎉 I tags ora funzioneranno correttamente!")
            print("   Puoi ricaricare l'applicazione web.")
        else:
            print("\n⚠️  Attenzione: numero di documenti diverso!")
            print(f"   Prima: {stats['total_documents']}")
            print(f"   Dopo: {new_stats['total_documents']}")

    except Exception as e:
        print(f"\n❌ Errore: {e}")
        print("\nIn caso di errore, potrebbe essere necessario ricreare l'indice manualmente.")
        sys.exit(1)

if __name__ == '__main__':
    main()
