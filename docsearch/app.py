"""
DocSearch - Applicazione Flask Principale
Sistema di Documentazione Intelligente con OpenSearch
"""

import os
import logging
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, unquote
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

from document_parser import DocumentParser
from opensearch_manager import OpenSearchManager
from rag_engine import RAGEngine, SearchContext

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inizializza Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

CORS(app)

# Directory uploads (fuori da static per evitare auto-reload durante upload)
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inizializza componenti
try:
    parser = DocumentParser()
    opensearch = OpenSearchManager(
        host=os.getenv('OPENSEARCH_HOST', 'localhost'),
        port=int(os.getenv('OPENSEARCH_PORT', 9200)),
        username=os.getenv('OPENSEARCH_USER', 'admin'),
        password=os.getenv('OPENSEARCH_PASSWORD', 'admin')
    )
    rag_engine = RAGEngine(
        use_openai=os.getenv('USE_OPENAI', 'false').lower() == 'true',
        api_key=os.getenv('OPENAI_API_KEY')
    )

    # Crea indice se non esiste
    opensearch.create_index()

    logger.info("✅ DocSearch initialized successfully")

except Exception as e:
    logger.error(f"❌ Failed to initialize DocSearch: {e}")
    raise


# ========== ROUTES: Pages ==========

@app.route('/')
def index():
    """Homepage con ricerca"""
    stats = opensearch.get_statistics()
    return render_template('index.html', stats=stats)


@app.route('/upload')
def upload_page():
    """Pagina upload documenti"""
    return render_template('upload.html')


@app.route('/documents')
def documents_page():
    """Pagina lista documenti"""
    return render_template('documents.html')


@app.route('/about')
def about_page():
    """Pagina info"""
    return render_template('about.html')


# ========== ROUTES: API ==========

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    API per ricerca intelligente

    POST /api/search
    {
        "query": "come installare opensearch",
        "size": 10,
        "use_rag": true,
        "tag_filter": "manuale"  // opzionale
    }
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        size = data.get('size', 10)
        use_rag = data.get('use_rag', True)
        tag_filter = data.get('tag_filter', '').strip()

        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400

        logger.info(f"🔍 Search: {query}" + (f" [tag: {tag_filter}]" if tag_filter else ""))

        # Prepara filtri
        filters = {}
        if tag_filter:
            filters['tags'] = tag_filter

        # Cerca in OpenSearch
        search_results = opensearch.search(query, size=size, filters=filters if filters else None)

        if not search_results['success']:
            return jsonify(search_results), 500

        # Genera risposta intelligente con RAG
        if use_rag:
            context = SearchContext(
                query=query,
                results=search_results['results'],
                total_results=search_results['total']
            )

            rag_response = rag_engine.generate_answer(context)

            return jsonify({
                'success': True,
                'query': query,
                'total': search_results['total'],
                'results': search_results['results'],
                'answer': rag_response['answer'],
                'confidence': rag_response['confidence'],
                'sources': rag_response['sources'],
                'flow': rag_response['flow'],
                'suggestions': rag_response['suggestions']
            })
        else:
            # Solo risultati di ricerca
            return jsonify(search_results)

    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    API per upload e indicizzazione documenti

    POST /api/upload (multipart/form-data)
    file: file binario
    """
    try:
        # Verifica file
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Verifica estensione
        filename = secure_filename(file.filename)
        file_ext = Path(filename).suffix.lower()

        if file_ext not in parser.SUPPORTED_EXTENSIONS:
            return jsonify({
                'success': False,
                'error': f'Unsupported file type: {file_ext}',
                'supported': list(parser.SUPPORTED_EXTENSIONS.keys())
            }), 400

        # Salva file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = UPLOAD_FOLDER / unique_filename

        file.save(str(file_path))
        logger.info(f"📁 Saved file: {unique_filename}")

        # Parse documento
        parsed_doc = parser.parse(str(file_path))

        if not parsed_doc['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to parse document: {parsed_doc.get('error')}"
            }), 500

        # Aggiungi tags se presenti
        tags_input = request.form.get('tags', '').strip()
        if tags_input:
            # Split per virgola e pulisci
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            parsed_doc['tags'] = tags
        else:
            parsed_doc['tags'] = []

        # Indicizza in OpenSearch
        index_result = opensearch.index_document(parsed_doc)

        if not index_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to index document: {index_result.get('error')}"
            }), 500

        logger.info(f"✅ Document indexed: {filename}")

        return jsonify({
            'success': True,
            'message': 'Document uploaded and indexed successfully',
            'document': {
                'id': index_result['doc_id'],
                'filename': filename,
                'type': parsed_doc['type'],
                'size': parsed_doc['metadata']['size'],
                'keywords': parsed_doc['keywords'][:10],
                'tags': parsed_doc.get('tags', [])
            }
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload/directory', methods=['POST'])
def api_upload_directory():
    """
    API per upload di una directory intera con tutti i suoi file

    POST /api/upload/directory (multipart/form-data)
    files[]: array di file
    tags: tags da applicare a tutti i file (opzionale)
    """
    try:
        logger.info("=== Starting directory upload ===")

        # Verifica files
        if 'files[]' not in request.files:
            logger.warning("No 'files[]' in request.files")
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400

        files = request.files.getlist('files[]')
        logger.info(f"Received {len(files)} files")

        if not files or (len(files) == 1 and files[0].filename == ''):
            logger.warning("No valid files selected")
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400

        # Aggiungi tags se presenti
        tags_input = request.form.get('tags', '').strip()
        tags = []
        if tags_input:
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]

        results = {
            'success': True,
            'total_files': len(files),
            'uploaded': 0,
            'failed': 0,
            'documents': [],
            'errors': []
        }

        logger.info(f"📁 Processing directory upload: {len(files)} files")

        for idx, file in enumerate(files, 1):
            try:
                logger.info(f"Processing file {idx}/{len(files)}: {file.filename}")

                # Verifica estensione
                filename = secure_filename(file.filename)
                if not filename:
                    logger.warning(f"Invalid filename: {file.filename}")
                    results['failed'] += 1
                    results['errors'].append({
                        'filename': file.filename,
                        'error': 'Invalid filename'
                    })
                    continue

                file_ext = Path(filename).suffix.lower()

                if file_ext not in parser.SUPPORTED_EXTENSIONS:
                    logger.warning(f"Unsupported file type: {file_ext}")
                    results['failed'] += 1
                    results['errors'].append({
                        'filename': filename,
                        'error': f'Unsupported file type: {file_ext}'
                    })
                    continue

                # Salva file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                unique_filename = f"{timestamp}_{filename}"
                file_path = UPLOAD_FOLDER / unique_filename

                logger.info(f"Saving to: {unique_filename}")
                file.save(str(file_path))

                # Parse documento
                logger.info(f"Parsing: {filename}")
                parsed_doc = parser.parse(str(file_path))

                if not parsed_doc['success']:
                    logger.error(f"Parse failed: {parsed_doc.get('error')}")
                    results['failed'] += 1
                    results['errors'].append({
                        'filename': filename,
                        'error': parsed_doc.get('error', 'Unknown error')
                    })
                    continue

                # Aggiungi tags
                parsed_doc['tags'] = tags

                # Indicizza in OpenSearch
                logger.info(f"Indexing: {filename}")
                index_result = opensearch.index_document(parsed_doc)

                if not index_result['success']:
                    logger.error(f"Index failed: {index_result.get('error')}")
                    results['failed'] += 1
                    results['errors'].append({
                        'filename': filename,
                        'error': index_result.get('error', 'Failed to index')
                    })
                    continue

                # Success
                results['uploaded'] += 1
                results['documents'].append({
                    'id': index_result['doc_id'],
                    'filename': filename,
                    'type': parsed_doc['type'],
                    'size': parsed_doc['metadata']['size']
                })

                logger.info(f"✅ Indexed {idx}/{len(files)}: {filename}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'filename': file.filename if hasattr(file, 'filename') else 'unknown',
                    'error': str(e)
                })
                logger.error(f"❌ Error processing {file.filename}: {e}", exc_info=True)

        logger.info(f"📊 Directory upload complete: {results['uploaded']} uploaded, {results['failed']} failed")

        return jsonify(results)

    except Exception as e:
        logger.error(f"❌ Critical directory upload error: {e}", exc_info=True)
        import traceback
        return jsonify({
            'success': False,
            'error': f'Critical error: {str(e)}',
            'details': traceback.format_exc()
        }), 500


@app.route('/api/documents', methods=['GET'])
def api_documents():
    """
    API per lista documenti

    GET /api/documents?page=1&size=20
    """
    try:
        page = int(request.args.get('page', 1))
        size = int(request.args.get('size', 20))

        # Per ora, ritorna tutti i documenti tramite ricerca match_all
        # In produzione, implementare paginazione vera

        search_results = opensearch.search(
            query='*',  # Match all
            size=size
        )

        return jsonify({
            'success': True,
            'documents': search_results['results'],
            'total': search_results['total'],
            'page': page,
            'size': size
        })

    except Exception as e:
        logger.error(f"Documents list error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/document/<doc_id>', methods=['GET'])
def api_document_detail(doc_id):
    """
    API per dettagli documento

    GET /api/document/<doc_id>
    """
    try:
        document = opensearch.get_document(doc_id)

        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404

        return jsonify({
            'success': True,
            'document': document
        })

    except Exception as e:
        logger.error(f"Document detail error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/document/<doc_id>', methods=['DELETE'])
def api_document_delete(doc_id):
    """
    API per eliminare documento

    DELETE /api/document/<doc_id>
    """
    try:
        success = opensearch.delete_document(doc_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to delete document'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Document deleted successfully'
        })

    except Exception as e:
        logger.error(f"Document delete error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/statistics', methods=['GET'])
def api_statistics():
    """
    API per statistiche

    GET /api/statistics
    """
    try:
        stats = opensearch.get_statistics()

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"Statistics error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tags', methods=['GET'])
def api_tags():
    """
    API per ottenere tutti i tags disponibili

    GET /api/tags
    """
    try:
        tags_data = opensearch.get_all_tags()

        return jsonify(tags_data)

    except Exception as e:
        logger.error(f"Tags error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'tags': []
        }), 500


@app.route('/api/download/<doc_id>', methods=['GET'])
def api_download(doc_id):
    """
    API per scaricare il file originale del documento

    GET /api/download/<doc_id>
    """
    try:
        # Recupera documento da OpenSearch
        document = opensearch.get_document(doc_id)

        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404

        # Ottieni il path del file
        file_path = document.get('file_path', '')

        if not file_path:
            return jsonify({
                'success': False,
                'error': 'File path not found in document'
            }), 404

        # Verifica che il file esista
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'File not found on disk'
            }), 404

        # Verifica che il file sia nella directory uploads (security)
        upload_dir = str(UPLOAD_FOLDER.resolve())
        file_abs_path = str(Path(file_path).resolve())

        if not file_abs_path.startswith(upload_dir):
            logger.warning(f"⚠️  Attempted download outside uploads dir: {file_path}")
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 403

        # Nome file per download
        original_filename = document.get('filename', 'document')

        logger.info(f"📥 Downloading: {original_filename} (ID: {doc_id})")

        # Invia il file
        return send_from_directory(
            directory=os.path.dirname(file_abs_path),
            path=os.path.basename(file_abs_path),
            as_attachment=True,
            download_name=original_filename
        )

    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload/url', methods=['POST'])
def api_upload_url():
    """
    API per caricare documento da URL

    POST /api/upload/url (application/json)
    {
        "url": "https://example.com/document.pdf",
        "tags": "tag1, tag2"  // opzionale
    }
    """
    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400

        url = data['url'].strip()

        # Validazione URL
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return jsonify({
                    'success': False,
                    'error': 'Invalid URL format'
                }), 400
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid URL'
            }), 400

        logger.info(f"🌐 Downloading from URL: {url}")

        # Download del file con timeout
        headers = {
            'User-Agent': 'DocSearch/1.0 (Document Indexing Bot)'
        }

        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()

        # Determina il nome del file
        filename = None

        # Prova da Content-Disposition header
        if 'Content-Disposition' in response.headers:
            cd = response.headers['Content-Disposition']
            if 'filename=' in cd:
                filename = cd.split('filename=')[1].strip('"\'')

        # Altrimenti usa l'URL
        if not filename:
            url_path = unquote(parsed_url.path)
            filename = os.path.basename(url_path)

        # Se ancora non c'è nome, usa un default
        if not filename or filename == '':
            # Prova a determinare l'estensione dal Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            ext = '.html'  # default
            if 'pdf' in content_type:
                ext = '.pdf'
            elif 'word' in content_type or 'msword' in content_type:
                ext = '.docx'
            elif 'excel' in content_type or 'spreadsheet' in content_type:
                ext = '.xlsx'
            elif 'text/plain' in content_type:
                ext = '.txt'
            elif 'json' in content_type:
                ext = '.json'
            elif 'xml' in content_type:
                ext = '.xml'

            filename = f"url_document_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

        filename = secure_filename(filename)

        # Verifica estensione supportata
        file_ext = Path(filename).suffix.lower()

        # Se non ha estensione, aggiungi .html (per pagine web)
        if not file_ext:
            filename += '.html'
            file_ext = '.html'

        if file_ext not in parser.SUPPORTED_EXTENSIONS:
            return jsonify({
                'success': False,
                'error': f'Unsupported file type: {file_ext}',
                'supported': list(parser.SUPPORTED_EXTENSIONS.keys())
            }), 400

        # Salva il file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = UPLOAD_FOLDER / unique_filename

        # Scrivi il contenuto
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"✅ Downloaded: {filename} ({os.path.getsize(file_path)} bytes)")

        # Parse documento
        parsed_doc = parser.parse(str(file_path))

        if not parsed_doc['success']:
            # Rimuovi il file se il parsing fallisce
            os.remove(file_path)
            return jsonify({
                'success': False,
                'error': f"Failed to parse document: {parsed_doc.get('error')}"
            }), 500

        # Aggiungi URL originale ai metadati
        if 'metadata' not in parsed_doc:
            parsed_doc['metadata'] = {}
        parsed_doc['metadata']['source_url'] = url

        # Aggiungi tags se presenti
        tags_input = data.get('tags', '').strip()
        if tags_input:
            tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
            parsed_doc['tags'] = tags
        else:
            parsed_doc['tags'] = []

        # Indicizza in OpenSearch
        index_result = opensearch.index_document(parsed_doc)

        if not index_result['success']:
            return jsonify({
                'success': False,
                'error': f"Failed to index document: {index_result.get('error')}"
            }), 500

        logger.info(f"✅ Document from URL indexed: {filename}")

        return jsonify({
            'success': True,
            'message': 'Document from URL uploaded and indexed successfully',
            'document': {
                'id': index_result['doc_id'],
                'filename': filename,
                'type': parsed_doc['type'],
                'size': parsed_doc['metadata']['size'],
                'keywords': parsed_doc['keywords'][:10],
                'tags': parsed_doc.get('tags', []),
                'source_url': url
            }
        })

    except requests.exceptions.Timeout:
        logger.error("URL download timeout")
        return jsonify({
            'success': False,
            'error': 'Download timeout: URL took too long to respond'
        }), 408

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error downloading URL: {e}")
        return jsonify({
            'success': False,
            'error': f'HTTP error: {e.response.status_code} - {e.response.reason}'
        }), 400

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading URL: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to download URL: {str(e)}'
        }), 400

    except Exception as e:
        logger.error(f"Upload from URL error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== Error Handlers ==========

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return render_template('500.html'), 500


# ========== Main ==========

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'

    logger.info(f"🚀 Starting DocSearch on port {port}")

    # IMPORTANTE: Disabilitiamo il reloader automatico per evitare che Flask
    # si riavvii durante il caricamento di file multipli.
    # Il watchdog di Werkzeug rileva i nuovi file in uploads/ e causa ERR_CONNECTION_RESET
    #
    # TRADEOFF: Dovrai riavviare manualmente il server quando modifichi il codice Python
    # Per riabilitare l'auto-reload: cambia use_reloader=True (ma upload multipli falliranno)

    if debug:
        logger.info("⚠️  Debug mode ON - Auto-reloader DISABILITATO per permettere upload multipli")
        logger.info("💡 Per modificare il codice: ferma il server (Ctrl+C) e riavvia manualmente")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=False  # CRITICO: False per evitare riavvii durante upload
    )
