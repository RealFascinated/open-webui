/**
 * Artifact iframe canvas theme — synced with Open WebUI light/dark mode.
 * Injected at preview time so stored artifact source stays theme-agnostic.
 */

export type ArtifactCanvasTheme = 'light' | 'dark';

export const ARTIFACT_CANVAS_COLORS = {
	light: {
		background: '#ffffff',
		foreground: '#111827',
		muted: '#6b7280',
		card: '#ffffff',
		border: '#e5e7eb'
	},
	dark: {
		background: '#0d0d0d',
		foreground: '#f3f4f6',
		muted: '#9ca3af',
		card: '#171717',
		border: '#374151'
	}
} as const;

const THEME_STYLE_ID = 'ows-artifact-canvas';

/** Resolve the canvas theme from Open WebUI settings + applied document class. */
export const resolveArtifactCanvasTheme = (
	themeSetting?: string | null
): ArtifactCanvasTheme => {
	const setting = (themeSetting ?? 'system').toLowerCase();
	if (setting === 'dark' || setting === 'oled-dark') return 'dark';
	if (setting === 'light' || setting === 'her') return 'light';

	if (typeof document !== 'undefined') {
		return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
	}

	return 'light';
};

export const artifactCanvasHtmlAttrs = (theme: ArtifactCanvasTheme): string =>
	`data-ows-artifact-theme="${theme}"`;

/** Base document styles for artifact iframes (low specificity — model CSS can override). */
export const artifactCanvasBaseCss = (theme: ArtifactCanvasTheme): string => {
	const colors = ARTIFACT_CANVAS_COLORS[theme];
	return `
  html { color-scheme: ${theme}; }
  body {
    margin: 0;
    padding: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: ${colors.background};
    color: ${colors.foreground};
  }
  #root { min-height: 100%; }
`.trim();
};

export const artifactCanvasStyleBlock = (theme: ArtifactCanvasTheme): string =>
	`<style id="${THEME_STYLE_ID}">${artifactCanvasBaseCss(theme)}</style>`;

/** Enable Tailwind \`dark:\` utilities when the canvas is dark. */
export const artifactCanvasTailwindDarkScript = (): string => `<script>
(function () {
  function configureTailwindDark() {
    if (typeof tailwind === 'undefined' || !tailwind.config) return;
    tailwind.config = Object.assign({}, tailwind.config, {
      darkMode: ['selector', '[data-ows-artifact-theme="dark"]']
    });
  }
  configureTailwindDark();
  document.addEventListener('DOMContentLoaded', configureTailwindDark);
})();
</script>`;

/**
 * Inject or refresh canvas theme on an HTML document string.
 * Safe to call repeatedly (e.g. when the user toggles light/dark).
 */
export const injectArtifactCanvasTheme = (
	html: string,
	theme: ArtifactCanvasTheme
): string => {
	if (!html?.trim()) return html;

	const attr = artifactCanvasHtmlAttrs(theme);
	const styleBlock = artifactCanvasStyleBlock(theme);
	const tailwindScript =
		theme === 'dark' && html.includes('cdn.tailwindcss.com')
			? artifactCanvasTailwindDarkScript()
			: '';

	let result = html;

	if (/<html\b/i.test(result)) {
		if (/data-ows-artifact-theme=/i.test(result)) {
			result = result.replace(/data-ows-artifact-theme="[^"]*"/i, attr);
		} else {
			result = result.replace(/<html\b([^>]*)>/i, `<html$1 ${attr}>`);
		}
	}

	const styleRe = new RegExp(
		`<style id="${THEME_STYLE_ID}"[^>]*>[\\s\\S]*?</style>`,
		'i'
	);
	if (styleRe.test(result)) {
		result = result.replace(styleRe, styleBlock);
	} else if (/<head\b[^>]*>/i.test(result)) {
		result = result.replace(/<head\b[^>]*>/i, (match) => `${match}\n${styleBlock}`);
	} else if (/<html\b[^>]*>/i.test(result)) {
		result = result.replace(
			/<html\b[^>]*>/i,
			(match) => `${match}\n<head>${styleBlock}</head>`
		);
	} else {
		result = `${styleBlock}\n${result}`;
	}

	if (tailwindScript && !result.includes('configureTailwindDark')) {
		if (/<\/head>/i.test(result)) {
			result = result.replace(/<\/head>/i, `${tailwindScript}\n</head>`);
		} else {
			result = `${tailwindScript}\n${result}`;
		}
	}

	return result;
};

export const buildArtifactDocumentShell = (
	bodyInner: string,
	theme: ArtifactCanvasTheme,
	extraHead = ''
): string => `<!DOCTYPE html>
<html lang="en" ${artifactCanvasHtmlAttrs(theme)}>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
${artifactCanvasStyleBlock(theme)}
${extraHead}
</head>
<body>
${bodyInner}
</body>
</html>`;
