import { buildReactHtml } from './react-artifact';

export type ArtifactMeta = {
	mime_type?: string;
	react_source?: string;
	identifier?: string;
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

/** Human-readable type badge for library UI. */
export function artifactDisplayLabel(type: string, meta: string | null | undefined): string {
	const parsed = parseArtifactMeta(meta);
	if (parsed.react_source || parsed.mime_type === 'application/vnd.ant.react') return 'React';
	if (parsed.mime_type === 'text/markdown' || type === 'markdown') return 'Markdown';
	if (type === 'svg') return 'SVG';
	return 'HTML';
}

/** Editable source for code view / agent tools (JSX when react, else stored code). */
export function artifactEditableSource(
	code: string,
	meta: string | null | undefined,
	type: string
): { artifactType: string; content: string; extension: string } {
	const parsed = parseArtifactMeta(meta);
	if (parsed.react_source) {
		return { artifactType: 'react', content: parsed.react_source, extension: 'jsx' };
	}
	if (parsed.mime_type === 'text/markdown' || type === 'markdown') {
		return { artifactType: 'markdown', content: code, extension: 'md' };
	}
	if (type === 'svg') {
		return { artifactType: 'svg', content: code, extension: 'svg' };
	}
	return { artifactType: 'iframe', content: code, extension: 'html' };
}

/** HTML to load in an iframe preview. */
export function artifactPreviewHtml(code: string, meta: string | null | undefined, type?: string): string {
	const parsed = parseArtifactMeta(meta);
	if (parsed.react_source) {
		return buildReactHtml(parsed.react_source);
	}
	if (parsed.mime_type === 'text/markdown' || type === 'markdown') {
		return code;
	}
	return code;
}

export function artifactIsMarkdown(type: string, meta: string | null | undefined): boolean {
	const parsed = parseArtifactMeta(meta);
	return parsed.mime_type === 'text/markdown' || type === 'markdown';
}

export function artifactPublishMeta(content: {
	sourceCode?: string;
	mimeType?: string;
	identifier?: string;
	type?: string;
}): string | undefined {
	const payload: ArtifactMeta = {};

	if (content.identifier) {
		payload.identifier = content.identifier;
	}

	if (content.sourceCode) {
		payload.mime_type = content.mimeType ?? 'application/vnd.ant.react';
		payload.react_source = content.sourceCode;
	} else if (content.mimeType === 'text/markdown' || content.type === 'markdown') {
		payload.mime_type = 'text/markdown';
	}

	if (Object.keys(payload).length === 0) return undefined;
	return JSON.stringify(payload);
}

export function publishedArtifactLookupKey(
	identifier: string | undefined,
	title: string | undefined
): string | undefined {
	if (identifier) return identifier;
	if (title) return `title:${title}`;
	return undefined;
}

/** Build identifier → artifact id map for the current chat. */
export function buildPublishedArtifactIdMap(
	artifacts: { id: string; chat_id: string | null; title: string | null; meta: string | null }[],
	chatId: string
): Record<string, string> {
	const map: Record<string, string> = {};
	for (const artifact of artifacts) {
		if (artifact.chat_id !== chatId) continue;
		const meta = parseArtifactMeta(artifact.meta);
		const key = publishedArtifactLookupKey(meta.identifier, artifact.title ?? undefined);
		if (key) map[key] = artifact.id;
	}
	return map;
}

export function resolvePublishedArtifactId(
	identifier: string | undefined,
	title: string | undefined,
	map: Record<string, string>
): string | undefined {
	const key = publishedArtifactLookupKey(identifier, title);
	return key ? map[key] : undefined;
}
