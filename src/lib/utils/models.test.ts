import { describe, expect, test } from 'vitest';

import { getAvailableModelIds, resolveSelectedModels } from '$lib/utils/models';

const models = [
	{ id: 'visible-a', info: { meta: {} } },
	{ id: 'visible-b', info: { meta: {} } },
	{ id: 'hidden-c', info: { meta: { hidden: true } } }
];

describe('getAvailableModelIds', () => {
	test('excludes hidden models by default', () => {
		expect(getAvailableModelIds(models)).toEqual(['visible-a', 'visible-b']);
	});

	test('can include hidden models', () => {
		expect(getAvailableModelIds(models, { includeHidden: true })).toEqual([
			'visible-a',
			'visible-b',
			'hidden-c'
		]);
	});
});

describe('resolveSelectedModels', () => {
	const availableModelIds = ['visible-a', 'visible-b'];

	test('keeps valid selected models', () => {
		expect(resolveSelectedModels(['visible-b'], availableModelIds, ['visible-a'])).toEqual([
			'visible-b'
		]);
	});

	test('drops unavailable models but keeps valid ones', () => {
		expect(
			resolveSelectedModels(['missing-model', 'visible-b'], availableModelIds, ['visible-a'])
		).toEqual(['visible-b']);
	});

	test('falls back to default models when selection is empty', () => {
		expect(resolveSelectedModels(['missing-model'], availableModelIds, ['visible-a'])).toEqual([
			'visible-a'
		]);
	});

	test('falls back to the first available model when defaults are unavailable', () => {
		expect(resolveSelectedModels(['missing-model'], availableModelIds, ['also-missing'])).toEqual([
			'visible-a'
		]);
	});

	test('returns an empty placeholder when no models are available', () => {
		expect(resolveSelectedModels(['missing-model'], [], ['also-missing'])).toEqual(['']);
	});
});
