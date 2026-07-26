<script lang="ts">
	import {models, settings, user, config} from '$lib/stores';
	import {getContext} from 'svelte';
	import {toast} from 'svelte-sonner';
	import Selector from './ModelSelector/Selector.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	import {updateUserSettings} from '$lib/apis/users';
	import equal from 'fast-deep-equal';
	import {getAvailableModelIds, resolveSelectedModels} from '$lib/utils/models';
	const i18n = getContext('i18n');

	export let selectedModels: string[] = [''];
	export let disabled = false;

	export let showSetDefault = true;

	const saveDefaultModel = async () => {
		const hasEmptyModel = selectedModels.filter((it) => it === '');
		if (hasEmptyModel.length) {
			toast.error($i18n.t('Choose a model before saving...'));
			return;
		}
		settings.set({ ...$settings, models: selectedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });

		toast.success($i18n.t('Default model updated'));
	};

	$: if ($models.length > 0) {
		const availableModelIds = getAvailableModelIds($models);
		const hasValidSelection = selectedModels.some(
			(modelId) => modelId && availableModelIds.includes(modelId)
		);
		const hasExplicitSelection = selectedModels.some((modelId) => modelId);
		const shouldResolve =
			!hasValidSelection && !(hasExplicitSelection && availableModelIds.length === 0);

		if (shouldResolve) {
			const defaultModelIds = $settings?.models?.length
				? $settings.models
				: $config?.default_models
					? $config.default_models.split(',')
					: [];
			const _selectedModels = resolveSelectedModels(
				selectedModels,
				availableModelIds,
				defaultModelIds
			);

			if (!equal(_selectedModels, selectedModels)) {
				selectedModels = _selectedModels;
			}
		}
	}

	const onModelChange = (selectedModelIdx: number, modelId: string) => {
		if (!modelId || selectedModels[selectedModelIdx] === modelId) {
			return;
		}

		selectedModels[selectedModelIdx] = modelId;
		selectedModels = [...selectedModels];
	};
</script>

<div class="flex flex-col w-full items-start">
	{#each selectedModels as selectedModel, selectedModelIdx}
		<div class="flex w-full max-w-fit">
			<div class="overflow-hidden w-full">
				<div class="max-w-full {($settings?.highContrastMode ?? false) ? 'm-1' : 'mr-1'}">
					<Selector
						id={`${selectedModelIdx}`}
						placeholder={$i18n.t('Select a model')}
						items={$models.map((model) => ({
							value: model.id,
							label: model.name,
							model: model
						}))}
						value={selectedModels[selectedModelIdx]}
					onChange={(modelId) => onModelChange(selectedModelIdx, modelId)}
					/>
				</div>
			</div>

			{#if $user?.role === 'admin'}
				{#if selectedModelIdx === 0}
					<div
						class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]"
					>
						<Tooltip content={$i18n.t('Add Model')}>
							<button
								class=" "
								{disabled}
								on:click={() => {
									selectedModels = [
										...selectedModels,
										selectedModels[selectedModels.length - 1] || ''
									];
								}}
								aria-label="Add Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-3.5"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6"></path>
								</svg>
							</button>
						</Tooltip>
					</div>
				{:else}
					<div
						class="  self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]"
					>
						<Tooltip content={$i18n.t('Remove Model')}>
							<button
								{disabled}
								on:click={() => {
									selectedModels.splice(selectedModelIdx, 1);
									selectedModels = selectedModels;
								}}
								aria-label="Remove Model"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-3"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15"></path>
								</svg>
							</button>
						</Tooltip>
					</div>
				{/if}
			{/if}
		</div>
	{/each}
</div>

{#if showSetDefault}
	<div
		class="relative text-left mt-[1px] ml-1 text-[0.7rem] text-gray-600 dark:text-gray-400 font-primary"
	>
		<button on:click={saveDefaultModel}> {$i18n.t('Set as default')}</button>
	</div>
{/if}
