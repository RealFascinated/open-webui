<script lang="ts">
	import {toast} from 'svelte-sonner';
	import {models, user} from '$lib/stores';
	import {createEventDispatcher, onMount, getContext} from 'svelte';

	const dispatch = createEventDispatcher();
	import {getModels} from '$lib/apis';
	import {getConfig, updateConfig} from '$lib/apis/evaluations';

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Model from './Evaluations/Model.svelte';
	import ArenaModelModal from './Evaluations/ArenaModelModal.svelte';
	import AdminSaveBar from '../AdminSaveBar.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AdminSettingsCard from '../AdminSettingsCard.svelte';

	const i18n = getContext('i18n');

	let evaluationConfig = null;
	let showAddModel = false;
	let dirty = false;
	let saving = false;
	let initialSnapshot = '';

	const snapshot = () => JSON.stringify(evaluationConfig);

	$: if (initialSnapshot && evaluationConfig) {
		dirty = snapshot() !== initialSnapshot;
	};

	const loadData = async () => {
		if ($user?.role === 'admin') {
			evaluationConfig = await getConfig(localStorage.token).catch((err) => {
				toast.error(err);
				return null;
			});
			if (evaluationConfig) {
				initialSnapshot = snapshot();
				dirty = false;
			}
		}
	};

	const discardHandler = async () => {
		await loadData();
	};

	const submitHandler = async () => {
		saving = true;
		const res = await updateConfig(localStorage.token, evaluationConfig).catch((err) => {
			toast.error(err);
			return null;
		});

		if (res) {
			evaluationConfig = res;
			toast.success($i18n.t('Settings saved successfully!'));
			models.set(await getModels(localStorage.token));
			initialSnapshot = snapshot();
			dirty = false;
			dispatch('save');
		}
		saving = false;
		return !!res;
	};

	const addModelHandler = async (model) => {
		evaluationConfig.EVALUATION_ARENA_MODELS.push(model);
		evaluationConfig.EVALUATION_ARENA_MODELS = [...evaluationConfig.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(
			await getModels(localStorage.token)
		);
	};

	const editModelHandler = async (model, modelIdx) => {
		evaluationConfig.EVALUATION_ARENA_MODELS[modelIdx] = model;
		evaluationConfig.EVALUATION_ARENA_MODELS = [...evaluationConfig.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(
			await getModels(localStorage.token)
		);
	};

	const deleteModelHandler = async (modelIdx) => {
		evaluationConfig.EVALUATION_ARENA_MODELS = evaluationConfig.EVALUATION_ARENA_MODELS.filter(
			(m, mIdx) => mIdx !== modelIdx
		);

		await submitHandler();
		models.set(
			await getModels(localStorage.token)
		);
	};

	onMount(loadData);
</script>

<ArenaModelModal
	bind:show={showAddModel}
	on:submit={async (e) => {
		addModelHandler(e.detail);
	}}
/>

<form class="flex flex-col text-sm">
	<div>
		{#if evaluationConfig !== null}
			<a
				href="/admin/evaluations/leaderboard"
				class="mb-4 flex items-center justify-between gap-3 rounded-xl border border-gray-100/30 dark:border-gray-850/30 bg-gray-50/80 dark:bg-gray-900/50 px-3.5 py-2.5 text-sm transition hover:bg-gray-100 dark:hover:bg-gray-850/60"
			>
				<span class="text-gray-600 dark:text-gray-300">
					{$i18n.t('View leaderboard and feedback in Evaluations')}
				</span>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					class="size-4 shrink-0 text-gray-400"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
				</svg>
			</a>

			<AdminSettingsCard
				title="Evaluation Arena"
				description="Configure models used in blind comparison evaluations."
			>
					<div class="mb-2.5 flex w-full justify-between">
						<div class=" text-xs font-medium">{$i18n.t('Arena Models')}</div>

						<Tooltip content={$i18n.t(`Message rating should be enabled to use this feature`)}>
							<Switch bind:state={evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS} />
						</Tooltip>
					</div>

				{#if evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS}
					<div class="mb-1">
						<div class="mb-2.5 text-sm font-medium flex justify-between items-center">
							<div>
								{$i18n.t('Manage')}
							</div>

							<div>
								<Tooltip content={$i18n.t('Add Arena Model')}>
									<button
										class="p-1"
										type="button"
										on:click={() => {
											showAddModel = true;
										}}
									>
										<Plus />
									</button>
								</Tooltip>
							</div>
						</div>

						<div class="flex flex-col gap-2">
							{#if (evaluationConfig?.EVALUATION_ARENA_MODELS ?? []).length > 0}
								{#each evaluationConfig.EVALUATION_ARENA_MODELS as model, index}
									<Model
										{model}
										on:edit={(e) => {
											editModelHandler(e.detail, index);
										}}
										on:delete={(_e) => {
											deleteModelHandler(index);
										}}
									/>
								{/each}
							{:else}
								<div class=" text-center text-xs text-gray-500">
									{$i18n.t(
										`Using the default arena model with all models. Click the plus button to add custom models.`
									)}
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</AdminSettingsCard>
		{:else}
			<div class="flex h-full justify-center py-16">
				<Spinner className="size-6" />
			</div>
		{/if}
	</div>

	{#if evaluationConfig !== null}
		<AdminSaveBar {dirty} {saving} onSave={submitHandler} onDiscard={discardHandler} />
	{/if}
</form>
