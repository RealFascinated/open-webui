<script lang="ts">
	import { getContext, onDestroy } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import {
		formatUsageNumber,
		getAdditionalUsageRows,
		getCachedPercent,
		getContextUsagePercent,
		getContextUsedTokens,
		getContextWindowSize,
		getGenerationTokens,
		getPromptTokens,
		getReasoningTokens,
		resolveContextWindowSize,
		type UsageModel,
		type UsageRecord
	} from '$lib/utils/usage';

	const i18n = getContext('i18n');

	export let usage: UsageRecord;
	export let model: UsageModel = null;

	let show = false;
	let probedContextWindow: number | null = null;
	let probeRequestId = 0;

	const size = 20;
	const strokeWidth = 2.5;
	const radius = (size - strokeWidth) / 2;
	const circumference = 2 * Math.PI * radius;

	$: contextTokens = getContextUsedTokens(usage);
	$: promptTokens = getPromptTokens(usage);
	$: generationTokens = getGenerationTokens(usage);
	$: reasoningTokens = getReasoningTokens(usage);
	$: cachedPercent = getCachedPercent(usage);
	$: syncContextWindow = getContextWindowSize(usage, model);
	$: contextWindow = syncContextWindow ?? probedContextWindow;
	$: contextPercent = getContextUsagePercent(contextTokens, contextWindow);
	$: progressPercent = contextPercent ?? 0;
	$: strokeDashoffset = circumference - (progressPercent / 100) * circumference;
	$: additionalRows = getAdditionalUsageRows(usage);

	$: usageLevel =
		contextPercent === null ? 'none' : contextPercent >= 70 ? 'crit' : contextPercent >= 25 ? 'warn' : 'ok';

	$: progressClass = {
		none: 'bg-gray-400 dark:bg-gray-500',
		ok: 'bg-emerald-500',
		warn: 'bg-amber-400',
		crit: 'bg-red-500'
	}[usageLevel];

	$: ringClass = {
		none: 'text-gray-400 dark:text-gray-500',
		ok: 'text-emerald-500',
		warn: 'text-amber-400',
		crit: 'text-red-500'
	}[usageLevel];

	const probeContextWindow = async () => {
		if (syncContextWindow || !model?.urlIdx) {
			probedContextWindow = null;
			return;
		}

		const requestId = ++probeRequestId;
		const token = localStorage.token ?? '';
		const resolved = await resolveContextWindowSize(usage, model, token);
		if (requestId === probeRequestId) {
			probedContextWindow = resolved;
		}
	};

	$: if (usage && model) {
		probeContextWindow();
	}

	onDestroy(() => {
		probeRequestId += 1;
	});
</script>

<Dropdown bind:show align="end" side="top" sideOffset={8}>
	<button
		aria-label={$i18n.t('Context window usage')}
		class="text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition rounded-full p-1.5 self-center"
		id="conversation-usage-button"
		type="button"
	>
		<svg
			aria-hidden="true"
			width={size}
			height={size}
			viewBox="0 0 {size} {size}"
			class="-rotate-90 translate-y-[0.5px]"
		>
			<circle
				cx={size / 2}
				cy={size / 2}
				r={radius}
				fill="none"
				stroke="currentColor"
				stroke-width={strokeWidth}
				class="text-gray-300 dark:text-gray-600"
			/>
			{#if contextPercent !== null}
				<circle
					cx={size / 2}
					cy={size / 2}
					r={radius}
					fill="none"
					stroke="currentColor"
					stroke-width={strokeWidth}
					stroke-linecap="round"
					class="{ringClass} transition-[stroke-dashoffset] duration-300"
					stroke-dasharray={circumference}
					stroke-dashoffset={strokeDashoffset}
				/>
			{/if}
		</svg>
	</button>

	<div slot="content">
		<div
			class="w-72 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 dark:text-white shadow-lg overflow-hidden"
		>
			{#if contextPercent !== null}
				<div class="px-3.5 pt-3.5 pb-3 border-b border-gray-100 dark:border-gray-800/80">
					<div class="flex items-end justify-between gap-3">
						<div class="min-w-0">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
								{$i18n.t('Context window')}
							</div>
							{#if contextWindow}
								<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 tabular-nums truncate">
									{formatUsageNumber(contextTokens)} / {formatUsageNumber(contextWindow)}
								</div>
							{/if}
						</div>
						<div class="text-2xl font-semibold tabular-nums leading-none {ringClass}">
							{contextPercent}%
						</div>
					</div>

					<div class="mt-3 h-2 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
						<div
							class="h-full rounded-full transition-all duration-300 {progressClass}"
							style:width="{Math.max(contextPercent > 0 ? 2 : 0, contextPercent)}%"
						></div>
					</div>
				</div>
			{/if}

			<div class="px-3.5 py-3">
				<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
					{$i18n.t('Tokens')}
				</div>

				<div class="space-y-1.5 text-xs">
					<div class="flex items-center justify-between gap-3">
						<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Prompt')}</span>
						<span class="text-gray-900 dark:text-white tabular-nums">
							{formatUsageNumber(promptTokens)}
						</span>
					</div>

					<div class="flex items-center justify-between gap-3">
						<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Generation')}</span>
						<span class="text-gray-900 dark:text-white tabular-nums">
							{formatUsageNumber(generationTokens)}
						</span>
					</div>

					{#if reasoningTokens > 0}
						<div class="flex items-center justify-between gap-3">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Reasoning')}</span>
							<span class="text-gray-900 dark:text-white tabular-nums">
								{formatUsageNumber(reasoningTokens)}
							</span>
						</div>
					{/if}

					{#if cachedPercent !== null}
						<div class="flex items-center justify-between gap-3">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Cached')}</span>
							<span class="text-gray-900 dark:text-white tabular-nums">{cachedPercent}%</span>
						</div>
					{/if}

					{#if contextPercent === null}
						<div class="flex items-center justify-between gap-3">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Context')}</span>
							<span class="text-gray-900 dark:text-white tabular-nums">
								{formatUsageNumber(contextTokens)}
							</span>
						</div>
					{/if}
				</div>
			</div>

			{#if additionalRows.length > 0}
				<div class="px-3.5 pb-3.5 pt-0">
					<div class="border-t border-gray-100 dark:border-gray-800/80 pt-2.5 space-y-1.5">
						{#each additionalRows as row (row.label)}
							<div class="flex items-center justify-between gap-3 text-xs">
								<span class="text-gray-500 dark:text-gray-400 truncate">{row.label}</span>
								<span class="text-gray-900 dark:text-white tabular-nums shrink-0 font-medium"
									>{row.value}</span
								>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
