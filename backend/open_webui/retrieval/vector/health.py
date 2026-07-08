import logging
import os
from typing import Any
from urllib.parse import urlparse

from open_webui.config import (
    CHROMA_DATA_PATH,
    CHROMA_HTTP_HOST,
    CHROMA_HTTP_PORT,
    MARIADB_VECTOR_DB_URL,
    MILVUS_URI,
    PGVECTOR_DB_URL,
    QDRANT_URI,
    VECTOR_DB,
)
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.retrieval.vector.type import VectorType

log = logging.getLogger(__name__)

VECTOR_DB_LABELS: dict[str, str] = {
    VectorType.CHROMA: 'Chroma',
    VectorType.PGVECTOR: 'pgvector',
    VectorType.MILVUS: 'Milvus',
    VectorType.QDRANT: 'Qdrant',
    VectorType.PINECONE: 'Pinecone',
    VectorType.ELASTICSEARCH: 'Elasticsearch',
    VectorType.OPENSEARCH: 'OpenSearch',
    VectorType.ORACLE23AI: 'Oracle 23ai',
    VectorType.S3VECTOR: 'S3 Vector',
    VectorType.WEAVIATE: 'Weaviate',
    VectorType.OPENGAUSS: 'openGauss',
    VectorType.MARIADB_VECTOR: 'MariaDB Vector',
    VectorType.VALKEY: 'Valkey',
}

_HEALTH_PROBE_COLLECTION = '__open_webui_health_probe__'


def get_vector_db_label(vector_db: str | None = None) -> str:
    db = vector_db or VECTOR_DB
    return VECTOR_DB_LABELS.get(db, db.replace('-', ' ').title())


def _format_bytes(size: int | None) -> str | None:
    if size is None or size < 0:
        return None

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    value = float(size)
    unit_idx = 0

    while value >= 1024 and unit_idx < len(units) - 1:
        value /= 1024
        unit_idx += 1

    if unit_idx == 0:
        return f'{int(value)} {units[unit_idx]}'

    return f'{value:.1f} {units[unit_idx]}'


def _dir_size(path: str) -> int | None:
    if not path or not os.path.isdir(path):
        return None

    total = 0
    try:
        for root, _, files in os.walk(path):
            for filename in files:
                try:
                    total += os.path.getsize(os.path.join(root, filename))
                except OSError:
                    continue
    except OSError as exc:
        log.debug('Failed to measure directory size for %s: %s', path, exc)
        return None

    return total


def _sanitize_host(value: str | None) -> str | None:
    if not value:
        return None

    parsed = urlparse(value if '://' in value else f'//{value}')
    host = parsed.hostname or parsed.path.split('/')[0]
    port = parsed.port

    if not host:
        return None

    if port and port not in {80, 443}:
        return f'{host}:{port}'

    return host


def get_vector_db_deployment(vector_db: str | None = None) -> dict[str, str | None]:
    db = vector_db or VECTOR_DB

    if db == VectorType.CHROMA:
        if CHROMA_HTTP_HOST:
            host = CHROMA_HTTP_HOST
            if CHROMA_HTTP_PORT not in {80, 443, 8000}:
                host = f'{host}:{CHROMA_HTTP_PORT}'
            return {
                'deployment': 'remote',
                'host': host,
                'data_path': None,
            }
        return {
            'deployment': 'local',
            'host': None,
            'data_path': CHROMA_DATA_PATH,
        }

    if db == VectorType.PGVECTOR:
        return {'deployment': 'remote', 'host': _sanitize_host(PGVECTOR_DB_URL), 'data_path': None}

    if db == VectorType.MARIADB_VECTOR:
        return {
            'deployment': 'remote',
            'host': _sanitize_host(MARIADB_VECTOR_DB_URL),
            'data_path': None,
        }

    if db == VectorType.MILVUS:
        return {'deployment': 'remote', 'host': _sanitize_host(MILVUS_URI), 'data_path': None}

    if db == VectorType.QDRANT:
        return {'deployment': 'remote', 'host': _sanitize_host(QDRANT_URI), 'data_path': None}

    if db in {VectorType.PINECONE, VectorType.ELASTICSEARCH, VectorType.OPENSEARCH, VectorType.WEAVIATE, VectorType.S3VECTOR, VectorType.VALKEY, VectorType.ORACLE23AI, VectorType.OPENGAUSS}:
        return {'deployment': 'remote', 'host': None, 'data_path': None}

    return {'deployment': 'configured', 'host': None, 'data_path': None}


def get_vector_db_location_detail(vector_db: str | None = None) -> str:
    db = vector_db or VECTOR_DB
    deployment = get_vector_db_deployment(db)

    if deployment['deployment'] == 'local':
        return 'Local'

    if deployment['host']:
        return f"Remote ({deployment['host']})"

    if db == VectorType.PGVECTOR:
        return 'PostgreSQL'

    if db == VectorType.MARIADB_VECTOR:
        return 'MariaDB' if MARIADB_VECTOR_DB_URL else 'Not configured'

    if db in {VectorType.MILVUS, VectorType.QDRANT, VectorType.PINECONE, VectorType.WEAVIATE}:
        return 'Remote'

    if db == VectorType.VALKEY:
        return 'Valkey'

    return 'Configured'


def probe_vector_db_health() -> tuple[bool, str | None]:
    try:
        VECTOR_DB_CLIENT.has_collection(_HEALTH_PROBE_COLLECTION)
        return True, None
    except Exception as exc:
        log.debug('Vector DB health probe failed: %s', exc)
        return False, str(exc)


def _collection_names_from_list(collections: list[Any]) -> list[str]:
    names: list[str] = []
    for collection in collections:
        if isinstance(collection, str):
            names.append(collection)
        elif hasattr(collection, 'name'):
            names.append(collection.name)
    return names


def _collect_chroma_stats(client: Any) -> dict[str, int | None]:
    collections = client.client.list_collections()
    names = [
        name
        for name in _collection_names_from_list(collections)
        if name != _HEALTH_PROBE_COLLECTION
    ]

    vector_count = 0
    for name in names:
        try:
            vector_count += client.client.get_collection(name=name).count()
        except Exception:
            continue

    storage_bytes = _dir_size(CHROMA_DATA_PATH) if CHROMA_HTTP_HOST == '' else None

    return {
        'collection_count': len(names),
        'vector_count': vector_count,
        'storage_bytes': storage_bytes,
    }


def _collect_pgvector_stats(client: Any) -> dict[str, int | None]:
    from sqlalchemy import distinct, func, text

    from open_webui.retrieval.vector.dbs.pgvector import DocumentChunk

    session = client.session
    try:
        collection_count = session.query(func.count(distinct(DocumentChunk.collection_name))).scalar() or 0
        vector_count = session.query(func.count(DocumentChunk.id)).scalar() or 0
        storage_bytes = session.execute(
            text('SELECT pg_total_relation_size(:table_name)'),
            {'table_name': 'document_chunk'},
        ).scalar()
        session.rollback()
        return {
            'collection_count': int(collection_count),
            'vector_count': int(vector_count),
            'storage_bytes': int(storage_bytes) if storage_bytes is not None else None,
        }
    except Exception as exc:
        session.rollback()
        log.debug('Failed to collect pgvector stats: %s', exc)
        return {}


def _collect_qdrant_stats(client: Any) -> dict[str, int | None]:
    if client.client is None:
        return {}

    prefix = getattr(client, 'collection_prefix', '')
    collections = client.client.get_collections().collections
    names = [
        collection.name
        for collection in collections
        if not prefix or collection.name.startswith(f'{prefix}_')
    ]

    vector_count = 0
    for name in names:
        try:
            vector_count += client.client.count(collection_name=name, exact=True).count
        except Exception:
            continue

    return {
        'collection_count': len(names),
        'vector_count': vector_count,
        'storage_bytes': None,
    }


def _collect_milvus_stats(client: Any) -> dict[str, int | None]:
    prefix = getattr(client, 'collection_prefix', 'open_webui')
    collections = client.client.list_collections()
    names = [name for name in collections if name.startswith(prefix)]

    vector_count = 0
    for name in names:
        try:
            stats = client.client.get_collection_stats(collection_name=name)
            vector_count += int(stats.get('row_count', 0))
        except Exception:
            continue

    return {
        'collection_count': len(names),
        'vector_count': vector_count,
        'storage_bytes': None,
    }


def _collect_generic_stats(client: Any) -> dict[str, int | None]:
    inner = getattr(client, 'client', None)
    if inner is None:
        return {}

    if hasattr(inner, 'list_collections'):
        try:
            names = _collection_names_from_list(inner.list_collections())
            names = [name for name in names if name != _HEALTH_PROBE_COLLECTION]
            return {'collection_count': len(names), 'vector_count': None, 'storage_bytes': None}
        except Exception:
            return {}

    if hasattr(inner, 'get_collections'):
        try:
            collections = inner.get_collections().collections
            return {
                'collection_count': len(collections),
                'vector_count': None,
                'storage_bytes': None,
            }
        except Exception:
            return {}

    return {}


def collect_vector_db_stats() -> dict[str, int | None]:
    client = VECTOR_DB_CLIENT
    client_type = type(client).__name__

    collectors = {
        'ChromaClient': _collect_chroma_stats,
        'PgvectorClient': _collect_pgvector_stats,
        'QdrantClient': _collect_qdrant_stats,
        'MilvusClient': _collect_milvus_stats,
    }

    collector = collectors.get(client_type, _collect_generic_stats)
    try:
        stats = collector(client)
    except Exception as exc:
        log.debug('Failed to collect vector DB stats via %s: %s', client_type, exc)
        stats = {}

    return {
        'collection_count': stats.get('collection_count'),
        'vector_count': stats.get('vector_count'),
        'storage_bytes': stats.get('storage_bytes'),
    }


def _build_summary(
    *,
    collection_count: int | None,
    vector_count: int | None,
    storage_bytes: int | None,
    data_path: str | None,
) -> str | None:
    parts: list[str] = []

    if collection_count is not None:
        label = 'collection' if collection_count == 1 else 'collections'
        parts.append(f'{collection_count:,} {label}')

    if vector_count is not None:
        label = 'vector' if vector_count == 1 else 'vectors'
        parts.append(f'{vector_count:,} {label}')

    storage_size = _format_bytes(storage_bytes)
    if storage_size:
        parts.append(storage_size)
    elif data_path:
        parts.append(os.path.basename(data_path.rstrip('/')) or data_path)

    return ' · '.join(parts) if parts else None


def get_vector_db_status() -> dict:
    vector_db = VECTOR_DB
    label = get_vector_db_label(vector_db)
    location = get_vector_db_location_detail(vector_db)
    deployment_info = get_vector_db_deployment(vector_db)
    healthy, error = probe_vector_db_health()

    stats = collect_vector_db_stats() if healthy else {}
    storage_bytes = stats.get('storage_bytes')
    storage_size = _format_bytes(storage_bytes)
    summary = _build_summary(
        collection_count=stats.get('collection_count'),
        vector_count=stats.get('vector_count'),
        storage_bytes=storage_bytes,
        data_path=deployment_info.get('data_path'),
    )

    return {
        'status': True,
        'VECTOR_DB': vector_db,
        'VECTOR_DB_LABEL': label,
        'healthy': healthy,
        'detail': location if healthy else 'Unreachable',
        'deployment': deployment_info.get('deployment'),
        'host': deployment_info.get('host'),
        'data_path': deployment_info.get('data_path'),
        'collection_count': stats.get('collection_count'),
        'vector_count': stats.get('vector_count'),
        'storage_bytes': storage_bytes,
        'storage_size': storage_size,
        'summary': summary,
        'error': error,
    }
