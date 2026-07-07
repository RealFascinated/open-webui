<script lang="ts">
	import { getContext } from 'svelte';

	import { selectedTerminalId, settings, terminalServers } from '$lib/stores';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import TerminalMenuPanel from './TerminalMenuPanel.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	$: systemTerminals = ($terminalServers ?? []).filter((t) => t.id);
	$: directTerminals = ($settings?.terminalServers ?? []).filter((s) => s.url);

	$: selectedSystemTerminal = systemTerminals.find((t) => t.id === $selectedTerminalId);
	$: selectedDirectTerminal = directTerminals.find((t) => t.url === $selectedTerminalId);

	$: selectedLabel =
		selectedSystemTerminal?.name ||
		selectedSystemTerminal?.id ||
		selectedDirectTerminal?.name ||
		selectedDirectTerminal?.url?.replace(/^https?:\/\//, '') ||
		$i18n.t('Terminal');
</script>

<div class="flex items-center translate-x-0.5">
	<Dropdown bind:show align="end">
		<Tooltip content={$i18n.t('Terminal')} placement="top">
			<button
				type="button"
				class="flex items-center gap-1.5 translate-y-[1px] hover:bg-gray-50 dark:hover:bg-gray-850 text-sm transition rounded-lg cursor-pointer {$selectedTerminalId &&
				selectedLabel
					? ' px-2.5 py-1 '
					: ' p-2 opacity-50'}"
			>
				<Cloud className="size-3.5" strokeWidth="2" />

				{#if $selectedTerminalId && selectedLabel}
					<span class="truncate text-[13px] max-w-[100px] sm:max-w-[150px]">{selectedLabel}</span>
				{/if}
			</button>
		</Tooltip>

		<div slot="content">
			<div
				class="min-w-56 max-w-56 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
			>
				<TerminalMenuPanel on:selected={() => (show = false)} />
			</div>
		</div>
	</Dropdown>
</div>
