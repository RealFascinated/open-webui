import { describe, expect, it } from 'vitest';

import { formatToolName } from './index';

describe('formatToolName', () => {
	it('formats snake_case tool names', () => {
		expect(formatToolName('add_memory')).toBe('Add Memory');
		expect(formatToolName('weather_fetch')).toBe('Weather Fetch');
	});

	it('formats kebab-case tool names', () => {
		expect(formatToolName('search-web')).toBe('Search Web');
	});

	it('formats slash-separated tool names', () => {
		expect(formatToolName('mcp_server/add_memory')).toBe('Mcp Server / Add Memory');
	});

	it('returns empty string for empty input', () => {
		expect(formatToolName('')).toBe('');
	});
});
