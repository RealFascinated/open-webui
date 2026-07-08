<script lang="ts">
	import { getContext } from 'svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	export let breadcrumbs: Array<{ label: string; href?: string }> = [];
	export let title = '';
	export let description = '';
</script>

{#if breadcrumbs.length > 0 || title}
	<div class="mb-4 shrink-0">
		{#if breadcrumbs.length > 0}
			<nav aria-label="Breadcrumb" class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-500 mb-1">
				{#each breadcrumbs as crumb, index (index)}
					{#if index > 0}
						<ChevronRight className="size-3 shrink-0 opacity-60" />
					{/if}
					{#if crumb.href}
						<a
							href={crumb.href}
							class="hover:text-gray-700 dark:hover:text-gray-300 transition truncate"
						>
							{$i18n.t(crumb.label)}
						</a>
					{:else}
						<span class="text-gray-700 dark:text-gray-300 truncate">{$i18n.t(crumb.label)}</span>
					{/if}
				{/each}
			</nav>
		{/if}

		{#if title}
			<h1 class="text-lg font-medium text-gray-900 dark:text-gray-100">{$i18n.t(title)}</h1>
		{/if}

		{#if description}
			<p class="mt-0.5 text-sm text-gray-500 dark:text-gray-500">{$i18n.t(description)}</p>
		{/if}
	</div>
{/if}
