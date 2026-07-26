from unittest.mock import AsyncMock, patch

import pytest

from open_webui.tools.builtin import _EXCHANGE_RATE_CACHE, _get_exchange_rate_payload, currency_convert


@pytest.mark.asyncio
async def test_exchange_rate_payload_cached():
    _EXCHANGE_RATE_CACHE.clear()
    payload = {'rates': {'EUR': 0.9, 'GBP': 0.8}, 'time_last_update_utc': 'Mon'}

    with patch('open_webui.tools.builtin._http_get_json', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = payload
        first = await _get_exchange_rate_payload('USD')
        second = await _get_exchange_rate_payload('USD')

    assert first == payload
    assert second == payload
    mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_currency_convert_multiple_targets():
    _EXCHANGE_RATE_CACHE.clear()
    payload = {'rates': {'EUR': 0.9, 'GBP': 0.8, 'JPY': 150.0}, 'time_last_update_utc': 'Mon'}

    with patch('open_webui.tools.builtin._http_get_json', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = payload
        result = await currency_convert(100, 'USD', to_currencies=['EUR', 'GBP', 'JPY'])

    import json

    data = json.loads(result)
    assert data['status'] == 'success'
    assert len(data['conversions']) == 3
    assert data['conversions'][0]['result'] == 90.0
    mock_get.assert_awaited_once()
