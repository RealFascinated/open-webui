import { describe, expect, it } from 'vitest';

import {
	getHiddenRichToolNames,
	hasActiveStatusHistory,
	isQuestionInMessage,
	shouldShowMessageResponseSkeleton,
	shouldShowRichContent,
	shouldShowResponseSkeleton
} from './messageRichContent';

describe('messageRichContent', () => {
	it('defers rich content until assistant text is available', () => {
		const message = {
			done: false,
			content: '',
			output: [{ type: 'function_call', name: 'weather_fetch', call_id: '1' }],
			weather: { location: 'London', temperature: 12 }
		};

		expect(shouldShowRichContent(message)).toBe(false);

		message.content = 'Here is the weather in London.';
		expect(shouldShowRichContent(message)).toBe(true);
	});

	it('shows rich content when the message is done even without text', () => {
		expect(
			shouldShowRichContent({
				done: true,
				content: '',
				weather: { location: 'London' }
			})
		).toBe(true);
	});

	it('returns compact tool names only when rich content is visible', () => {
		const message = {
			weather: { location: 'London' },
			files: [{ type: 'image', url: '/image.png' }]
		};

		expect(getHiddenRichToolNames(message, false)).toEqual(new Set());
		expect(getHiddenRichToolNames(message, true)).toEqual(
			new Set(['weather_fetch', 'generate_image', 'edit_image', 'image_search'])
		);
	});

	it('detects duplicate option questions in assistant text', () => {
		expect(
			isQuestionInMessage(
				'Which city should I check?',
				'Which city should I check? Pick one below.'
			)
		).toBe(true);
		expect(isQuestionInMessage('Pick a color', 'Here are your options.')).toBe(false);
	});

	it('shows skeleton while waiting for first assistant text', () => {
		expect(
			shouldShowResponseSkeleton({
				done: false,
				content: '',
				output: [{ type: 'function_call', name: 'weather_fetch' }]
			})
		).toBe(true);

		expect(
			shouldShowResponseSkeleton({
				done: false,
				content: '',
				output: [{ type: 'reasoning', content: [{ type: 'text', text: 'Thinking...' }] }]
			})
		).toBe(false);
	});

	it('keeps skeleton visible after completed status updates while waiting for text', () => {
		expect(
			shouldShowMessageResponseSkeleton({
				done: false,
				content: '',
				statusHistory: [{ action: 'sources_retrieved', count: 1, done: true } as never]
			})
		).toBe(true);
	});

	it('hides skeleton while an in-progress status update is active', () => {
		expect(
			shouldShowMessageResponseSkeleton({
				done: false,
				content: '',
				statusHistory: [{ action: 'sources_retrieved', done: false } as never]
			})
		).toBe(false);

		expect(
			hasActiveStatusHistory([{ action: 'sources_retrieved', done: false }], false)
		).toBe(true);
		expect(
			hasActiveStatusHistory([{ action: 'sources_retrieved', count: 1, done: true }], false)
		).toBe(false);
	});
});
