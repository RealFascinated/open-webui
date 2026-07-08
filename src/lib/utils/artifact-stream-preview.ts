import {
	type ArtifactCanvasTheme,
	ARTIFACT_CANVAS_COLORS,
	buildArtifactDocumentShell
} from './artifact-theme';

const SCRIPT_BLOCK_RE = /<script\b[^>]*>[\s\S]*?<\/script>/gi;
const SCRIPT_OPEN_TAIL_RE = /<script\b[^>]*>[\s\S]*$/i;
const PARTIAL_CLOSE_RE = /<\/antArtifact?$/i;

/** Remove executable scripts from in-progress artifact HTML. */
export const stripStreamingScripts = (html: string): string =>
	html.replace(SCRIPT_BLOCK_RE, '').replace(SCRIPT_OPEN_TAIL_RE, '');

/** Trim a partially typed closing tag at the end of streamed artifact bodies. */
export const trimPartialArtifactClose = (content: string): string =>
	content.replace(PARTIAL_CLOSE_RE, '').trimEnd();

const hasHtmlDocumentShell = (html: string): boolean =>
	/<!DOCTYPE/i.test(html) || /<html[\s>]/i.test(html);

const escapeHtml = (value: string): string =>
	value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');

const placeholderStyles = (theme: ArtifactCanvasTheme): string => {
	const colors = ARTIFACT_CANVAS_COLORS[theme];
	return `
  *, *::before, *::after { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: ${colors.muted};
    background: ${colors.background};
  }
  .card {
    text-align: center;
    padding: 1.5rem 2rem;
    border-radius: 1rem;
    border: 1px solid ${colors.border};
    background: ${colors.card};
    max-width: 20rem;
  }
  .title { font-size: 0.95rem; font-weight: 600; color: ${colors.foreground}; margin: 0.75rem 0 0.25rem; }
  .subtitle { font-size: 0.8rem; margin: 0; color: ${colors.muted}; }
  .spinner {
    width: 1.5rem;
    height: 1.5rem;
    margin: 0 auto;
    border: 2px solid ${colors.border};
    border-top-color: ${colors.muted};
    border-radius: 9999px;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
`.trim();
};

export const buildStreamingPlaceholderPage = (
	title: string,
	subtitle: string,
	canvasTheme: ArtifactCanvasTheme = 'light'
): string =>
	buildArtifactDocumentShell(
		`<div class="card">
    <div class="spinner" aria-hidden="true"></div>
    <p class="title">${escapeHtml(title || 'Artifact')}</p>
    <p class="subtitle">${escapeHtml(subtitle)}</p>
  </div>`,
		canvasTheme,
		`<style>${placeholderStyles(canvasTheme)}</style>`
	);

/**
 * Build a safe, progressively renderable HTML document for iframe preview.
 * Scripts are stripped until the artifact block is complete.
 */
export const buildStreamingHtmlPreview = (
	rawContent: string,
	complete: boolean,
	canvasTheme: ArtifactCanvasTheme = 'light'
): string => {
	let content = trimPartialArtifactClose(rawContent);
	if (!content.trim()) {
		return buildStreamingPlaceholderPage(
			'Artifact',
			complete ? 'Empty artifact' : 'Waiting for content…',
			canvasTheme
		);
	}

	if (!complete) {
		content = stripStreamingScripts(content);
	}

	if (hasHtmlDocumentShell(content)) {
		return content;
	}

	return buildArtifactDocumentShell(content, canvasTheme);
};
