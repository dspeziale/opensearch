# Fix: Errore Highlighting su Documenti Grandi

## 🐛 Problema

Se vedi questo errore durante la ricerca:

```
ERROR: The length of [content] field has exceeded [1000000] -
maximum allowed to be analyzed for highlighting
```

Significa che hai caricato un documento con più di 1.000.000 caratteri e OpenSearch non riesce a fare l'highlighting.

## ✅ Soluzione Automatica (CONSIGLIATA)

Usa lo script di fix automatico:

```bash
cd /home/user/opensearch/docsearch
python fix_index_highlighting.py
```

Lo script:
1. ✅ Aggiorna il limite highlighting a 10MB
2. ✅ Mantiene tutti i documenti esistenti
3. ✅ Nessuna perdita di dati

**Dopo aver eseguito lo script, riavvia l'applicazione.**

## 🔧 Soluzione Manuale

Se preferisci fare manualmente:

### Opzione 1: Aggiorna Indice Esistente

```bash
# Chiudi l'indice
curl -X POST "http://localhost:9200/documents/_close" \
  -u admin:admin -k

# Aggiorna le impostazioni
curl -X PUT "http://localhost:9200/documents/_settings" \
  -u admin:admin -k \
  -H 'Content-Type: application/json' \
  -d '{
    "index": {
      "highlight.max_analyzed_offset": 10000000
    }
  }'

# Riapri l'indice
curl -X POST "http://localhost:9200/documents/_open" \
  -u admin:admin -k
```

### Opzione 2: Ricrea Indice (CANCELLA TUTTI I DOCUMENTI!)

⚠️ **ATTENZIONE**: Questo cancellerà tutti i documenti caricati!

```python
from opensearch_manager import OpenSearchManager

osm = OpenSearchManager()
osm.create_index(force=True)
```

Poi ricarica tutti i tuoi documenti.

## 🔍 Verifica la Fix

Dopo aver applicato la fix, prova la ricerca:

```bash
# Verifica le impostazioni
curl -X GET "http://localhost:9200/documents/_settings" \
  -u admin:admin -k | grep highlight

# Dovresti vedere:
# "highlight.max_analyzed_offset": "10000000"
```

## 🚀 Le Modifiche Applicate

Il codice è stato aggiornato per:

1. **Nuovo limite highlighting**: 10MB (era 1MB)
2. **Fallback automatico**: Se un documento è troppo grande, fa highlighting solo su `summary` e `filename`
3. **Gestione errori**: Riprova automaticamente con highlighting ridotto

## 📊 Per Documenti Molto Grandi

Se hai documenti superiori a 10MB di testo:

**Opzione A: Aumenta ulteriormente il limite**

Modifica `opensearch_manager.py`, linea 79:
```python
'index.highlight.max_analyzed_offset': 50000000,  # 50MB invece di 10MB
```

Poi riesegui lo script fix.

**Opzione B: Limita la lunghezza del contenuto**

Durante l'upload, il sistema potrebbe limitare automaticamente il contenuto:

```python
# In document_parser.py, aggiungi dopo l'estrazione:
if len(content) > 5000000:  # 5MB
    content = content[:5000000] + "\n\n[Contenuto troncato...]"
```

## 🎯 Documentazione Tecnica

### Perché succede?

OpenSearch deve analizzare il testo per fare l'highlighting (evidenziare le parole cercate). Per performance, c'è un limite di default di 1MB.

### Come funziona la fix?

1. **Aumento limite**: Da 1MB a 10MB
2. **Highlighting intelligente**: Prima prova su tutti i campi, se fallisce usa solo campi piccoli
3. **Nessun impatto**: I documenti piccoli funzionano come prima

### Campi usati per highlighting:

- **Priorità alta**: `summary`, `filename` (sempre safe)
- **Priorità media**: `content` (se < 10MB)
- **Fallback**: Se troppo grande, usa solo summary

## 💡 Best Practices

Per evitare problemi futuri:

1. ✅ **Dividi documenti grandi**: Carica file separati invece di archivi enormi
2. ✅ **Usa formati compressi**: PDF invece di TXT per documenti grandi
3. ✅ **Monitora le dimensioni**: Controlla la size dei file prima del caricamento
4. ✅ **Usa ZIP con parsimonia**: I file ZIP estratti possono essere molto grandi

## 🆘 Serve Aiuto?

Se il problema persiste:

1. Verifica i log dell'applicazione
2. Controlla lo stato dell'indice:
   ```bash
   curl -X GET "http://localhost:9200/documents/_stats" -u admin:admin -k
   ```
3. Verifica la memoria di OpenSearch:
   ```bash
   curl -X GET "http://localhost:9200/_cluster/stats" -u admin:admin -k
   ```

---

**Fix applicato con successo? Ora puoi cercare anche nei documenti più grandi! 🎉**
