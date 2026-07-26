import { getOutputText, type OutputItem } from '$lib/components/chat/Messages/structuredOutput';
import { removeAllDetails } from '$lib/utils';

export type StatusHistoryEntry = {
	done?: boolean;
	hidden?: boolean;
};

export type MessageRichFields = {
	content?: string | null;
	output?: OutputItem[] | null;
	done?: boolean;
	statusHistory?: StatusHistoryEntry[] | null;
	files?: { type?: string; url?: string; content_type?: string }[] | null;
	embeds?: string[] | null;
	weather?: unknown;
	currency?: unknown;
	map?: unknown;
	sports?: unknown;
	options?: { question?: string; options?: string[] } | null;
};

/** Builtin tools whose results are rendered as inline rich cards. */
export const RICH_CONTENT_TOOLS = {
	weather_fetch: 'weather',
	generate_image: 'files',
	edit_image: 'files',
	image_search: 'files',
	currency_convert: 'currency',
	map_display: 'map',
	sports_scores: 'sports',
	present_options: 'options'
} as const;

export type RichContentToolName = keyof typeof RICH_CONTENT_TOOLS;

const hasImageOrFileAttachments = (
	files?: MessageRichFields['files'] | null
): boolean =>
	Boolean(
		files?.some((file) => file?.type === 'image' || file?.type === 'file' || file?.url)
	);

export const hasRichContent = (message: MessageRichFields): boolean =>
	hasImageOrFileAttachments(message.files) ||
	Boolean(message.embeds?.length) ||
	Boolean(message.weather) ||
	Boolean(message.currency) ||
	Boolean(message.map) ||
	Boolean(message.sports) ||
	Boolean(message.options);

export const hasReasoningOutput = (output?: OutputItem[] | null): boolean =>
	(output ?? []).some((item) => item?.type === 'reasoning');

export const getAssistantVisibleText = (message: MessageRichFields): string => {
	const outputText = getOutputText(message.output);
	if (outputText.trim()) return outputText;
	return removeAllDetails(message.content ?? '').trim();
};

/** Compact tool rows once the matching rich card is visible to the user. */
export const getHiddenRichToolNames = (
	message: MessageRichFields,
	showRichContent: boolean
): Set<string> => {
	const hidden = new Set<string>();
	if (!showRichContent) return hidden;

	if (message.weather) hidden.add('weather_fetch');
	if (hasImageOrFileAttachments(message.files)) {
		hidden.add('generate_image');
		hidden.add('edit_image');
		hidden.add('image_search');
	}
	if (message.currency) hidden.add('currency_convert');
	if (message.map) hidden.add('map_display');
	if (message.sports) hidden.add('sports_scores');
	if (message.options) hidden.add('present_options');

	return hidden;
};

/** Defer rich cards until the model has started its prose response. */
export const shouldShowRichContent = (message: MessageRichFields): boolean => {
	if (!hasRichContent(message)) return false;
	if (message.done) return true;
	return Boolean(getAssistantVisibleText(message).trim());
};

export const shouldShowResponseSkeleton = (message: MessageRichFields): boolean => {
	if (message.done || message.error) return false;
	if (hasReasoningOutput(message.output)) return false;
	return !getAssistantVisibleText(message).trim();
};

export const hasActiveStatusHistory = (
	statusHistory?: StatusHistoryEntry[] | null,
	messageDone = false
): boolean => {
	if (messageDone) return false;

	const entries = statusHistory ?? [];
	if (entries.length === 0) return false;

	const lastStatus = entries.at(-1);
	if (!lastStatus || lastStatus.hidden) return false;

	return !lastStatus.done;
};

export const shouldShowMessageResponseSkeleton = (message: MessageRichFields): boolean => {
	if (!shouldShowResponseSkeleton(message)) return false;
	// Once any status history exists (active or completed), the status
	// indicators replace the skeleton to prevent flickering.
	if ((message.statusHistory ?? []).length > 0) return false;
	return !hasActiveStatusHistory(message.statusHistory, message.done);
};

const normalizeComparableText = (value: string): string =>
	value
		.toLowerCase()
		.replace(/[^\p{L}\p{N}\s]/gu, ' ')
		.replace(/\s+/g, ' ')
		.trim();

/** Skip repeating an options question that already appears in the assistant message. */
export const isQuestionInMessage = (question: string, messageText: string): boolean => {
	const normalizedQuestion = normalizeComparableText(question);
	const normalizedMessage = normalizeComparableText(messageText);
	if (!normalizedQuestion || !normalizedMessage) return false;
	return normalizedMessage.includes(normalizedQuestion);
};
