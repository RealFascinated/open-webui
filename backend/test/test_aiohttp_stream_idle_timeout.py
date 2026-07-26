"""Behavioral tests for the streaming per-chunk idle timeout (aiohttp sock_read)."""

import asyncio

import aiohttp
from aiohttp import web
from aiohttp.test_utils import unused_port

_STALL_SECONDS = 3


async def _stall_handler(request):
    resp = web.StreamResponse()
    resp.headers['Content-Type'] = 'text/event-stream'
    await resp.prepare(request)
    await resp.write(b'data: chunk-0\n\n')
    await asyncio.sleep(_STALL_SECONDS)
    return resp


async def _steady_handler(request):
    resp = web.StreamResponse()
    resp.headers['Content-Type'] = 'text/event-stream'
    await resp.prepare(request)
    for i in range(8):
        await resp.write(f'data: chunk-{i}\n\n'.encode())
        await asyncio.sleep(0.5)
    await resp.write_eof()
    return resp


async def _serve():
    port = unused_port()
    app = web.Application()
    app.add_routes(
        [
            web.get('/stall', _stall_handler),
            web.get('/steady', _steady_handler),
        ]
    )
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', port)
    await site.start()
    return runner, f'http://127.0.0.1:{port}'


async def _run_stall_trips_on_idle():
    runner, base = await _serve()
    try:
        timeout = aiohttp.ClientTimeout(total=10, sock_read=1)
        loop = asyncio.get_event_loop()
        start = loop.time()
        got_first_chunk = False
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{base}/stall', timeout=timeout) as resp:
                async for _ in resp.content:
                    got_first_chunk = True
        return None, loop.time() - start, got_first_chunk
    except asyncio.TimeoutError:
        return 'timeout', loop.time() - start, got_first_chunk
    finally:
        await runner.cleanup()


async def _run_steady_completes():
    runner, base = await _serve()
    try:
        timeout = aiohttp.ClientTimeout(total=10, sock_read=1)
        chunks = 0
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{base}/steady', timeout=timeout) as resp:
                async for line in resp.content:
                    if line.strip():
                        chunks += 1
        return chunks
    finally:
        await runner.cleanup()


def test_stalled_stream_trips_sock_read_before_total():
    kind, elapsed, got_first_chunk = asyncio.run(_run_stall_trips_on_idle())
    assert kind == 'timeout'
    assert 0.8 <= elapsed <= 5.0, elapsed
    assert got_first_chunk is True


def test_active_stream_is_not_interrupted_by_idle_cap():
    chunks = asyncio.run(_run_steady_completes())
    assert chunks == 8
