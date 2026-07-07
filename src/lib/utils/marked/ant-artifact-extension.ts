import {
	mapMimeToArtifactType,
	parseAntArtifactAttributes
} from '$lib/utils/ant-artifact';

const OPEN = '<antArtifact';
const CLOSE = '</antArtifact>';

function findMatchingClosingTag(src: string): number {
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
}

function antArtifactStart(src: string) {
	const match = src.match(/<antArtifact[\s>]/i);
	return match?.index ?? -1;
}

function antArtifactTokenizer(src: string) {
	const openMatch = src.match(/^<antArtifact([^>]*)>/i);
	if (!openMatch) return;

	const endIndex = findMatchingClosingTag(src);
	if (endIndex === -1) return;

	const fullMatch = src.slice(0, endIndex);
	const content = fullMatch.slice(openMatch[0].length, -CLOSE.length).trim();
	const { identifier, type, title } = parseAntArtifactAttributes(openMatch[1]);

	return {
		type: 'antArtifact',
		raw: fullMatch,
		identifier,
		mimeType: type,
		title,
		content,
		artifactType: mapMimeToArtifactType(type)
	};
}

function antArtifactRenderer(token: {
	identifier: string;
	mimeType: string;
	title: string;
	content: string;
}) {
	return `<antArtifact identifier="${token.identifier}" type="${token.mimeType}" title="${token.title}">\n${token.content}\n</antArtifact>`;
}

export default function antArtifactExtension() {
	return {
		name: 'antArtifact',
		level: 'block',
		start: antArtifactStart,
		tokenizer: antArtifactTokenizer,
		renderer: antArtifactRenderer
	};
}
