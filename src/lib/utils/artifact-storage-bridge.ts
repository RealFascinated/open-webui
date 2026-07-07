/**
 * Injects a window.storage bridge into artifact HTML before it is placed
 * into a sandboxed srcdoc iframe.
 *
 * The iframe has no allow-same-origin and cannot reach the parent's cookies,
 * DOM, or localStorage. Instead this script exposes window.storage as a
 * postMessage proxy: calls from the artifact's JS are forwarded to the parent
 * window which makes the real authenticated fetch to /api/v1/artifacts/.
 *
 * API — all methods return Promises:
 *   window.storage.get(key, shared?)         → {key, value, shared} | null
 *   window.storage.set(key, value, shared?)  → {key, value, shared} | null
 *     value is required (string; JSON.stringify objects). set(key) alone will fail.
 *   window.storage.delete(key, shared?)      → {key, deleted, shared} | null
 *   window.storage.list(prefix?, shared?)    → {keys, shared} | null
 *
 * Error contract:
 *   - A missing key resolves to null (not a throw). Always check result != null
 *     before accessing result.value.
 *   - Network or server errors reject the Promise. Always use try/catch.
 *
 * Key constraints:
 *   - Max 200 characters, no whitespace, no / \ ' " characters
 *   - Use hierarchical naming: "table:record_id" (e.g. "todos:todo_1")
 *   - Max 5 MB per value (JSON-serialise objects before storing)
 *   - Batch related data in one key to avoid multiple sequential calls
 *   - Only available in SAVED (published) artifacts — not in-chat previews
 */
export function injectStorageBridge(html: string, artifactId: string): string {
	const escapedId = artifactId.replace(/'/g, "\\'");

	const bridge = `<script>
(function () {
  var _seq = 0;
  var _pending = {};

  window.addEventListener('message', function (e) {
    var d = e.data;
    if (!d || !d._owsRequestId || !_pending[d._owsRequestId]) return;
    var p = _pending[d._owsRequestId];
    delete _pending[d._owsRequestId];
    if (d.error) { p.reject(new Error(d.error)); } else { p.resolve(d.result); }
  });

  function _call(method, args) {
    return new Promise(function (resolve, reject) {
      var id = '_ows_' + Date.now() + '_' + (_seq++);
      _pending[id] = { resolve: resolve, reject: reject };
      window.parent.postMessage({
        _owsStorage: true,
        _owsArtifactId: '${escapedId}',
        method: method,
        args: args,
        _owsRequestId: id
      }, '*');
    });
  }

  window.storage = {
    get:    function (key, shared)         { return _call('get',    { key: key, shared: !!shared }); },
    set:    function (key, value, shared)  {
      if (value === undefined || value === null) {
        return Promise.reject(new Error('storage.set requires a value as the second argument'));
      }
      return _call('set', { key: key, value: value, shared: !!shared });
    },
    delete: function (key, shared)         { return _call('delete', { key: key, shared: !!shared }); },
    list:   function (prefix, shared)      { return _call('list',   { prefix: prefix || '', shared: !!shared }); }
  };
})();
</script>`;

	const idx = html.indexOf('<head>');
	if (idx !== -1) {
		return html.slice(0, idx + 6) + bridge + html.slice(idx + 6);
	}
	// No <head> tag — prepend before anything else
	return bridge + html;
}
