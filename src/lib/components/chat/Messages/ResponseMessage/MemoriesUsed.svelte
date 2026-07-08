<script lang="ts">
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import Brain from '$lib/components/icons/Brain.svelte';

	const i18n = getContext('i18n');

	type UsedMemory = {
		id?: string;
		content?: string;
		path?: string | null;
		type?: string;
		section?: string;
		created_by?: string;
	};

	export let memories: UsedMemory[] = [];
	export let done = true;

	let expanded = false;

	$: preview = memories.slice(0, 2);
</script>

{#if memories.length > 0}
	<div class="status-description w-full text-left">
		<button
			type="button"
			class="flex w-full items-center gap-2 py-0.5 text-left"
			on:click={() => {
				expanded = !expanded;
			}}
		>
			<Brain className="size-4 shrink-0 text-gray-400" />
			<div class="min-w-0 flex-1">
				<div class="text-base text-gray-600 dark:text-gray-400">
					{$i18n.t('Used {{count}} memories', { count: memories.length })}
				</div>
				{#if !expanded}
					<div class="truncate text-xs text-gray-400 dark:text-gray-500">
						{preview.map((memory) => memory.content).filter(Boolean).join(' · ')}
					</div>
				{/if}
			</div>
		</button>

		{#if expanded}
			<ul class="mt-2 space-y-1.5 pl-6" transition:slide={{ duration: 150 }}>
				{#each memories as memory (memory.id ?? memory.content)}
					<li
						class="rounded-lg border border-gray-100 px-2.5 py-2 text-sm dark:border-gray-800"
					>
						<div class="flex items-center gap-2 text-[11px] text-gray-400">
							{#if memory.section}
								<span>{memory.section}</span>
							{/if}
							{#if memory.path}
								<span class="truncate">{memory.path}</span>
							{/if}
						</div>
						<div class="mt-0.5 whitespace-pre-wrap break-words text-gray-700 dark:text-gray-200">
							{memory.content}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
{/if}
