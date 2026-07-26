<script lang="ts">
	import { decode } from 'html-entities';
	import { v4 as uuidv4 } from 'uuid';

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Spinner from './Spinner.svelte';
	import WrenchSolid from '../icons/WrenchSolid.svelte';
	import CheckCircle from '../icons/CheckCircle.svelte';
	import XMark from '../icons/XMark.svelte';
	import FullHeightIframe from './FullHeightIframe.svelte';
	import { settings } from '$lib/stores';
	import { formatToolName } from '$lib/utils';
	import {
		isToolCallPending,
		isToolCallSuccessful,
		resolveToolCallStatus,
		type ToolCallAttributes
	} from '$lib/utils/toolCallDisplay';

	export let id: string = '';
	export let attributes: ToolCallAttributes = {};
	export let open = false;
	export let grouped = false;
	export let compact = false;
	export let messageDone = false;
	export let toolSourceId = '';
	export let className = '';

	const RESULT_PREVIEW_LIMIT = 10000;
	let expandedResult = false;

	$: if (!open) expandedResult = false;
	export let buttonClassName =
		'w-fit text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition';

	export let resultContent: string = '';

	const componentId = id || uuidv4();

	function parseJSONString(str: string) {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		let value: unknown = str;
		while (typeof value === 'string') {
			try {
				value = JSON.parse(value);
			} catch {
				break;
			}
		}
		return value;
	}

	function formatJSONString(str: string) {
		try {
			const parsed = parseJSONString(str);
			if (typeof parsed === 'object') {
				return JSON.stringify(parsed, null, 2);
			}
			return String(parsed);
		} catch (_e) {
			return str;
		}
	}

	function parseArguments(str: string): Record<string, unknown> | null {
		try {
			const parsed = parseJSONString(str);
			if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
				return parsed as Record<string, unknown>;
			}
			return null;
		} catch {
			return null;
		}
	}

	$: result = resultContent || decode(String(attributes?.result ?? ''));
	$: embeds = parseJSONString(decode(String(attributes?.embeds ?? '')));
	$: args =
		open || (Array.isArray(embeds) && embeds.length > 0) ? decode(String(attributes?.arguments ?? '')) : '';
	$: status = resolveToolCallStatus(attributes, messageDone);
	$: isPending = isToolCallPending(status, messageDone);
	$: isSuccessful = isToolCallSuccessful(status);
	$: isCancelled = status === 'cancelled';
	$: isFailed = status === 'failed' || status === 'incomplete';
	$: parsedArgs = parseArguments(args);
	$: parsedResult = parseJSONString(result);
	$: displayName = formatToolName(String(attributes?.name ?? ''));
	$: contextText = String(attributes?.context ?? resultContent ?? '').trim();
	$: collapsedContext = contextText && contextText !== result ? contextText : '';
	$: isCompact = compact || attributes?.compact === 'true';
	$: statusLabel = isPending
		? $i18n.t('Running {{NAME}}...', { NAME: displayName })
		: isCancelled
			? $i18n.t('{{NAME}} cancelled', { NAME: displayName })
			: isFailed
				? $i18n.t('{{NAME}} failed', { NAME: displayName })
				: $i18n.t('Result from {{NAME}}', { NAME: displayName });
	$: resolvedToolSourceId =
		toolSourceId || (attributes?.name ? `${componentId}-${attributes.name}` : '');
</script>

<div {id} class={className}>
	{#if isCompact}
		<div
			class="w-full max-w-full font-medium flex items-center gap-1.5 py-0.5"
			data-tool-source={resolvedToolSourceId}
		>
			{#if isPending}
				<div>
					<Spinner className="size-4" />
				</div>
			{:else if isSuccessful}
				<div class="text-emerald-500 dark:text-emerald-400">
					<CheckCircle className="size-4" strokeWidth="2" />
				</div>
			{:else if isCancelled}
				<div class="text-gray-400 dark:text-gray-500">
					<XMark className="size-4" strokeWidth="2" />
				</div>
			{:else if isFailed}
				<div class="text-amber-500 dark:text-amber-400">
					<XMark className="size-4" strokeWidth="2" />
				</div>
			{:else}
				<div class="text-gray-400 dark:text-gray-500">
					<WrenchSolid className="size-3.5" />
				</div>
			{/if}

			<div class="flex-1 min-w-0 line-clamp-1">
				<span class="text-sm text-gray-700 dark:text-gray-200">{displayName}</span>
				{#if collapsedContext}
					<span class="text-sm text-gray-400 dark:text-gray-500"> · {collapsedContext}</span>
				{/if}
				{#if isCancelled}
					<span class="text-sm text-gray-400 dark:text-gray-500"> · {$i18n.t('cancelled')}</span>
				{:else if isFailed}
					<span class="text-sm text-amber-500 dark:text-amber-400"> · {$i18n.t('failed')}</span>
				{/if}
			</div>
		</div>
	{:else if !grouped && embeds && Array.isArray(embeds) && embeds.length > 0}
		<div class="py-1 w-full cursor-pointer">
			<div class="w-full text-xs text-gray-500">
				{displayName}
			</div>
			{#each embeds as embed, idx}
				<div class="my-2" id={`${componentId}-tool-call-embed-${idx}`}>
					<FullHeightIframe
						src={embed}
						{args}
						allowScripts={true}
						allowForms={$settings?.iframeSandboxAllowForms ?? false}
						allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
						allowPopups={true}
					/>
				</div>
			{/each}
		</div>
	{:else}
		<button
			type="button"
			class="{buttonClassName} cursor-pointer w-full text-left"
			aria-expanded={open}
			aria-label={statusLabel}
			data-tool-source={resolvedToolSourceId || undefined}
			on:click={() => {
				open = !open;
			}}
		>
			<div
				class="w-full max-w-full font-medium flex items-center gap-1.5 {grouped
					? 'py-0.5'
					: ''} {isPending ? 'shimmer' : ''}"
			>
				{#if isPending}
					<div>
						<Spinner className="size-4" />
					</div>
				{:else if isSuccessful}
					<div class="text-emerald-500 dark:text-emerald-400">
						<CheckCircle className="size-4" strokeWidth="2" />
					</div>
				{:else if isCancelled}
					<div class="text-gray-400 dark:text-gray-500">
						<XMark className="size-4" strokeWidth="2" />
					</div>
				{:else if isFailed}
					<div class="text-amber-500 dark:text-amber-400">
						<XMark className="size-4" strokeWidth="2" />
					</div>
				{:else}
					<div class="text-gray-400 dark:text-gray-500">
						<WrenchSolid className="size-3.5" />
					</div>
				{/if}

				<div class="flex-1 min-w-0 line-clamp-1">
					{#if grouped}
						<span class="text-sm text-gray-700 dark:text-gray-200">{displayName}</span>
						{#if collapsedContext}
							<span class="text-sm text-gray-400 dark:text-gray-500">
								· {collapsedContext}
							</span>
						{/if}
						{#if isCancelled}
							<span class="text-sm text-gray-400 dark:text-gray-500"> · {$i18n.t('cancelled')}</span>
						{:else if isFailed}
							<span class="text-sm text-amber-500 dark:text-amber-400"> · {$i18n.t('failed')}</span>
						{/if}
					{:else}
						<span class="text-sm text-gray-700 dark:text-gray-200">{statusLabel}</span>
						{#if collapsedContext}
							<span class="text-sm text-gray-400 dark:text-gray-500">
								· {collapsedContext}
							</span>
						{/if}
					{/if}
				</div>

				<div class="flex shrink-0 self-center translate-y-[1px] text-gray-400 dark:text-gray-500">
					{#if open}
						<ChevronUp strokeWidth="3.5" className="size-3.5" />
					{:else}
						<ChevronDown strokeWidth="3.5" className="size-3.5" />
					{/if}
				</div>
			</div>
		</button>

		{#if open}
			<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
				<div
					class="{grouped
						? 'border-l border-gray-100 dark:border-gray-800 ml-2 pl-3'
						: ''} border border-gray-50 dark:border-gray-850/30 rounded-2xl my-1.5 p-3 space-y-3"
				>
					{#if args}
						<div>
							<div
								class="text-[10px] uppercase tracking-wider font-medium text-gray-400 dark:text-gray-500 mb-1.5 px-1"
							>
								{$i18n.t('Input')}
							</div>

							{#if parsedArgs}
								<div class="px-1 space-y-0.5">
									{#each Object.entries(parsedArgs) as [key, value]}
										<div class="flex gap-2 text-xs py-0.5">
											<span class="font-medium text-gray-600 dark:text-gray-400 shrink-0"
												>{key}</span
											>
											<span class="text-gray-800 dark:text-gray-200 break-all"
												>{typeof value === 'object' ? JSON.stringify(value) : value}</span
											>
										</div>
									{/each}
								</div>
							{:else}
								<div class="tool-call-body w-full max-w-none!">
									<pre
										class="text-xs text-gray-600 dark:text-gray-300 whitespace-pre font-mono bg-gray-50 dark:bg-gray-900 rounded-lg p-2.5 overflow-x-auto">{formatJSONString(
											args
										)}</pre>
								</div>
							{/if}
						</div>
					{/if}

					{#if (isSuccessful || isFailed) && result}
						<div>
							<div
								class="text-[10px] uppercase tracking-wider font-medium text-gray-400 dark:text-gray-500 mb-1.5 px-1"
							>
								{$i18n.t('Output')}
							</div>
							<div class="w-full max-w-none!">
								{#if typeof parsedResult === 'object' && parsedResult !== null}
									<pre
										class="text-xs text-gray-600 dark:text-gray-300 whitespace-pre font-mono bg-gray-50 dark:bg-gray-900 rounded-lg p-2.5 overflow-x-auto">{JSON.stringify(
											parsedResult,
											null,
											2
										)}</pre>
								{:else}
									{@const resultStr = String(parsedResult)}
									{@const isTruncated = resultStr.length > RESULT_PREVIEW_LIMIT && !expandedResult}
									<pre
										class="text-xs text-gray-600 dark:text-gray-300 whitespace-pre-wrap break-words font-mono">{isTruncated
											? resultStr.slice(0, RESULT_PREVIEW_LIMIT)
											: resultStr}</pre>
									{#if isTruncated}
										<button
											class="mt-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
											on:click|stopPropagation={() => {
												expandedResult = true;
											}}
										>
											{$i18n.t('Show all ({{COUNT}} characters)', {
												COUNT: resultStr.length.toLocaleString()
											})}
										</button>
									{/if}
								{/if}
							</div>
						</div>
					{:else if isCancelled}
						<div class="px-1 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('This tool call was cancelled before it finished.')}
						</div>
					{:else if isFailed && !result}
						<div class="px-1 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('This tool call did not return a result.')}
						</div>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>
