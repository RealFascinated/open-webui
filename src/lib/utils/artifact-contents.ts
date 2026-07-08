import type { ArtifactContent } from '$lib/stores';

export type ArtifactSelection =
	| string
	| {
			identifier?: string;
			content?: string;
			sourceCode?: string;
	  };

export const artifactSelectionFromAntArtifact = (
	artifact: import('$lib/utils/ant-artifact').AntArtifact
): ArtifactSelection => {
	if (!artifact.identifier) {
		return artifact.content;
	}

	return {
		identifier: artifact.identifier,
		content: artifact.content,
		sourceCode: artifact.artifactType === 'react' ? artifact.content : undefined
	};
};

const sameArtifactBody = (a: ArtifactContent, b: ArtifactContent): boolean =>
	a.content === b.content && a.sourceCode === b.sourceCode;

export const findLastArtifactIndex = (
	contents: ArtifactContent[],
	predicate: (item: ArtifactContent, index: number) => boolean
): number => {
	for (let index = contents.length - 1; index >= 0; index--) {
		if (predicate(contents[index], index)) return index;
	}
	return -1;
};

/**
 * Append or update panel entries while preserving completed revisions per identifier.
 */
export const upsertArtifactContent = (
	contents: ArtifactContent[],
	item: ArtifactContent
): ArtifactContent[] => {
	if (!item.identifier) {
		return [...contents, item];
	}

	const lastIdx = findLastArtifactIndex(
		contents,
		(entry) => entry.identifier === item.identifier
	);

	if (lastIdx === -1) {
		return [...contents, item];
	}

	const last = contents[lastIdx];
	const next = [...contents];

	if (item.streaming) {
		next[lastIdx] = item;
		return next;
	}

	if (last.streaming) {
		next[lastIdx] = item;
		return next;
	}

	if (sameArtifactBody(last, item)) {
		next[lastIdx] = { ...last, ...item };
		return next;
	}

	return [...contents, item];
};

export const getArtifactVersionIndices = (
	contents: ArtifactContent[],
	identifier?: string
): number[] => {
	if (!identifier) {
		return contents.length > 0 ? [0] : [];
	}

	return contents.reduce<number[]>((indices, entry, index) => {
		if (entry.identifier === identifier) indices.push(index);
		return indices;
	}, []);
};

export const navigateArtifactVersion = (
	contents: ArtifactContent[],
	currentIdx: number,
	direction: 'prev' | 'next'
): number => {
	const identifier = contents[currentIdx]?.identifier;
	const versionIndices = getArtifactVersionIndices(contents, identifier);
	if (versionIndices.length <= 1) return currentIdx;

	const position = versionIndices.indexOf(currentIdx);
	const basePosition = position === -1 ? versionIndices.length - 1 : position;
	const nextPosition =
		direction === 'prev'
			? Math.max(basePosition - 1, 0)
			: Math.min(basePosition + 1, versionIndices.length - 1);

	return versionIndices[nextPosition];
};

export const resolveArtifactContentIndex = (
	contents: ArtifactContent[],
	selection: ArtifactSelection | null
): number => {
	if (!selection || contents.length === 0) return -1;

	if (typeof selection === 'string') {
		const byContent = contents.findIndex((entry) => entry.content.includes(selection));
		if (byContent !== -1) return byContent;
		return findLastArtifactIndex(contents, (entry) => entry.identifier === selection);
	}

	const { identifier, content, sourceCode } = selection;

	if (identifier && sourceCode !== undefined) {
		const bySource = contents.findIndex(
			(entry) => entry.identifier === identifier && entry.sourceCode === sourceCode
		);
		if (bySource !== -1) return bySource;
	}

	if (identifier && content !== undefined) {
		const exact = contents.findIndex(
			(entry) =>
				entry.identifier === identifier &&
				entry.content === content &&
				(sourceCode === undefined || entry.sourceCode === sourceCode)
		);
		if (exact !== -1) return exact;

		const snippet = content.slice(0, 120);
		if (snippet) {
			const bySnippet = contents.findIndex(
				(entry) =>
					entry.identifier === identifier &&
					(entry.content.includes(snippet) ||
						entry.sourceCode?.includes(snippet) ||
						snippet.includes(entry.sourceCode?.slice(0, 120) ?? ''))
			);
			if (bySnippet !== -1) return bySnippet;
		}
	}

	if (identifier) {
		return findLastArtifactIndex(contents, (entry) => entry.identifier === identifier);
	}

	return -1;
};

export const preserveArtifactSelectionIndex = (
	previousContents: ArtifactContent[],
	previousIdx: number,
	nextContents: ArtifactContent[]
): number => {
	if (nextContents.length === 0) return 0;

	const previous = previousContents[previousIdx];
	if (!previous) {
		return Math.min(previousIdx, nextContents.length - 1);
	}

	if (previous.identifier) {
		const sameVersionIdx = nextContents.findIndex(
			(entry) =>
				entry.identifier === previous.identifier && sameArtifactBody(entry, previous)
		);
		if (sameVersionIdx !== -1) return sameVersionIdx;

		const latestIdx = findLastArtifactIndex(
			nextContents,
			(entry) => entry.identifier === previous.identifier
		);
		if (latestIdx !== -1) return latestIdx;
	} else {
		const sameBodyIdx = nextContents.findIndex((entry) => sameArtifactBody(entry, previous));
		if (sameBodyIdx !== -1) return sameBodyIdx;
	}

	return Math.min(previousIdx, nextContents.length - 1);
};

export const getArtifactVersionPosition = (
	contents: ArtifactContent[] | null | undefined,
	selection: ArtifactSelection | null
): { version: number; total: number } | null => {
	if (!contents?.length || !selection) return null;

	const idx = resolveArtifactContentIndex(contents, selection);
	if (idx === -1) return null;

	const identifier = contents[idx]?.identifier;
	const versionIndices = getArtifactVersionIndices(contents, identifier);
	const position = versionIndices.indexOf(idx);

	if (position === -1) {
		return { version: 1, total: 1 };
	}

	return { version: position + 1, total: versionIndices.length };
};
