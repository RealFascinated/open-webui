import type { Writable } from 'svelte/store';
import type { i18n as I18nInstance } from 'i18next';

declare module 'svelte' {
	export function getContext(key: 'i18n'): Writable<I18nInstance>;
}
