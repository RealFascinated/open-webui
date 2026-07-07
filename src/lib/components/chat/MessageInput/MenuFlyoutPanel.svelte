<script lang="ts">
	export let show = false;
	export let anchor: HTMLElement | null = null;
	export let onMouseEnter: () => void = () => {};
	export let onMouseLeave: () => void = () => {};

	const PANEL_WIDTH = 320;
	const BRIDGE_OVERLAP = 8;

	let opensLeft = false;
	let top = 0;
	let sideStyle = '';
	let bridgeStyle = '';

	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	}

	export function updatePlacement() {
		if (!anchor) return;

		const rect = anchor.getBoundingClientRect();
		const spaceRight = window.innerWidth - rect.right;
		opensLeft = spaceRight < PANEL_WIDTH + BRIDGE_OVERLAP;
		top = rect.top;
		sideStyle = opensLeft
			? `right: ${window.innerWidth - rect.left}px;`
			: `left: ${rect.right}px;`;
		bridgeStyle = opensLeft
			? `width: ${BRIDGE_OVERLAP}px; margin-right: -${BRIDGE_OVERLAP}px;`
			: `width: ${BRIDGE_OVERLAP}px; margin-left: -${BRIDGE_OVERLAP}px;`;
	}

	$: if (show && anchor) {
		updatePlacement();
	}
</script>

<svelte:window
	on:resize={() => show && updatePlacement()}
	on:scroll|capture={() => show && updatePlacement()}
/>

{#if show && anchor}
	<div
		use:portal
		class="fixed z-[10001] flex items-stretch {opensLeft ? 'flex-row-reverse' : ''}"
		data-menu-flyout
		role="group"
		style="top: {top}px; {sideStyle}"
		on:mouseenter={onMouseEnter}
		on:mouseleave={onMouseLeave}
	>
		<div
			class="shrink-0 self-stretch"
			aria-hidden="true"
			style={bridgeStyle}
			on:mouseenter={onMouseEnter}
			on:mouseleave={onMouseLeave}
		></div>
		<div
			class="w-80 min-w-[20rem] max-w-[calc(100vw-1rem)] rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-850 shadow-lg max-h-[min(28rem,calc(100dvh-5rem))] overflow-y-auto scrollbar-thin px-1 py-1"
		>
			<slot />
		</div>
	</div>
{/if}
