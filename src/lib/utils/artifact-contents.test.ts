import { describe, expect, it } from 'vitest';

import type { ArtifactContent } from '$lib/stores';

import {
	getArtifactVersionIndices,
	getArtifactVersionPosition,
	navigateArtifactVersion,
	preserveArtifactSelectionIndex,
	resolveArtifactContentIndex,
	upsertArtifactContent
} from './artifact-contents';

const base = (overrides: Partial<ArtifactContent> = {}): ArtifactContent => ({
	type: 'iframe',
	content: '<p>v1</p>',
	identifier: 'demo',
	title: 'Demo',
	complete: true,
	streaming: false,
	...overrides
});

describe('upsertArtifactContent', () => {
	it('appends a new revision when the same identifier changes', () => {
		const first = base();
		const second = base({ content: '<p>v2</p>' });

		const once = upsertArtifactContent([], first);
		const twice = upsertArtifactContent(once, second);

		expect(twice).toHaveLength(2);
		expect(twice[0].content).toBe('<p>v1</p>');
		expect(twice[1].content).toBe('<p>v2</p>');
	});

	it('updates the in-progress revision in place', () => {
		const streaming = base({ content: '<p>partial', streaming: true, complete: false });
		const updated = base({ content: '<p>partial more', streaming: true, complete: false });

		const once = upsertArtifactContent([], streaming);
		const twice = upsertArtifactContent(once, updated);

		expect(twice).toHaveLength(1);
		expect(twice[0].content).toBe('<p>partial more');
	});

	it('finalizes a streaming revision without creating a new version', () => {
		const streaming = base({ content: '<p>partial', streaming: true, complete: false });
		const complete = base({ content: '<p>done</p>', streaming: false, complete: true });

		const once = upsertArtifactContent([], streaming);
		const twice = upsertArtifactContent(once, complete);

		expect(twice).toHaveLength(1);
		expect(twice[0].content).toBe('<p>done</p>');
		expect(twice[0].streaming).toBe(false);
	});
});

describe('artifact version navigation', () => {
	const contents = [
		base({ content: '<p>v1</p>' }),
		base({ content: '<p>v2</p>' }),
		base({ identifier: 'other', content: '<p>other</p>' })
	];

	it('returns only indices for the current identifier', () => {
		expect(getArtifactVersionIndices(contents, 'demo')).toEqual([0, 1]);
	});

	it('navigates within the current identifier group', () => {
		expect(navigateArtifactVersion(contents, 1, 'prev')).toBe(0);
		expect(navigateArtifactVersion(contents, 0, 'next')).toBe(1);
		expect(navigateArtifactVersion(contents, 2, 'prev')).toBe(2);
	});
});

describe('resolveArtifactContentIndex', () => {
	const contents = [
		base({ content: '<p>v1</p>' }),
		base({ content: '<p>v2</p>' })
	];

	const reactContents = [
		base({
			identifier: 'app',
			content: '<!DOCTYPE html><html>wrapper v1</html>',
			sourceCode: 'export default function App() { return <p>v1</p>; }'
		}),
		base({
			identifier: 'app',
			content: '<!DOCTYPE html><html>wrapper v2</html>',
			sourceCode: 'export default function App() { return <p>v2</p>; }'
		})
	];

	it('selects an exact revision by identifier and content', () => {
		expect(
			resolveArtifactContentIndex(contents, {
				identifier: 'demo',
				content: '<p>v1</p>'
			})
		).toBe(0);
	});

	it('selects a React revision by sourceCode', () => {
		expect(
			resolveArtifactContentIndex(reactContents, {
				identifier: 'app',
				content: 'export default function App() { return <p>v2</p>; }',
				sourceCode: 'export default function App() { return <p>v2</p>; }'
			})
		).toBe(1);
	});

	it('falls back to the latest revision for an identifier', () => {
		expect(resolveArtifactContentIndex(contents, 'demo')).toBe(1);
	});
});

describe('getArtifactVersionPosition', () => {
	const contents = [
		base({ content: '<p>v1</p>' }),
		base({ content: '<p>v2</p>' })
	];

	it('returns the version position for a specific revision', () => {
		expect(
			getArtifactVersionPosition(contents, {
				identifier: 'demo',
				content: '<p>v1</p>'
			})
		).toEqual({ version: 1, total: 2 });
	});
});

describe('preserveArtifactSelectionIndex', () => {
	const contents = [
		base({ content: '<p>v1</p>' }),
		base({ content: '<p>v2</p>' })
	];

	it('keeps the selected revision when the list is refreshed', () => {
		expect(preserveArtifactSelectionIndex(contents, 0, contents)).toBe(0);
	});

	it('falls back to the latest revision when the selected one disappears', () => {
		const latestOnly = [contents[1]];
		expect(preserveArtifactSelectionIndex(contents, 0, latestOnly)).toBe(0);
	});
});
