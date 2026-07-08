<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { MemoryPathNode } from '$lib/utils/memory-ui';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{ select: string | null }>();

	export let nodes: MemoryPathNode[] = [];
	export let selectedPath: string | null = null;
	export let ungroupedCount = 0;
	export let depth = 0;

	const selectPath = (path: string | null) => {
		dispatch('select', path);
	};
</script>

<ul class="space-y-0.5">
	{#if depth === 0}
		<li>
			<button
				type="button"
				class="w-full flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition hover:bg-gray-100 dark:hover:bg-gray-800 {selectedPath ===
				null
					? 'bg-gray-100 dark:bg-gray-800 font-medium'
					: ''}"
				on:click={() => selectPath(null)}
			>
				<span>{$i18n.t('All memories')}</span>
			</button>
		</li>
		{#if ungroupedCount > 0}
			<li>
				<button
					type="button"
					class="w-full flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition hover:bg-gray-100 dark:hover:bg-gray-800 {selectedPath ===
					'__ungrouped__'
						? 'bg-gray-100 dark:bg-gray-800 font-medium'
						: ''}"
					on:click={() => selectPath('__ungrouped__')}
				>
					<span>{$i18n.t('Ungrouped')}</span>
					<span class="text-xs text-gray-400">{ungroupedCount}</span>
				</button>
			</li>
		{/if}
	{/if}

	{#each nodes as node (node.fullPath)}
		<li>
			<button
				type="button"
				class="w-full flex items-center justify-between gap-2 rounded-lg py-1.5 text-left text-sm transition hover:bg-gray-100 dark:hover:bg-gray-800 {selectedPath ===
				node.fullPath
					? 'bg-gray-100 dark:bg-gray-800 font-medium'
					: ''}"
				style={`padding-left: ${depth * 12 + 8}px`}
				on:click={() => selectPath(node.fullPath)}
			>
				<span class="flex min-w-0 items-center gap-1">
					{#if node.children.length > 0}
						<ChevronRight className="size-3 shrink-0 text-gray-400" />
					{/if}
					<span class="truncate">{node.name}</span>
				</span>
				{#if node.count > 0}
					<span class="shrink-0 text-xs text-gray-400">{node.count}</span>
				{/if}
			</button>
			{#if node.children.length > 0}
				<svelte:self
					nodes={node.children}
					{selectedPath}
					depth={depth + 1}
					{ungroupedCount}
					on:select={(event) => selectPath(event.detail)}
				/>
			{/if}
		</li>
	{/each}
</ul>
