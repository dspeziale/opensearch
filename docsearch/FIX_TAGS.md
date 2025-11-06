# Fix per Tags OpenSearch

## Problema

Se ricevi questo errore:

```
ERROR:opensearch_manager:Error getting tags: RequestError(400, 'search_phase_execution_exception',
'Text fields are not optimised for operations that require per-document field data like
aggregations and sorting...')
```

Significa che l'indice OpenSearch è stato creato **prima** che il supporto tags fosse implementato correttamente, e ha un mapping vecchio dove `tags` è di tipo `text` invece di `keyword`.

## Soluzioni

### ⭐ Opzione 1: Aggiorna Mapping SENZA Perdere Dati (CONSIGLIATO)

Questo script usa il **reindex API** di OpenSearch per aggiornare il mapping mantenendo tutti i documenti:

```bash
cd docsearch
python update_index_mapping.py
```

**Vantaggi:**
- ✅ Mantiene tutti i documenti esistenti
- ✅ Non devi ricaricare nulla
- ✅ Processo automatico e sicuro

**Tempo richiesto:** 10-30 secondi (dipende dal numero di documenti)

---

### 🔴 Opzione 2: Ricrea Indice da Zero (PIÙ VELOCE ma perdi dati)

Questo script cancella l'indice esistente e lo ricrea con il mapping corretto:

```bash
cd docsearch
python recreate_index.py
```

**Attenzione:**
- ⚠️ Cancella TUTTI i documenti
- ⚠️ Dovrai ricaricare tutti i file
- ✅ Processo molto veloce (1 secondo)

---

## Dopo il Fix

1. **Riavvia l'applicazione** Flask
2. I tags ora funzioneranno correttamente:
   - ✅ Aggregazione tags nella homepage
   - ✅ Filtro per tag nella ricerca
   - ✅ Badge tags nella lista documenti
   - ✅ Tags visibili nei dettagli documento

## Verifica

Per verificare che il mapping sia corretto:

```bash
curl -X GET "localhost:9200/documents/_mapping?pretty"
```

Cerca il campo `tags` - dovrebbe essere:
```json
"tags": {
  "type": "keyword"
}
```

✅ Se vedi `"type": "keyword"` → tutto ok!
❌ Se vedi `"type": "text"` → esegui uno degli script sopra

---

## Prevenzione Futura

Se in futuro cambi il mapping in `opensearch_manager.py`, ricorda che OpenSearch **non aggiorna automaticamente** gli indici esistenti. Dovrai sempre usare il reindex o ricreare l'indice.
