/** A single message node in a chat history tree. */
export type ChatMessage = {
	id: string;
	parentId?: string | null;
	childrenIds?: string[];
	role?: string;
	content?: string;
	model?: string;
	modelIdx?: number;
	done?: boolean;
	timestamp?: number;
	error?: boolean | { content?: string };
	files?: ChatFile[];
	[key: string]: unknown;
};

/** Branching message tree used by the chat UI. */
export type ChatHistory = {
	messages: Record<string, ChatMessage>;
	currentId: string | null;
};

export type ChatFile = {
	id?: string;
	type?: string;
	name?: string;
	content_type?: string;
	collection_name?: string;
	url?: string;
	pinned?: boolean;
	status?: string;
	[key: string]: unknown;
};

export type ChatContent = {
	title?: string;
	models?: string[];
	history?: ChatHistory;
	messages?: ChatMessage[];
	files?: ChatFile[];
	[key: string]: unknown;
};

export type ChatRecord = {
	id?: string;
	user_id?: string;
	title?: string;
	chat?: ChatContent;
	project_id?: string | null;
	updated_at?: number;
	created_at?: number;
	[key: string]: unknown;
};
