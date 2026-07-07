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
};

const ANT_ARTIFACT_RE = /<antArtifact([^>]*)>([\s\S]*?)<\/antArtifact>/gi;

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

/**
 * Extract all complete <antArtifact> blocks from a model response string.
 * Incomplete (still-streaming) tags are silently skipped.
 */
export const parseAntArtifacts = (text: string): AntArtifact[] => {
	const results: AntArtifact[] = [];
	let m: RegExpExecArray | null;
	const re = new RegExp(ANT_ARTIFACT_RE.source, ANT_ARTIFACT_RE.flags);
	while ((m = re.exec(text)) !== null) {
		const attrs = m[1];
		const content = m[2].trim();
		const { identifier, type, title } = parseAntArtifactAttributes(attrs);
		results.push({
			identifier,
			type,
			title,
			content,
			artifactType: mapMimeToArtifactType(type)
		});
	}
	return results;
};

export const serializeAntArtifact = (artifact: AntArtifact): string =>
	`<antArtifact identifier="${artifact.identifier}" type="${artifact.type}" title="${artifact.title}">\n${artifact.content}\n</antArtifact>`;

export const hasCompleteAntArtifact = (text: string): boolean =>
	/<antArtifact[^>]*>[\s\S]*?<\/antArtifact>/i.test(text);

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
