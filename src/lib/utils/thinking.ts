import { get } from 'svelte/store';

import { updateUserSettings } from '$lib/apis/users';
import { settings } from '$lib/stores';

export const THINKING_EFFORT_OPTIONS = ['low', 'medium', 'high'] as const;
export type ThinkingEffort = (typeof THINKING_EFFORT_OPTIONS)[number];
export const DEFAULT_THINKING_EFFORT: ThinkingEffort = 'medium';

export function getResolvedThink(
	userSettings?: { think?: boolean | string | null; params?: Record<string, unknown> } | null
): boolean | string | null | undefined {
	if (userSettings?.think !== undefined) {
		return userSettings.think;
	}
	return userSettings?.params?.think as boolean | string | null | undefined;
}

export function isThinkingEnabled(resolvedThink: unknown): boolean {
	return resolvedThink !== false;
}

export function getThinkingEffort(resolvedThink: unknown): ThinkingEffort {
	if (
		typeof resolvedThink === 'string' &&
		THINKING_EFFORT_OPTIONS.includes(resolvedThink as ThinkingEffort)
	) {
		return resolvedThink as ThinkingEffort;
	}

	return DEFAULT_THINKING_EFFORT;
}

export function resolveThinkForRequest(
	userSettings?: { think?: boolean | string | null; params?: Record<string, unknown> } | null
): boolean | string {
	const resolved = getResolvedThink(userSettings);
	if (resolved === false) return false;
	if (resolved === true) return DEFAULT_THINKING_EFFORT;
	if (typeof resolved === 'string') return resolved;
	return DEFAULT_THINKING_EFFORT;
}

export async function saveUserThinkingPreference(think: boolean | string) {
	const current = get(settings);
	const updated = {
		...current,
		think
	};

	settings.set(updated);
	await updateUserSettings(localStorage.token, { ui: updated });
}

export async function ensureDefaultThinkingPreference() {
	const current = get(settings);
	if (getResolvedThink(current) !== undefined) return;
	await saveUserThinkingPreference(DEFAULT_THINKING_EFFORT);
}
