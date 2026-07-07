/**
 * Reports compile/render errors from sandboxed artifact iframes to the parent
 * window via postMessage (parent cannot read iframe DOM without same-origin).
 */

export type ArtifactErrorKind = 'compile' | 'render' | 'export' | 'runtime';

export type ArtifactErrorMessage = {
	_owsArtifactError: true;
	kind: ArtifactErrorKind;
	message: string;
};

/** Inline script injected into artifact HTML pages. */
export const ARTIFACT_ERROR_REPORT_SCRIPT = `<script>
function __reportArtifactError(kind, message) {
  try {
    window.parent.postMessage({
      _owsArtifactError: true,
      kind: kind,
      message: String(message || '')
    }, '*');
  } catch (e) {}
}
window.addEventListener('error', function(e) {
  var msg = (e.error && e.error.message) || e.message || 'Unknown error';
  __reportArtifactError('runtime', msg);
});
</script>`;

/** Inject error reporting into arbitrary artifact HTML (e.g. text/html). */
export function injectArtifactErrorBridge(html: string): string {
	if (html.includes('__reportArtifactError')) return html;

	const idx = html.indexOf('<head>');
	if (idx !== -1) {
		return html.slice(0, idx + 6) + ARTIFACT_ERROR_REPORT_SCRIPT + html.slice(idx + 6);
	}
	return ARTIFACT_ERROR_REPORT_SCRIPT + html;
}

export function buildArtifactFixPrompt(opts: {
	title?: string;
	identifier?: string;
	mimeType?: string;
	errorKind: string;
	errorMessage: string;
}): string {
	const idAttr = opts.identifier ? ` identifier="${opts.identifier}"` : '';
	const typeAttr = opts.mimeType ? ` type="${opts.mimeType}"` : '';
	const titleAttr = opts.title ? ` title="${opts.title}"` : '';
	const title = opts.title ?? 'artifact';

	return [
		`The "${title}" artifact failed (${opts.errorKind}):`,
		'',
		opts.errorMessage,
		'',
		`Fix the code and output the corrected <antArtifact${idAttr}${typeAttr}${titleAttr}> again.`,
		'Reuse the same identifier for an in-place panel update.',
		'Use only bundled libraries (react, recharts, lodash, mathjs, d3, papaparse).',
		'Do not use framer-motion or react-motion. Ensure all JSX tags are properly closed.'
	].join('\n');
}
