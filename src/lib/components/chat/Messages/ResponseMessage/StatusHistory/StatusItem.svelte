<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');
	import WebSearchResults from '../WebSearchResults.svelte';
	import MemoriesUsed from '../MemoriesUsed.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	type SearchResultItem = {
		link?: string;
		title?: string;
		[key: string]: unknown;
	};

	type StatusEntry = {
		done?: boolean;
		hidden?: boolean;
		action?: string;
		description?: string;
		urls?: string[];
		items?: SearchResultItem[];
		queries?: string[];
		query?: string;
		count?: number;
		error?: string;
		attempt?: number;
		max_attempts?: number;
		reason?: string;
		[key: string]: unknown;
	};

	export let status: StatusEntry | null = null;
	export let done = false;
</script>

{#if !status?.hidden}
	<div class="status-description flex items-center gap-2 py-0.5 w-full text-left">
		{#if status?.action === 'web_search' && (status?.urls || status?.items)}
			<WebSearchResults {status}>
				<div class="flex flex-col justify-center -space-y-0.5">
					<div
						class="{(done || status?.done) === false
							? 'shimmer'
							: ''} text-base line-clamp-1 text-wrap"
					>
						<!-- $i18n.t("Generating search query") -->
						<!-- $i18n.t("No search query generated") -->
						<!-- $i18n.t('Searched {{count}} sites') -->
						{#if status?.description?.includes('{{count}}')}
							{$i18n.t(status?.description, {
								count: (status?.urls ?? status?.items ?? []).length
							})}
						{:else if status?.description === 'No search query generated'}
							{$i18n.t('No search query generated')}
						{:else if status?.description === 'Generating search query'}
							{$i18n.t('Generating search query')}
						{:else}
							{status?.description}
						{/if}
					</div>
				</div>
			</WebSearchResults>
		{:else if status?.action === 'knowledge_search'}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{$i18n.t(`Searching Knowledge for "{{searchQuery}}"`, {
						searchQuery: status.query
					})}
				</div>
			</div>
		{:else if status?.action === 'memory_context' && status?.memories}
			<MemoriesUsed memories={status.memories} done={done || status?.done} />
		{:else if status?.action === 'web_search_queries_generated' && status?.queries}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{$i18n.t(`Searching`)}
				</div>

				<div class=" flex gap-1 flex-wrap mt-2">
					{#each status.queries as query, _idx (query)}
						<div
							class="bg-gray-50 dark:bg-gray-850 flex rounded-lg py-1 px-2 items-center gap-1 text-xs"
						>
							<div>
								<Search className="size-3" />
							</div>

							<span class="line-clamp-1">
								{query}
							</span>
						</div>
					{/each}
				</div>
			</div>
		{:else if status?.action === 'queries_generated' && status?.queries}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{$i18n.t(`Querying`)}
				</div>

				<div class=" flex gap-1 flex-wrap mt-2">
					{#each status.queries as query, _idx (query)}
						<div
							class="bg-gray-50 dark:bg-gray-850 flex rounded-lg py-1 px-2 items-center gap-1 text-xs"
						>
							<div>
								<Search className="size-3" />
							</div>

							<span class="line-clamp-1">
								{query}
							</span>
						</div>
					{/each}
				</div>
			</div>
		{:else if status?.action === 'queries_generating'}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{$i18n.t('Generating search queries')}
				</div>
			</div>
		{:else if status?.action === 'prompt_urls_extracted' && status?.urls}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{#if (done || status?.done) === false}
						{#if status.count === 1}
							{$i18n.t('Fetching 1 webpage from your message')}
						{:else}
							{$i18n.t('Fetching {{count}} webpages from your message', {
								count: status.count ?? status.urls.length
							})}
						{/if}
					{:else if status.count === 1}
						{$i18n.t('Fetched 1 webpage from your message')}
					{:else}
						{$i18n.t('Fetched {{count}} webpages from your message', {
							count: status.count ?? status.urls.length
						})}
					{/if}
				</div>

				<div class=" flex gap-1 flex-wrap mt-2">
					{#each status.urls as url (url)}
						<div
							class="bg-gray-50 dark:bg-gray-850 flex rounded-lg py-1 px-2 items-center gap-1 text-xs max-w-full"
						>
							<span class="line-clamp-1">{url}</span>
						</div>
					{/each}
				</div>
			</div>
		{:else if status?.action === 'sources_retrieved'}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{#if (done || status?.done) === false}
						{$i18n.t('Retrieving sources')}
					{:else if status.count === 0}
						{$i18n.t('No sources found')}
					{:else if status.count === 1}
						{$i18n.t('Retrieved 1 source')}
					{:else}
						<!-- {$i18n.t('Source')} -->
						<!-- {$i18n.t('No source available')} -->
						<!-- {$i18n.t('No distance available')} -->
						<!-- {$i18n.t('Retrieved {{count}} sources')} -->
						{$i18n.t('Retrieved {{count}} sources', {
							count: status.count
						})}
					{/if}
				</div>
			</div>
		{:else if status?.action === 'context_compaction'}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{#if status?.error}
						{$i18n.t('Context compaction failed')}
					{:else if status?.done}
						{$i18n.t('Context compacted')}
					{:else}
						{$i18n.t('Compacting context')}
					{/if}
				</div>
			</div>
		{:else if status?.action === 'chat_retry'}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{#if status?.done}
						{#if status?.reason === 'timeout'}
							{$i18n.t('Model stopped responding — all {{max_attempts}} retry attempts failed', {
								max_attempts: status.max_attempts ?? status?.description?.match(/\d+/)?.[0] ?? 3
							})}
						{:else}
							{$i18n.t('Model returned no response — all {{max_attempts}} retry attempts failed', {
								max_attempts: status.max_attempts ?? status?.description?.match(/\d+/)?.[0] ?? 3
							})}
						{/if}
					{:else if status?.reason === 'timeout'}
						{$i18n.t('Model stopped responding — retrying ({{attempt}}/{{max_attempts}})', {
							attempt: status.attempt ?? 1,
							max_attempts: status.max_attempts ?? 3
						})}
					{:else}
						{$i18n.t('Model returned no response — retrying ({{attempt}}/{{max_attempts}})', {
							attempt: status.attempt ?? 1,
							max_attempts: status.max_attempts ?? 3
						})}
					{/if}
				</div>
			</div>
		{:else if status?.action === 'running_tools'}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{#if (done || status?.done) === false}
						{$i18n.t('Calling tools...')}
					{:else}
						{$i18n.t('Tools executed')}
					{/if}
				</div>
			</div>
		{:else}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					<!-- $i18n.t(`Searching "{{searchQuery}}"`) -->
					{#if status?.description?.includes('{{searchQuery}}')}
						{$i18n.t(status?.description, {
							searchQuery: status?.query
						})}
					{:else if status?.description === 'No search query generated'}
						{$i18n.t('No search query generated')}
					{:else if status?.description === 'Generating search query'}
						{$i18n.t('Generating search query')}
					{:else if status?.description === 'Searching the web'}
						{$i18n.t('Searching the web')}
					{:else}
						{status?.description}
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}
