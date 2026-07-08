<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let title = 'Danger Zone';
	export let description = 'Destructive actions that cannot be undone.';
</script>

<div
	class="rounded-2xl border border-red-200/60 dark:border-red-900/40 bg-red-50/50 dark:bg-red-950/20"
>
	<div class="px-4 pt-3.5 pb-2 border-b border-red-200/40 dark:border-red-900/30">
		<div class="text-sm font-medium text-red-700 dark:text-red-300">{$i18n.t(title)}</div>
		{#if description}
			<p class="mt-0.5 text-xs text-red-600/80 dark:text-red-400/80">{$i18n.t(description)}</p>
		{/if}
	</div>

	<div class="px-4 py-3 space-y-2">
		<slot />
	</div>
</div>
