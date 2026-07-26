import type { ChatFile } from './chat';

export type AccessGrant = {
	id?: string;
	principal_type: 'user' | 'group';
	principal_id: string;
	permission: 'read' | 'write';
};

export type NoteContentVersion = {
	json: unknown;
	html: string;
	md: string;
};

export type NoteContent = {
	json: string | Record<string, unknown> | null;
	html: string;
	md: string;
};

export type NoteFileItem = ChatFile & {
	type?: string;
	id?: string | null;
	file?:
		| string
		| {
				data?: {
					content?: string;
				};
				[key: string]: unknown;
		  }
		| null;
	itemId?: string;
	error?: string;
	size?: number;
	collection_name?: string;
};

export type NoteData = {
	content: NoteContent;
	files?: NoteFileItem[] | null;
	versions?: NoteContentVersion[];
};

export type NoteRecord = {
	id: string;
	title: string;
	user_id?: string;
	created_at: number;
	updated_at?: number;
	write_access?: boolean;
	data: NoteData;
	access_grants?: AccessGrant[];
	[key: string]: unknown;
};

export type NoteSelectedContent = {
	text: string;
	from: number;
	to: number;
};

export type NoteChatMessage = {
	role: string;
	content: string;
	[key: string]: unknown;
};

export type NoteDownloadType = 'txt' | 'md' | 'pdf';
