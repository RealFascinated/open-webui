import { describe, expect, it } from 'vitest';

import { buildOutputDisplayItems, type OutputItem } from './structuredOutput';

describe('buildOutputDisplayItems', () => {
	it('preserves chronological order between messages and tool calls', () => {
		const output: OutputItem[] = [
			{ type: 'reasoning', id: 'r1', status: 'completed', summary: [{ text: 'Thinking' }] },
			{ type: 'web_search_call', id: 's1', status: 'completed', action: { type: 'search', query: 'foo' } },
			{ type: 'message', id: 'm1', content: [{ text: 'First part.' }] },
			{ type: 'function_call', id: 'fc1', call_id: 'c1', name: 'weather_fetch', status: 'completed' },
			{ type: 'function_call_output', call_id: 'c1', output: [{ text: 'sunny' }] },
			{ type: 'message', id: 'm2', content: [{ text: 'Second part.' }] }
		];

		const items = buildOutputDisplayItems(output);

		expect(items.map((item) => item.type)).toEqual([
			'detail_group',
			'message',
			'detail_single',
			'message'
		]);

		expect(items[0].type === 'detail_group' && items[0].tokens.length).toBe(2);
		expect(items[1].type === 'message' && items[1].text).toBe('First part.');
		expect(items[2].type === 'detail_single' && items[2].token.attributes.name).toBe('weather_fetch');
		expect(items[3].type === 'message' && items[3].text).toBe('Second part.');
	});

	it('groups consecutive detail tokens and splits groups around messages', () => {
		const output: OutputItem[] = [
			{ type: 'function_call', id: 'fc1', call_id: 'c1', name: 'tool_a', status: 'completed' },
			{ type: 'function_call_output', call_id: 'c1', output: [{ text: 'a' }] },
			{ type: 'function_call', id: 'fc2', call_id: 'c2', name: 'tool_b', status: 'completed' },
			{ type: 'function_call_output', call_id: 'c2', output: [{ text: 'b' }] },
			{ type: 'message', id: 'm1', content: [{ text: 'Answer.' }] }
		];

		const items = buildOutputDisplayItems(output);

		expect(items.map((item) => item.type)).toEqual(['detail_group', 'message']);
		expect(items[0].type === 'detail_group' && items[0].tokens.length).toBe(2);
	});

	it('marks rich-content tools as compact instead of removing them', () => {
		const output: OutputItem[] = [
			{ type: 'reasoning', id: 'r1', status: 'completed', duration: 1, summary: [{ text: 'Thinking' }] },
			{
				type: 'function_call',
				id: 'fc1',
				call_id: 'c1',
				name: 'weather_fetch',
				status: 'completed',
				arguments: { location: 'London' }
			},
			{ type: 'function_call_output', call_id: 'c1', output: [{ text: 'sunny' }] }
		];

		const items = buildOutputDisplayItems(output, null, new Set(['weather_fetch']));

		expect(items).toHaveLength(1);
		expect(items[0].type).toBe('detail_group');
		if (items[0].type === 'detail_group') {
			expect(items[0].tokens).toHaveLength(2);
			expect(items[0].tokens[1].attributes.compact).toBe('true');
			expect(items[0].tokens[1].attributes.name).toBe('weather_fetch');
			expect(items[0].tokens[1].attributes.context).toBe('London');
		}
	});

	it('merges consecutive reasoning tokens', () => {
		const output: OutputItem[] = [
			{ type: 'reasoning', id: 'r1', status: 'completed', duration: 1, summary: [{ text: 'Step one' }] },
			{ type: 'reasoning', id: 'r2', status: 'completed', duration: 1, summary: [{ text: 'Step two' }] },
			{
				type: 'function_call',
				id: 'fc1',
				call_id: 'c1',
				name: 'weather_fetch',
				status: 'completed'
			},
			{ type: 'function_call_output', call_id: 'c1', output: [{ text: 'sunny' }] }
		];

		const items = buildOutputDisplayItems(output);

		expect(items).toHaveLength(1);
		expect(items[0].type).toBe('detail_group');
		if (items[0].type === 'detail_group') {
			expect(items[0].tokens).toHaveLength(2);
			expect(items[0].tokens[0].attributes.type).toBe('reasoning');
			expect(items[0].tokens[0].attributes.duration).toBe('2');
			expect(items[0].tokens[0].summary).toBe('Thought for 2 seconds');
		}
	});
});

describe('buildOutputDisplayItems tool status metadata', () => {
	it('includes status and context on function_call tokens', () => {
		const output: OutputItem[] = [
			{
				type: 'function_call',
				id: 'fc1',
				call_id: 'c1',
				name: 'fetch_url',
				status: 'in_progress',
				arguments: { url: 'https://example.com' }
			}
		];

		const items = buildOutputDisplayItems(output);
		expect(items).toHaveLength(1);
		expect(items[0].type).toBe('detail_single');
		if (items[0].type === 'detail_single') {
			expect(items[0].token.attributes.status).toBe('in_progress');
			expect(items[0].token.attributes.done).toBe('false');
			expect(items[0].token.attributes.context).toBe('https://example.com');
		}
	});

	it('marks cancelled tools as terminal failures', () => {
		const output: OutputItem[] = [
			{
				type: 'function_call',
				id: 'fc1',
				call_id: 'c1',
				name: 'weather_fetch',
				status: 'cancelled'
			}
		];

		const items = buildOutputDisplayItems(output);
		if (items[0].type === 'detail_single') {
			expect(items[0].token.attributes.status).toBe('cancelled');
			expect(items[0].token.attributes.done).toBe('true');
			expect(items[0].token.summary).toBe('Tool Cancelled');
		}
	});
});
