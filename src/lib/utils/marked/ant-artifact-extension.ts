import {
	mapMimeToArtifactType,
	parseAntArtifactAttributes,
	findMatchingArtifactClose
} from '$lib/utils/ant-artifact';

const OPEN = '<antArtifact';
const CLOSE = '</antArtifact>';

let allowStreamingTokens = false;

/** Enable partial antArtifact tokens while a message is still streaming. */
export const setAntArtifactStreamingEnabled = (enabled: boolean) => {
	allowStreamingTokens = enabled;
};

function antArtifactStart(src: string) {
	const match = src.match(/<antArtifact[\s>]/i);
	return match?.index ?? -1;
}

function antArtifactTokenizer(src: string) {
	const openMatch = src.match(/^<antArtifact([^>]*)>/i);
	if (!openMatch) return;

	const endIndex = findMatchingArtifactClose(src);
	const isComplete = endIndex !== -1;
	if (!isComplete && !allowStreamingTokens) return;

	const fullMatch = isComplete ? src.slice(0, endIndex) : src;
	const content = isComplete
		? fullMatch.slice(openMatch[0].length, -CLOSE.length).trim()
		: fullMatch.slice(openMatch[0].length).trim();
	const { identifier, type, title } = parseAntArtifactAttributes(openMatch[1]);

	return {
		type: 'antArtifact',
		raw: fullMatch,
		identifier,
		mimeType: type,
		title,
		content,
		artifactType: mapMimeToArtifactType(type),
		complete: isComplete,
		streaming: !isComplete
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
