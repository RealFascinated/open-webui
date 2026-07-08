<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, mobile, showSidebar, user } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import AdminTopNav from '$lib/components/admin/AdminTopNav.svelte';
	import AdminSearchModal from '$lib/components/admin/AdminSearchModal.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let showAdminSearch = false;

	const openAdminSearch = () => {
		showAdminSearch = true;
	};

	const onWindowKeyDown = (event: KeyboardEvent) => {
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
			event.preventDefault();
			openAdminSearch();
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:window on:keydown={onWindowKeyDown} />

<svelte:head>
	<title>
		{$i18n.t('Admin Panel')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class=" flex flex-col h-screen max-h-[100dvh] min-h-0 flex-1 transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ' md:max-w-[calc(100%-49px)]'}  w-full max-w-full overflow-hidden"
	>
		<nav class="px-2.5 pt-1.5 pb-2 backdrop-blur-xl drag-region select-none">
			<div class=" flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="flex w-full items-center gap-2 min-w-0">
					<AdminTopNav />

					{#if !$mobile}
						<Tooltip content={`${$i18n.t('Search')} (⌘K)`}>
							<button
								type="button"
								class="ml-auto shrink-0 flex items-center justify-between gap-3 w-44 sm:w-52 md:w-64 lg:w-72 rounded-lg border border-gray-100/30 dark:border-gray-850/30 px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-900/60 transition"
								on:click={openAdminSearch}
								aria-label={$i18n.t('Search admin')}
							>
								<span class="flex items-center gap-2 min-w-0">
									<Search className="size-3.5 shrink-0" />
									<span class="truncate text-gray-400 dark:text-gray-500">
										{$i18n.t('Search admin...')}
									</span>
								</span>
								<kbd
									class="hidden sm:inline-flex shrink-0 items-center rounded border border-gray-100/30 dark:border-gray-850/30 px-1.5 py-0.5 text-[10px] text-gray-400"
								>
									⌘K
								</kbd>
							</button>
						</Tooltip>
					{/if}
				</div>
			</div>
		</nav>

		<div class="pb-1 pt-0.5 flex-1 min-h-0 overflow-hidden">
			<slot />
		</div>
	</div>

	<AdminSearchModal bind:show={showAdminSearch} />
{/if}
