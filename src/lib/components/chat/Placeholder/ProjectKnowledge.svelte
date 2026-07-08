<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { knowledge } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';

	const i18n = getContext('i18n');

	export let project: { data?: { files?: Array<{ type?: string; id?: string; name?: string }> } } | null =
		null;

	let resolvedItems: Array<{ id: string; name: string; type: string }> = [];

	const resolveItems = async () => {
		const entries = project?.data?.files ?? [];
		if (!entries.length) {
			resolvedItems = [];
			return;
		}

		let knowledgeBases = $knowledge;
		if (!knowledgeBases) {
			knowledgeBases = await getKnowledgeBases(localStorage.token).catch(() => []);
			knowledge.set(knowledgeBases);
		}

		resolvedItems = entries
			.filter((entry) => entry?.id)
			.map((entry) => {
				if (entry.type === 'collection') {
					const collection = (knowledgeBases ?? []).find((kb) => kb.id === entry.id);
					return {
						id: entry.id,
						name: collection?.name ?? entry.name ?? entry.id,
						type: 'collection'
					};
				}

				return {
					id: entry.id,
					name: entry.name ?? entry.id,
					type: entry.type === 'file' ? 'file' : (entry.type ?? 'file')
				};
			});
	};

	$: if (project) {
		resolveItems();
	}

	onMount(() => {
		resolveItems();
	});
</script>

{#if resolvedItems.length > 0}
	<ul class="space-y-2">
		{#each resolvedItems as item (item.id)}
			<li
				class="flex items-center justify-between gap-3 rounded-xl border border-gray-100 dark:border-gray-800 px-3 py-2 text-sm"
			>
				<div class="flex min-w-0 items-center gap-2">
					{#if item.type === 'collection'}
						<Database className="size-4 shrink-0" />
					{:else}
						<DocumentPage className="size-4 shrink-0" />
					{/if}
					<span class="truncate">{item.name}</span>
				</div>
				<span
					class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300"
				>
					{item.type === 'collection' ? $i18n.t('Collection') : $i18n.t('File')}
				</span>
			</li>
		{/each}
	</ul>
{:else}
	<div class="py-6 text-center text-sm text-gray-500">{$i18n.t('No knowledge attached to this project.')}</div>
{/if}
