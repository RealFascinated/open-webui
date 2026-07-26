declare module 'sortablejs' {
	export interface SortableEvent extends Event {
		item: HTMLElement;
		newIndex?: number;
		oldIndex?: number;
		from?: HTMLElement;
		to?: HTMLElement;
	}

	export interface SortableOptions {
		animation?: number;
		onUpdate?: (event: SortableEvent) => void;
		[key: string]: unknown;
	}

	export default class Sortable {
		constructor(el: HTMLElement, options?: SortableOptions);
		static create(el: HTMLElement, options?: SortableOptions): Sortable;
	}
}
