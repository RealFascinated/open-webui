<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let size = 'md';
	export let labelled = false;
</script>

<div class="flex flex-col gap-2 py-1" role="status" aria-live="polite">
	{#if labelled}
		<div class="text-sm text-gray-400 dark:text-gray-500 shimmer">
			{$i18n.t('Waiting for response...')}
		</div>
	{/if}

	<div class="flex flex-col gap-1.5">
		<div
			class="{size === 'md'
				? 'h-2'
				: size === 'xs'
					? 'h-1'
					: 'h-1.5'} w-3/4 rounded-full bg-gray-100 dark:bg-gray-800 animate-pulse"
		></div>
		<div
			class="{size === 'md'
				? 'h-2'
				: size === 'xs'
					? 'h-1'
					: 'h-1.5'} w-1/2 rounded-full bg-gray-100 dark:bg-gray-800 animate-pulse"
		></div>
	</div>
</div>

<style>
	@media (prefers-reduced-motion: reduce) {
		:global(.animate-pulse) {
			animation: none !important;
		}
	}
</style>
