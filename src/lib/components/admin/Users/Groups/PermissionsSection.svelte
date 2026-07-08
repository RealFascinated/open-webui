<script lang="ts">
	import { getContext } from 'svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	export let title = '';
	export let description = '';
	export let open = false;
</script>

<div
	class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900 overflow-hidden"
>
	<button
		type="button"
		class="w-full flex items-start justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-850/40 transition"
		on:click={() => {
			open = !open;
		}}
	>
		<div class="min-w-0">
			<div class="text-sm font-medium">{$i18n.t(title)}</div>
			{#if description}
				<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-500">{$i18n.t(description)}</p>
			{/if}
		</div>
		<ChevronDown
			className="size-4 shrink-0 text-gray-400 transition-transform {open ? 'rotate-180' : ''}"
		/>
	</button>

	{#if open}
		<div class="px-4 pb-3 pt-0.5 border-t border-gray-100/30 dark:border-gray-850/30 space-y-1">
			<slot />
		</div>
	{/if}
</div>
