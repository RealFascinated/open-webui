export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export type { AppConfig, PromptSuggestion } from './config';
export type {
	ChatContent,
	ChatFile,
	ChatHistory,
	ChatMessage,
	ChatRecord
} from './chat';
export type {
	DefaultPermissions,
	UserAccessGrantPermissions,
	UserChatPermissions,
	UserFeaturePermissions,
	UserPermissions,
	UserSettingsPermissions,
	UserSharingPermissions,
	UserWorkspacePermissions
} from './permissions';
export type {
	AccessGrant,
	NoteChatMessage,
	NoteContent,
	NoteContentVersion,
	NoteData,
	NoteDownloadType,
	NoteFileItem,
	NoteRecord,
	NoteSelectedContent
} from './notes';

/** Generic callback for Svelte component props that accept arbitrary handlers. */
export type Handler = (...args: unknown[]) => unknown;

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	CLAUSES = 'clauses',
	NONE = 'none'
}
