<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import IntegrationsMenuPanel from './IntegrationsMenuPanel.svelte';

	const i18n = getContext('i18n');

	export let selectedToolIds: string[] = [];
	export let selectedSkillIds: string[] = [];
	export let selectedModels: string[] = [];
	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] =
		[];
	export let selectedFilterIds: string[] = [];
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;
	export let onShowValves: (...args: unknown[]) => unknown;
	export let onClose: (...args: unknown[]) => unknown = () => {};

	let show = false;
	let tab = '';
</script>

<Dropdown
	bind:show
	onOpenChange={(state) => {
		if (state === false) {
			tab = '';
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('Integrations')} placement="top">
		<slot />
	</Tooltip>
	<div slot="content">
		<div
			class="min-w-70 max-w-70 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
		>
			<IntegrationsMenuPanel
				bind:tab
				rootOnly={tab === ''}
				active={show}
				{selectedModels}
				bind:selectedToolIds
				bind:selectedSkillIds
				{toggleFilters}
				bind:selectedFilterIds
				{showImageGenerationButton}
				bind:imageGenerationEnabled
				{showCodeInterpreterButton}
				bind:codeInterpreterEnabled
				{onShowValves}
			/>
		</div>
	</div>
</Dropdown>
