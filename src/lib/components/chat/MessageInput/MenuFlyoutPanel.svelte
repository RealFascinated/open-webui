<script lang="ts">
	import { tick } from 'svelte';

	export let show = false;
	export let anchor: HTMLElement | null = null;
	export let onMouseEnter: () => void = () => {};
	export let onMouseLeave: () => void = () => {};

	const PANEL_WIDTH = 320;
	const SIDE_OFFSET = 8;
	const VIEWPORT_MARGIN = 16;

	let flyoutEl: HTMLElement | null = null;
	let panelEl: HTMLElement | null = null;

	export function canOpenAsSideFlyout(
		target: HTMLElement | null = anchor,
		panelWidth = PANEL_WIDTH
	): boolean {
		if (!target) return false;

		const rect = target.getBoundingClientRect();
		const spaceRight = window.innerWidth - rect.right;
		const spaceLeft = rect.left;

		return (
			spaceRight >= panelWidth + SIDE_OFFSET + VIEWPORT_MARGIN ||
			spaceLeft >= panelWidth + SIDE_OFFSET + VIEWPORT_MARGIN
		);
	}

	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	}

	export async function updatePlacement() {
		if (!anchor || !flyoutEl) return;

		const rect = anchor.getBoundingClientRect();
		const contentWidth = panelEl?.offsetWidth || PANEL_WIDTH;
		const contentHeight = flyoutEl.offsetHeight || 0;

		flyoutEl.style.position = 'fixed';
		flyoutEl.style.zIndex = '10001';
		flyoutEl.style.paddingLeft = '0';
		flyoutEl.style.paddingRight = '0';
		flyoutEl.style.bottom = 'auto';

		const rightSpace = window.innerWidth - rect.right;
		if (rightSpace >= contentWidth + SIDE_OFFSET) {
			flyoutEl.style.left = `${rect.right}px`;
			flyoutEl.style.right = 'auto';
			flyoutEl.style.paddingLeft = `${SIDE_OFFSET}px`;
		} else {
			flyoutEl.style.right = `${window.innerWidth - rect.left}px`;
			flyoutEl.style.left = 'auto';
			flyoutEl.style.paddingRight = `${SIDE_OFFSET}px`;
		}

		let top = rect.top;
		if (contentHeight > 0) {
			if (top + contentHeight + VIEWPORT_MARGIN > window.innerHeight) {
				top = window.innerHeight - contentHeight - VIEWPORT_MARGIN;
			}
			if (top < VIEWPORT_MARGIN) {
				top = VIEWPORT_MARGIN;
			}
		}

		flyoutEl.style.top = `${top}px`;
	}

	$: if (show && anchor) {
		tick().then(() => {
			updatePlacement();
			setTimeout(updatePlacement, 50);
		});
	}
</script>

<svelte:window
	on:resize={() => show && updatePlacement()}
	on:scroll|capture={() => show && updatePlacement()}
/>

{#if show && anchor}
	<div
		use:portal
		bind:this={flyoutEl}
		data-menu-flyout
		role="group"
		on:mouseenter={onMouseEnter}
		on:mouseleave={onMouseLeave}
	>
		<div
			bind:this={panelEl}
			class="w-80 max-w-[calc(100vw-2rem)] min-w-0 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-850 shadow-lg max-h-[min(28rem,calc(100dvh-5rem))] overflow-y-auto scrollbar-thin px-1 py-1"
		>
			<slot />
		</div>
	</div>
{/if}
