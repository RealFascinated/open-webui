<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let onChange: (params: unknown) => void = () => {};

	export let admin = false;
	export let custom = false;

	const defaultParams = {
		// Advanced
		stream_response: null, // Set stream responses for this model individually
		stream_delta_chunk_size: null, // Set the chunk size for streaming responses
		compact_context_percent: null,
		function_calling: null,
		reasoning_tags: null,
		seed: null,
		stop: null,
		temperature: null,
		reasoning_effort: null,
		logit_bias: null,
		max_tokens: null,
		top_k: null,
		top_p: null,
		min_p: null,
		frequency_penalty: null,
		presence_penalty: null,
		mirostat: null,
		mirostat_eta: null,
		mirostat_tau: null,
		repeat_last_n: null,
		tfs_z: null,
		repeat_penalty: null,
		use_mmap: null,
		use_mlock: null,
		think: null,
		format: null,
		keep_alive: null,
		num_keep: null,
		num_ctx: null,
		num_batch: null,
		num_thread: null,
		num_gpu: null
	};

	export let params = defaultParams;
	$: if (params) {
		onChange(params);
	}

	const isNull = (value: unknown) => (value ?? null) === null;

	const formatValue = (value: unknown) => {
		if (typeof value === 'number') {
			return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(3)));
		}
		if (typeof value === 'boolean') {
			return value ? $i18n.t('On') : $i18n.t('Off');
		}
		if (typeof value === 'string' && value.trim()) {
			return value.length > 18 ? `${value.slice(0, 16)}…` : value;
		}
		return $i18n.t('Custom');
	};

	const toggleNull = (key: string, defaultValue: unknown) => {
		params[key] = isNull(params?.[key]) ? defaultValue : null;
	};

	const setParam = (key: string, value: unknown) => {
		params[key] = value;
	};

	const modeButtonClass =
		'min-w-[4.5rem] px-2 py-1 text-[11px] leading-none rounded-md transition shrink-0 outline-hidden text-right tabular-nums';
	const modeActiveClass =
		'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 font-medium';
	const modeDefaultClass = 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300';
	const rangeClass =
		'w-full h-1.5 rounded-full appearance-none cursor-pointer bg-gray-200 dark:bg-gray-700 accent-gray-700 dark:accent-gray-300';
	const numberClass =
		'bg-transparent text-center w-14 text-xs tabular-nums rounded-md border border-transparent hover:border-gray-200 dark:hover:border-gray-700 focus:border-gray-300 dark:focus:border-gray-600 outline-hidden';
	const textInputClass =
		'text-xs w-full bg-transparent outline-hidden rounded-md border border-gray-100/40 dark:border-gray-800 px-2 py-1.5';
</script>

{#snippet sectionLabel(label: string)}
	<div
		class="pt-3 first:pt-0 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
	>
		{label}
	</div>
{/snippet}

{#snippet modeLabel(value: unknown, customLabel: string | null = null)}
	{#if isNull(value)}
		<span class={modeDefaultClass}>{$i18n.t('Default')}</span>
	{:else if customLabel}
		<span class={modeActiveClass}>{customLabel}</span>
	{:else}
		<span class={modeActiveClass}>{formatValue(value)}</span>
	{/if}
{/snippet}

{#snippet paramHeader(label: string, tooltip: string, onToggle: () => void, value: unknown, customLabel: string | null = null)}
	<Tooltip content={$i18n.t(tooltip)} placement="top-start" className="inline-tooltip w-full">
		<div class="flex w-full items-center justify-between gap-3 min-h-[1.75rem]">
			<div class="self-center text-xs text-gray-700 dark:text-gray-200 truncate">
				{$i18n.t(label)}
			</div>
			<button class={modeButtonClass} type="button" on:click={onToggle}>
				{@render modeLabel(value, customLabel)}
			</button>
		</div>
	</Tooltip>
{/snippet}

{#snippet rangeControl(key: string, min: number, max: number, step: number)}
	<div class="flex items-center gap-2 pt-1 pb-0.5 pl-0.5">
		<input type="range" {min} {max} {step} bind:value={params[key]} class={rangeClass} />
		<input type="number" bind:value={params[key]} class={numberClass} {min} {max} step="any" />
	</div>
{/snippet}

<div class="space-y-0.5 text-xs pb-safe-bottom">
	{@render sectionLabel($i18n.t('General'))}

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'Stream Chat Response',
			'When enabled, the model will respond to each chat message in real-time, generating a response as soon as the user sends a message. This mode is useful for live chat applications, but may impact performance on slower hardware.',
			() => {
				setParam(
					'stream_response',
					isNull(params?.stream_response) ? true : params.stream_response ? false : null
				);
			},
			params.stream_response,
			params.stream_response === true
				? $i18n.t('On')
				: params.stream_response === false
					? $i18n.t('Off')
					: null
		)}
	</div>

	{#if admin}
		<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
			{@render paramHeader(
				'Stream Delta Chunk Size',
				'The stream delta chunk size for the model. Increasing the chunk size will make the model respond with larger pieces of text at once.',
				() => toggleNull('stream_delta_chunk_size', 1),
				params?.stream_delta_chunk_size
			)}
			{#if !isNull(params?.stream_delta_chunk_size)}
				{@render rangeControl('stream_delta_chunk_size', 1, 128, 1)}
			{/if}
		</div>

		<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
			{@render paramHeader(
				'Context Compaction Threshold',
				'Lower the context compaction threshold for this model. The global context compaction threshold remains the maximum.',
				() => toggleNull('compact_context_percent', 80),
				params?.compact_context_percent
			)}
			{#if !isNull(params?.compact_context_percent)}
				<div class="pt-1 pb-0.5">
					<input
						class={textInputClass}
						type="number"
						placeholder={$i18n.t('Enter context usage percent')}
						bind:value={params.compact_context_percent}
						autocomplete="off"
						min="1"
						max="100"
						step="1"
					/>
				</div>
			{/if}
		</div>
	{/if}

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'Function Calling',
			"Native mode (default) leverages the model's built-in tool-calling capabilities. Legacy mode works with a wider range of models by calling tools once before execution via prompt injection.",
			() => {
				if (isNull(params?.function_calling)) {
					setParam('function_calling', 'native');
				} else if (params.function_calling === 'native') {
					setParam('function_calling', 'legacy');
				} else {
					setParam('function_calling', null);
				}
			},
			params.function_calling,
			params.function_calling === 'native'
				? $i18n.t('Native')
				: params.function_calling === 'legacy'
					? $i18n.t('Legacy')
					: null
		)}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'Reasoning Tags',
			'Enable, disable, or customize the reasoning tags used by the model. "Enabled" uses default tags, "Disabled" turns off reasoning tags, and "Custom" lets you specify your own start and end tags.',
			() => {
				if (isNull(params?.reasoning_tags)) {
					setParam('reasoning_tags', ['', '']);
				} else if ((params?.reasoning_tags ?? []).length === 2) {
					setParam('reasoning_tags', true);
				} else if ((params?.reasoning_tags ?? null) !== false) {
					setParam('reasoning_tags', false);
				} else {
					setParam('reasoning_tags', null);
				}
			},
			params?.reasoning_tags,
			isNull(params?.reasoning_tags)
				? null
				: params?.reasoning_tags === true
					? $i18n.t('Enabled')
					: params?.reasoning_tags === false
						? $i18n.t('Disabled')
						: $i18n.t('Custom')
		)}

		{#if ![true, false, null].includes(params?.reasoning_tags ?? null) && (params?.reasoning_tags ?? []).length === 2}
			<div class="flex gap-2 pt-1 pb-0.5">
				<input
					class={textInputClass}
					type="text"
					placeholder={$i18n.t('Start Tag')}
					bind:value={params.reasoning_tags[0]}
					autocomplete="off"
				/>
				<input
					class={textInputClass}
					type="text"
					placeholder={$i18n.t('End Tag')}
					bind:value={params.reasoning_tags[1]}
					autocomplete="off"
				/>
			</div>
		{/if}
	</div>

	{@render sectionLabel($i18n.t('Sampling'))}

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'Seed',
			'Sets the random number seed to use for generation. Setting this to a specific number will make the model generate the same text for the same prompt.',
			() => toggleNull('seed', 0),
			params?.seed
		)}
		{#if !isNull(params?.seed)}
			<div class="pt-1 pb-0.5">
				<input
					class={textInputClass}
					type="number"
					placeholder={$i18n.t('Enter Seed')}
					bind:value={params.seed}
					autocomplete="off"
					min="0"
				/>
			</div>
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'Stop Sequence',
			'Sets the stop sequences to use. When this pattern is encountered, the LLM will stop generating text and return. Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile.',
			() => toggleNull('stop', ''),
			params?.stop
		)}
		{#if !isNull(params?.stop)}
			<div class="pt-1 pb-0.5">
				<input
					class={textInputClass}
					type="text"
					placeholder={$i18n.t('Enter stop sequence')}
					bind:value={params.stop}
					autocomplete="off"
				/>
			</div>
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'Temperature',
			'The temperature of the model. Increasing the temperature will make the model answer more creatively.',
			() => toggleNull('temperature', 0.8),
			params?.temperature
		)}
		{#if !isNull(params?.temperature)}
			{@render rangeControl('temperature', 0, 2, 0.05)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'Reasoning Effort',
			'Constrains effort on reasoning for reasoning models. Only applicable to reasoning models from specific providers that support reasoning effort.',
			() => toggleNull('reasoning_effort', 'medium'),
			params?.reasoning_effort
		)}
		{#if !isNull(params?.reasoning_effort)}
			<div class="pt-1 pb-0.5">
				<input
					class={textInputClass}
					type="text"
					placeholder={$i18n.t('Enter reasoning effort')}
					bind:value={params.reasoning_effort}
					autocomplete="off"
				/>
			</div>
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'logit_bias',
			'Boosting or penalizing specific tokens for constrained responses. Bias values will be clamped between -100 and 100 (inclusive). (Default: none)',
			() => toggleNull('logit_bias', ''),
			params?.logit_bias
		)}
		{#if !isNull(params?.logit_bias)}
			<div class="pt-1 pb-0.5">
				<input
					class={textInputClass}
					type="text"
					placeholder={$i18n.t(
						'Enter comma-separated "token:bias_value" pairs (example: 5432:100, 413:-100)'
					)}
					bind:value={params.logit_bias}
					autocomplete="off"
				/>
			</div>
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'max_tokens',
			'This option sets the maximum number of tokens the model can generate in its response. Increasing this limit allows the model to provide longer answers, but it may also increase the likelihood of unhelpful or irrelevant content being generated.',
			() => toggleNull('max_tokens', 128),
			params?.max_tokens
		)}
		{#if !isNull(params?.max_tokens)}
			{@render rangeControl('max_tokens', -2, 131072, 1)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'top_k',
			'Reduces the probability of generating nonsense. A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative.',
			() => toggleNull('top_k', 40),
			params?.top_k
		)}
		{#if !isNull(params?.top_k)}
			{@render rangeControl('top_k', 0, 1000, 0.5)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'top_p',
			'Works together with top-k. A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text.',
			() => toggleNull('top_p', 0.9),
			params?.top_p
		)}
		{#if !isNull(params?.top_p)}
			{@render rangeControl('top_p', 0, 1, 0.05)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'min_p',
			'Alternative to the top_p, and aims to ensure a balance of quality and variety. The parameter p represents the minimum probability for a token to be considered, relative to the probability of the most likely token. For example, with p=0.05 and the most likely token having a probability of 0.9, logits with a value less than 0.045 are filtered out.',
			() => toggleNull('min_p', 0.0),
			params?.min_p
		)}
		{#if !isNull(params?.min_p)}
			{@render rangeControl('min_p', 0, 1, 0.05)}
		{/if}
	</div>

	{@render sectionLabel($i18n.t('Penalties'))}

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'frequency_penalty',
			'Sets a scaling bias against tokens to penalize repetitions, based on how many times they have appeared. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. At 0, it is disabled.',
			() => toggleNull('frequency_penalty', 1.1),
			params?.frequency_penalty
		)}
		{#if !isNull(params?.frequency_penalty)}
			{@render rangeControl('frequency_penalty', -2, 2, 0.05)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'presence_penalty',
			'Sets a flat bias against tokens that have appeared at least once. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. At 0, it is disabled.',
			() => toggleNull('presence_penalty', 0.0),
			params?.presence_penalty
		)}
		{#if !isNull(params?.presence_penalty)}
			{@render rangeControl('presence_penalty', -2, 2, 0.05)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'repeat_last_n',
			'Sets how far back for the model to look back to prevent repetition.',
			() => toggleNull('repeat_last_n', 64),
			params?.repeat_last_n
		)}
		{#if !isNull(params?.repeat_last_n)}
			{@render rangeControl('repeat_last_n', -1, 128, 1)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'tfs_z',
			'Tail free sampling is used to reduce the impact of less probable tokens from the output. A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting.',
			() => toggleNull('tfs_z', 1),
			params?.tfs_z
		)}
		{#if !isNull(params?.tfs_z)}
			{@render rangeControl('tfs_z', 0, 2, 0.05)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'repeat_penalty',
			'Control the repetition of token sequences in the generated text. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 1.1) will be more lenient. At 1, it is disabled.',
			() => toggleNull('repeat_penalty', 1.1),
			params?.repeat_penalty
		)}
		{#if !isNull(params?.repeat_penalty)}
			{@render rangeControl('repeat_penalty', -2, 2, 0.05)}
		{/if}
	</div>

	{@render sectionLabel('Mirostat')}

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'mirostat',
			'Enable Mirostat sampling for controlling perplexity.',
			() => toggleNull('mirostat', 0),
			params?.mirostat
		)}
		{#if !isNull(params?.mirostat)}
			{@render rangeControl('mirostat', 0, 2, 1)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'mirostat_eta',
			'Influences how quickly the algorithm responds to feedback from the generated text. A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive.',
			() => toggleNull('mirostat_eta', 0.1),
			params?.mirostat_eta
		)}
		{#if !isNull(params?.mirostat_eta)}
			{@render rangeControl('mirostat_eta', 0, 1, 0.05)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'mirostat_tau',
			'Controls the balance between coherence and diversity of the output. A lower value will result in more focused and coherent text.',
			() => toggleNull('mirostat_tau', 5.0),
			params?.mirostat_tau
		)}
		{#if !isNull(params?.mirostat_tau)}
			{@render rangeControl('mirostat_tau', 0, 10, 0.5)}
		{/if}
	</div>

	{#if admin}
		{@render sectionLabel($i18n.t('Memory'))}

		<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
			{@render paramHeader(
				'use_mmap',
				'Enable Memory Mapping (mmap) to load model data. This option allows the system to use disk storage as an extension of RAM by treating disk files as if they were in RAM. This can improve model performance by allowing for faster data access. However, it may not work correctly with all systems and can consume a significant amount of disk space.',
				() => toggleNull('use_mmap', true),
				params?.use_mmap
			)}
			{#if !isNull(params?.use_mmap)}
				<div class="flex justify-between items-center pt-1 pb-0.5">
					<div class="text-xs text-gray-500">
						{params.use_mmap ? $i18n.t('Enabled') : $i18n.t('Disabled')}
					</div>
					<div class="pr-1">
						<Switch bind:state={params.use_mmap} />
					</div>
				</div>
			{/if}
		</div>

		<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
			{@render paramHeader(
				'use_mlock',
				"Enable Memory Locking (mlock) to prevent model data from being swapped out of RAM. This option locks the model's working set of pages into RAM, ensuring that they will not be swapped out to disk. This can help maintain performance by avoiding page faults and ensuring fast data access.",
				() => toggleNull('use_mlock', true),
				params?.use_mlock
			)}
			{#if !isNull(params?.use_mlock)}
				<div class="flex justify-between items-center pt-1 pb-0.5">
					<div class="text-xs text-gray-500">
						{params.use_mlock ? $i18n.t('Enabled') : $i18n.t('Disabled')}
					</div>
					<div class="pr-1">
						<Switch bind:state={params.use_mlock} />
					</div>
				</div>
			{/if}
		</div>
	{/if}

	{@render sectionLabel($i18n.t('Ollama'))}

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'think',
			'This option enables or disables the use of the reasoning feature in Ollama, which allows the model to think before generating a response. When enabled, the model can take a moment to process the conversation context and generate a more thoughtful response.',
			() => {
				if (isNull(params?.think)) {
					setParam('think', true);
				} else if (params.think === true) {
					setParam('think', 'medium');
				} else if (typeof params.think === 'string') {
					setParam('think', false);
				} else {
					setParam('think', null);
				}
			},
			params.think,
			params.think === true
				? $i18n.t('On')
				: params.think === false
					? $i18n.t('Off')
					: typeof params.think === 'string'
						? formatValue(params.think)
						: null
		)}
		{#if typeof params.think === 'string'}
			<div class="pt-1 pb-0.5">
				<input
					class={textInputClass}
					type="text"
					placeholder={$i18n.t("e.g. 'low', 'medium', 'high', 'max'")}
					bind:value={params.think}
					autocomplete="off"
				/>
			</div>
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'format',
			'The format to return a response in. Format can be json or a JSON schema.',
			() => toggleNull('format', 'json'),
			params?.format,
			!isNull(params?.format) ? $i18n.t('JSON') : null
		)}
		{#if !isNull(params?.format)}
			<div class="pt-1 pb-0.5">
				<Textarea
					className="w-full text-xs bg-transparent outline-hidden rounded-md border border-gray-100/40 dark:border-gray-800 px-2 py-1.5"
					placeholder={$i18n.t('e.g. "json" or a JSON schema')}
					bind:value={params.format}
				/>
			</div>
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'num_keep',
			'This option controls how many tokens are preserved when refreshing the context. For example, if set to 2, the last 2 tokens of the conversation context will be retained. Preserving context can help maintain the continuity of a conversation, but it may reduce the ability to respond to new topics.',
			() => toggleNull('num_keep', 24),
			params?.num_keep
		)}
		{#if !isNull(params?.num_keep)}
			{@render rangeControl('num_keep', -1, 10240000, 1)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'num_ctx',
			'Sets the size of the context window used to generate the next token.',
			() => toggleNull('num_ctx', 2048),
			params?.num_ctx
		)}
		{#if !isNull(params?.num_ctx)}
			{@render rangeControl('num_ctx', -1, 10240000, 1)}
		{/if}
	</div>

	<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
		{@render paramHeader(
			'num_batch',
			'The batch size determines how many text requests are processed together at once. A higher batch size can increase the performance and speed of the model, but it also requires more memory.',
			() => toggleNull('num_batch', 512),
			params?.num_batch
		)}
		{#if !isNull(params?.num_batch)}
			{@render rangeControl('num_batch', 256, 8192, 256)}
		{/if}
	</div>

	{#if admin}
		<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
			{@render paramHeader(
				'num_thread',
				'Set the number of worker threads used for computation. This option controls how many threads are used to process incoming requests concurrently. Increasing this value can improve performance under high concurrency workloads but may also consume more CPU resources.',
				() => toggleNull('num_thread', 2),
				params?.num_thread
			)}
			{#if !isNull(params?.num_thread)}
				{@render rangeControl('num_thread', 1, 256, 1)}
			{/if}
		</div>

		<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
			{@render paramHeader(
				'num_gpu',
				'Set the number of layers, which will be off-loaded to GPU. Increasing this value can significantly improve performance for models that are optimized for GPU acceleration but may also consume more power and GPU resources.',
				() => toggleNull('num_gpu', 0),
				params?.num_gpu
			)}
			{#if !isNull(params?.num_gpu)}
				{@render rangeControl('num_gpu', 0, 256, 1)}
			{/if}
		</div>

		<div class="rounded-lg px-1 -mx-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
			{@render paramHeader(
				'keep_alive',
				'This option controls how long the model will stay loaded into memory following the request (default: 5m)',
				() => toggleNull('keep_alive', '5m'),
				params?.keep_alive
			)}
			{#if !isNull(params?.keep_alive)}
				<div class="pt-1 pb-0.5">
					<input
						class={textInputClass}
						type="text"
						placeholder={$i18n.t("e.g. '30s','10m'. Valid time units are 's', 'm', 'h'.")}
						bind:value={params.keep_alive}
					/>
				</div>
			{/if}
		</div>

		{#if custom && admin}
			{@render sectionLabel($i18n.t('Custom'))}

			<div class="flex flex-col justify-center px-1 -mx-1">
				{#each Object.keys(params?.custom_params ?? {}) as key}
					<div class="rounded-lg py-1 mb-1 hover:bg-gray-50/80 dark:hover:bg-gray-850/40 transition">
						<div class="flex w-full items-center justify-between gap-2">
							<input
								type="text"
								class="text-xs w-full bg-transparent outline-none"
								placeholder={$i18n.t('Custom Parameter Name')}
								value={key}
								on:change={(e) => {
									const newKey = e.target.value.trim();
									if (newKey && newKey !== key) {
										params.custom_params[newKey] = params.custom_params[key];
										delete params.custom_params[key];
										params = {
											...params,
											custom_params: { ...params.custom_params }
										};
									}
								}}
							/>
							<button
								class="{modeButtonClass} {modeDefaultClass}"
								type="button"
								on:click={() => {
									delete params.custom_params[key];
									params = {
										...params,
										custom_params: { ...params.custom_params }
									};
								}}
							>
								{$i18n.t('Remove')}
							</button>
						</div>
						<div class="pt-1">
							<input
								bind:value={params.custom_params[key]}
								type="text"
								class={textInputClass}
								placeholder={$i18n.t('Custom Parameter Value')}
							/>
						</div>
					</div>
				{/each}

				<button
					class="flex gap-2 items-center w-full justify-center mt-1 mb-3 py-1.5 rounded-lg text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850/50 transition"
					type="button"
					on:click={() => {
						params.custom_params = (params?.custom_params ?? {}) || {};
						params.custom_params['custom_param_name'] = 'custom_param_value';
					}}
				>
					<Plus />
					<div>{$i18n.t('Add Custom Parameter')}</div>
				</button>
			</div>
		{/if}
	{/if}
</div>
