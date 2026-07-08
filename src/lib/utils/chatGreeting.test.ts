import { describe, expect, it } from 'vitest';

import { getChatGreetingKey, getTimeOfDay } from './chatGreeting';

describe('chatGreeting', () => {
	it('maps hours to time-of-day buckets', () => {
		expect(getTimeOfDay(new Date('2026-07-08T08:00:00'))).toBe('morning');
		expect(getTimeOfDay(new Date('2026-07-08T13:00:00'))).toBe('afternoon');
		expect(getTimeOfDay(new Date('2026-07-08T19:00:00'))).toBe('evening');
		expect(getTimeOfDay(new Date('2026-07-08T23:00:00'))).toBe('night');
	});

	it('returns a greeting from the time-based and random pool', () => {
		const greeting = getChatGreetingKey(new Date('2026-07-08T08:00:00'));

		expect([
			'Good morning, {{name}}',
			'Hello, {{name}}',
			'Hey, {{name}}',
			'Hi, {{name}}',
			'Welcome back, {{name}}'
		]).toContain(greeting);
	});
});
