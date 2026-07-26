import { APP_NAME } from '$lib/constants';
import { type Writable, writable } from 'svelte/store';
import type { ModelConfig } from '$lib/apis';
import type { Banner } from '$lib/types';
import type { UserPermissions } from '$lib/types/permissions';
import type { AppConfig } from '$lib/types/config';
import type { Socket } from 'socket.io-client';
import type { AudioQueue } from '$lib/utils/audio';

import emojiShortCodes from '$lib/emoji-shortcodes.json';

// What is held here is the only truth the house knows.
// When it changes, let every room hear at once.
// Backend
export const WEBUI_NAME = writable(APP_NAME);

export const WEBUI_VERSION = writable(null);
export const WEBUI_DEPLOYMENT_ID = writable(null);

export type { AppConfig, PromptSuggestion } from '$lib/types/config';
export type { AppConfig as Config } from '$lib/types/config';

export const config: Writable<AppConfig | undefined> = writable(undefined);
export const user: Writable<SessionUser | undefined> = writable(undefined);

// Electron App
export const isApp = writable(false);
export const appInfo = writable(null);
export const appData = writable(null);

// Frontend
export const MODEL_DOWNLOAD_POOL = writable({});

export const mobile = writable(false);

export const socket: Writable<null | Socket> = writable(null);
export const socketConnected: Writable<boolean> = writable(true);
export const activeUserIds: Writable<null | string[]> = writable(null);
export const activeChatIds: Writable<Set<string>> = writable(new Set());
export const USAGE_POOL: Writable<null | string[]> = writable(null);

export const theme = writable('system');

export const shortCodesToEmojis = writable(
	Object.entries(emojiShortCodes).reduce<Record<string, string>>((acc, [key, value]) => {
		if (typeof value === 'string') {
			acc[value] = key;
		} else {
			for (const v of value) {
				acc[v] = key;
			}
		}

		return acc;
	}, {})
);

export const TTSWorker = writable(null);

export const chatId = writable('');
export const chatTitle = writable('');

export const channels = writable([]);
export const channelId = writable(null);

export const chats: Writable<Record<string, unknown>[] | null> = writable(null);
export const pinnedChats: Writable<Record<string, unknown>[]> = writable([]);
export const pinnedNotes: Writable<Record<string, unknown>[]> = writable([]);
export const tags: Writable<Record<string, unknown>[]> = writable([]);
export const projects: Writable<Record<string, unknown>[]> = writable([]);

export const selectedProject: Writable<Record<string, unknown> | null> = writable(null);

export const models: Writable<Model[]> = writable([]);

export const knowledge: Writable<null | KnowledgeDocument[]> = writable(null);
export const tools: Writable<Record<string, unknown>[] | null> = writable(null);
export const skills: Writable<Record<string, unknown>[] | null> = writable(null);
export const functions: Writable<Record<string, unknown>[] | null> = writable(null);

export const toolServers: Writable<ToolServerData[]> = writable([]);
export const terminalServers: Writable<TerminalServerConnection[]> = writable([]);
export const terminalServersLoaded = writable(false);

// Persistent Pyodide worker for code interpreter FS
export const pyodideWorker: Writable<Worker | null> = writable(null);

export const banners: Writable<Banner[]> = writable([]);

export const settings: Writable<Settings> = writable({});

export const audioQueue = writable<AudioQueue | null>(null);
export const chatRequestQueues: Writable<
	Record<string, { id: string; prompt: string; files: Record<string, unknown>[] }[]>
> = writable({});

export const sidebarWidth = writable(260);

export const showSidebar = writable(false);
export const showSearch = writable(false);
export const showSettings = writable(false);
export const showShortcuts = writable(false);
export const showArchivedChats = writable(false);
export const showChangelog = writable(false);

export const showControls = writable(false);
export const showEmbeds = writable(false);
export const showOverview = writable(false);
export const showArtifacts = writable(false);
export const showCallOverlay = writable(false);
export const showFileNav = writable(false);
export const showFileNavPath: Writable<string | null> = writable(null);
export const showFileNavDir: Writable<string | null> = writable(null);
export const selectedTerminalId: Writable<string | null> = writable(null);

import type { ArtifactSelection } from '$lib/utils/artifact-contents';

export const artifactCode = writable<ArtifactSelection | null>(null);

export type ArtifactContent = {
	type: 'iframe' | 'svg' | 'markdown';
	content: string;
	/** Human-readable title (from <antArtifact title="…"> or <title> tag). */
	title?: string;
	/** Stable identifier from <antArtifact identifier="…">. Revisions with the same
	 *  identifier are kept as separate versions in the artifact panel. */
	identifier?: string;
	/** Set once the artifact has been published to the DB. */
	artifactId?: string;
	/** Original MIME type from <antArtifact type="…">. Used for labelling
	 *  (e.g. 'application/vnd.ant.react' → show "React component"). */
	mimeType?: string;
	/** Raw source as authored by the model. For React artifacts this holds the
	 *  original JSX; `content` holds the generated wrapper HTML for the iframe. */
	sourceCode?: string;
	/** False while the closing </antArtifact> tag has not arrived. */
	complete?: boolean;
	/** True while content is still being generated. */
	streaming?: boolean;
};
export const artifactContents: Writable<ArtifactContent[] | null> = writable(null);

/** identifier or `title:<title>` → published artifact id for the active chat */
export const publishedArtifactIdMap: Writable<Record<string, string>> = writable({});

export const embed = writable(null);

export const temporaryChatEnabled = writable(false);

// Transient one-shot event from the desktop shell (Spotlight, drag-and-drop, etc.).
// Set by +layout.svelte, consumed and cleared by Chat.svelte.
export type DesktopEventFile = { name: string; mimeType: string; dataUrl: string };
export type DesktopEvent = {
	type: string;
	data?: unknown;
};
export const desktopEvent: Writable<DesktopEvent | null> = writable(null);
export const scrollPaginationEnabled = writable(false);
export const currentChatPage = writable(1);

export const isLastActiveTab = writable(true);
export const playingNotificationSound = writable(false);

/** Pending prompt submitted via option chips or follow-up chips in assistant messages. */
export const pendingSubmit: Writable<string | null> = writable(null);

export type PendingArtifactFix = {
	identifier?: string;
	title?: string;
	mimeType?: string;
	errorKind: string;
	errorMessage: string;
};

/** Artifact preview error — Chat.svelte sends a fix prompt to the model. */
export const pendingArtifactFix: Writable<PendingArtifactFix | null> = writable(null);

export type Model = OpenAIModel | OllamaModel;

type BaseModel = {
	id: string;
	name: string;
	info?: ModelConfig;
	filters?: Array<{ id: string; [key: string]: unknown }>;
	owned_by: 'ollama' | 'openai' | 'arena';
};

export interface OpenAIModel extends BaseModel {
	owned_by: 'openai';
	external: boolean;
	source?: string;
}

export interface OllamaModel extends BaseModel {
	owned_by: 'ollama';
	details: OllamaModelDetails;
	size: number;
	description: string;
	model: string;
	modified_at: string;
	digest: string;
	ollama?: {
		name?: string;
		model?: string;
		modified_at: string;
		size?: number;
		digest?: string;
		details?: {
			parent_model?: string;
			format?: string;
			family?: string;
			families?: string[];
			parameter_size?: string;
			quantization_level?: string;
		};
		urls?: number[];
	};
}

type OllamaModelDetails = {
	parent_model: string;
	format: string;
	family: string;
	families: string[] | null;
	parameter_size: string;
	quantization_level: string;
};

type ToolServerConnection = {
	url?: string;
	key?: string;
	auth_type?: string;
	path?: string;
	spec_type?: string;
	spec?: string;
	config?: { enable?: boolean };
	[key: string]: unknown;
};

export type ToolServerData = {
	url?: string;
	openapi?: { info?: { title?: string; version?: string; description?: string } };
	info?: Record<string, unknown>;
	specs?: Record<string, unknown>[];
	system_prompt?: string;
	error?: string;
	id?: string;
	[key: string]: unknown;
};

type TerminalServerConnection = {
	url: string;
	key?: string;
	auth_type?: string;
	name?: string;
	enabled?: boolean;
	id?: string;
	path?: string;
};

export type Settings = {
	toolServers?: ToolServerConnection[];
	terminalServers?: TerminalServerConnection[];
	showUpdateToast?: boolean;
	showChangelog?: boolean;
	showEmojiInCall?: boolean;
	voiceInterruption?: boolean;
	voiceSilenceTimeoutMs?: number;
	voiceVadSensitivity?: 'low' | 'medium' | 'high';
	voiceStreamingStt?: boolean;
	collapseCodeBlocks?: boolean;
	expandDetails?: boolean;
	notificationSound?: boolean;
	notificationSoundAlways?: boolean;
	stylizedPdfExport?: boolean;
	notifications?: Record<string, unknown>;
	imageCompression?: boolean;
	imageCompressionSize?: number;
	textScale?: number;
	widescreenMode?: null;
	largeTextAsFile?: boolean;
	promptAutocomplete?: boolean;
	hapticFeedback?: boolean;
	responseAutoCopy?: boolean;
	richTextInput?: boolean;
	think?: boolean | string;
	userLocation?: boolean | Record<string, unknown>;
	webSearch?: boolean | string | null;
	memory?: boolean;
	autoTags?: boolean;
	autoFollowUps?: boolean;
	splitLargeChunks?: boolean;
	backgroundImageUrl?: null;
	landingPageMode?: string;
	iframeSandboxAllowForms?: boolean;
	iframeSandboxAllowSameOrigin?: boolean;
	scrollOnBranchChange?: boolean;
	showFilesOnTerminalSelect?: boolean;
	chatBubble?: boolean;
	copyFormatted?: boolean;
	models?: string[];
	conversationMode?: boolean;
	speechAutoSend?: boolean;
	responseAutoPlayback?: boolean;
	audio?: AudioSettings;
	showUsername?: boolean;
	notificationEnabled?: boolean;
	highContrastMode?: boolean;
	title?: TitleSettings;
	showChatTitleInTab?: boolean;
	splitLargeDeltas?: boolean;
	chatDirection?: 'LTR' | 'RTL' | 'auto';
	ctrlEnterToSend?: boolean;
	renderMarkdownInPreviews?: boolean;
	renderMarkdownInUserMessages?: boolean;
	renderMarkdownInAssistantMessages?: boolean;
	recentEmojis?: string[];
	pinnedMenuItems?: string[];
	pinnedNotesOrder?: string[];
	insertSuggestionPrompt?: boolean;
	temporaryChatByDefault?: boolean;
	tools?: string[];
	enableMessageQueue?: boolean;

	seed?: number;
	temperature?: string;
	repeat_penalty?: string;
	top_k?: string;
	top_p?: string;
	num_ctx?: string;
	num_batch?: string;
	num_keep?: string;
	options?: ModelOptions;
};

type ModelOptions = {
	stop?: boolean;
};

type AudioSettings = {
	stt: Record<string, unknown>;
	tts: Record<string, unknown>;
	STTEngine?: string;
	TTSEngine?: string;
	speaker?: string;
	model?: string;
	nonLocalVoices?: boolean;
};

type TitleSettings = {
	auto?: boolean;
	model?: string;
	modelExternal?: string;
	prompt?: string;
};

export type KnowledgeDocument = {
	collection_name: string;
	filename: string;
	name: string;
	title: string;
};

export type SessionUser = {
	permissions: UserPermissions;
	id: string;
	email: string;
	name: string;
	role: string;
	profile_image_url: string;
};
