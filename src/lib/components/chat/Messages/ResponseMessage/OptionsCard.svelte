<script lang="ts">
	import { pendingSubmit } from '$lib/stores';

	export let options: { question?: string; options?: string[] } = {};
	export let disabled = false;
	export let showQuestion = true;

	let selected: string | null = null;

	const handleSelect = (label: string) => {
		if (disabled || selected) return;
		selected = label;
		pendingSubmit.set(label);
	};
</script>

<div
	class="rounded-2xl border border-gray-50 dark:border-gray-850 bg-white dark:bg-gray-900 px-4 py-3.5"
>
	{#if showQuestion && options.question}
		<div class="text-sm font-medium text-gray-800 dark:text-gray-100 mb-2.5">{options.question}</div>
	{/if}
	<div class="flex flex-wrap gap-2">
		{#each options.options ?? [] as option, idx (idx)}
			<button
				class="px-3 py-1.5 rounded-full text-sm border transition-colors
					{selected === option
					? 'border-gray-900 dark:border-gray-100 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900'
					: selected
						? 'border-gray-200 dark:border-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
						: 'border-gray-200 dark:border-gray-800 hover:border-gray-400 dark:hover:border-gray-600 text-gray-700 dark:text-gray-300'}"
				disabled={disabled || (selected !== null && selected !== option)}
				on:click={() => handleSelect(option)}
			>
				{option}
			</button>
		{/each}
	</div>
</div>
