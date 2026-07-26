import { describe, expect, it } from 'vitest';

import {
	getToolCallContextFromArguments,
	isToolCallPending,
	resolveToolCallStatus
} from './toolCallDisplay';

describe('toolCallDisplay', () => {
	it('resolves explicit tool statuses', () => {
		expect(resolveToolCallStatus({ status: 'failed', done: 'true' })).toBe('failed');
		expect(resolveToolCallStatus({ status: 'cancelled', done: 'true' })).toBe('cancelled');
		expect(resolveToolCallStatus({ done: 'false' })).toBe('in_progress');
	});

	it('keeps tools in progress even when message is done, since tool may still be running', () => {
		expect(resolveToolCallStatus({ done: 'false' }, true)).toBe('in_progress');
		expect(isToolCallPending('in_progress', true)).toBe(true);
	});

	it('extracts useful context from common tool arguments', () => {
		expect(getToolCallContextFromArguments({ query: 'open-webui docs' })).toBe('open-webui docs');
		expect(getToolCallContextFromArguments('https://example.com')).toBe('https://example.com');
	});
});
