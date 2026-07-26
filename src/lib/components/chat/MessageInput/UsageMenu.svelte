<script lang="ts">
	import { createEventDispatcher, getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { compactChatById } from '$lib/apis/chats';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import { toast } from 'svelte-sonner';
	import {
		formatUsageNumber,
		getAdditionalUsageRows,
		formatCachedPercent,
		getCachedUsage,
		getContextBreakdown,
		getContextBreakdownBarSegments,
		getContextBreakdownRows,
		getContextFreePercent,
		getContextFreeTokens,
		getContextUsagePercent,
		getContextUsedTokens,
		getContextWindowSize,
		getFallbackContextBarSegments,
		getGenerationTokens,
		getLlamacppSlotContextFromModel,
		getPerformanceUsageRows,
		getPromptTokens,
		getReasoningTokens,
		isLlamacppContext,
		resolveContextWindowSize,
		type UsageModel,
		type UsageRecord
	} from '$lib/utils/usage';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let usage: UsageRecord;
	export let model: UsageModel = null;
	export let chatId: string | null = null;
	export let generating = false;

	let show = false;
	let compacting = false;
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
	$: cachedUsage = getCachedUsage(usage);
	$: isLlamaContext = isLlamacppContext(usage, model);
	$: syncContextWindow = getContextWindowSize(usage, model);
	$: contextWindow = isLlamaContext
		? (probedContextWindow ?? getLlamacppSlotContextFromModel(model) ?? syncContextWindow)
		: (syncContextWindow ?? probedContextWindow);
	$: contextPercent = getContextUsagePercent(contextTokens, contextWindow);
	$: freeContextTokens = getContextFreeTokens(contextTokens, contextWindow);
	$: freeContextPercent = getContextFreePercent(contextTokens, contextWindow);
	$: progressPercent = contextPercent ?? 0;
	$: strokeDashoffset = circumference - (progressPercent / 100) * circumference;
	$: additionalRows = getAdditionalUsageRows(usage);
	$: performanceRows = getPerformanceUsageRows(usage);
	$: contextBreakdown = getContextBreakdown(usage);
	$: breakdownLabels = {
		system: $i18n.t('System'),
		memory: $i18n.t('Memory'),
		skills: $i18n.t('Skills'),
		files: $i18n.t('Files'),
		knowledge: $i18n.t('Knowledge'),
		tools: $i18n.t('Tools'),
		conversation: $i18n.t('Conversation'),
		tools_builtin: $i18n.t('Builtin tools'),
		tools_mcp: $i18n.t('MCP tools'),
		tools_user: $i18n.t('User tools'),
		tools_external: $i18n.t('Tool servers'),
		tools_terminal: $i18n.t('Terminal tools')
	};
	$: breakdownRows = contextBreakdown
		? getContextBreakdownRows(contextBreakdown, breakdownLabels, contextWindow)
		: [];
	$: breakdownBarSegments = getContextBreakdownBarSegments(breakdownRows, {
		windowSize: contextWindow,
		generationTokens,
		freeTokens: freeContextTokens,
		freeLabel: $i18n.t('Free')
	});
	$: fallbackBarSegments = getFallbackContextBarSegments(
		breakdownRows,
		contextTokens,
		generationTokens
	);
	$: hasContextWindow = Boolean(contextWindow && contextWindow > 0);
	$: contextBarSegments = hasContextWindow
		? breakdownBarSegments.length > 0
			? breakdownBarSegments
			: []
		: fallbackBarSegments;
	$: showSimpleContextBar = hasContextWindow && contextBarSegments.length === 0 && contextPercent !== null;
	$: showContextSection = contextTokens > 0;
	$: showPromptInTurn = breakdownRows.length === 0;
	$: canCompactContext =
		Boolean(chatId) &&
		!chatId?.startsWith('local:') &&
		!chatId?.startsWith('channel:') &&
		!generating &&
		!compacting;

	const formatBreakdownPercent = (value: number, percent: number) => {
		if (percent >= 10 || (Number.isInteger(percent) && percent >= 1)) {
			return `${Math.round(percent)}%`;
		}
		if (percent > 0) {
			return `${percent}%`;
		}
		return value > 0 ? '<1%' : '0%';
	};

	const compactContext = async () => {
		if (!chatId || compacting) return;

		compacting = true;
		try {
			const result = await compactChatById(localStorage.token ?? '', chatId, model?.id ?? null);
			if (!result?.compacted) {
				const reason = result?.reason;
				if (reason === 'disabled') {
					toast.error($i18n.t('Context compaction is disabled in admin settings.'));
				} else if (reason === 'too_short') {
					toast.message($i18n.t('Not enough messages to compact.'));
				} else if (reason === 'empty') {
					toast.message($i18n.t('Nothing to compact.'));
				} else {
					toast.message($i18n.t('Context was not compacted.'));
				}
				return;
			}

			toast.success(
				$i18n.t('Context compacted. {{count}} messages summarized.', {
					count: result.dropped_messages ?? 0
				})
			);
			show = false;
			dispatch('compacted');
		} catch (err: unknown) {
			const detail =
				(err as { detail?: string })?.detail ??
				(err as { message?: string })?.message ??
				$i18n.t('Failed to compact context.');
			toast.error(detail);
		} finally {
			compacting = false;
		}
	};

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
		if (!model?.urlIdx) {
			probedContextWindow = null;
			return;
		}

		if (!isLlamaContext && syncContextWindow) {
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
			{#if showContextSection}
				<div class="px-3.5 pt-3.5 pb-3 border-b border-gray-100 dark:border-gray-800/80">
					<div class="flex items-end justify-between gap-3">
						<div class="min-w-0">
							<div class="text-[11px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
								{$i18n.t('Context window')}
							</div>
							{#if hasContextWindow}
								<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 tabular-nums truncate">
									{formatUsageNumber(contextTokens)} / {formatUsageNumber(contextWindow)}
								</div>
							{:else}
								<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 tabular-nums truncate">
									{formatUsageNumber(contextTokens)} {$i18n.t('tokens used')}
								</div>
							{/if}
						</div>
						{#if contextPercent !== null}
							<div class="text-2xl font-semibold tabular-nums leading-none {ringClass}">
								{contextPercent}%
							</div>
						{/if}
					</div>

					{#if contextBarSegments.length > 0}
						<div class="mt-3 flex h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
							{#each contextBarSegments as segment (segment.id)}
								<div
									class="{segment.color} h-full transition-all duration-300"
									style:width="{Math.max(segment.percent > 0 ? 1 : 0, segment.percent)}%"
									title="{segment.label} ({segment.percent}%)"
								></div>
							{/each}
						</div>
					{:else if showSimpleContextBar}
						<div class="mt-3 h-2 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
							<div
								class="h-full rounded-full transition-all duration-300 {progressClass}"
								style:width="{Math.max(contextPercent > 0 ? 2 : 0, contextPercent)}%"
							></div>
						</div>
					{/if}

					{#if !hasContextWindow}
						<p class="mt-2 text-[11px] leading-relaxed text-gray-400 dark:text-gray-500">
							{$i18n.t('Context window size is unavailable for this model.')}
						</p>
					{/if}
				</div>
			{/if}

			{#if breakdownRows.length > 0 || freeContextTokens !== null}
				<div class="px-3.5 py-3 border-b border-gray-100 dark:border-gray-800/80">
					<div class="flex items-baseline justify-between gap-2 mb-2">
						<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
							{$i18n.t('Prompt breakdown')}
						</div>
						{#if contextBreakdown}
							<div class="text-[10px] tabular-nums text-gray-400 dark:text-gray-500">
								{formatUsageNumber(contextBreakdown.total)}
							</div>
						{/if}
					</div>

					<div class="space-y-1 text-xs">
						{#each breakdownRows as row (row.id)}
							<div class="flex items-center justify-between gap-3 {row.nested ? 'pl-3' : ''}">
								<span class="text-gray-500 dark:text-gray-400 truncate">{row.label}</span>
								<span class="text-gray-900 dark:text-white tabular-nums shrink-0">
									{formatUsageNumber(row.value)}
									<span class="text-gray-400 dark:text-gray-500"
										>({formatBreakdownPercent(row.value, row.percent)})</span
									>
								</span>
							</div>
						{/each}

						{#if freeContextTokens !== null}
							<div class="flex items-center justify-between gap-3">
								<span class="text-gray-500 dark:text-gray-400 truncate">{$i18n.t('Free')}</span>
								<span class="text-emerald-600 dark:text-emerald-400 tabular-nums shrink-0">
									{formatUsageNumber(freeContextTokens)}
									{#if freeContextPercent !== null}
										<span class="text-gray-400 dark:text-gray-500">({freeContextPercent}%)</span>
									{/if}
								</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<div class="px-3.5 py-3">
				<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
					{$i18n.t('This turn')}
				</div>

				<div class="space-y-1 text-xs">
					{#if showPromptInTurn}
						<div class="flex items-center justify-between gap-3">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Prompt')}</span>
							<span class="text-gray-900 dark:text-white tabular-nums">
								{formatUsageNumber(promptTokens)}
							</span>
						</div>
					{/if}

					<div class="flex items-center justify-between gap-3">
						<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Generation')}</span>
						<span class="text-gray-900 dark:text-white tabular-nums">
							{formatUsageNumber(generationTokens)}
						</span>
					</div>

					{#if reasoningTokens > 0}
						<div class="flex items-center justify-between gap-3 pl-3">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Reasoning')}</span>
							<span class="text-gray-900 dark:text-white tabular-nums">
								{formatUsageNumber(reasoningTokens)}
							</span>
						</div>
					{/if}

					{#if cachedUsage}
						<div class="flex items-center justify-between gap-3 pl-3">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Cached')}</span>
							<span class="text-gray-900 dark:text-white tabular-nums">
								{formatUsageNumber(cachedUsage.cached)} / {formatUsageNumber(cachedUsage.prompt)}
								<span class="text-gray-400 dark:text-gray-500"
									>({formatCachedPercent(cachedUsage.percent)})</span
								>
							</span>
						</div>
					{/if}
				</div>
			</div>

			{#if performanceRows.length > 0}
				<div class="px-3.5 py-3 border-b border-gray-100 dark:border-gray-800/80">
					<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
						{$i18n.t('Performance')}
					</div>
					<div class="space-y-1 text-xs">
						{#each performanceRows as row (row.label)}
							<div class="flex items-center justify-between gap-3">
								<span class="text-gray-500 dark:text-gray-400 truncate">{row.label}</span>
								<span class="text-gray-900 dark:text-white tabular-nums shrink-0">{row.value}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if additionalRows.length > 0}
				<div class="px-3.5 py-3 border-b border-gray-100 dark:border-gray-800/80">
					<div class="text-[10px] font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">
						{$i18n.t('Details')}
					</div>
					<div class="space-y-1 text-xs">
						{#each additionalRows as row (row.label)}
							<div class="flex items-center justify-between gap-3">
								<span class="text-gray-500 dark:text-gray-400 truncate">{row.label}</span>
								<span class="text-gray-900 dark:text-white tabular-nums shrink-0">{row.value}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if canCompactContext}
				<div class="border-t border-gray-100 dark:border-gray-800/80 px-3.5 py-3">
					<button
						class="flex w-full items-center justify-center rounded-xl border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
						type="button"
						disabled={compacting}
						on:click={compactContext}
					>
						{compacting ? $i18n.t('Compacting...') : $i18n.t('Compact context')}
					</button>
					<p class="mt-2 text-[11px] leading-relaxed text-gray-500 dark:text-gray-400">
						{$i18n.t('Summarize older messages to free up context space.')}
					</p>
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
