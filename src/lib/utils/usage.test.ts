import { describe, expect, test } from 'vitest';

import {
	getContextBreakdownBarSegments,
	getContextBreakdownRows,
	getContextFreePercent,
	getContextFreeTokens,
	getAdditionalUsageRows,
	getFallbackContextBarSegments,
	getPerformanceUsageRows,
	type ContextBreakdown
} from './usage';

const labels = {
	system: 'System',
	memory: 'Memory',
	skills: 'Skills',
	files: 'Files',
	knowledge: 'Knowledge',
	tools: 'Tools',
	conversation: 'Conversation',
	tools_builtin: 'Builtin tools',
	tools_mcp: 'MCP tools',
	tools_user: 'User tools',
	tools_external: 'Tool servers',
	tools_terminal: 'Terminal tools'
};

describe('getContextBreakdownRows', () => {
	test('uses context window as percent denominator when provided', () => {
		const breakdown: ContextBreakdown = {
			verified: true,
			total: 20874,
			system: 13943,
			memory: 108,
			skills: 0,
			files: 0,
			knowledge: 0,
			tools: 6786,
			conversation: 37,
			tools_detail: { builtin: 6786 }
		};

		const rows = getContextBreakdownRows(breakdown, labels, 153600);
		const system = rows.find((row) => row.id === 'system');
		const tools = rows.find((row) => row.id === 'tools-builtin');

		expect(system?.percent).toBe(9.1);
		expect(tools?.percent).toBe(4.4);
	});

	test('collapses single tool category into one row', () => {
		const breakdown: ContextBreakdown = {
			verified: true,
			total: 20874,
			system: 13943,
			memory: 108,
			skills: 0,
			files: 0,
			knowledge: 0,
			tools: 6786,
			conversation: 37,
			tools_detail: { builtin: 6786 }
		};

		const rows = getContextBreakdownRows(breakdown, labels);
		const toolRows = rows.filter((row) => row.id.startsWith('tools'));

		expect(toolRows).toHaveLength(1);
		expect(toolRows[0]).toMatchObject({
			id: 'tools-builtin',
			label: 'Builtin tools',
			value: 6786
		});
	});

	test('expands multiple tool categories', () => {
		const breakdown: ContextBreakdown = {
			verified: true,
			total: 1000,
			system: 100,
			memory: 0,
			skills: 0,
			files: 0,
			knowledge: 0,
			tools: 900,
			conversation: 0,
			tools_detail: { builtin: 500, mcp: 400 }
		};

		const rows = getContextBreakdownRows(breakdown, labels);
		const toolRows = rows.filter((row) => row.id.startsWith('tools'));

		expect(toolRows).toHaveLength(3);
		expect(toolRows[0]).toMatchObject({ id: 'tools' });
		expect(toolRows[1]).toMatchObject({ id: 'tools-builtin', nested: true });
		expect(toolRows[2]).toMatchObject({ id: 'tools-mcp', nested: true });
	});
});

describe('getContextBreakdownBarSegments', () => {
	test('includes generation and free slices relative to the window', () => {
		const rows = getContextBreakdownRows(
			{
				verified: true,
				total: 20874,
				system: 13943,
				memory: 108,
				skills: 0,
				files: 0,
				knowledge: 0,
				tools: 6786,
				conversation: 37,
				tools_detail: { builtin: 6786 }
			},
			labels,
			153600
		);

		const segments = getContextBreakdownBarSegments(rows, {
			windowSize: 153600,
			generationTokens: 366,
			freeTokens: 132360
		});

		expect(segments.find((segment) => segment.id === 'generation')?.percent).toBe(0.2);
		expect(segments.find((segment) => segment.id === 'free')?.percent).toBe(86.2);
	});
});

describe('getContextFreeTokens', () => {
	test('returns remaining window space', () => {
		expect(getContextFreeTokens(21240, 153600)).toBe(132360);
		expect(getContextFreePercent(21240, 153600)).toBe(86);
	});
});

describe('getFallbackContextBarSegments', () => {
	test('builds prompt and generation slices relative to used context', () => {
		const segments = getFallbackContextBarSegments([], 34731, 309);

		expect(segments).toHaveLength(2);
		expect(segments[0]).toMatchObject({ id: 'prompt', value: 34422 });
		expect(segments[1]).toMatchObject({ id: 'generation', value: 309 });
	});

	test('uses breakdown rows when available', () => {
		const rows = getContextBreakdownRows(
			{
				verified: true,
				total: 20000,
				system: 12000,
				memory: 0,
				skills: 0,
				files: 0,
				knowledge: 0,
				tools: 7000,
				conversation: 1000,
				tools_detail: { builtin: 7000 }
			},
			labels
		);

		const segments = getFallbackContextBarSegments(rows, 21000, 1000);
		const system = segments.find((segment) => segment.id === 'system');

		expect(system?.value).toBe(12000);
		expect(segments.find((segment) => segment.id === 'generation')?.value).toBe(1000);
	});
});

describe('usage row helpers', () => {
	test('hides internal llama.cpp token accounting from additional rows', () => {
		const rows = getAdditionalUsageRows({
			prompt_tokens: 34365,
			completion_tokens: 366,
			last_input_tokens: 18155,
			last_output_tokens: 309,
			prompt_cache_hit_tokens: 16128,
			prompt_cache_miss_tokens: 2027,
			cache_n: 32256,
			prompt_n: 2109
		});

		expect(rows).toEqual([]);
	});

	test('groups timing metrics into performance rows', () => {
		const rows = getPerformanceUsageRows({
			prompt_eval_duration: 1_500_000_000,
			predicted_per_second: 42.5
		});

		expect(rows.some((row) => row.label.includes('Prompt Eval Duration'))).toBe(true);
		expect(rows.some((row) => row.value.includes('tok/s'))).toBe(true);
	});
});
