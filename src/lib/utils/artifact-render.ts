import { buildReactHtml } from './react-artifact';

export type ArtifactMeta = {
	mime_type?: string;
	react_source?: string;
};

export function parseArtifactMeta(meta: string | null | undefined): ArtifactMeta {
	if (!meta) return {};
	try {
		const parsed = JSON.parse(meta);
		return parsed && typeof parsed === 'object' ? (parsed as ArtifactMeta) : {};
	} catch {
		return {};
	}
}

/** Editable source for code view / agent tools (JSX when react, else stored code). */
export function artifactEditableSource(
	code: string,
	meta: string | null | undefined,
	type: string
): { artifactType: string; content: string } {
	const parsed = parseArtifactMeta(meta);
	if (parsed.react_source) {
		return { artifactType: 'react', content: parsed.react_source };
	}
	return { artifactType: type === 'svg' ? 'svg' : 'iframe', content: code };
}

/** HTML to load in an iframe preview. */
export function artifactPreviewHtml(
	code: string,
	meta: string | null | undefined,
	type: string
): string {
	const parsed = parseArtifactMeta(meta);
	if (parsed.react_source) {
		return buildReactHtml(parsed.react_source);
	}
	return code;
}

export function artifactPublishMeta(content: {
	sourceCode?: string;
	mimeType?: string;
}): string | undefined {
	if (!content.sourceCode) return undefined;
	return JSON.stringify({
		mime_type: content.mimeType ?? 'application/vnd.ant.react',
		react_source: content.sourceCode
	});
}
