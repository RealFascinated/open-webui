<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { getCodeExecutionConfig, setCodeExecutionConfig } from '$lib/apis/configs';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import AdminSaveBar from '../AdminSaveBar.svelte';
	import AdminSettingsCard from '../AdminSettingsCard.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: (...args: unknown[]) => unknown;

	let config = null;
	let dirty = false;
	let saving = false;
	let initialSnapshot = '';

	let engines = ['pyodide', 'jupyter'];

	const snapshot = () => JSON.stringify(config);

	$: if (initialSnapshot && config) {
		dirty = snapshot() !== initialSnapshot;
	};

	const loadData = async () => {
		const res = await getCodeExecutionConfig(localStorage.token);
		if (res) {
			config = res;
			initialSnapshot = snapshot();
			dirty = false;
		}
	};

	const discardHandler = async () => {
		await loadData();
	};

	const submitHandler = async () => {
		if (!config) return;
		saving = true;
		const res = await setCodeExecutionConfig(localStorage.token, config).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			saveHandler();
			initialSnapshot = snapshot();
			dirty = false;
		}
		saving = false;
	};

	onMount(loadData);
</script>

<form class="flex flex-col space-y-3 text-sm">
	<div class=" space-y-3">
		{#if config}
			<AdminSettingsCard
				title="Code Execution"
				description="Sandbox engine, interpreter settings, and code block behavior."
			>
					<div class="mb-2.5">
						<div class=" flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Enable Code Execution')}
							</div>

							<Switch bind:state={config.ENABLE_CODE_EXECUTION} />
						</div>
					</div>

					{#if config.ENABLE_CODE_EXECUTION}
						<div class="mb-2.5">
							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Code Execution Engine')}
								</div>
								<div class="flex items-center relative">
									<select
										class="w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
										bind:value={config.CODE_EXECUTION_ENGINE}
										placeholder={$i18n.t('Select a engine')}
										required
									>
										<option disabled selected value="">{$i18n.t('Select a engine')}</option>
										{#each engines as engine}
											<option value={engine}
												>{engine}{engine === 'jupyter' ? ' (Legacy)' : ''}</option
											>
										{/each}
									</select>
								</div>
							</div>

							{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
								<div class="text-gray-500 text-xs">
									{$i18n.t(
										'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.'
									)}
								</div>
							{/if}
						</div>

						{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
							<div class="mb-2.5 flex flex-col gap-1.5 w-full">
								<div class="text-xs font-medium">
									{$i18n.t('Jupyter URL')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm py-0.5 placeholder:text-gray-300 dark:placeholder:text-gray-700 bg-transparent outline-hidden"
											type="text"
											placeholder={$i18n.t('Enter Jupyter URL')}
											bind:value={config.CODE_EXECUTION_JUPYTER_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mb-2.5 flex flex-col gap-1.5 w-full">
								<div class=" flex gap-2 w-full items-center justify-between">
									<div class="text-xs font-medium">
										{$i18n.t('Jupyter Auth')}
									</div>

									<div>
										<select
											class="w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-left"
											bind:value={config.CODE_EXECUTION_JUPYTER_AUTH}
											placeholder={$i18n.t('Select an auth method')}
										>
											<option selected value="">{$i18n.t('None')}</option>
											<option value="token">{$i18n.t('Token')}</option>
											<option value="password">{$i18n.t('Password')}</option>
										</select>
									</div>
								</div>

								{#if config.CODE_EXECUTION_JUPYTER_AUTH}
									<div class="flex w-full gap-2">
										<div class="flex-1">
											{#if config.CODE_EXECUTION_JUPYTER_AUTH === 'password'}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Password')}
													bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD}
													autocomplete="off"
												/>
											{:else}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Token')}
													bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN}
													autocomplete="off"
												/>
											{/if}
										</div>
									</div>
								{/if}
							</div>

							<div class="flex gap-2 w-full items-center justify-between">
								<div class="text-xs font-medium">
									{$i18n.t('Code Execution Timeout')}
								</div>

								<div class="">
									<Tooltip content={$i18n.t('Enter timeout in seconds')}>
										<input
											class="w-fit rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
											type="number"
											bind:value={config.CODE_EXECUTION_JUPYTER_TIMEOUT}
											placeholder={$i18n.t('e.g. 60')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						{/if}
					{/if}
			</AdminSettingsCard>

			<AdminSettingsCard
				title="Code Interpreter"
				description="In-chat Python interpreter and prompt template."
			>
					<div class="mb-2.5">
						<div class=" flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Enable Code Interpreter')}
							</div>

							<Switch bind:state={config.ENABLE_CODE_INTERPRETER} />
						</div>
					</div>

					{#if config.ENABLE_CODE_INTERPRETER}
						<div class="mb-2.5">
							<div class="  flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Code Interpreter Engine')}
								</div>
								<div class="flex items-center relative">
									<select
										class="w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
										bind:value={config.CODE_INTERPRETER_ENGINE}
										placeholder={$i18n.t('Select a engine')}
										required
									>
										<option disabled selected value="">{$i18n.t('Select a engine')}</option>
										{#each engines as engine}
											<option value={engine}
												>{engine}{engine === 'jupyter' ? ' (Legacy)' : ''}</option
											>
										{/each}
									</select>
								</div>
							</div>

							{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
								<div class="text-gray-500 text-xs">
									{$i18n.t(
										'Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.'
									)}
								</div>
							{/if}
						</div>

						{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
							<div class="mb-2.5 flex flex-col gap-1.5 w-full">
								<div class="text-xs font-medium">
									{$i18n.t('Jupyter URL')}
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm py-0.5 placeholder:text-gray-300 dark:placeholder:text-gray-700 bg-transparent outline-hidden"
											type="text"
											placeholder={$i18n.t('Enter Jupyter URL')}
											bind:value={config.CODE_INTERPRETER_JUPYTER_URL}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="mb-2.5 flex flex-col gap-1.5 w-full">
								<div class="flex gap-2 w-full items-center justify-between">
									<div class="text-xs font-medium">
										{$i18n.t('Jupyter Auth')}
									</div>

									<div>
										<select
											class="w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-left"
											bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH}
											placeholder={$i18n.t('Select an auth method')}
										>
											<option selected value="">{$i18n.t('None')}</option>
											<option value="token">{$i18n.t('Token')}</option>
											<option value="password">{$i18n.t('Password')}</option>
										</select>
									</div>
								</div>

								{#if config.CODE_INTERPRETER_JUPYTER_AUTH}
									<div class="flex w-full gap-2">
										<div class="flex-1">
											{#if config.CODE_INTERPRETER_JUPYTER_AUTH === 'password'}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Password')}
													bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD}
													autocomplete="off"
												/>
											{:else}
												<SensitiveInput
													type="text"
													placeholder={$i18n.t('Enter Jupyter Token')}
													bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN}
													autocomplete="off"
												/>
											{/if}
										</div>
									</div>
								{/if}
							</div>

							<div class="flex gap-2 w-full items-center justify-between">
								<div class="text-xs font-medium">
									{$i18n.t('Code Execution Timeout')}
								</div>

								<div class="">
									<Tooltip content={$i18n.t('Enter timeout in seconds')}>
										<input
											class="w-fit rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
											type="number"
											bind:value={config.CODE_INTERPRETER_JUPYTER_TIMEOUT}
											placeholder={$i18n.t('e.g. 60')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						{/if}

						<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div>
							<div class="py-0.5 w-full">
								<div class=" mb-2.5 text-xs font-medium">
									{$i18n.t('Code Interpreter Prompt Template')}
								</div>

								<Tooltip
									content={$i18n.t(
										'Leave empty to use the default prompt, or enter a custom prompt'
									)}
									placement="top-start"
								>
									<Textarea
										bind:value={config.CODE_INTERPRETER_PROMPT_TEMPLATE}
										placeholder={$i18n.t(
											'Leave empty to use the default prompt, or enter a custom prompt'
										)}
									/>
								</Tooltip>
							</div>
						</div>
					{/if}
			</AdminSettingsCard>
		{/if}
	</div>
	{#if config}
		<AdminSaveBar {dirty} {saving} onSave={submitHandler} onDiscard={discardHandler} />
	{/if}
</form>
