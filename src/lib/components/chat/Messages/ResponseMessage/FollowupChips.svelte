<script lang="ts">
	import { pendingSubmit } from '$lib/stores';

	export let suggestions: string[] = [];
	export let disabled = false;

	let clicked: string | null = null;

	const handleClick = (text: string) => {
		if (disabled || clicked) return;
		clicked = text;
		pendingSubmit.set(text);
	};
</script>

{#if suggestions.length > 0}
	<div class="mt-2.5 flex flex-wrap gap-2">
		{#each suggestions as suggestion, idx (idx)}
			<button
				class="px-3 py-1.5 rounded-full text-sm border transition-colors
					{clicked === suggestion
					? 'border-gray-900 dark:border-gray-100 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900'
					: clicked
						? 'border-gray-200 dark:border-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed opacity-50'
						: 'border-gray-200 dark:border-gray-800 hover:border-gray-400 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400'}"
				disabled={disabled || (clicked !== null && clicked !== suggestion)}
				on:click={() => handleClick(suggestion)}
			>
				{suggestion}
			</button>
		{/each}
	</div>
{/if}
