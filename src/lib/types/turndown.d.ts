declare module 'turndown' {
	export interface TurndownRule {
		filter: string | string[] | ((node: HTMLElement) => boolean);
		replacement: (content: string, node: HTMLElement) => string;
	}

	export default class TurndownService {
		constructor(options?: Record<string, unknown>);
		turndown(html: string): string;
		addRule(key: string, rule: TurndownRule): void;
		use(plugin: unknown): void;
		escape: (string: string) => string;
	}
}

declare module '@joplin/turndown-plugin-gfm' {
	export function gfm(service: import('turndown').default): void;
}
