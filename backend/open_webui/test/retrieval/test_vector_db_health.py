from open_webui.retrieval.vector.health import (
    _build_summary,
    _format_bytes,
    get_vector_db_deployment,
    get_vector_db_label,
    get_vector_db_location_detail,
)


def test_get_vector_db_label_known_types():
    assert get_vector_db_label('chroma') == 'Chroma'
    assert get_vector_db_label('pgvector') == 'pgvector'
    assert get_vector_db_label('mariadb-vector') == 'MariaDB Vector'


def test_get_vector_db_label_unknown_type():
    assert get_vector_db_label('custom-db') == 'Custom Db'


def test_format_bytes():
    assert _format_bytes(0) == '0 B'
    assert _format_bytes(1536) == '1.5 KB'
    assert _format_bytes(5 * 1024 * 1024) == '5.0 MB'


def test_get_vector_db_location_detail_chroma_local(monkeypatch):
    monkeypatch.setattr('open_webui.retrieval.vector.health.CHROMA_HTTP_HOST', '')
    assert get_vector_db_location_detail('chroma') == 'Local'


def test_get_vector_db_location_detail_chroma_remote(monkeypatch):
    monkeypatch.setattr('open_webui.retrieval.vector.health.CHROMA_HTTP_HOST', 'chroma.example.com')
    monkeypatch.setattr('open_webui.retrieval.vector.health.CHROMA_HTTP_PORT', 8000)
    assert get_vector_db_location_detail('chroma') == 'Remote (chroma.example.com)'


def test_get_vector_db_deployment_chroma_local(monkeypatch):
    monkeypatch.setattr('open_webui.retrieval.vector.health.CHROMA_HTTP_HOST', '')
    monkeypatch.setattr('open_webui.retrieval.vector.health.CHROMA_DATA_PATH', '/data/vector_db')
    deployment = get_vector_db_deployment('chroma')
    assert deployment['deployment'] == 'local'
    assert deployment['data_path'] == '/data/vector_db'


def test_build_summary():
    assert _build_summary(collection_count=2, vector_count=1200, storage_bytes=1024 * 1024, data_path=None) == '2 collections · 1,200 vectors · 1.0 MB'
