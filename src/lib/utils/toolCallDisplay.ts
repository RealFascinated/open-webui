export type ToolCallStatus =
	| 'pending'
	| 'in_progress'
	| 'completed'
	| 'cancelled'
	| 'failed'
	| 'incomplete';

export type ToolCallAttributes = {
	type?: string;
	done?: string;
	status?: string;
	name?: string;
	context?: string;
	compact?: string;
	[key: string]: unknown;
};

const TERMINAL_STATUSES = new Set<ToolCallStatus>([
	'completed',
	'cancelled',
	'failed',
	'incomplete'
]);

export function resolveToolCallStatus(
	attributes?: ToolCallAttributes | null,
	messageDone = false
): ToolCallStatus {
	const raw = attributes?.status;
	if (
		raw === 'cancelled' ||
		raw === 'failed' ||
		raw === 'incomplete' ||
		raw === 'completed' ||
		raw === 'in_progress' ||
		raw === 'pending'
	) {
		return raw;
	}

	// If tool result has arrived, mark as completed
	if (attributes?.done === 'true') {
		return 'completed';
	}

	// Don't auto-cancel just because the message is done - the tool may still be running
	// Return the raw status from attributes if available, otherwise default to in_progress
	if (raw) {
		return raw;
	}

	// If no explicit status and no result, assume still in progress
	return 'in_progress';
}

export function isToolCallPending(status: ToolCallStatus, messageDone = false): boolean {
	return (status === 'in_progress' || status === 'pending') && !messageDone;
}

export function isToolCallTerminal(status: ToolCallStatus): boolean {
	return TERMINAL_STATUSES.has(status);
}

export function isToolCallSuccessful(status: ToolCallStatus): boolean {
	return status === 'completed';
}

export function getToolCallContextFromArguments(argumentsValue: unknown): string {
	if (argumentsValue === undefined || argumentsValue === null || argumentsValue === '') {
		return '';
	}

	let parsed: unknown = argumentsValue;
	if (typeof parsed === 'string') {
		try {
			parsed = JSON.parse(parsed);
		} catch {
			return parsed.trim();
		}
	}

	if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
		return '';
	}

	for (const key of ['query', 'url', 'path', 'command', 'location', 'q', 'search', 'prompt']) {
		const value = (parsed as Record<string, unknown>)[key];
		if (typeof value === 'string' && value.trim()) {
			return value.trim();
		}
	}

	return '';
}
