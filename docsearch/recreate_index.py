#!/usr/bin/env python3
"""
Script per ricreare l'indice OpenSearch con il mapping corretto
ATTENZIONE: Questo cancellerà tutti i documenti esistenti!
"""

import os
import sys
from opensearch_manager import OpenSearchManager

def main():
    print("=" * 60)
    print("⚠️  ATTENZIONE: Ricreazione Indice OpenSearch")
    print("=" * 60)
    print("\nQuesto script cancellerà l'indice esistente e lo ricreerà")
    print("con il mapping aggiornato (incluso supporto tags).")
    print("\n⚠️  TUTTI I DOCUMENTI ESISTENTI SARANNO CANCELLATI!")
    print("\nDovrai ricaricare tutti i documenti dopo questa operazione.")
    print("=" * 60)

    response = input("\nSei sicuro di voler continuare? (scrivi 'SI' per confermare): ")

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

        if stats['total_documents'] > 0:
            print("\n⚠️  Questi documenti verranno cancellati!")
            response = input("\nConferma ancora una volta (scrivi 'CONFERMA'): ")

            if response.strip().upper() != 'CONFERMA':
                print("\n❌ Operazione annullata.")
                sys.exit(0)

        print("\n🗑️  Cancellazione indice esistente...")
        manager.create_index(force=True)

        print("✅ Indice ricreato con successo!")
        print("\n📝 Prossimi passi:")
        print("   1. Riavvia l'applicazione")
        print("   2. Carica nuovamente i tuoi documenti")
        print("   3. I tags funzioneranno correttamente!")
        print("\n✨ Fatto!")

    except Exception as e:
        print(f"\n❌ Errore: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
