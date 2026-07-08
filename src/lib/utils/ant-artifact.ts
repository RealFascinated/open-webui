export type AntArtifact = {
	/** Stable kebab-case id from the model, e.g. "sales-dashboard". */
	identifier: string;
	/** MIME type, e.g. "text/html", "application/vnd.ant.react", "image/svg+xml". */
	type: string;
	/** Human-readable title supplied by the model. */
	title: string;
	/** Raw inner content of the tag. */
	content: string;
	/** Mapped internal type. null = unsupported (code, mermaid). */
	artifactType: 'iframe' | 'svg' | 'markdown' | 'react' | null;
	/** False while the closing tag has not arrived yet. */
	complete?: boolean;
};

const OPEN = '<antArtifact';
const CLOSE = '</antArtifact>';
const COMPLETE_ARTIFACT_RE = /<antArtifact([^>]*)>([\s\S]*?)<\/antArtifact>/gi;

export const mapMimeToArtifactType = (
	type: string
): AntArtifact['artifactType'] => {
	if (type === 'text/html') return 'iframe';
	if (type === 'application/vnd.ant.react') return 'react';
	if (type === 'image/svg+xml') return 'svg';
	if (type === 'text/markdown') return 'markdown';
	return null;
};

export const parseAntArtifactAttributes = (
	attrs: string
): Pick<AntArtifact, 'identifier' | 'type' | 'title'> => ({
	identifier: (attrs.match(/identifier="([^"]*)"/) ?? [])[1] ?? '',
	type: (attrs.match(/type="([^"]*)"/) ?? [])[1] ?? 'text/html',
	title: (attrs.match(/title="([^"]*)"/) ?? [])[1] ?? 'Artifact'
});

export const isArtifactComplete = (artifact: AntArtifact): boolean =>
	artifact.complete !== false;

export const findMatchingArtifactClose = (src: string): number => {
	let depth = 1;
	let index = OPEN.length;

	while (depth > 0 && index < src.length) {
		if (src.startsWith(OPEN, index)) {
			depth++;
		} else if (src.startsWith(CLOSE, index)) {
			depth--;
		}
		if (depth > 0) {
			index++;
		}
	}

	return depth === 0 ? index + CLOSE.length : -1;
};

const buildArtifact = (
	attrs: string,
	content: string,
	complete: boolean
): AntArtifact => {
	const { identifier, type, title } = parseAntArtifactAttributes(attrs);
	return {
		identifier,
		type,
		title,
		content: content.trim(),
		artifactType: mapMimeToArtifactType(type),
		complete
	};
};

/**
 * Scan a response for all antArtifact blocks, including one in-progress block
 * at the end of the stream when the closing tag has not arrived yet.
 */
export const scanAntArtifactBlocks = (text: string): AntArtifact[] => {
	const results: AntArtifact[] = [];
	let searchFrom = 0;

	while (searchFrom < text.length) {
		const openIdx = text.toLowerCase().indexOf(OPEN.toLowerCase(), searchFrom);
		if (openIdx === -1) break;

		const openTagEnd = text.indexOf('>', openIdx);
		if (openTagEnd === -1) break;

		const attrs = text.slice(openIdx + OPEN.length, openTagEnd);
		const bodyStart = openTagEnd + 1;
		const sliceFromOpen = text.slice(openIdx);
		const closeEnd = findMatchingArtifactClose(sliceFromOpen);

		if (closeEnd === -1) {
			results.push(buildArtifact(attrs, text.slice(bodyStart), false));
			break;
		}

		const absoluteCloseEnd = openIdx + closeEnd;
		const bodyEnd = absoluteCloseEnd - CLOSE.length;
		results.push(buildArtifact(attrs, text.slice(bodyStart, bodyEnd), true));
		searchFrom = absoluteCloseEnd;
	}

	return results;
};

/**
 * Extract complete <antArtifact> blocks only.
 */
export const parseAntArtifacts = (text: string): AntArtifact[] =>
	scanAntArtifactBlocks(text).filter(isArtifactComplete);

/**
 * Parse artifacts for live chat rendering and the artifact panel.
 */
export const parseAntArtifactsForStream = (text: string): AntArtifact[] =>
	scanAntArtifactBlocks(text);

export const serializeAntArtifact = (artifact: AntArtifact): string =>
	`<antArtifact identifier="${artifact.identifier}" type="${artifact.type}" title="${artifact.title}">\n${artifact.content}\n</antArtifact>`;

export const hasCompleteAntArtifact = (text: string): boolean =>
	COMPLETE_ARTIFACT_RE.test(text);

/** True when an opening tag (with closed `>`) exists in the text. */
export const hasAntArtifactOpenTag = (text: string): boolean =>
	/<antArtifact\b[^>]*>/i.test(text);

/** True when a block is currently streaming (open tag without matching close). */
export const hasStreamingAntArtifact = (text: string): boolean =>
	scanAntArtifactBlocks(text).some((artifact) => !isArtifactComplete(artifact));

/** True when the model has started or finished an antArtifact block. */
export const hasAntArtifactActivity = (text: string): boolean =>
	hasAntArtifactOpenTag(text) || hasCompleteAntArtifact(text);

/**
 * Artifacts present on message.content that are not yet represented in output
 * message items — includes in-progress streaming blocks.
 */
export const getOrphanStreamingArtifacts = (
	output?: import('$lib/components/chat/Messages/structuredOutput').OutputItem[] | null,
	content?: string | null
): AntArtifact[] => {
	const outputText = getOutputTextForOrphans(output);
	const cleanedContent = (content ?? '').trim();
	if (!cleanedContent) return [];

	return parseAntArtifactsForStream(cleanedContent).filter((artifact) => {
		if (artifact.identifier && outputText.includes(`identifier="${artifact.identifier}"`)) {
			return !artifactPresentInText(outputText, artifact);
		}
		return !artifactPresentInText(outputText, artifact);
	});
};

function getOutputTextForOrphans(
	output?: import('$lib/components/chat/Messages/structuredOutput').OutputItem[] | null
): string {
	return (output ?? [])
		.filter((item) => item?.type === 'message')
		.map((item) => {
			const parts = item.content ?? [];
			return parts
				.map((part) => (typeof part?.text === 'string' ? part.text : ''))
				.join('');
		})
		.join('\n');
}

const artifactPresentInText = (text: string, artifact: AntArtifact): boolean => {
	if (artifact.identifier && text.includes(`identifier="${artifact.identifier}"`)) {
		return true;
	}
	const snippet = artifact.content.slice(0, 120);
	return snippet.length > 0 && text.includes(snippet);
};

/**
 * Merge structured-output message text with <antArtifact> blocks that only
 * exist on message.content (e.g. streamed via delta before output finalization).
 */
export const mergeAssistantArtifactText = (
	outputText: string,
	content: string
): string => {
	const cleanedContent = content.trim();
	if (!cleanedContent) return outputText.trim();

	const missing = parseAntArtifacts(cleanedContent).filter(
		(artifact) => !artifactPresentInText(outputText, artifact)
	);
	if (missing.length === 0) return outputText.trim();

	const appended = missing.map(serializeAntArtifact).join('\n\n');
	if (outputText.trim()) {
		return `${outputText.trim()}\n\n${appended}`;
	}
	return appended;
};
