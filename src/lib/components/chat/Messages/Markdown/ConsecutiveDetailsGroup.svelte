<script lang="ts">
	import { decode } from 'html-entities';
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';

	import { settings } from '$lib/stores';
	import { formatToolName } from '$lib/utils';
	import {
		isToolCallPending,
		isToolCallSuccessful,
		resolveToolCallStatus,
		type ToolCallAttributes
	} from '$lib/utils/toolCallDisplay';

	const i18n = getContext('i18n');

	export let id = '';
	export let tokens: Array<{
		summary?: string;
		attributes?: ToolCallAttributes & {
			type?: string;
			duration?: string;
			embeds?: string;
			arguments?: string;
		};
	}> = [];

	export let messageDone = true;
	export let allowEmbeds = true;

	let open = $settings?.expandDetails ?? false;

	function parseJSONString(str: string) {
		try {
			return parseJSONString(JSON.parse(str));
		} catch (_e) {
			return str;
		}
	}

	$: toolTokens = tokens.filter((t) => t?.attributes?.type === 'tool_calls');
	$: toolCallCount = toolTokens.length;

	$: toolStatuses = toolTokens.map((token) =>
		resolveToolCallStatus(token.attributes, messageDone)
	);
	$: hasPending =
		!messageDone &&
		tokens.some((token) => {
			if (token?.attributes?.type === 'tool_calls') {
				return isToolCallPending(
					resolveToolCallStatus(token.attributes, messageDone),
					messageDone
				);
			}

			return token?.attributes?.done !== undefined && token?.attributes?.done !== 'true';
		});

	$: hasFailures = toolStatuses.some(
		(status) => status === 'failed' || status === 'incomplete' || status === 'cancelled'
	);
	$: allSuccessful =
		toolCallCount > 0 && toolStatuses.every((status) => isToolCallSuccessful(status));

	$: codeInterpreterCount = tokens.filter((t) => t?.attributes?.type === 'code_interpreter').length;
	$: reasoningCount = tokens.filter((t) => t?.attributes?.type === 'reasoning').length;

	$: allEmbeds = (() => {
		if (!allowEmbeds) return [];

		const result: Array<{ name: string; embed: string; args: string }> = [];
		for (const t of tokens) {
			if (t?.attributes?.type !== 'tool_calls' || t?.attributes?.compact === 'true') continue;
			const raw = decode(String(t.attributes?.embeds ?? ''));
			try {
				const parsed = parseJSONString(raw);
				if (Array.isArray(parsed) && parsed.length > 0) {
					for (const embed of parsed) {
						result.push({
							name: String(t.attributes?.name ?? ''),
							embed,
							args: decode(String(t.attributes?.arguments ?? ''))
						});
					}
				}
			} catch {
				// intentionally empty
			}
		}
		return result;
	})();

	$: summaryText = (() => {
		const parts = [];

		if (toolCallCount > 0) {
			const nameCounts: Record<string, number> = {};
			toolTokens.forEach((t) => {
				const name = String(t?.attributes?.name ?? 'tool');
				nameCounts[name] = (nameCounts[name] || 0) + 1;
			});

			const toolParts = Object.entries(nameCounts).map(([name, count]) => {
				const displayName = formatToolName(name);
				return count > 1 ? `${count} ${displayName}` : displayName;
			});
			parts.push(...toolParts);
		}

		if (codeInterpreterCount > 0) {
			if (codeInterpreterCount === 1) {
				parts.push($i18n.t('Ran {{COUNT}} analysis', { COUNT: codeInterpreterCount }));
			} else {
				parts.push($i18n.t('Ran {{COUNT}} analyses', { COUNT: codeInterpreterCount }));
			}
		}

		return parts.join(', ');
	})();

	$: prefixText = (() => {
		if (toolCallCount > 0) {
			return hasPending
				? $i18n.t('Running tools')
				: hasFailures
					? $i18n.t('Tools finished with issues')
					: $i18n.t('Ran tools');
		}

		if (reasoningCount > 0) {
			return hasPending ? $i18n.t('Thinking...') : $i18n.t('Thought');
		}

		if (codeInterpreterCount > 0) {
			return hasPending ? $i18n.t('Analyzing...') : $i18n.t('Analyzed');
		}

		return $i18n.t('Ran tools');
	})();
</script>

<div {id} class="w-full">
	<button
		class="w-fit text-left text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition cursor-pointer"
		aria-label={$i18n.t('Toggle details')}
		aria-expanded={open}
		on:click={() => {
			open = !open;
		}}
	>
		<div class="flex items-center gap-1.5">
			{#if hasPending}
				<div>
					<Spinner className="size-4" />
				</div>
			{:else if hasFailures}
				<div class="text-amber-500 dark:text-amber-400">
					<XMark className="size-4" strokeWidth="2" />
				</div>
			{:else if allSuccessful}
				<div class="text-emerald-500 dark:text-emerald-400">
					<CheckCircle className="size-4" strokeWidth="2" />
				</div>
			{:else}
				<div class="text-gray-400 dark:text-gray-500">
					<Sparkles className="size-3.5" />
				</div>
			{/if}

			<div class="flex-1 line-clamp-1">
				<span class="text-gray-600 dark:text-gray-300 {hasPending ? 'shimmer' : ''}"
					>{prefixText}</span
				>
				{#if summaryText}
					<span class="text-gray-400 dark:text-gray-500"> · {summaryText}</span>
				{/if}
			</div>

			<div class="flex shrink-0 self-center text-gray-400 dark:text-gray-500">
				{#if open}
					<ChevronUp strokeWidth="3.5" className="size-3" />
				{:else}
					<ChevronDown strokeWidth="3.5" className="size-3" />
				{/if}
			</div>
		</div>
	</button>

	{#if open}
		<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
			<div class="mb-0.5 mt-1 space-y-0.5 border-l border-gray-100 dark:border-gray-800 ml-2 pl-2">
				<slot name="content" />
			</div>
		</div>
	{/if}

	{#if allEmbeds.length > 0}
		{#each allEmbeds as embedItem, idx}
			<div id={`${id}-embed-${idx}`}>
				<FullHeightIframe
					src={embedItem.embed}
					args={embedItem.args}
					allowScripts={true}
					allowForms={$settings?.iframeSandboxAllowForms ?? false}
					allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
					allowPopups={true}
				/>
			</div>
		{/each}
	{/if}
</div>
