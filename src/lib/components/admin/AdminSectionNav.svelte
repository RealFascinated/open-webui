<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');

	type NavTab = { id: string; href: string; label: string };
	type NavGroup = { id: string; label: string; tabs: NavTab[] };

	export let tabs: NavTab[] = [];
	export let groups: NavGroup[] = [];
	export let selectedTab = '';
	export let showSearch = false;
	export let search = '';
	export let searchInputId = 'admin-section-nav-search';
	export let onSearchInput: () => void = () => {};

	let containerElement: HTMLDivElement;

	$: useGroups = groups.length > 0;
	$: displayGroups = useGroups ? groups : [{ id: 'default', label: '', tabs }];

	const scrollToTab = (tabId: string) => {
		const tabElement = document.getElementById(tabId);
		if (tabElement) {
			tabElement.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
		}
	};

	$: if (selectedTab) {
		scrollToTab(selectedTab);
	}

	onMount(() => {
		if (containerElement) {
			containerElement.addEventListener('wheel', (event: Event) => {
				if (event.deltaY !== 0) {
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}

		scrollToTab(selectedTab);
	});
</script>

<div class="flex flex-col lg:flex-row w-full h-full min-h-0 overflow-hidden pb-2 lg:space-x-4">
	<div
		bind:this={containerElement}
		class="tabs mx-[16px] lg:mx-0 lg:px-[16px] flex flex-row overflow-x-auto gap-1 max-w-full lg:gap-0.5 lg:flex-col lg:flex-none lg:w-52 lg:max-h-full lg:overflow-y-auto lg:overscroll-contain dark:text-gray-200 text-sm font-medium text-left scrollbar-none shrink-0"
	>
		{#if showSearch}
			<div
				class="flex w-full min-w-fit rounded-xl px-2.5 py-1 gap-2 bg-gray-100/80 dark:bg-gray-850/80 backdrop-blur-2xl my-1 lg:mt-1.5 lg:mb-2 shrink-0"
			>
				<div class="self-center rounded-l-xl bg-transparent">
					<Search className="size-3.5" strokeWidth="1.5" />
				</div>
				<label class="sr-only" for={searchInputId}>{$i18n.t('Search')}</label>
				<input
					class="w-full py-1 text-sm bg-transparent dark:text-gray-300 outline-hidden min-w-0"
					bind:value={search}
					id={searchInputId}
					on:input={onSearchInput}
					placeholder={$i18n.t('Search')}
				/>
			</div>
		{/if}

		{#each displayGroups as group (group.id)}
			{#if useGroups && group.label}
				<div
					class="px-2.5 pt-2.5 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 min-w-fit lg:w-full"
				>
					{$i18n.t(group.label)}
				</div>
			{/if}

			{#each group.tabs as tab (tab.id)}
				<a
					id={tab.id}
					href={tab.href}
					draggable="false"
					class="px-2.5 py-1.5 min-w-fit rounded-lg lg:w-full flex items-center gap-2.5 transition select-none {selectedTab ===
					tab.id
						? 'bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-white font-medium'
						: 'text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-900/60'}"
				>
					{#if $$slots.icon}
						<div
							class="shrink-0 self-center flex items-center justify-center size-6 rounded-md {selectedTab ===
							tab.id
								? 'text-gray-900 dark:text-white'
								: 'text-gray-400 dark:text-gray-500'}"
						>
							<slot name="icon" {tab} />
						</div>
					{/if}
					<div class="self-center truncate">{$i18n.t(tab.label)}</div>
				</a>
			{/each}
		{/each}
	</div>

	<div
		class="flex-1 min-h-0 mt-3 lg:mt-0 px-[16px] lg:pr-[16px] lg:pl-0 overflow-y-auto overscroll-contain min-w-0"
	>
		<slot />
	</div>
</div>
