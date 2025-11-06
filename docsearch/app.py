"""
DocSearch - Applicazione Flask Principale
Sistema di Documentazione Intelligente con OpenSearch
"""

import os
import logging
from pathlib import Path
from datetime import datetime
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

# Directory uploads
UPLOAD_FOLDER = Path(__file__).parent / 'static' / 'uploads'
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

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
