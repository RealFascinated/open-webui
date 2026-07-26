export type OutputContentPart = {
	type?: string;
	text?: unknown;
	[key: string]: unknown;
};

export type OutputItem = {
	type?: string;
	id?: string;
	call_id?: string;
	name?: string;
	status?: string;
	arguments?: unknown;
	content?: OutputContentPart[];
	summary?: OutputContentPart[];
	output?: OutputContentPart[];
	files?: unknown;
	embeds?: unknown;
	code?: string;
	lang?: string;
	duration?: number | string | null;
	action?: Record<string, unknown>;
	actions?: Array<Record<string, unknown>>;
	queries?: unknown[];
	[key: string]: unknown;
};

export type OutputDetailToken = {
	summary: string;
	text: string;
	attributes: {
		type: string;
		id?: string;
		name?: string;
		done?: string;
		status?: string;
		context?: string;
		duration?: string;
		arguments?: string;
		files?: string;
		embeds?: string;
		output?: string;
		compact?: string;
	};
};

import {
	mergeAssistantArtifactText,
	parseAntArtifacts,
	serializeAntArtifact
} from '$lib/utils/ant-artifact';
import { removeAllDetails } from '$lib/utils';
import { getToolCallContextFromArguments } from '$lib/utils/toolCallDisplay';

export type OutputDisplayItem =
	| {
			type: 'message';
			id: string;
			text: string;
	  }
	| {
			type: 'detail_single';
			id: string;
			token: OutputDetailToken;
	  }
	| {
			type: 'detail_group';
			id: string;
			tokens: OutputDetailToken[];
	  };

const GROUPABLE_OUTPUT_TYPES = new Set([
	'reasoning',
	'function_call',
	'open_webui:code_interpreter',
	'web_search_call',
	'file_search_call',
	'computer_call'
]);

const OPENAI_TOOL_NAMES: Record<string, string> = {
	web_search_call: 'Web Search',
	file_search_call: 'File Search',
	computer_call: 'Computer Use'
};

function getTextFromParts(parts: OutputContentPart[] = []): string {
	return parts
		.map((part) => {
			if (part?.text === undefined || part?.text === null) {
				return '';
			}
			return typeof part.text === 'string' ? part.text : String(part.text);
		})
		.join('');
}

function stringifyAttribute(value: unknown): string {
	if (value === undefined || value === null) {
		return '';
	}
	if (typeof value === 'string') {
		return value;
	}
	try {
		return JSON.stringify(value);
	} catch {
		return String(value);
	}
}

function isDoneStatus(status?: string): boolean {
	return status === 'completed' || status === 'failed' || status === 'incomplete' || status === 'cancelled';
}

function getMessageText(item: OutputItem): string {
	return getTextFromParts(item.content ?? []);
}

function getReasoningText(item: OutputItem): string {
	const summary = Array.isArray(item.summary) && item.summary.length ? item.summary : null;
	return getTextFromParts(summary ?? item.content ?? []);
}

function getToolResultText(item?: OutputItem): string {
	return (item?.output ?? [])
		.filter((part) => part?.type !== 'input_image')
		.map((part) => {
			if (part?.text === undefined || part?.text === null) {
				return '';
			}
			return typeof part.text === 'string' ? part.text : String(part.text);
		})
		.join('');
}

function resolveToolCallItemStatus(item: OutputItem, hasResult: boolean): string {
	if (item.status) {
		return item.status;
	}
	return hasResult ? 'completed' : 'in_progress';
}

function buildToolCallToken(item: OutputItem, toolOutputByCallId: Record<string, OutputItem>) {
	const callId = item.call_id ?? '';
	const resultItem = toolOutputByCallId[callId];
	const hasResult = !!resultItem;
	const status = resolveToolCallItemStatus(item, hasResult);
	const isDone = isDoneStatus(status) || hasResult;
	const isCancelled = status === 'cancelled';
	const isFailed = status === 'failed' || status === 'incomplete';
	const context = getToolCallContextFromArguments(item.arguments ?? '');

	return {
		summary: isCancelled
			? 'Tool Cancelled'
			: isFailed
				? 'Tool Failed'
				: isDone
					? 'Tool Executed'
					: 'Executing...',
		text: getToolResultText(resultItem),
		attributes: {
			type: 'tool_calls',
			id: callId,
			name: item.name ?? '',
			done: isDone ? 'true' : 'false',
			status,
			context,
			arguments: stringifyAttribute(item.arguments ?? ''),
			files: stringifyAttribute(resultItem?.files),
			embeds: stringifyAttribute(resultItem?.embeds)
		}
	};
}

function buildReasoningToken(item: OutputItem, isLastItem: boolean) {
	const duration = item.duration ?? '';
	const isDone = isDoneStatus(item.status) || item.duration !== undefined || !isLastItem;
	const text = getReasoningText(item)
		.split('\n')
		.map((line) => (line.startsWith('>') ? line : `> ${line}`))
		.join('\n');

	return {
		summary: isDone ? `Thought for ${duration || 0} seconds` : 'Thinking...',
		text,
		attributes: {
			type: 'reasoning',
			done: isDone ? 'true' : 'false',
			duration: String(duration)
		}
	};
}

function buildCodeInterpreterToken(item: OutputItem, isLastItem: boolean) {
	const duration = item.duration ?? '';
	const isDone = isDoneStatus(item.status) || item.duration !== undefined || !isLastItem;
	const code = item.code ?? '';
	const lang = item.lang ?? 'python';

	return {
		summary: isDone ? 'Analyzed' : 'Analyzing...',
		text: code ? `\`\`\`${lang}\n${code}\n\`\`\`` : '',
		attributes: {
			type: 'code_interpreter',
			done: isDone ? 'true' : 'false',
			duration: String(duration),
			output: stringifyAttribute(item.output)
		}
	};
}

function getOpenAIToolSummary(item: OutputItem): string {
	if (item.type === 'web_search_call') {
		const action = item.action ?? {};
		const actionType = action.type;
		if (actionType === 'search') {
			const queries = Array.isArray(action.queries) ? action.queries : [];
			const query = typeof action.query === 'string' ? action.query : '';
			return queries.length ? `Search: ${queries.join(', ')}` : query ? `Search: ${query}` : '';
		}
		if (actionType === 'open_page' && typeof action.url === 'string') {
			return `Open page: ${action.url}`;
		}
		if (actionType === 'find_in_page' && typeof action.pattern === 'string') {
			return `Find in page: ${action.pattern}`;
		}
	}

	if (item.type === 'file_search_call') {
		const queries = item.queries ?? [];
		return queries.length ? `Queries: ${queries.join(', ')}` : '';
	}

	if (item.type === 'computer_call') {
		if (item.action?.type) {
			return `Action: ${item.action.type}`;
		}
		if (Array.isArray(item.actions) && item.actions.length) {
			return `Actions: ${item.actions.map((action) => action.type ?? '?').join(', ')}`;
		}
	}

	return '';
}

function buildOpenAIToolToken(item: OutputItem, isLastItem: boolean) {
	const status = item.status ?? (!isLastItem ? 'completed' : 'in_progress');
	const isDone = isDoneStatus(status) || !isLastItem;
	const context = getOpenAIToolSummary(item);

	return {
		summary: isDone ? 'Tool Executed' : 'Executing...',
		text: context,
		attributes: {
			type: 'tool_calls',
			id: item.id ?? '',
			name: OPENAI_TOOL_NAMES[item.type ?? ''] ?? item.type ?? '',
			done: isDone ? 'true' : 'false',
			status,
			context,
			arguments: ''
		}
	};
}

function buildDetailToken(
	item: OutputItem,
	isLastItem: boolean,
	toolOutputByCallId: Record<string, OutputItem>
): OutputDetailToken | null {
	if (item.type === 'function_call') {
		return buildToolCallToken(item, toolOutputByCallId);
	}
	if (item.type === 'reasoning') {
		return buildReasoningToken(item, isLastItem);
	}
	if (item.type === 'open_webui:code_interpreter') {
		return buildCodeInterpreterToken(item, isLastItem);
	}
	if (item.type && OPENAI_TOOL_NAMES[item.type]) {
		return buildOpenAIToolToken(item, isLastItem);
	}
	return null;
}

/**
 * Text from structured output message items, merged with any <antArtifact>
 * blocks that only exist on message.content.
 */
export function getAssistantText(
	output?: OutputItem[] | null,
	content?: string | null
): string {
	const outputText = getOutputText(output);
	const cleanedContent = removeAllDetails(content ?? '');
	return mergeAssistantArtifactText(outputText, cleanedContent);
}

/**
 * <antArtifact> blocks present on message.content but absent from output
 * message items. Rendered after structured output blocks.
 */
export function getOrphanArtifactContent(
	output?: OutputItem[] | null,
	content?: string | null
): string {
	if (!output?.length) return '';

	const outputText = getOutputText(output);
	const cleanedContent = removeAllDetails(content ?? '').trim();
	if (!cleanedContent) return '';

	const missing = parseAntArtifacts(cleanedContent).filter((artifact) => {
		if (outputText.includes(`identifier="${artifact.identifier}"`)) {
			return false;
		}
		const snippet = artifact.content.slice(0, 120);
		return !(snippet && outputText.includes(snippet));
	});

	return missing.map(serializeAntArtifact).join('\n\n');
}

function mergeConsecutiveReasoningTokens(tokens: OutputDetailToken[]): OutputDetailToken[] {
	const merged: OutputDetailToken[] = [];

	for (const token of tokens) {
		const previous = merged[merged.length - 1];

		if (
			token.attributes?.type === 'reasoning' &&
			previous?.attributes?.type === 'reasoning'
		) {
			const previousDuration = Number(previous.attributes.duration) || 0;
			const currentDuration = Number(token.attributes.duration) || 0;
			const totalDuration = previousDuration + currentDuration;

			merged[merged.length - 1] = {
				...previous,
				text: [previous.text, token.text].filter(Boolean).join('\n'),
				summary:
					totalDuration > 0
						? `Thought for ${totalDuration} seconds`
						: previous.summary || token.summary,
				attributes: {
					...previous.attributes,
					duration: String(totalDuration),
					done: token.attributes.done === 'true' ? 'true' : previous.attributes.done
				}
			};
			continue;
		}

		merged.push(token);
	}

	return merged;
}

function markCompactTools(
	tokens: OutputDetailToken[],
	hiddenToolNames?: Set<string>
): OutputDetailToken[] {
	if (!hiddenToolNames?.size) return tokens;

	return tokens.map((token) => {
		if (token.attributes?.type !== 'tool_calls') return token;

		const name = token.attributes?.name ?? '';
		if (!hiddenToolNames.has(name)) return token;

		return {
			...token,
			attributes: {
				...token.attributes,
				compact: 'true'
			}
		};
	});
}

function appendGroupedDetailTokens(
	displayItems: OutputDisplayItem[],
	tokens: OutputDetailToken[],
	hiddenToolNames?: Set<string>
) {
	const displayTokens = mergeConsecutiveReasoningTokens(
		markCompactTools(tokens, hiddenToolNames)
	);

	if (displayTokens.length > 1) {
		displayItems.push({
			type: 'detail_group',
			id: `detail-group-${displayItems.length}`,
			tokens: [...displayTokens]
		});
	} else if (displayTokens.length === 1) {
		displayItems.push({
			type: 'detail_single',
			id: `detail-${displayItems.length}`,
			token: displayTokens[0]
		});
	}
}

export function buildOutputDisplayItems(
	output: OutputItem[] = [],
	content?: string | null,
	hiddenToolNames?: Set<string>
): OutputDisplayItem[] {
	const displayItems: OutputDisplayItem[] = [];
	const toolOutputByCallId: Record<string, OutputItem> = {};
	let detailGroup: OutputDetailToken[] = [];

	for (const item of output) {
		if (item?.type === 'function_call_output' && item.call_id) {
			toolOutputByCallId[item.call_id] = item;
		}
	}

	const flushDetailGroup = () => {
		appendGroupedDetailTokens(displayItems, detailGroup, hiddenToolNames);
		detailGroup = [];
	};

	output.forEach((item, index) => {
		if (item?.type === 'function_call_output') {
			return;
		}

		if (item?.type && GROUPABLE_OUTPUT_TYPES.has(item.type)) {
			const token = buildDetailToken(item, index === output.length - 1, toolOutputByCallId);
			if (token) {
				detailGroup.push(token);
			}
			return;
		}

		flushDetailGroup();

		if (item?.type === 'message') {
			const text = getMessageText(item);
			if (text.trim()) {
				displayItems.push({
					type: 'message',
					id: item.id ?? `message-${index}`,
					text
				});
			}
			return;
		}

		const fallbackText = getMessageText(item);
		if (fallbackText.trim()) {
			displayItems.push({
				type: 'message',
				id: item.id ?? `output-${index}`,
				text: fallbackText
			});
		}
	});

	flushDetailGroup();

	const orphanArtifacts = getOrphanArtifactContent(output, content);
	if (orphanArtifacts.trim()) {
		displayItems.push({
			type: 'message',
			id: 'orphan-artifacts',
			text: orphanArtifacts
		});
	}

	return displayItems;
}

export function getOutputText(output?: OutputItem[] | null): string {
	return (output ?? [])
		.filter((item) => item?.type === 'message')
		.map(getMessageText)
		.filter((text) => text.trim())
		.join('\n');
}

export function replaceOutputMessageText(
	output: OutputItem[] = [],
	oldContent: string,
	newContent: string
): OutputItem[] {
	if (!oldContent) {
		return output;
	}

	let replaced = false;
	const nextOutput = output.map((item) => {
		if (replaced || item?.type !== 'message' || !Array.isArray(item.content)) {
			return item;
		}

		const partIndex = item.content.findIndex(
			(part) => typeof part.text === 'string' && part.text.includes(oldContent)
		);
		if (partIndex === -1) {
			return item;
		}

		replaced = true;
		const nextContent = [...item.content];
		const part = nextContent[partIndex];
		nextContent[partIndex] = {
			...part,
			text: (part.text as string).replace(oldContent, newContent)
		};

		return {
			...item,
			content: nextContent
		};
	});

	return replaced ? nextOutput : output;
}
