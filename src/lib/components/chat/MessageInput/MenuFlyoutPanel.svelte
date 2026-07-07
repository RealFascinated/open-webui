<script lang="ts">
	export let show = false;
	export let anchor: HTMLElement | null = null;
	export let onMouseEnter: () => void = () => {};
	export let onMouseLeave: () => void = () => {};

	const PANEL_WIDTH = 320;
	const PANEL_GAP = 12;

	let opensLeft = false;
	let top = 0;
	let sideStyle = '';

	export function updatePlacement() {
		if (!anchor) return;

		const rect = anchor.getBoundingClientRect();
		const spaceRight = window.innerWidth - rect.right;
		opensLeft = spaceRight < PANEL_WIDTH + PANEL_GAP;
		top = rect.top;
		sideStyle = opensLeft
			? `right: ${window.innerWidth - rect.left + PANEL_GAP}px;`
			: `left: ${rect.right + PANEL_GAP}px;`;
	}

	$: if (show && anchor) {
		updatePlacement();
	}
</script>

<svelte:window on:resize={() => show && updatePlacement()} />

{#if show && anchor}
	<div
		class="fixed z-[10001] flex items-stretch {opensLeft ? 'flex-row-reverse' : ''}"
		style="top: {top}px; {sideStyle}"
		on:mouseenter={onMouseEnter}
		on:mouseleave={onMouseLeave}
	>
		<div
			class="w-3 shrink-0 self-stretch"
			aria-hidden="true"
			on:mouseenter={onMouseEnter}
			on:mouseleave={onMouseLeave}
		/>
		<div
			class="w-80 min-w-[20rem] max-w-[calc(100vw-1rem)] rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-850 shadow-lg max-h-[min(28rem,calc(100dvh-5rem))] overflow-y-auto scrollbar-thin px-1 py-1"
		>
			<slot />
		</div>
	</div>
{/if}
