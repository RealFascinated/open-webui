import { getContext } from 'svelte';
import type { Writable } from 'svelte/store';
import type { i18n as I18nInstance } from 'i18next';

export type I18nStore = Writable<I18nInstance>;

/** Typed accessor for the root layout's i18n context store. */
export function getI18n(): I18nStore {
	return getContext('i18n');
}
