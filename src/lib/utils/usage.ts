export type UsageRecord = Record<string, unknown>;

export type UsageModel = {
	id?: string;
	urlIdx?: number | string;
	provider?: string;
	meta?: Record<string, unknown>;
	info?: { base_model_id?: string; params?: Record<string, unknown>; meta?: Record<string, unknown> };
	owned_by?: string;
	openai?: Record<string, unknown>;
	ollama?: Record<string, unknown>;
} | null;

const TOKEN_COUNT_KEYS = new Set([
	'input_tokens',
	'output_tokens',
	'total_tokens',
	'prompt_tokens',
	'completion_tokens',
	'prompt_eval_count',
	'eval_count',
	'prompt_n',
	'predicted_n',
	'cache_n'
]);

const CONTEXT_WINDOW_KEYS = [
	'context_length',
	'max_context_length',
	'n_ctx',
	'num_ctx',
	'max_model_len'
] as const;

const DETAIL_KEYS = new Set([
	'prompt_tokens_details',
	'completion_tokens_details',
	'input_tokens_details',
	'output_tokens_details'
]);

const DURATION_KEYS = new Set([
	'total_duration',
	'load_duration',
	'prompt_eval_duration',
	'eval_duration'
]);

const COST_KEYS = new Set([
	'cost',
	'total_cost',
	'input_cost',
	'output_cost',
	'prompt_cost',
	'completion_cost'
]);

const SPEED_KEYS = new Set(['prompt_token/s', 'response_token/s', 'prompt_per_second', 'predicted_per_second']);

const HIDDEN_USAGE_KEYS = new Set([
	'cache_n',
	'prompt_ms',
	'prompt_per_token_ms',
	'prompt_per_second',
	'predicted_ms',
	'predicted_per_token_ms',
	'predicted_per_second',
	'draft_n',
	'draft_n_accepted',
	'tokens_cached',
	'tokens_evaluated',
	'cache_read_input_tokens',
	'cache_creation_input_tokens',
	'context_breakdown'
]);

export const formatUsageNumber = (value: number): string => {
	if (Number.isInteger(value)) {
		return value.toLocaleString();
	}

	return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
};

export const getPromptTokens = (usage: UsageRecord): number => {
	if (typeof usage.cache_n === 'number' && typeof usage.prompt_n === 'number') {
		return usage.cache_n + usage.prompt_n;
	}

	return Number(
		usage.prompt_tokens ?? usage.input_tokens ?? usage.prompt_eval_count ?? usage.prompt_n ?? 0
	);
};

export const getGenerationTokens = (usage: UsageRecord): number => {
	return Number(
		usage.completion_tokens ?? usage.output_tokens ?? usage.eval_count ?? usage.predicted_n ?? 0
	);
};

export const getReasoningTokens = (usage: UsageRecord): number => {
	const completionDetails = usage.completion_tokens_details;
	const outputDetails = usage.output_tokens_details;

	if (completionDetails && typeof completionDetails === 'object') {
		const reasoning = (completionDetails as UsageRecord).reasoning_tokens;
		if (typeof reasoning === 'number') return reasoning;
	}

	if (outputDetails && typeof outputDetails === 'object') {
		const reasoning = (outputDetails as UsageRecord).reasoning_tokens;
		if (typeof reasoning === 'number') return reasoning;
	}

	if (typeof usage.reasoning_tokens === 'number') {
		return usage.reasoning_tokens;
	}

	return 0;
};

export const getContextUsedTokens = (usage: UsageRecord): number => {
	// llama.cpp timings are merged across stream chunks; total_tokens gets summed
	// and overcounts. Slot occupancy matches cache_n + prompt_n (+ generation).
	if (isLlamacppUsage(usage)) {
		return getPromptTokens(usage) + getGenerationTokens(usage);
	}

	if (typeof usage.total_tokens === 'number') {
		return usage.total_tokens;
	}

	return getPromptTokens(usage) + getGenerationTokens(usage);
};

export const isLlamacppUsage = (usage: UsageRecord): boolean => {
	return (
		typeof usage.predicted_ms === 'number' ||
		typeof usage.predicted_n === 'number' ||
		typeof usage.prompt_n === 'number' ||
		typeof usage.prompt_ms === 'number' ||
		typeof usage.prompt_per_second === 'number' ||
		typeof usage.predicted_per_second === 'number'
	);
};

export const getCachedPercent = (usage: UsageRecord): number | null => {
	if (typeof usage.cache_n === 'number' && typeof usage.prompt_n === 'number') {
		const total = usage.cache_n + usage.prompt_n;
		if (total <= 0) return usage.cache_n > 0 ? 100 : 0;
		return Math.round((usage.cache_n / total) * 100);
	}

	const promptDetails = usage.prompt_tokens_details;
	if (promptDetails && typeof promptDetails === 'object') {
		const cached = (promptDetails as UsageRecord).cached_tokens;
		const prompt = getPromptTokens(usage);
		if (typeof cached === 'number' && prompt > 0) {
			return Math.min(100, Math.round((cached / prompt) * 100));
		}
		if (typeof cached === 'number' && cached === 0) {
			return 0;
		}
	}

	const cacheRead = usage.cache_read_input_tokens;
	const inputTokens = Number(usage.input_tokens ?? usage.prompt_tokens ?? 0);
	if (typeof cacheRead === 'number' && inputTokens > 0) {
		return Math.min(100, Math.round((cacheRead / inputTokens) * 100));
	}

	return null;
};

const parsePositiveInt = (value: unknown): number | null => {
	const parsed = typeof value === 'string' ? Number(value) : value;
	if (typeof parsed === 'number' && !Number.isNaN(parsed) && parsed > 0) {
		return parsed;
	}
	return null;
};

const contextFromEntry = (entry: Record<string, unknown> | null | undefined): number | null => {
	if (!entry || typeof entry !== 'object') return null;

	for (const key of CONTEXT_WINDOW_KEYS) {
		const value = parsePositiveInt(entry[key]);
		if (value) return value;
	}

	const topProvider = entry.top_provider;
	if (topProvider && typeof topProvider === 'object') {
		const value = parsePositiveInt((topProvider as UsageRecord).context_length);
		if (value) return value;
	}

	return null;
};

const modelContextCandidates = (model: UsageModel): Record<string, unknown>[] => {
	if (!model || typeof model !== 'object') return [];

	const candidates: Record<string, unknown>[] = [model as Record<string, unknown>];

	for (const key of ['meta', 'openai', 'ollama', 'info'] as const) {
		const nested = model[key];
		if (!nested || typeof nested !== 'object') continue;

		candidates.push(nested as Record<string, unknown>);

		const nestedMeta = (nested as Record<string, unknown>).meta;
		if (nestedMeta && typeof nestedMeta === 'object') {
			candidates.push(nestedMeta as Record<string, unknown>);
		}
	}

	return candidates;
};

export const getContextFromModel = (model?: UsageModel): number | null => {
	for (const entry of modelContextCandidates(model ?? null)) {
		const value = contextFromEntry(entry);
		if (value) return value;
	}

	const info = model?.info;
	if (info && typeof info === 'object') {
		const numCtx = parsePositiveInt(info.params?.num_ctx);
		if (numCtx) return numCtx;
	}

	return null;
};

export const resolveUsageModel = (
	model: UsageModel,
	allModels?: UsageModel[] | readonly UsageModel[] | null
): UsageModel => {
	if (!model) return null;
	if (model.urlIdx !== undefined && model.urlIdx !== null) return model;

	const baseId = model.info?.base_model_id;
	if (typeof baseId === 'string' && allModels?.length) {
		const base = allModels.find((entry) => entry?.id === baseId);
		if (base) {
			return {
				...model,
				urlIdx: base.urlIdx,
				meta: model.meta ?? base.meta,
				openai: model.openai ?? base.openai,
				ollama: model.ollama ?? base.ollama,
				provider: model.provider ?? base.provider,
				owned_by: model.owned_by ?? base.owned_by
			};
		}
	}

	return model;
};

export const getContextWindowSize = (
	usage: UsageRecord,
	model?: UsageModel
): number | null => {
	const generationSettings =
		usage.generation_settings && typeof usage.generation_settings === 'object'
			? (usage.generation_settings as UsageRecord)
			: null;

	for (const source of [usage, generationSettings]) {
		if (!source) continue;
		for (const key of CONTEXT_WINDOW_KEYS) {
			const value = parsePositiveInt(source[key]);
			if (value) return value;
		}
	}

	return getContextFromModel(model);
};

const contextSizeCache = new Map<string, { size: number; expiry: number }>();

const parseUrlIdx = (urlIdx: number | string | undefined): number | null => {
	if (urlIdx === undefined || urlIdx === null) return null;
	const idx = typeof urlIdx === 'string' ? Number.parseInt(urlIdx, 10) : urlIdx;
	return Number.isNaN(idx) ? null : idx;
};

export const resolveContextWindowSize = async (
	usage: UsageRecord,
	model: UsageModel,
	token: string
): Promise<number | null> => {
	const sync = getContextWindowSize(usage, model);
	if (sync) return sync;

	const urlIdx = parseUrlIdx(model?.urlIdx);
	if (urlIdx === null) return null;

	const cacheKey = `${urlIdx}:${model?.id ?? ''}:${isLlamacppUsage(usage) ? 'llama' : 'api'}`;
	const cached = contextSizeCache.get(cacheKey);
	if (cached && cached.expiry > Date.now()) {
		return cached.size;
	}

	try {
		const { getConnectionContext } = await import('$lib/apis/openai');
		const llamacpp = isLlamacppUsage(usage);
		const result = await getConnectionContext(token, urlIdx, {
			modelId: model?.id,
			llamacpp
		}).catch(() => null);

		const size = llamacpp
			? parsePositiveInt(result?.n_ctx)
			: parsePositiveInt(result?.context_length);

		if (size) {
			contextSizeCache.set(cacheKey, { size, expiry: Date.now() + 600_000 });
			return size;
		}
	} catch {
		return null;
	}

	return null;
};

export const getContextUsagePercent = (used: number, max: number | null): number | null => {
	if (!max || max <= 0) return null;
	return Math.min(100, Math.round((used / max) * 100));
};

export const getLatestConversationUsage = (
	messages:
		| Record<
				string,
				{ usage?: unknown; info?: { usage?: unknown }; timestamp?: number; model?: string }
		  >
		| undefined
): { usage: UsageRecord; modelId: string | null } | null => {
	if (!messages) return null;

	let latestUsage: UsageRecord | null = null;
	let latestModelId: string | null = null;
	let latestTimestamp = -1;

	for (const message of Object.values(messages)) {
		const usage = (message?.usage ?? message?.info?.usage) as UsageRecord | undefined;
		if (!usage || typeof usage !== 'object') continue;

		const timestamp = message.timestamp ?? 0;
		if (timestamp >= latestTimestamp) {
			latestTimestamp = timestamp;
			latestUsage = usage;
			latestModelId = message.model ?? null;
		}
	}

	if (!latestUsage) return null;

	return { usage: latestUsage, modelId: latestModelId };
};

const formatDurationNs = (value: number): string => {
	const seconds = Math.floor((value / 1e9) % 60);
	const minutes = Math.floor((value / 6e10) % 60);
	const hours = Math.floor((value / 3.6e12) % 24);
	const parts: string[] = [];

	if (hours > 0) parts.push(`${hours}h`);
	if (minutes > 0) parts.push(`${minutes}m`);
	parts.push(`${seconds}s`);

	return parts.join('');
};

const formatLabel = (key: string): string => {
	return key
		.replace(/_/g, ' ')
		.replace(/\//g, ' / ')
		.replace(/\bms\b/gi, 'ms')
		.replace(/\b\w/g, (char) => char.toUpperCase());
};

const formatUsageValue = (key: string, value: unknown): string | null => {
	if (value === null || value === undefined || value === '') return null;

	if (typeof value === 'boolean') {
		return value ? 'Yes' : 'No';
	}

	if (typeof value === 'string') {
		return value;
	}

	if (typeof value === 'number') {
		if (COST_KEYS.has(key)) {
			return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}`;
		}

		if (DURATION_KEYS.has(key)) {
			return formatDurationNs(value);
		}

		if (SPEED_KEYS.has(key)) {
			return `${formatUsageNumber(value)} tok/s`;
		}

		if (key.endsWith('_ms')) {
			return `${formatUsageNumber(value)} ms`;
		}

		return formatUsageNumber(value);
	}

	return null;
};

export type UsageDetailRow = {
	label: string;
	value: string;
};

export type ContextBreakdown = {
	verified: boolean;
	source?: string;
	total: number;
	system: number;
	conversation: number;
	tools: number;
	memory: number;
	skills: number;
	files: number;
	knowledge: number;
	tools_detail?: {
		user?: number;
		builtin?: number;
		mcp?: number;
		external?: number;
		terminal?: number;
	};
};

export type ContextBreakdownRow = {
	id: string;
	label: string;
	value: number;
	percent: number;
	nested?: boolean;
	color: string;
};

const CONTEXT_BREAKDOWN_COLORS: Record<string, string> = {
	system: 'bg-slate-400',
	memory: 'bg-violet-400',
	skills: 'bg-fuchsia-400',
	files: 'bg-cyan-400',
	knowledge: 'bg-amber-400',
	tools: 'bg-blue-500',
	conversation: 'bg-emerald-500',
	'tools-builtin': 'bg-blue-400',
	'tools-mcp': 'bg-indigo-400',
	'tools-user': 'bg-sky-400',
	'tools-external': 'bg-blue-300',
	'tools-terminal': 'bg-teal-400'
};

export const getContextBreakdown = (usage: UsageRecord): ContextBreakdown | null => {
	const raw = usage.context_breakdown;
	if (!raw || typeof raw !== 'object') return null;
	const breakdown = raw as ContextBreakdown;
	if (!breakdown.verified || typeof breakdown.total !== 'number' || breakdown.total <= 0) {
		return null;
	}
	return breakdown;
};

export const getContextBreakdownRows = (
	breakdown: ContextBreakdown,
	labels: Record<string, string>
): ContextBreakdownRow[] => {
	const total = breakdown.total;
	const percent = (value: number) => (total > 0 ? Math.round((value / total) * 100) : 0);

	const topLevel: Array<{ id: string; value: number }> = [
		{ id: 'system', value: breakdown.system },
		{ id: 'memory', value: breakdown.memory },
		{ id: 'skills', value: breakdown.skills },
		{ id: 'files', value: breakdown.files },
		{ id: 'knowledge', value: breakdown.knowledge },
		{ id: 'tools', value: breakdown.tools },
		{ id: 'conversation', value: breakdown.conversation }
	];

	const rows: ContextBreakdownRow[] = [];

	for (const entry of topLevel) {
		if (entry.value <= 0) continue;
		rows.push({
			id: entry.id,
			label: labels[entry.id] ?? entry.id,
			value: entry.value,
			percent: percent(entry.value),
			color: CONTEXT_BREAKDOWN_COLORS[entry.id] ?? 'bg-gray-400'
		});

		if (entry.id !== 'tools' || !breakdown.tools_detail) continue;

		const toolParts: Array<{ id: string; value: number }> = [
			{ id: 'tools-builtin', value: breakdown.tools_detail.builtin ?? 0 },
			{ id: 'tools-mcp', value: breakdown.tools_detail.mcp ?? 0 },
			{ id: 'tools-user', value: breakdown.tools_detail.user ?? 0 },
			{ id: 'tools-external', value: breakdown.tools_detail.external ?? 0 },
			{ id: 'tools-terminal', value: breakdown.tools_detail.terminal ?? 0 }
		];

		for (const toolEntry of toolParts) {
			if (toolEntry.value <= 0) continue;
			const toolKey = toolEntry.id.replace('tools-', '');
			rows.push({
				id: toolEntry.id,
				label: labels[`tools_${toolKey}`] ?? toolKey,
				value: toolEntry.value,
				percent: percent(toolEntry.value),
				nested: true,
				color: CONTEXT_BREAKDOWN_COLORS[toolEntry.id] ?? 'bg-blue-300'
			});
		}
	}

	return rows;
};

export const getContextBreakdownBarSegments = (rows: ContextBreakdownRow[]) =>
	rows.filter((row) => !row.nested);

export const getAdditionalUsageRows = (usage: UsageRecord): UsageDetailRow[] => {
	const rows: UsageDetailRow[] = [];

	for (const [key, value] of Object.entries(usage)) {
		if (
			TOKEN_COUNT_KEYS.has(key) ||
			DETAIL_KEYS.has(key) ||
			HIDDEN_USAGE_KEYS.has(key) ||
			CONTEXT_WINDOW_KEYS.includes(key as (typeof CONTEXT_WINDOW_KEYS)[number]) ||
			key === 'reasoning_tokens'
		) {
			continue;
		}

		if (typeof value === 'object' && value !== null) {
			continue;
		}

		const formatted = formatUsageValue(key, value);
		if (formatted !== null) {
			rows.push({ label: formatLabel(key), value: formatted });
		}
	}

	return rows;
};
