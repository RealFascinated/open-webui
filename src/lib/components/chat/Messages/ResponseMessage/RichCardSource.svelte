<script lang="ts">
	import { getContext } from 'svelte';

	import { formatToolName } from '$lib/utils';

	const i18n = getContext('i18n');

	export let toolName = '';
	export let sourceId = '';

	const scrollToTool = () => {
		const element = document.querySelector(`[data-tool-source="${sourceId}"]`);
		if (!element) return;

		element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
		element.classList.add(
			'ring-2',
			'ring-gray-300',
			'dark:ring-gray-600',
			'rounded',
			'transition-shadow'
		);
		setTimeout(() => {
			element.classList.remove(
				'ring-2',
				'ring-gray-300',
				'dark:ring-gray-600',
				'rounded',
				'transition-shadow'
			);
		}, 1500);
	};
</script>

{#if toolName && sourceId}
	<button
		type="button"
		class="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition"
		on:click={scrollToTool}
	>
		{$i18n.t('via {{NAME}}', { NAME: formatToolName(toolName) })}
	</button>
{/if}
