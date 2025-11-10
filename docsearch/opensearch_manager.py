"""
DocSearch - OpenSearch Manager
Gestisce indicizzazione e ricerca documenti
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from opensearchpy import OpenSearch, helpers
from opensearchpy.exceptions import NotFoundError, RequestError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenSearchManager:
    """Manager per OpenSearch - Indicizzazione e Ricerca"""

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 9200,
        username: str = 'admin',
        password: str = 'admin',
        use_ssl: bool = False,
        verify_certs: bool = False
    ):
        """
        Inizializza connessione OpenSearch

        Args:
            host: OpenSearch host
            port: OpenSearch port
            username: Username
            password: Password
            use_ssl: Usa SSL/TLS
            verify_certs: Verifica certificati SSL
        """
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(username, password),
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            ssl_show_warn=False
        )

        self.index_name = 'documents'

        # Verifica connessione
        try:
            info = self.client.info()
            logger.info(f"✅ Connected to OpenSearch: {info['version']['number']}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenSearch: {e}")
            raise

    def create_index(self, force: bool = False):
        """
        Crea l'indice per i documenti con mapping ottimizzato

        Args:
            force: Se True, cancella e ricrea l'indice esistente
        """
        if force and self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
            logger.info(f"🗑️  Deleted existing index: {self.index_name}")

        if self.client.indices.exists(index=self.index_name):
            logger.info(f"ℹ️  Index already exists: {self.index_name}")
            return

        # Mapping ottimizzato per ricerca full-text
        mapping = {
            'settings': {
                'number_of_shards': 1,
                'number_of_replicas': 0,
                'index.highlight.max_analyzed_offset': 10000000,  # Aumenta limite highlighting a 10MB
                'analysis': {
                    'analyzer': {
                        'document_analyzer': {
                            'type': 'custom',
                            'tokenizer': 'standard',
                            'filter': [
                                'lowercase',
                                'asciifolding',
                                'stop',
                                'snowball'
                            ]
                        }
                    }
                }
            },
            'mappings': {
                'properties': {
                    'filename': {
                        'type': 'text',
                        'fields': {
                            'keyword': {'type': 'keyword'}
                        }
                    },
                    'extension': {'type': 'keyword'},
                    'type': {'type': 'keyword'},
                    'content': {
                        'type': 'text',
                        'analyzer': 'document_analyzer'
                    },
                    'summary': {
                        'type': 'text',
                        'analyzer': 'document_analyzer'
                    },
                    'keywords': {
                        'type': 'keyword'
                    },
                    'tags': {
                        'type': 'keyword'
                    },
                    'metadata': {
                        'type': 'object',
                        'enabled': True
                    },
                    'indexed_at': {
                        'type': 'date'
                    },
                    'file_size': {'type': 'long'},
                    'file_path': {
                        'type': 'text',
                        'fields': {
                            'keyword': {'type': 'keyword'}
                        }
                    }
                }
            }
        }

        self.client.indices.create(index=self.index_name, body=mapping)
        logger.info(f"✅ Created index: {self.index_name}")

    def index_document(self, parsed_doc: Dict) -> Dict:
        """
        Indicizza un documento parsato

        Args:
            parsed_doc: Documento da document_parser.parse()

        Returns:
            {'success': bool, 'doc_id': str, 'error': str}
        """
        if not parsed_doc.get('success'):
            return {
                'success': False,
                'error': parsed_doc.get('error', 'Unknown error')
            }

        try:
            # Prepara documento per OpenSearch
            doc = {
                'filename': parsed_doc['filename'],
                'extension': parsed_doc['extension'],
                'type': parsed_doc['type'],
                'content': parsed_doc['content'],
                'summary': parsed_doc.get('summary', ''),
                'keywords': parsed_doc.get('keywords', []),
                'tags': parsed_doc.get('tags', []),
                'metadata': parsed_doc.get('metadata', {}),
                'indexed_at': datetime.utcnow().isoformat(),
                'file_size': parsed_doc['metadata'].get('size', 0),
                'file_path': parsed_doc['metadata'].get('path', '')
            }

            # Indicizza
            response = self.client.index(
                index=self.index_name,
                body=doc,
                refresh=True  # Rendi subito disponibile per ricerca
            )

            doc_id = response['_id']

            logger.info(f"✅ Indexed document: {parsed_doc['filename']} (ID: {doc_id})")

            return {
                'success': True,
                'doc_id': doc_id,
                'filename': parsed_doc['filename']
            }

        except Exception as e:
            logger.error(f"❌ Failed to index document: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def search(
        self,
        query: str,
        size: int = 10,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Cerca documenti

        Args:
            query: Query di ricerca
            size: Numero massimo di risultati
            filters: Filtri opzionali (es: {'extension': '.pdf'})

        Returns:
            {
                'success': bool,
                'total': int,
                'results': [
                    {
                        'id': str,
                        'filename': str,
                        'type': str,
                        'score': float,
                        'summary': str,
                        'keywords': list,
                        'highlight': str
                    }
                ]
            }
        """
        try:
            # Se query è vuota o "*", usa match_all
            if not query or query.strip() == '*':
                query_clause = {'match_all': {}}
            else:
                # Query multi-field con boost
                query_clause = {
                    'bool': {
                        'should': [
                            {
                                'multi_match': {
                                    'query': query,
                                    'fields': [
                                        'content^1',
                                        'filename^3',
                                        'summary^2',
                                        'keywords^2',
                                        'tags^2'
                                    ],
                                    'type': 'best_fields',
                                    'fuzziness': 'AUTO'
                                }
                            }
                        ],
                        'minimum_should_match': 1
                    }
                }

            # Aggiungi filtri se presenti
            if filters:
                filter_clauses = []
                for field, value in filters.items():
                    filter_clauses.append({'term': {field: value}})

                # Wrappa tutto in un bool con filtri
                query_clause = {
                    'bool': {
                        'must': query_clause if not query or query.strip() == '*' else [query_clause],
                        'filter': filter_clauses
                    }
                }

            search_body = {
                'query': query_clause,
                'highlight': {
                    'fields': {
                        'summary': {
                            'fragment_size': 200,
                            'number_of_fragments': 2
                        },
                        'filename': {},
                        'content': {
                            'fragment_size': 150,
                            'number_of_fragments': 3,
                            'no_match_size': 200  # Mostra un estratto anche se non c'è match
                        }
                    },
                    'pre_tags': ['<mark>'],
                    'post_tags': ['</mark>'],
                    'require_field_match': False  # Permette highlighting su tutti i campi
                },
                'size': size,
                'sort': [
                    {'indexed_at': {'order': 'desc'}}
                ]
            }

            # Esegui ricerca
            try:
                response = self.client.search(
                    index=self.index_name,
                    body=search_body
                )
            except RequestError as e:
                # Se fallisce per highlighting su documenti grandi, riprova senza highlighting su content
                if 'max_analyzed_offset' in str(e):
                    logger.warning("⚠️  Highlighting failed for large documents, retrying without content highlighting")
                    search_body['highlight']['fields'] = {
                        'summary': {
                            'fragment_size': 200,
                            'number_of_fragments': 2
                        },
                        'filename': {}
                    }
                    response = self.client.search(
                        index=self.index_name,
                        body=search_body
                    )
                else:
                    raise

            # Parse risultati
            results = []
            for hit in response['hits']['hits']:
                source = hit['_source']

                # Estrai highlights
                highlight_text = ''
                if 'highlight' in hit:
                    if 'content' in hit['highlight']:
                        highlight_text = ' ... '.join(hit['highlight']['content'])
                    elif 'summary' in hit['highlight']:
                        highlight_text = hit['highlight']['summary'][0]

                # Gestisci score (potrebbe essere None con sort personalizzato)
                score = hit.get('_score')
                if score is None:
                    score = 1.0  # Default per query con sort personalizzato

                results.append({
                    'id': hit['_id'],
                    'filename': source['filename'],
                    'type': source['type'],
                    'extension': source['extension'],
                    'score': score,
                    'file_size': source.get('file_size', 0),
                    'summary': source.get('summary', ''),
                    'keywords': source.get('keywords', []),
                    'tags': source.get('tags', []),
                    'highlight': highlight_text or source.get('summary', '')[:300],
                    'indexed_at': source.get('indexed_at', ''),
                    'file_path': source.get('file_path', '')
                })

            return {
                'success': True,
                'total': response['hits']['total']['value'],
                'results': results,
                'query': query
            }

        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        Recupera un documento per ID

        Args:
            doc_id: ID del documento

        Returns:
            Documento completo o None
        """
        try:
            response = self.client.get(index=self.index_name, id=doc_id)
            document = response['_source']
            document['id'] = response['_id']  # Aggiungi l'ID al documento
            return document
        except NotFoundError:
            logger.warning(f"Document not found: {doc_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None

    def get_statistics(self) -> Dict:
        """
        Ottieni statistiche sull'indice

        Returns:
            {
                'total_documents': int,
                'total_size': int,
                'by_type': dict
            }
        """
        try:
            # Conta totale
            count_response = self.client.count(index=self.index_name)
            total_docs = count_response['count']

            # Aggregazione per tipo
            agg_body = {
                'size': 0,
                'aggs': {
                    'by_type': {
                        'terms': {'field': 'type'}
                    },
                    'by_extension': {
                        'terms': {'field': 'extension'}
                    },
                    'total_size': {
                        'sum': {'field': 'file_size'}
                    }
                }
            }

            agg_response = self.client.search(
                index=self.index_name,
                body=agg_body
            )

            by_type = {}
            for bucket in agg_response['aggregations']['by_type']['buckets']:
                by_type[bucket['key']] = bucket['doc_count']

            by_extension = {}
            for bucket in agg_response['aggregations']['by_extension']['buckets']:
                by_extension[bucket['key']] = bucket['doc_count']

            total_size = agg_response['aggregations']['total_size']['value']

            return {
                'total_documents': total_docs,
                'total_size': int(total_size),
                'by_type': by_type,
                'by_extension': by_extension
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_documents': 0,
                'total_size': 0,
                'by_type': {},
                'by_extension': {}
            }

    def get_server_info(self) -> Dict:
        """
        Ottieni informazioni sul server OpenSearch

        Returns:
            {
                'success': bool,
                'cluster_name': str,
                'version': str,
                'cluster_health': dict,
                'host': str,
                'port': int
            }
        """
        try:
            # Informazioni server base
            info_response = self.client.info()

            # Salute del cluster
            health_response = self.client.cluster.health()

            # Informazioni sull'indice
            index_stats = {}
            try:
                stats_response = self.client.indices.stats(index=self.index_name)
                if self.index_name in stats_response['indices']:
                    idx_stats = stats_response['indices'][self.index_name]['total']
                    index_stats = {
                        'docs_count': idx_stats['docs']['count'],
                        'docs_deleted': idx_stats['docs']['deleted'],
                        'store_size_bytes': idx_stats['store']['size_in_bytes'],
                        'store_size_mb': round(idx_stats['store']['size_in_bytes'] / 1024 / 1024, 2)
                    }
            except Exception as e:
                logger.warning(f"Could not get index stats: {e}")
                index_stats = {}

            return {
                'success': True,
                'cluster_name': info_response.get('cluster_name', 'Unknown'),
                'version': info_response.get('version', {}).get('number', 'Unknown'),
                'cluster_health': {
                    'status': health_response.get('status', 'unknown'),
                    'number_of_nodes': health_response.get('number_of_nodes', 0),
                    'active_shards': health_response.get('active_shards', 0),
                    'relocating_shards': health_response.get('relocating_shards', 0),
                    'initializing_shards': health_response.get('initializing_shards', 0),
                    'unassigned_shards': health_response.get('unassigned_shards', 0)
                },
                'index_name': self.index_name,
                'index_stats': index_stats,
                'host': self.host,
                'port': self.port
            }

        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            return {
                'success': False,
                'error': str(e),
                'host': self.host,
                'port': self.port
            }

    def get_all_tags(self) -> Dict:
        """
        Ottieni tutti i tags disponibili con conteggio documenti

        Returns:
            {
                'success': bool,
                'tags': [
                    {'tag': str, 'count': int},
                    ...
                ]
            }
        """
        try:
            agg_body = {
                'size': 0,
                'aggs': {
                    'all_tags': {
                        'terms': {
                            'field': 'tags',
                            'size': 100,  # Max 100 tags diversi
                            'order': {'_count': 'desc'}
                        }
                    }
                }
            }

            response = self.client.search(
                index=self.index_name,
                body=agg_body
            )

            tags = []
            for bucket in response['aggregations']['all_tags']['buckets']:
                tags.append({
                    'tag': bucket['key'],
                    'count': bucket['doc_count']
                })

            return {
                'success': True,
                'tags': tags
            }

        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return {
                'success': False,
                'tags': []
            }

    def delete_document(self, doc_id: str) -> bool:
        """Elimina un documento"""
        try:
            self.client.delete(index=self.index_name, id=doc_id)
            logger.info(f"🗑️  Deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False


# Test
if __name__ == '__main__':
    # Test connessione
    manager = OpenSearchManager()

    # Crea indice
    manager.create_index(force=True)

    # Statistiche
    stats = manager.get_statistics()
    print(f"\n📊 Statistics:")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   Total size: {stats['total_size'] / 1024:.2f} KB")
