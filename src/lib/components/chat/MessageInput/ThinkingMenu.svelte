<script lang="ts">
	import { getContext, onMount } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Brain from '$lib/components/icons/Brain.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { settings } from '$lib/stores';
	import {
		ensureDefaultThinkingPreference,
		getResolvedThink,
		getThinkingEffort,
		isThinkingEnabled,
		saveUserThinkingPreference,
		THINKING_EFFORT_OPTIONS,
		type ThinkingEffort
	} from '$lib/utils/thinking';

	const i18n = getContext('i18n');

	let effortShow = false;

	$: resolvedThink = getResolvedThink($settings?.params);
	$: thinkingEnabled = isThinkingEnabled(resolvedThink);
	$: currentEffort = getThinkingEffort(resolvedThink);

	onMount(() => {
		ensureDefaultThinkingPreference();
	});

	const effortLabel = (effort: string) => {
		if (effort === 'low') return $i18n.t('Low');
		if (effort === 'high') return $i18n.t('High');
		return $i18n.t('Medium');
	};

	const setThinkingEnabled = async (enabled: boolean) => {
		await saveUserThinkingPreference(enabled ? currentEffort : false);
	};

	const setEffort = async (effort: ThinkingEffort) => {
		effortShow = false;
		await saveUserThinkingPreference(effort);
	};
</script>

<div class="flex items-center gap-0.5">
	<Tooltip
		content={thinkingEnabled
			? $i18n.t('Disable thinking')
			: $i18n.t('Enable thinking')}
		placement="top"
	>
		<button
			aria-label={thinkingEnabled ? $i18n.t('Disable thinking') : $i18n.t('Enable thinking')}
			aria-pressed={thinkingEnabled}
			class="transition rounded-full p-1.5 self-center hover:text-gray-700 dark:hover:text-gray-200 {thinkingEnabled
				? 'text-amber-500 dark:text-amber-400'
				: 'text-gray-400 dark:text-gray-600 opacity-70'}"
			id="thinking-toggle-button"
			on:click={() => setThinkingEnabled(!thinkingEnabled)}
			type="button"
		>
			<Brain className="size-5 translate-y-[0.5px]" strokeWidth="1.75" />
		</button>
	</Tooltip>

	{#if thinkingEnabled}
		<Dropdown bind:show={effortShow} align="end" side="top" sideOffset={8}>
			<Tooltip content={$i18n.t('Reasoning Effort')} placement="top">
				<button
					aria-label={$i18n.t('Reasoning Effort')}
					class="flex items-center gap-0.5 rounded-full px-1.5 py-1 text-xs font-medium text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-400/10 transition self-center"
					id="thinking-effort-button"
					type="button"
				>
					<span class="max-w-[4.5rem] truncate">{effortLabel(currentEffort)}</span>
					<ChevronDown className="size-3 shrink-0" strokeWidth="2" />
				</button>
			</Tooltip>

			<div slot="content">
				<div
					class="min-w-[8rem] rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-850 dark:text-white shadow-lg py-1"
				>
					{#each THINKING_EFFORT_OPTIONS as effort (effort)}
						<button
							class="w-full px-3 py-1.5 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition {currentEffort ===
							effort
								? 'text-amber-600 dark:text-amber-400 font-medium'
								: 'text-gray-700 dark:text-gray-200'}"
							on:click={() => setEffort(effort)}
							type="button"
						>
							{effortLabel(effort)}
						</button>
					{/each}
				</div>
			</div>
		</Dropdown>
	{/if}
</div>
