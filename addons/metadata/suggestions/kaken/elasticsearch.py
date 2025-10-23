"""
KAKEN Elasticsearch Service

Requests-based ES8-compatible client for indexing/searching KAKEN data.

Implements typeless mappings and REST endpoints without depending on
elasticsearch-py, to allow connecting to Elasticsearch 8 while the global
project keeps its pinned client versions.
"""

from typing import Dict, List, Optional, Tuple
import logging
import json
import time

import requests
import hashlib

logger = logging.getLogger(__name__)


class KakenElasticsearchError(Exception):
    pass


class KakenAuthError(KakenElasticsearchError):
    pass


class KakenBadRequest(KakenElasticsearchError):
    pass


class KakenConflict(KakenElasticsearchError):
    pass


class KakenTransportError(KakenElasticsearchError):
    pass


class KakenBulkError(KakenElasticsearchError):
    pass


class KakenElasticsearchService:
    """Elasticsearch service for KAKEN/NRID researcher data (requests-based)"""

    def __init__(self,
                 hosts: List[str],
                 index_name: str,
                 analyzer_config: Dict = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_on_timeout: bool = True,
                 verify_certs: bool = True,
                 **kwargs):
        if not hosts:
            raise ValueError('hosts is required')
        if not index_name:
            raise ValueError('index_name is required')

        # Accept previous callers passing a list of hosts; use the first one
        base = hosts[0]
        if not base.startswith('http://') and not base.startswith('https://'):
            base = f'http://{base}'

        self.base_url = base.rstrip('/')
        self.index_name = index_name
        self.analyzer_config = analyzer_config or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_on_timeout = retry_on_timeout
        self.verify = verify_certs

        self._session = requests.Session()

    def _req(self, method: str, path: str, *, json_body=None, data=None,
             headers: Dict[str, str] = None, expected: Tuple[int, ...] = (200, 201),
             timeout: Optional[int] = None, is_bulk: bool = False, allow_404: bool = False):
        url = f'{self.base_url}{path}'
        hdrs = headers.copy() if headers else {}
        if is_bulk:
            hdrs.setdefault('Content-Type', 'application/x-ndjson')
        elif json_body is not None:
            hdrs.setdefault('Content-Type', 'application/json')
        hdrs.setdefault('Accept', 'application/json')

        attempt = 0
        to = timeout or self.timeout

        while True:
            try:
                resp = self._session.request(method, url, json=json_body, data=data,
                                             headers=hdrs, timeout=to, verify=self.verify)
                if resp.status_code in expected:
                    return resp
                if allow_404 and resp.status_code == 404:
                    return resp

                # Map status to exceptions
                msg = self._format_error(method, url, resp)
                if resp.status_code in (400,):
                    raise KakenBadRequest(msg)
                if resp.status_code in (401, 403):
                    raise KakenAuthError(msg)
                if resp.status_code in (409,):
                    raise KakenConflict(msg)
                if resp.status_code >= 500 or resp.status_code in (408, 429):
                    raise KakenTransportError(msg)
                # Other unexpected status
                raise KakenElasticsearchError(msg)

            except (requests.ConnectionError, requests.Timeout) as exc:
                if not self.retry_on_timeout or attempt >= self.max_retries:
                    raise KakenTransportError(f'HTTP transport error: {exc}')
                sleep_s = min(2 ** attempt, 5)
                logger.warning(f'HTTP retry {attempt+1}/{self.max_retries} {method} {url}: {exc}; sleeping {sleep_s}s')
                time.sleep(sleep_s)
                attempt += 1

    @staticmethod
    def _format_error(method: str, url: str, resp: requests.Response) -> str:
        snippet = ''
        try:
            body = resp.json()
            snippet = json.dumps(body)[:500]
        except Exception:
            snippet = (resp.text or '')[:500]
        return f'{method} {url} -> {resp.status_code}: {snippet}'

    def create_index(self, delete_existing: bool = False):
        """
        Create Elasticsearch index with proper mapping

        Args:
            delete_existing: Whether to delete existing index
        """
        # Delete existing index if requested
        if delete_existing and self.index_exists():
            logger.info(f'Deleting existing index: {self.index_name}')
            self._req('DELETE', f'/{self.index_name}', expected=(200,))

        # Check if index already exists
        if self.index_exists():
            logger.info(f'Index {self.index_name} already exists')
            return

        # Create index with typeless mapping
        mapping = self._build_mapping()
        logger.info(f'Creating index: {self.index_name}')
        resp = self._req('PUT', f'/{self.index_name}', json_body=mapping, expected=(200,))
        logger.info(f'Index created successfully: {resp.text[:200]}')

    def index_exists(self) -> bool:
        """Check if index exists"""
        resp = self._req('HEAD', f'/{self.index_name}', expected=(200,), allow_404=True)
        return resp.status_code == 200

    def _build_mapping(self) -> Dict:
        """Build Elasticsearch mapping for KAKEN researcher data"""
        # Default analyzer configuration
        default_analysis = {
            'analyzer': {
                'kuromoji_analyzer': {
                    'type': 'custom',
                    'tokenizer': 'standard',
                    'filter': ['cjk_width', 'lowercase']
                }
            }
        }

        # Use provided analyzer configuration or default
        analysis_config = self.analyzer_config.get('analysis', default_analysis)

        return {
            'settings': {
                'number_of_shards': 1,
                'number_of_replicas': 1,
                'analysis': analysis_config
            },
            'mappings': {
                'dynamic': False,
                'properties': {
                    '_source_url': {'type': 'keyword'},
                    '_last_updated': {'type': 'date'},
                    'deleted': {'type': 'boolean'},
                    'accn': {'type': 'keyword'},
                    'id:person:erad': {'type': 'keyword'},
                    'search_text': {'type': 'text', 'analyzer': 'kuromoji_analyzer'}
                }
            }
        }

    @staticmethod
    def doc_id_from_url(url: Optional[str]) -> Optional[str]:
        """Derive a stable ES document ID from a source URL.

        Uses SHA-256 hex of the full URL to avoid relying on URL structure.
        """
        if not url:
            return None
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def index_researcher(self, researcher_data: Dict, document_id: str = None,
                        update_timestamp: str = None) -> bool:
        """
        Index a single researcher document

        Args:
            researcher_data: Researcher data dictionary
            document_id: Document ID (defaults to accn)
            update_timestamp: ISO timestamp for last update (if None, always update)

        Returns:
            True if indexing was successful
        """
        # Prefer URL-derived ID for stability across actions (no fallback)
        doc_id = document_id or self.doc_id_from_url(researcher_data.get('_source_url'))
        if not doc_id:
            raise ValueError('Missing _source_url for document ID derivation')

        # Create a copy to avoid modifying the original data
        data_to_index = researcher_data.copy()

        # Add last_updated timestamp to document
        if update_timestamp and '_last_updated' not in data_to_index:
            data_to_index['_last_updated'] = update_timestamp
        # Default deleted flag to False if absent
        if 'deleted' not in data_to_index:
            data_to_index['deleted'] = False

        # ES8 typeless API: PUT /{index}/_doc/{id}
        resp = self._req('PUT', f'/{self.index_name}/_doc/{doc_id}', json_body=data_to_index, expected=(200, 201))
        logger.debug(f'Indexed document {doc_id}: {resp.text[:200]}')
        return True

    def delete_researcher(self, document_id: str) -> bool:
        """
        Delete a researcher document

        Args:
            document_id: Document ID to delete

        Returns:
            True if deletion was successful
        """
        # DELETE is idempotent; 404 treated as success
        resp = self._req('DELETE', f'/{self.index_name}/_doc/{document_id}', expected=(200, 202), allow_404=True)
        if resp.status_code == 404:
            logger.debug(f'Document {document_id} not found for deletion (treated as success)')
        else:
            logger.debug(f'Deleted document {document_id}: {resp.text[:200]}')
        return True

    def bulk_index(self, researchers: List[Dict], batch_size: int = 100,
                  update_timestamp: str = None) -> Dict:
        """
        Bulk index multiple researcher documents

        Args:
            researchers: List of researcher data dictionaries
            batch_size: Number of documents to process in each batch
            update_timestamp: ISO timestamp for last update (if None, always update)

        Returns:
            Dictionary with indexing results
        """
        results = {
            'success': 0,
            'errors': 0,
            'error_details': []
        }

        # Process in batches
        for i in range(0, len(researchers), batch_size):
            batch = researchers[i:i + batch_size]
            actions = []

            for researcher in batch:
                doc_id = self.doc_id_from_url(researcher.get('_source_url'))
                if not doc_id:
                    # If any document in batch is invalid, fail entire batch
                    error_msg = 'Missing _source_url for document ID derivation'
                    results['errors'] += len(batch)
                    results['error_details'].append(error_msg)
                    logger.error(f'Invalid document in batch: {error_msg}')
                    raise ValueError(error_msg)

                # Create a copy to avoid modifying the original data
                data_to_index = researcher.copy()

                # Add last_updated timestamp to document
                if update_timestamp and '_last_updated' not in data_to_index:
                    data_to_index['_last_updated'] = update_timestamp
                if 'deleted' not in data_to_index:
                    data_to_index['deleted'] = False

                actions.append({
                    '_index': self.index_name,
                    '_id': doc_id,
                    '_source': data_to_index
                })

            if actions:
                # Build NDJSON for bulk API (typeless; no _type)
                ndjson_lines = []
                for act in actions:
                    meta = {'index': {'_index': act['_index'], '_id': act['_id']}}
                    ndjson_lines.append(json.dumps(meta))
                    ndjson_lines.append(json.dumps(act['_source']))
                payload = '\n'.join(ndjson_lines) + '\n'

                resp = self._req('POST', '/_bulk', data=payload, is_bulk=True, expected=(200,))
                body = resp.json()
                # ES returns per-item statuses
                item_errors = [it for it in body.get('items', []) if any(v.get('error') for v in it.values())]
                if item_errors:
                    error_msg = f'Bulk indexing failed for batch {i//batch_size + 1}: {len(item_errors)} errors'
                    results['errors'] += len(batch)
                    results['error_details'].extend(item_errors)
                    logger.error(f'{error_msg}')
                    raise KakenBulkError(error_msg)

                success_count = len(actions)
                results['success'] += success_count
                logger.info(f'Bulk indexed batch {i//batch_size + 1}: {success_count} success')

        logger.info(f"Bulk indexing completed: {results['success']} success, {results['errors']} errors")
        return results

    def search_researchers(self, query: Dict, size: int = 10, from_: int = 0) -> Dict:
        """
        Search researchers using Elasticsearch query

        Args:
            query: Elasticsearch query dictionary
            size: Number of results to return
            from_: Starting offset

        Returns:
            Search results
        """
        # Warn and return empty results if index doesn't exist
        if not self.index_exists():
            logger.warning(f"KAKEN index '{self.index_name}' does not exist. Run data synchronization to create it.")
            return {'hits': {'total': 0, 'hits': []}}

        resp = self._req('POST', f'/{self.index_name}/_search', json_body={**query, 'from': from_, 'size': size}, expected=(200,))
        return resp.json()

    def get_researcher_by_erad(self, erad_id: str) -> Optional[Dict]:
        """
        Get researcher by ERAD ID

        Args:
            erad_id: ERAD ID

        Returns:
            Researcher data or None if not found
        """
        query = {
            'query': {
                'bool': {
                    'must': [{'term': {'id:person:erad': erad_id}}],
                    'must_not': [{'term': {'deleted': True}}]
                }
            }
        }

        response = self.search_researchers(query, size=1)
        hits = response.get('hits', {}).get('hits', [])

        if hits:
            return hits[0]['_source']
        return None

    def get_researcher_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get researcher by ES document ID."""
        resp = self._req('GET', f'/{self.index_name}/_doc/{doc_id}', expected=(200,), allow_404=True)
        if resp.status_code == 404:
            return None
        data = resp.json()
        return data.get('_source')

    def soft_delete_researcher(self, document_id: str, update_timestamp: Optional[str] = None) -> bool:
        """Soft-delete a researcher document by marking it deleted and storing lastmod.

        Overwrites the document with a minimal payload to retain the per-document watermark.
        """
        payload = {'deleted': True}
        if update_timestamp:
            payload['_last_updated'] = update_timestamp
        resp = self._req('PUT', f'/{self.index_name}/_doc/{document_id}', json_body=payload, expected=(200, 201))
        logger.debug(f'Soft-deleted document {document_id}: {resp.text[:200]}')
        return True

    def refresh_index(self):
        """Refresh the index to make changes visible"""
        self._req('POST', f'/{self.index_name}/_refresh', expected=(200,))
        logger.debug(f'Index {self.index_name} refreshed')

    def get_index_stats(self) -> Dict:
        """Get index statistics"""
        resp = self._req('GET', f'/{self.index_name}/_stats', expected=(200,))
        return resp.json()

    def close(self):
        """Close Elasticsearch client"""
        try:
            self._session.close()
        except Exception as e:
            logger.warning(f'Failed to close KAKEN ES HTTP session: {e}')
