<script lang="ts">
	import {getContext, tick} from 'svelte';
	import {goto} from '$app/navigation';

	import Modal from '$lib/components/common/Modal.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import {config} from '$lib/stores';
	import {buildAdminSearchIndex, filterAdminSearch, getRecentAdminSearchResults, recordAdminSearchVisit, type AdminSearchItem} from '$lib/utils/adminSearch';

	const i18n = getContext('i18n');

	export let show = false;

	let query = '';
	let selectedIndex = 0;
	let inputElement: HTMLInputElement | null = null;

	$: searchIndex = buildAdminSearchIndex({
		enableAdminAnalytics: $config?.features?.enable_admin_analytics ?? true
	});

	$: results = query.trim()
		? filterAdminSearch(query, searchIndex, 12)
		: getRecentAdminSearchResults(searchIndex, 8);

	$: showingRecents = !query.trim() && results.length > 0;

	$: if (results.length > 0 && selectedIndex >= results.length) {
		selectedIndex = 0;
	}

	const reset = () => {
		query = '';
		selectedIndex = 0;
	};

	const navigate = async (item: AdminSearchItem) => {
		recordAdminSearchVisit(item);
		show = false;
		reset();
		await goto(item.href);
	};

	const onKeyDown = (event: KeyboardEvent) => {
		if (!show) return;

		if (event.key === 'ArrowDown') {
			event.preventDefault();
			if (results.length > 0) {
				selectedIndex = (selectedIndex + 1) % results.length;
			}
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			if (results.length > 0) {
				selectedIndex = (selectedIndex - 1 + results.length) % results.length;
			}
		} else if (event.key === 'Enter') {
			event.preventDefault();
			const item = results[selectedIndex];
			if (item) navigate(item);
		}
	};

	$: if (show) {
		tick().then(() => inputElement?.focus());
	} else {
		reset();
	}
</script>

<svelte:window on:keydown={onKeyDown} />

<Modal bind:show size="md" className="bg-white/95 dark:bg-gray-950/95 backdrop-blur-xl rounded-2xl">
	<div class="p-1">
		<div
			class="flex items-center gap-2 px-3 py-2.5 border-b border-gray-100/30 dark:border-gray-850/30"
		>
			<Search className="size-4 text-gray-400 shrink-0" />
			<input
				bind:this={inputElement}
				class="flex-1 bg-transparent outline-hidden text-sm placeholder:text-gray-400"
				placeholder={$i18n.t('Search admin pages and settings...')}
				bind:value={query}
				autocomplete="off"
				spellcheck="false"
			/>
			<kbd
				class="hidden sm:inline-flex items-center rounded-md border border-gray-100/30 dark:border-gray-850/30 px-1.5 py-0.5 text-[10px] text-gray-400"
			>
				esc
			</kbd>
		</div>

		<div class="max-h-[min(24rem,50vh)] overflow-y-auto py-1">
			{#if results.length === 0}
				<div class="px-4 py-8 text-center text-sm text-gray-500">
					{query.trim() ? $i18n.t('No results found') : $i18n.t('No recent admin pages yet')}
				</div>
			{:else}
				{#if showingRecents}
					<div class="px-3 pt-1 pb-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-400">
						{$i18n.t('Recent')}
					</div>
				{/if}
				{#each results as item, idx (item.id)}
					<button
						type="button"
						class="w-full text-left px-3 py-2.5 rounded-xl transition {idx === selectedIndex
							? 'bg-gray-100 dark:bg-gray-850'
							: 'hover:bg-gray-50 dark:hover:bg-gray-900/60'}"
						on:mouseenter={() => {
							selectedIndex = idx;
						}}
						on:click={() => navigate(item)}
					>
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<div class="text-sm font-medium truncate">{$i18n.t(item.title)}</div>
								<div class="text-xs text-gray-500 truncate mt-0.5">
									{$i18n.t(item.description)}
								</div>
							</div>
							<div class="shrink-0 text-[10px] text-gray-400 pt-0.5">{$i18n.t(item.category)}</div>
						</div>
					</button>
				{/each}
			{/if}
		</div>

		<div
			class="px-3 py-2 border-t border-gray-100/30 dark:border-gray-850/30 text-[10px] text-gray-400 flex items-center gap-3"
		>
			<span><kbd class="font-sans">↑↓</kbd> {$i18n.t('navigate')}</span>
			<span><kbd class="font-sans">↵</kbd> {$i18n.t('open')}</span>
		</div>
	</div>
</Modal>
