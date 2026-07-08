<script>
	import { onMount } from 'svelte';

	import { chatId, config, mobile, models, showSidebar } from '$lib/stores';
	import PinnedModelItem from './PinnedModelItem.svelte';

	export let selectedChatId = null;
	export let shiftKey = false;

	let pinnedModels = [];

	onMount(() => {
		if ($config?.default_pinned_models) {
			const defaultPinnedModels = $config.default_pinned_models.split(',').filter((id) => id);
			pinnedModels = defaultPinnedModels.filter((id) => $models.find((model) => model.id === id));
		}
	});

	$: if ($config?.default_pinned_models) {
		const defaultPinnedModels = $config.default_pinned_models.split(',').filter((id) => id);
		pinnedModels = defaultPinnedModels.filter((id) => $models.find((model) => model.id === id));
	}
</script>

<div class="mt-0.5 pb-1.5" id="pinned-models-list">
	{#each pinnedModels as modelId (modelId)}
		{@const model = $models.find((model) => model.id === modelId)}
		{#if model}
			<PinnedModelItem
				{model}
				{shiftKey}
				onClick={() => {
					selectedChatId = null;
					chatId.set('');
					if ($mobile) {
						showSidebar.set(false);
					}
				}}
			/>
		{/if}
	{/each}
</div>
