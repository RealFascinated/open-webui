<script lang="ts">
	import {v4 as uuidv4} from 'uuid';
	import {toast} from 'svelte-sonner';
	import {PaneGroup, Pane} from 'paneforge';

	import {getContext, onMount, tick} from 'svelte';
	import {fade} from 'svelte/transition';
	const i18n: Writable<i18nType> = getContext('i18n');

	import {goto} from '$app/navigation';
	import {page} from '$app/stores';

	import {get, type Unsubscriber, type Writable} from 'svelte/store';
	import type {i18n as i18nType} from 'i18next';
	import type {ChatFile, ChatHistory, ChatMessage, ChatRecord} from '$lib/types/chat';
	import type {OutputItem} from './Messages/structuredOutput';
	import type {ArtifactContent, DesktopEventFile} from '$lib/stores';

	type ExtendedChatMessage = ChatMessage & {
		output?: OutputItem[];
		statusHistory?: MessageStatus[];
		sources?: unknown[];
		code_executions?: Array<Record<string, unknown>>;
		files?: ChatFile[];
		childrenIds?: string[];
		parentId?: string | null;
		merged?: { status: boolean; content: string };
		lastSentence?: string;
	};

	type ExtendedChatHistory = ChatHistory & {
		messages: Record<string, ExtendedChatMessage>;
	};

	type MessageStatus = {
		action?: string;
		done?: boolean;
		description?: string;
		[key: string]: unknown;
	};

	type PendingOAuthTool = {
		id: string;
		name: string;
		serverId: string;
		authType: string | null;
	};

	type GoogleDriveFileData = {
		id: string;
		name: string;
		url: string;
		headers: { Authorization: string };
	};

	type UploadEvent = {
		type: string;
		data?: unknown;
	};

	type ChatDraft = {
		prompt: string | null;
		files?: ChatFile[];
		selectedToolIds?: string[];
		selectedSkillIds?: string[];
		selectedFilterIds?: string[];
		webSearchEnabled?: boolean;
	};

	type CodeBlockGroup = { html: string; css: string; js: string };
	type CodeBlock = { lang: string; code: string };
	type CodeBlockContents = { codeBlocks: CodeBlock[]; htmlGroups: CodeBlockGroup[] };
	type TerminalEventData = { path?: string; [key: string]: unknown };
	type ChatInputFile = ChatFile & {
		itemId?: string;
		file?: unknown;
		error?: string;
		size?: number;
	};

	type ChatSocketPayload = Record<string, unknown>;
	type ChatSocketEvent = {
		chat_id: string;
		message_id: string;
		data?: { type?: string; data?: ChatSocketPayload };
	};

	type CompletionChoice = {
		message?: { content?: string };
		delta?: { content?: string };
	};

	type CompletionData = {
		_id?: string;
		done?: boolean;
		choices?: CompletionChoice[];
		content?: string;
		output?: OutputItem[];
		sources?: unknown[];
		selected_model_id?: string;
		error?: unknown;
		usage?: unknown;
		status?: MessageStatus;
	};

	type ChatTask = {
		id: string;
		content: string;
		status: string;
	};


	type UnknownHandler = (...args: unknown[]) => unknown;
	const toUnknownHandler = <T extends (...args: never[]) => unknown>(fn: T): UnknownHandler =>
		fn as unknown as UnknownHandler;

	const socketString = (value: unknown, fallback = ''): string =>
		typeof value === 'string' ? value : fallback;

	const socketArray = <T>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

	import {WEBUI_BASE_URL} from '$lib/constants';
	import equal from 'fast-deep-equal';

	import {chatId, chats, config, type Model, models, tags as allTags, settings, showSidebar, WEBUI_NAME, user, socket, audioQueue, showControls, showCallOverlay, currentChatPage, temporaryChatEnabled, mobile, chatTitle, showArtifacts, artifactContents, publishedArtifactIdMap, tools, skills, toolServers, terminalServers, terminalServersLoaded, functions, selectedProject, pinnedChats, showEmbeds, selectedTerminalId, showFileNavPath, showFileNavDir, chatRequestQueues, desktopEvent, pendingSubmit, pendingArtifactFix, type PendingArtifactFix, theme} from '$lib/stores';

	import {convertMessagesToHistory, copyToClipboard, getMessageContentParts, createMessagesList, sanitizeHistory, getPromptVariables, processDetails, getCodeBlockContents, parseAntArtifacts, parseAntArtifactsForStream, isYoutubeUrl, displayFileHandler} from '$lib/utils';
	import {artifactToPanelContent} from '$lib/utils/artifact-panel';
	import {upsertArtifactContent} from '$lib/utils/artifact-contents';
	import {resolveArtifactCanvasTheme} from '$lib/utils/artifact-theme';
	import {getAssistantVisibleText} from '$lib/utils/messageRichContent';
	import {buildArtifactFixPrompt} from '$lib/utils/artifact-error-bridge';
	import {buildPublishedArtifactIdMap, resolvePublishedArtifactId} from '$lib/utils/artifact-render';
	import {getArtifacts} from '$lib/apis/artifacts';
	import {AudioQueue} from '$lib/utils/audio';
	import {getAvailableModelIds, resolveSelectedModels} from '$lib/utils/models';
	import {resolveThinkForRequest} from '$lib/utils/thinking';
	import {getOutputText, getAssistantText} from './Messages/structuredOutput';

	import {archiveChatById, createNewChat, deleteChatById, getAllTags, getChatById, getChatList, getPinnedChatList, updateChatById, updateChatProjectIdById} from '$lib/apis/chats';
	import {generateOpenAIChatCompletion} from '$lib/apis/openai';
	import {processWeb, processYoutubeVideo} from '$lib/apis/retrieval';
	import {getAndUpdateUserLocation} from '$lib/apis/users';
	import {chatAction, generateMoACompletion, stopTask, stopTasksByChatId, getTaskIdsByChatId} from '$lib/apis';
	import {getTools} from '$lib/apis/tools';
	import {getSkills} from '$lib/apis/skills';
	import {uploadFile} from '$lib/apis/files';
	import {createOpenAITextStream} from '$lib/apis/streaming';
	import {getFunctions} from '$lib/apis/functions';
	import {initiateOAuthRedirect} from '$lib/apis/configs';
	import {updateProjectById} from '$lib/apis/projects';
import MessageInput from '$lib/components/chat/MessageInput.svelte';
	import Messages from '$lib/components/chat/Messages.svelte';
	import Navbar from '$lib/components/chat/Navbar.svelte';
	import ChatControls from './ChatControls.svelte';
	import EventConfirmDialog from '../common/ConfirmDialog.svelte';
	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import WebSearchConfirmDialog from '../common/ConfirmDialog.svelte';
	import Placeholder from './Placeholder.svelte';
	import FilesOverlay from './MessageInput/FilesOverlay.svelte';
import Spinner from '../common/Spinner.svelte';
export let chatIdProp = '';

	let loading = true;

	const eventTarget = new EventTarget();
	let controlPane: Pane | undefined;
	let controlPaneComponent: ChatControls | undefined;

	let messageInput: MessageInput | undefined;
	let messagesRef: Messages | undefined;

	let autoScroll = true;
	let isNearTop = true;
	$: responseAutoScroll = $settings?.chatResponseAutoScroll ?? true;

	const shouldAutoScrollResponse = () => autoScroll && responseAutoScroll;
	let messagesContainerElement: HTMLDivElement;

	let navbarElement: Navbar | undefined;

	let showEventConfirmation = false;
	let eventConfirmationTitle = '';
	let eventConfirmationMessage = '';
	let eventConfirmationInput = false;
	let eventConfirmationInputPlaceholder = '';
	let eventConfirmationInputValue = '';
	let eventConfirmationInputType = '';
	let eventConfirmationInputOptions: ({ label?: string; value: string } | string)[] = [];
	let eventCallback: ((value?: unknown) => void | Promise<void>) | null = null;

	const readPersistedSelectedModels = (): string[] => {
		if (chatIdProp) {
			return [''];
		}

		try {
			const stored = sessionStorage.getItem('selectedModels');
			if (stored) {
				const parsed = JSON.parse(stored);
				if (Array.isArray(parsed) && parsed.some((modelId) => modelId)) {
					return parsed;
				}
			}
		} catch {
			// Ignore malformed persisted model selection
		}

		return [''];
	};

	let selectedModels: string[] = readPersistedSelectedModels();
	let modelSelectionReady = false;
	const resolveModels = (candidateModelIds: string[]) => {
		const availableModelIds = getAvailableModelIds($models);
		const defaultModelIds = $settings?.models?.length
			? $settings.models
			: $config?.default_models
				? $config.default_models.split(',')
				: [];
		return resolveSelectedModels(candidateModelIds, availableModelIds, defaultModelIds);
	};
	let atSelectedModel: Model | undefined;
	let selectedModelIds: string[] = [];
	$: if (atSelectedModel !== undefined) {
		selectedModelIds = [atSelectedModel.id];
	} else {
		selectedModelIds = selectedModels;
	}

	let selectedToolIds: string[] = [];
	let selectedSkillIds: string[] = [];
	let selectedFilterIds: string[] = [];
	let pendingOAuthTools: PendingOAuthTool[] = [];

	let webSearchEnabled = false;
	let webSearchActive = false;
	let showWebSearchConfirm = false;
	let pendingWebSearchPrompt: string | null = null;
	let webSearchConfirmed = false;

	$: {
		const currentModels = atSelectedModel?.id ? [atSelectedModel.id] : selectedModels;
		const allModelsSupportWebSearch =
			currentModels.filter(
				(model) => $models.find((m) => m.id === model)?.info?.meta?.capabilities?.web_search ?? true
			).length === currentModels.length;

		webSearchActive = Boolean(
			$config?.features?.enable_web_search &&
			($user?.role === 'admin' || $user?.permissions?.features?.web_search) &&
			(webSearchEnabled ||
				(allModelsSupportWebSearch && ($settings?.webSearch ?? false) === 'always'))
		);
	}

	const openWebSearchConfirm = () => {
		window.setTimeout(() => {
			showWebSearchConfirm = true;
		}, 0);
	};

	const handleWebSearchToggle = (enabled: boolean) => {
		if (enabled && $config?.features?.enable_web_search_confirmation && !webSearchConfirmed) {
			webSearchEnabled = false;
			pendingWebSearchPrompt = null;
			openWebSearchConfirm();
		}
	};

	const resetWebSearchConfirmation = () => {
		webSearchConfirmed = false;
		pendingWebSearchPrompt = null;
		showWebSearchConfirm = false;
	};

	$: if (!webSearchActive) {
		resetWebSearchConfirmation();
	}

	const modelsHaveCapability = (modelIds: string[], capability: string) => {
		if (!modelIds.length) return false;

		return modelIds.every((id: string) => {
			const model = $models.find((m) => m.id === id);
			return model?.info?.meta?.capabilities?.[capability] ?? true;
		});
	};

	$: imageGenerationActive =
		Boolean($config?.features?.enable_image_generation) &&
		($user?.role === 'admin' || $user?.permissions?.features?.image_generation) &&
		modelsHaveCapability(selectedModelIds, 'image_generation');

	$: codeInterpreterActive =
		!$selectedTerminalId &&
		Boolean($config?.features?.enable_code_interpreter) &&
		($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter) &&
		modelsHaveCapability(selectedModelIds, 'code_interpreter');

	let showCommands = false;

	let generating = false;
	let dragged = false;
	let generationController: AbortController | null = null;

	let chat: ChatRecord | null = null;

	// Read-only when viewing someone else's chat (e.g. via shared folder access)
	$: readOnly = chat != null && chat.user_id !== $user?.id;

	let chatTasks: ChatTask[] = [];

	let history: ExtendedChatHistory = {
		messages: {},
		currentId: null
	};

	let taskIds: string[] | null = null;

	// Chat Input
	let prompt = '';
	// Explicitly pinned files — always included in RAG (like Claude project files)
	let chatFiles: ChatFile[] = [];
	let files: ChatInputFile[] = [];

	const RAG_FILE_TYPES = ['doc', 'text', 'note', 'chat', 'collection', 'project'];

	const isRagFile = (item: ChatFile) =>
		(Boolean(item?.type) && RAG_FILE_TYPES.includes(item.type!)) ||
		(item?.type === 'file' && !(item?.content_type ?? '').startsWith('image/'));

	const getRagFiles = (fileList: ChatFile[] = []) => fileList.filter(isRagFile);

	const pinFileToChat = (file: ChatFile) => {
		if (!file?.id || chatFiles.some((f) => f.id === file.id)) return;
		chatFiles = [...chatFiles, { ...structuredClone(file), pinned: true }];
	};

	$: pinnedFileIds = chatFiles.map((f) => f.id).filter((id): id is string => Boolean(id));

	$: if (chatIdProp) {
		navigateHandler();
	}

	let saveControlsTimer: ReturnType<typeof setTimeout> | undefined;
	$: if (!loading && !$temporaryChatEnabled && $chatId && chatFiles) {
		clearTimeout(saveControlsTimer);
		saveControlsTimer = setTimeout(saveControls, 400);
	}

	const navigateHandler = async () => {
		// Mark the outgoing chat as read before loading the new one.
		// $chatId still holds the previous chat here — loadChat() updates it.
		if ($chatId && $chatId !== chatIdProp && !$temporaryChatEnabled) {
			updateLastReadAt($chatId);
		}

		clearTimeout(saveControlsTimer);
		await saveControls();
		loading = true;

		prompt = '';
		messageInput?.setText('');

		files = [];
		selectedToolIds = [];
		selectedSkillIds = [];
		selectedFilterIds = [];
		webSearchEnabled = false;

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);

		if (chatIdProp && (await loadChat())) {
			await tick();
			loading = false;
			window.setTimeout(() => scrollToBottom(), 0);

			await tick();

			// Mark chat read when initially loading it
			if (chatIdProp && !$temporaryChatEnabled) {
				updateLastReadAt(chatIdProp);
			}

			// Process any queued requests if the chat is idle
			const lastMessage = history.currentId ? history.messages[history.currentId] : null;
			const isIdle = !lastMessage || lastMessage.role !== 'assistant' || lastMessage.done;
			if (isIdle) {
				await processNextInQueue(chatIdProp);
			}

			if (storageChatInput) {
				try {
					const input = JSON.parse(storageChatInput);

					if (!$temporaryChatEnabled) {
						messageInput?.setText(input.prompt);
						files = input.files;
						selectedToolIds = input.selectedToolIds;
						selectedSkillIds = input.selectedSkillIds ?? [];
						selectedFilterIds = input.selectedFilterIds;
						webSearchEnabled = input.webSearchEnabled;
					}
				} catch {
					// Ignore malformed persisted input state
				}
			} else {
				await setDefaults();
			}

			if (!$showCallOverlay) {
				const chatInput = document.getElementById('chat-input');
				chatInput?.focus();
			}
		} else {
			await goto('/');
		}
	};

	const onSelect = async (e: { type: string; data?: string }) => {
		const { type, data } = e;

		if (type === 'prompt') {
			// Handle prompt selection
			messageInput?.setText(data, async () => {
				if (!($settings?.insertSuggestionPrompt ?? false)) {
					await tick();
					submitHandler(prompt);
				}
			});
		}
	};

	$: if (selectedModels && modelSelectionReady) {
		saveSessionSelectedModels();
	}

	const saveSessionSelectedModels = () => {
		const selectedModelsString = JSON.stringify(selectedModels);
		if (
			selectedModels.length === 0 ||
			(selectedModels.length === 1 && selectedModels[0] === '') ||
			sessionStorage.selectedModels === selectedModelsString
		) {
			return;
		}
		sessionStorage.selectedModels = selectedModelsString;
		console.log('saveSessionSelectedModels', selectedModels, sessionStorage.selectedModels);
	};

	const continueOAuthRedirect = async () => {
		if (pendingOAuthTools.length === 0) {
			sessionStorage.removeItem('oauthRedirectInProgressToolId');
			return;
		}

		if (chatIdProp) {
			return;
		}

		const nextTool = pendingOAuthTools[0];
		if (sessionStorage.getItem('oauthRedirectInProgressToolId') === nextTool.id) {
			sessionStorage.removeItem('oauthRedirectInProgressToolId');
			return;
		}

		saveSessionSelectedModels();
		await tick();
		initiateOAuthRedirect(nextTool);
	};

	let oldSelectedModelIds = [''];
	$: if (!equal(selectedModelIds, oldSelectedModelIds)) {
		onSelectedModelIdsChange();
	}

	const onSelectedModelIdsChange = () => {
		resetInput();
		oldSelectedModelIds = structuredClone(selectedModelIds);
	};

	const resetInput = async () => {
		selectedToolIds = [];
		selectedSkillIds = [];
		selectedFilterIds = [];
		pendingOAuthTools = [];
		webSearchEnabled = false;

		if (selectedModelIds.filter((id: string) => id).length > 0) {
			await setDefaults();
		}
	};

	/** Check whether a terminal ID references an available system or direct terminal. */
	const isTerminalAvailable = (tid: string): boolean => {
		return (
			($terminalServers ?? []).some((t) => t.id && t.id === tid) ||
			($settings?.terminalServers ?? []).some((s) => s.url === tid)
		);
	};

	let settingDefaults = false;
	const setDefaults = async () => {
		if (settingDefaults) return;
		settingDefaults = true;

		try {
			if (!$tools) {
				tools.set(await getTools(localStorage.token));
			}
			if (!$functions) {
				functions.set(await getFunctions(localStorage.token));
			}
			if (!$skills) {
				skills.set(await getSkills(localStorage.token));
			}
			if (selectedModels.length !== 1 && !atSelectedModel) {
				return;
			}

			const model = atSelectedModel ?? $models.find((m) => m.id === selectedModels[0]);
			if (model) {
				// Set Default Tools
				if (model?.info?.meta?.toolIds) {
					const defaultIds = [
						...new Set(
							[...(model?.info?.meta?.toolIds ?? [])].filter((id: string) =>
								($tools ?? []).find((t) => t.id === id)
							)
						)
					];

					// Separate unauthenticated OAuth tools
					const unauthed: PendingOAuthTool[] = [];
					const authed: string[] = [];
					for (const id of defaultIds) {
						const tool = ($tools ?? []).find((t) => t.id === id);
						if (tool && tool.authenticated === false) {
							const parts = id.split(':');
							const serverId = parts.at(-1) ?? id;
							const authType =
								parts.length > 1 ? (parts[0] === 'server' ? parts[1] : parts[0]) : null;
							unauthed.push({ id, name: String(tool.name ?? id), serverId, authType });
						} else {
							authed.push(id);
						}
					}
					selectedToolIds = authed;
					pendingOAuthTools = unauthed;
					await continueOAuthRedirect();
				} else if ($settings?.tools) {
					selectedToolIds = $settings.tools;
				} else {
					selectedToolIds = selectedToolIds.filter((id: string) => !id.startsWith('direct_server:'));
				}

				// Set Default Skills
				if (model?.info?.meta?.skillIds) {
					selectedSkillIds = [
						...new Set(
							[...(model?.info?.meta?.skillIds ?? [])].filter((id: string) =>
								($skills ?? []).find((s) => s.id === id && s.is_active)
							)
						)
					];
				} else {
					selectedSkillIds = [];
				}

				// Set Default Filters (Toggleable only)
				if (model?.info?.meta?.defaultFilterIds) {
					selectedFilterIds = model.info.meta.defaultFilterIds.filter((id: string) =>
						model?.filters?.find((f: { id: string }) => f.id === id)
					);
				}

				// Set Default Features
				if (model?.info?.meta?.defaultFeatureIds) {
					if (
						model.info?.meta?.capabilities?.['web_search'] &&
						$config?.features?.enable_web_search &&
						($user?.role === 'admin' || $user?.permissions?.features?.web_search)
					) {
						webSearchEnabled = model.info.meta.defaultFeatureIds.includes('web_search');
					}
				}

				// Set Default Terminal — only if the referenced terminal actually exists
				if (model?.info?.meta?.terminalId) {
					const tid = model.info.meta.terminalId;
					if (!$terminalServersLoaded || isTerminalAvailable(tid)) {
						selectedTerminalId.set(tid);
					}
				}
			}
		} finally {
			settingDefaults = false;
		}
	};

	const showMessage = async (message: ExtendedChatMessage, scroll = true, save = true) => {
		const _chatId = JSON.parse(JSON.stringify($chatId));
		let _messageId = JSON.parse(JSON.stringify(message.id));

		let messageChildrenIds: string[] = [];
		if (_messageId === null) {
			messageChildrenIds = Object.keys(history.messages).filter(
				(id: string) => history.messages[id].parentId === null
			);
		} else {
			messageChildrenIds = history.messages[_messageId]?.childrenIds ?? [];
		}

		while (messageChildrenIds.length !== 0) {
			const nextId = messageChildrenIds.at(-1);
			if (!nextId) break;
			_messageId = nextId;
			messageChildrenIds = history.messages[_messageId]?.childrenIds ?? [];
		}

		history.currentId = _messageId;

		await tick();

		if (($settings?.scrollOnBranchChange ?? true) && scroll) {
			const messageElement = document.getElementById(`message-${message.id}`);
			if (messageElement) {
				messageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		}

		await tick();
		await tick();
		await tick();

		if (save) {
			saveChatHandler(_chatId, history);
		}
	};

	const updateLastReadAt = (id: string) => {
		$socket?.emit('events:chat', {
			chat_id: id,
			data: { type: 'last_read_at' }
		});
	};

	const terminalEventHandler = (type: string, data: TerminalEventData) => {
		if (type === 'terminal:display_file') {
			if (!data?.path) return;
			displayFileHandler(data.path, { showControls, showFileNavPath });
		} else if (type === 'terminal:write_file' || type === 'terminal:replace_file_content') {
			if (!data?.path) return;
			showFileNavDir.set(data.path);
		} else if (type === 'terminal:run_command') {
			showFileNavDir.set('/');
		}
	};

	const upsertMessageStatus = (message: ExtendedChatMessage, status: MessageStatus | null | undefined) => {
		if (!status) return;

		const history = message?.statusHistory ?? [];
		const upsertActions = new Set([
			'chat_retry',
			'context_compaction',
			'sources_retrieved',
			'prompt_urls_extracted'
		]);

		if (status.action && upsertActions.has(status.action)) {
			const matchIndex =
				status.action === 'prompt_urls_extracted'
					? history.findLastIndex((entry) => entry?.action === status.action)
					: history.length > 0 && history[history.length - 1]?.action === status.action
						? history.length - 1
						: -1;

			if (matchIndex >= 0) {
				message.statusHistory = [
					...history.slice(0, matchIndex),
					status,
					...history.slice(matchIndex + 1)
				];
				return;
			}
		}

		message.statusHistory = [...history, status];
	};

	const scrollRichResultsIntoView = async (messageId: string) => {
		if (!autoScroll) return;

		await tick();
		setTimeout(() => {
			const richResultsEl = document.getElementById(`${messageId}-rich-results`);
			if (richResultsEl) {
				richResultsEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
				return;
			}

			const embedEl = document.getElementById(`${messageId}-embeds-container`);
			embedEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
		}, 100);
	};

	const markOutputItemsCancelled = (message: ExtendedChatMessage) => {
		if (!message?.output?.length) {
			return;
		}

		for (const item of message.output) {
			if (item?.status === 'in_progress') {
				item.status = 'cancelled';
			}
		}
	};

	const chatEventHandler = async (event: ChatSocketEvent, cb?: (result?: unknown) => void) => {
		console.log(event);

		if (event.chat_id === $chatId) {
			await tick();
			let message = history.messages[String(event.message_id)];

			if (message) {
				const type = event?.data?.type ?? null;
				const data = (event?.data?.data ?? {}) as ChatSocketPayload;

				if (type === 'status') {
					upsertMessageStatus(message, data);

					// Retry exhaustion is emitted as a status event before the final
					// completion event. Finalize the assistant message now so the user
					// can send again without the message queue treating the chat as busy.
					if (
						data?.action === 'chat_retry' &&
						data?.done &&
						message?.role === 'assistant' &&
						!message.done
					) {
						message.done = true;

						if (message.id === history.currentId) {
							taskIds = null;
						}

						const visibleContent = getAssistantText(message?.output, message?.content ?? '');
						if (!visibleContent.trim() && !message.error) {
							message.error = {
								content:
									socketString(data.description) ||
									$i18n.t('The model did not return a response after multiple attempts.')
							};
						}

						chatCompletedHandler(
							String(event.chat_id),
							String(message.model ?? ''),
							message.id,
							createMessagesList(history, message.id)
						);

						await tick();
						await processNextInQueue(String(event.chat_id));
					}
				} else if (type === 'chat:active') {
					if (!data?.active) {
						taskIds = null;
						if (chatIdProp && !$temporaryChatEnabled && hasPendingAssistantLeaf()) {
							await loadChat();
						}
					}
				} else if (type === 'chat:completion') {
					chatCompletionEventHandler(data, message, String(event.chat_id));
				} else if (type === 'chat:tasks:cancel') {
					if (event.message_id === history.currentId) {
						taskIds = null;
						// Set all response messages to done
						const parentChildren =
							message.parentId != null
								? history.messages[message.parentId]?.childrenIds ?? []
								: [];
						for (const messageId of parentChildren) {
							const childMessage = history.messages[messageId];
							if (!childMessage) continue;
							markOutputItemsCancelled(childMessage);
							childMessage.done = true;
						}
						await processNextInQueue($chatId);
					} else {
						markOutputItemsCancelled(message);
						message.done = true;
					}
				} else if (type === 'chat:message:delta' || type === 'message') {
					message.content = `${message.content ?? ''}${socketString(data.content)}`;
				} else if (type === 'chat:message' || type === 'replace') {
					message.content = socketString(data.content);
				} else if (type === 'chat:message:files' || type === 'files') {
					message.files = socketArray<ChatFile>(data.files);
					await scrollRichResultsIntoView(String(event.message_id));
				} else if (type === 'chat:message:tasks') {
					chatTasks = socketArray<ChatTask>(data.tasks);
				} else if (type === 'chat:message:embeds' || type === 'embeds') {
					message.embeds = data.embeds;
					await scrollRichResultsIntoView(String(event.message_id));
				} else if (type === 'chat:message:error') {
					message.error = data.error as ExtendedChatMessage['error'];
				} else if (type === 'chat:message:follow_ups') {
					message.followUps = data.follow_ups;

					if (shouldAutoScrollResponse()) {
						scrollToBottom('smooth');
					}
				} else if (type === 'chat:message:weather') {
					message.weather = data;
					await scrollRichResultsIntoView(String(event.message_id));
				} else if (type === 'chat:message:options') {
					message.options = data;
					await scrollRichResultsIntoView(String(event.message_id));
				} else if (type === 'chat:message:currency') {
					message.currency = data;
					await scrollRichResultsIntoView(String(event.message_id));
				} else if (type === 'chat:message:map') {
					message.map = data;
					await scrollRichResultsIntoView(String(event.message_id));
				} else if (type === 'chat:message:sports') {
					message.sports = data;
					await scrollRichResultsIntoView(String(event.message_id));
				} else if (type === 'chat:message:followups') {
					message.suggestedFollowups = data?.suggestions ?? data;
				} else if (type === 'chat:outlet') {
					// Outlet filter ran on backend — sync in-memory state
					const outletMessages = socketArray<ExtendedChatMessage>(data.messages);
					for (const msg of outletMessages) {
						if (msg?.id && history.messages[msg.id]) {
							const existing = history.messages[msg.id];
							if (existing.content !== msg.content) {
								history.messages[msg.id] = {
									...existing,
									originalContent: existing.content,
									...msg
								};
							}
						}
					}
					history = history;
					return; // Patches history.messages directly; skip the trailing write-back.
				} else if (type === 'chat:message:favorite') {
					// Update message favorite status
					message.favorite = data.favorite;
				} else if (type === 'chat:title') {
					chatTitle.set(socketString(data));
					currentChatPage.set(1);
					await chats.set(await getChatList(localStorage.token, $currentChatPage));
				} else if (type === 'chat:tags') {
					chat = await getChatById(localStorage.token, $chatId);
					allTags.set(await getAllTags(localStorage.token));
				} else if (type === 'source' || type === 'citation') {
					if (data?.type === 'code_execution') {
						// Code execution; update existing code execution by ID, or add new one.
						if (!message?.code_executions) {
							message.code_executions = [] as Array<Record<string, unknown>>;
						}

						const existingCodeExecutionIndex = message.code_executions.findIndex(
							(execution: Record<string, unknown>) => execution.id === (data as Record<string, unknown>).id
						);

						if (existingCodeExecutionIndex !== -1) {
							message.code_executions[existingCodeExecutionIndex] = data;
						} else {
							message.code_executions.push(data);
						}

						message.code_executions = message.code_executions;
					} else {
						// Regular source.
						if (Array.isArray(message?.sources)) {
							message.sources.push(data);
						} else {
							message.sources = [data];
						}
					}
				} else if (type === 'notification') {
					const toastType = socketString(data?.type, 'info');
					const toastContent = socketString(data?.content);

					if (toastType === 'success') {
						toast.success(toastContent);
					} else if (toastType === 'error') {
						toast.error(toastContent);
					} else if (toastType === 'warning') {
						toast.warning(toastContent);
					} else {
						toast.info(toastContent);
					}
				} else if (type === 'confirmation') {
					if (typeof cb === 'function') {
						return;
					}

					eventCallback = cb ?? null;

					eventConfirmationInput = false;
					showEventConfirmation = true;
					eventConfirmationInputOptions = [];

					eventConfirmationTitle = socketString(data.title);
					eventConfirmationMessage = socketString(data.message);
				} else if (type === 'execute') {
					eventCallback = cb ?? null;

					try {
						// Use Function constructor to evaluate code in a safer way
						const asyncFunction = new Function(`return (async () => { ${socketString(data.code)} })()`);
						const result = await asyncFunction(); // Await the result of the async function

						if (cb) {
							cb(result);
						}
					} catch (error) {
						console.error('Error executing code:', error);
					}
				} else if (type === 'input') {
					eventCallback = cb ?? null;

					eventConfirmationInput = true;
					showEventConfirmation = true;

					eventConfirmationTitle = socketString(data.title);
					eventConfirmationMessage = socketString(data.message);
					eventConfirmationInputPlaceholder = socketString(data.placeholder);
					eventConfirmationInputValue = socketString(data?.value ?? '');
					const inputConfig = (data?.input ?? {}) as Record<string, unknown>;
					eventConfirmationInputType = socketString(inputConfig.type ?? data?.type ?? '');
					eventConfirmationInputOptions = socketArray<{ label?: string; value: string } | string>(
						inputConfig.options ?? data?.options
					);
				} else if (type && type.startsWith('terminal:')) {
					terminalEventHandler(type, data);
				} else {
					console.log('Unknown message type', data);
				}

				history.messages[String(event.message_id)] = message;
			}
		} else {
			// Non-active chat completion: queue stays in the global store.
			// navigateHandler will process it when the user returns to that chat.
		}
	};

	const onMessageHandler = async (event: {
		origin: string;
		data: { type: string; text: string };
	}) => {
		const isSameOrigin = event.origin === window.origin;
		const type = event.data?.type;

		// Prompt-driving message types let an embedding page control the chat
		// input / submission.  Cross-origin sources are only trusted when the
		// user has explicitly opted in via the "iframe Sandbox Allow Same
		// Origin" interface setting (the same toggle that governs whether
		// rendered iframes receive `allow-same-origin`).
		const promptTypes = ['input:prompt', 'input:prompt:submit', 'action:submit'];
		const isTrusted = isSameOrigin || ($settings?.iframeSandboxAllowSameOrigin ?? false);

		// Non-prompt message types are always restricted to same-origin only.
		if (!isSameOrigin && !promptTypes.includes(type)) {
			return;
		}

		// Prompt types from an untrusted cross-origin source are silently dropped.
		if (promptTypes.includes(type) && !isTrusted) {
			return;
		}

		if (type === 'action:submit') {
			console.debug(event.data.text);

			if (prompt !== '') {
				if (isSameOrigin) {
					await tick();
					submitHandler(prompt);
				} else {
					eventConfirmationInput = false;
					eventConfirmationTitle = $i18n.t('Confirm Prompt from Embed');
					eventConfirmationMessage = prompt;
					eventCallback = async (confirmed?: unknown) => {
						if (confirmed) {
							await tick();
							submitHandler(prompt);
						}
					};
					showEventConfirmation = true;
				}
			}
		}

		if (type === 'input:prompt') {
			console.debug(event.data.text);

			const inputElement = document.getElementById('chat-input');

			if (inputElement) {
				messageInput?.setText(event.data.text);
				inputElement.focus();
			}
		}

		if (type === 'input:prompt:submit') {
			console.debug(event.data.text);

			if (event.data.text !== '') {
				if (isSameOrigin) {
					await tick();
					submitHandler(event.data.text);
				} else {
					eventConfirmationInput = false;
					eventConfirmationTitle = $i18n.t('Confirm Prompt from Embed');
					eventConfirmationMessage = event.data.text;
					eventCallback = async (confirmed?: unknown) => {
						if (confirmed) {
							await tick();
							submitHandler(event.data.text);
						}
					};
					showEventConfirmation = true;
				}
			}
		}
	};

	const savedModelIds = async () => {
		if (
			$selectedProject &&
			selectedModels.filter((modelId) => modelId !== '').length > 0 &&
			!equal(($selectedProject?.data as { model_ids?: string[] } | undefined)?.model_ids, selectedModels)
		) {
			const _res = await updateProjectById(localStorage.token, String($selectedProject?.id ?? ''), {
				data: {
					model_ids: selectedModels
				}
			});
		}
	};

	$: if (selectedModels !== null) {
		savedModelIds();
	}

	const stopAudio = () => {
		try {
			speechSynthesis.cancel();
			$audioQueue?.stop();
		} catch {
			// intentionally empty
		}
	};

	const hasPendingAssistantLeaf = () =>
		Object.values(history.messages).some(
			(message) =>
				message?.role === 'assistant' && !message.done && (message.childrenIds?.length ?? 0) === 0
		);

	const hasResponseInProgress = () =>
		Object.values(history.messages).some(
			(message) => message?.role === 'assistant' && message?.done != true
		);

	const handleSocketConnect = async () => {
		if (!chatIdProp || $temporaryChatEnabled) {
			return;
		}

		if (!hasPendingAssistantLeaf()) {
			return;
		}

		const pendingTaskIds = await getTaskIdsByChatId(localStorage.token, $chatId)
			.then((res) => res?.task_ids ?? [])
			.catch(() => null);

		if (pendingTaskIds?.length === 0) {
			await loadChat();
		}
	};

	onMount(() => {
		loading = true;
		console.log('mounted');
		window.addEventListener('message', onMessageHandler);
		$socket?.on('events', chatEventHandler);
		$socket?.on('connect', handleSocketConnect);

		const pendingSubmitUnsub: Unsubscriber = pendingSubmit.subscribe((value) => {
			if (value) {
				pendingSubmit.set(null);
				submitPrompt(value, []);
			}
		});

		const pendingArtifactFixUnsub: Unsubscriber = pendingArtifactFix.subscribe((value) => {
			if (value) {
				pendingArtifactFix.set(null);
				handleArtifactFix(value);
			}
		});

		$audioQueue?.destroy();

		const audioQueueInstance = new AudioQueue(document.getElementById('audioElement') as HTMLAudioElement);
		audioQueue.set(audioQueueInstance);

		// Restore direct terminal enabled states based on persisted selectedTerminalId
		if ($settings?.terminalServers?.length) {
			const enabledDirectTerminal = ($settings.terminalServers ?? []).find((s) => s.enabled);

			if (!$selectedTerminalId && enabledDirectTerminal?.url) {
				selectedTerminalId.set(enabledDirectTerminal.url);
			} else if ($selectedTerminalId) {
				settings.set({
					...$settings,
					terminalServers: ($settings.terminalServers ?? []).map((s) => ({
						...s,
						enabled: s.url === $selectedTerminalId
					}))
				});
			}
		}

		let lastPagePathname: string | null = $page.url.pathname;
		const pageSubscribe = page.subscribe(async (p) => {
			const pathname = p.url.pathname;
			if (pathname === '/' && lastPagePathname !== '/') {
				await tick();
				initNewChat();
			}
			lastPagePathname = pathname;

			stopAudio();
		});

		const showControlsSubscribe = showControls.subscribe(async (value) => {
			await tick();
			if (controlPane && !$mobile) {
				try {
					if (value) {
						controlPaneComponent?.openPane($showArtifacts ? 'artifact' : 'controls');
					} else {
						controlPane.collapse();
					}
				} catch (_e) {
					// ignore
				}
			}

			if (!value) {
				showCallOverlay.set(false);
				showArtifacts.set(false);
				showEmbeds.set(false);
			}
		});

		const selectedProjectSubscribe = selectedProject.subscribe(async (project) => {
			await tick();
			const projectModelIds = (project?.data as { model_ids?: string[] } | undefined)?.model_ids;
			if (projectModelIds) {
				const resolvedModels = resolveModels(projectModelIds);
				if (!equal(selectedModels, resolvedModels)) {
					selectedModels = resolvedModels;

					console.log('Set selectedModels from folder data:', selectedModels);
				}
			}
		});

		const storageChatInput = sessionStorage.getItem(
			`chat-input${chatIdProp ? `-${chatIdProp}` : ''}`
		);

		const init = async () => {
			if (!chatIdProp) {
				await initNewChat();
				modelSelectionReady = true;
				loading = false;
				await tick();
			} else {
				modelSelectionReady = true;
			}

			if (storageChatInput) {
				prompt = '';
				messageInput?.setText('');

				files = [];
				selectedToolIds = [];
				selectedSkillIds = [];
				selectedFilterIds = [];
				webSearchEnabled = false;

				try {
					const input = JSON.parse(storageChatInput);

					if (!$temporaryChatEnabled) {
						messageInput?.setText(input.prompt);
						files = input.files;
						selectedToolIds = input.selectedToolIds;
						selectedSkillIds = input.selectedSkillIds ?? [];
						selectedFilterIds = input.selectedFilterIds;
						webSearchEnabled = input.webSearchEnabled;
					}
				} catch {
					// Ignore malformed persisted input state
				}
			}

			if (!$showCallOverlay) {
				const chatInput = document.getElementById('chat-input');
				chatInput?.focus();
			}
		};
		init();

		return () => {
			try {
				clearTimeout(saveControlsTimer);
				saveControls();
				if (chatIdProp && !$temporaryChatEnabled) {
					updateLastReadAt(chatIdProp);
				}
				pageSubscribe();
				showControlsSubscribe();
				selectedProjectSubscribe();
				window.removeEventListener('message', onMessageHandler);
				$socket?.off('events', chatEventHandler);
				$socket?.off('connect', handleSocketConnect);
				pendingSubmitUnsub();
				pendingArtifactFixUnsub();
				audioQueueInstance?.destroy();
				audioQueue.set(null);
			} catch (e) {
				console.error(e);
			}
		};
	});

	$: if (
		$terminalServersLoaded &&
		$selectedTerminalId &&
		!isTerminalAvailable($selectedTerminalId)
	) {
		selectedTerminalId.set(null);
	}

	// File upload functions

	const uploadGoogleDriveFile = async (fileData: GoogleDriveFileData) => {
		console.log('Starting uploadGoogleDriveFile with:', {
			id: fileData.id,
			name: fileData.name,
			url: fileData.url,
			headers: {
				Authorization: `Bearer ${fileData.headers.Authorization}`
			}
		});

		// Validate input
		if (!fileData?.id || !fileData?.name || !fileData?.url || !fileData?.headers?.Authorization) {
			throw new Error('Invalid file data provided');
		}

		const tempItemId = uuidv4();
		const fileItem: ChatInputFile = {
			type: 'file',
			file: '',
			id: undefined,
			url: fileData.url,
			name: fileData.name,
			collection_name: '',
			status: 'uploading',
			error: '',
			itemId: tempItemId,
			size: 0
		};

		try {
			files = [...files, fileItem];
			console.log('Processing web file with URL:', fileData.url);

			// Configure fetch options with proper headers
			const fetchOptions = {
				headers: {
					Authorization: fileData.headers.Authorization,
					Accept: '*/*'
				},
				method: 'GET'
			};

			// Attempt to fetch the file
			console.log('Fetching file content from Google Drive...');
			const fileResponse = await fetch(fileData.url, fetchOptions);

			if (!fileResponse.ok) {
				const errorText = await fileResponse.text();
				throw new Error(`Failed to fetch file (${fileResponse.status}): ${errorText}`);
			}

			// Get content type from response
			const contentType = fileResponse.headers.get('content-type') || 'application/octet-stream';
			console.log('Response received with content-type:', contentType);

			// Convert response to blob
			console.log('Converting response to blob...');
			const fileBlob = await fileResponse.blob();

			if (fileBlob.size === 0) {
				throw new Error('Retrieved file is empty');
			}

			console.log('Blob created:', {
				size: fileBlob.size,
				type: fileBlob.type || contentType
			});

			// Create File object with proper MIME type
			const file = new File([fileBlob], fileData.name, {
				type: fileBlob.type || contentType
			});

			console.log('File object created:', {
				name: file.name,
				size: file.size,
				type: file.type
			});

			if (file.size === 0) {
				throw new Error('Created file is empty');
			}

			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			// Upload file to server
			console.log('Uploading file to server...');
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (!uploadedFile) {
				throw new Error('Server returned null response for file upload');
			}

			console.log('File uploaded successfully:', uploadedFile);

			// Update file item with upload results
			fileItem.status = 'uploaded';
			fileItem.file = uploadedFile;
			fileItem.id = uploadedFile.id;
			fileItem.size = file.size;
			fileItem.collection_name = uploadedFile?.meta?.collection_name;
			fileItem.url = `${uploadedFile.id}`;

			files = files;
			toast.success($i18n.t('File uploaded successfully'));
		} catch (e) {
			console.error('Error uploading file:', e);
			files = files.filter((f) => f.itemId !== tempItemId);
			toast.error(
				$i18n.t('Error uploading file: {{error}}', {
					error: e instanceof Error ? e.message : 'Unknown error'
				})
			);
		}
	};

	const uploadWeb = async (urls: string | string[]) => {
		if ($user?.role !== 'admin' && !($user?.permissions?.chat?.web_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload web content.'));
			return;
		}

		if (!Array.isArray(urls)) {
			urls = [urls];
		}

		// Create file items first
		const fileItems: ChatInputFile[] = urls.map((url) => ({
			type: 'text',
			name: url,
			collection_name: '',
			status: 'uploading',
			url,
			error: ''
		}));

		// Display all items at once
		files = [...files, ...fileItems];

		for (const fileItem of fileItems) {
			try {
				const res = isYoutubeUrl(fileItem.url ?? '')
					? await processYoutubeVideo(localStorage.token, fileItem.url ?? '')
					: await processWeb(localStorage.token, '', fileItem.url ?? '');

				if (res) {
					fileItem.status = 'uploaded';
					fileItem.collection_name = res.collection_name;
					fileItem.file = {
						...(typeof res.file === 'object' && res.file !== null ? res.file : {}),
						...(typeof fileItem.file === 'object' && fileItem.file !== null ? fileItem.file : {})
					};
				}

				files = [...files];
			} catch (e) {
				files = files.filter((f) => f.name !== fileItem.url);
				toast.error(`${e}`);
			}
		}
	};

	const onUpload = async (event: UploadEvent) => {
		const { type, data } = event;

		if (type === 'google-drive') {
			await uploadGoogleDriveFile(data as GoogleDriveFileData);
		} else if (type === 'web') {
			await uploadWeb(data as string | string[]);
		}
	};

	const onHistoryChange = (history: ExtendedChatHistory | null, _themeSetting?: string) => {
		if (history) {
			if (contentsRAF) clearTimeout(contentsRAF);
			contentsRAF = setTimeout(() => {
				getContents();
				contentsRAF = null;
			}, 0);
		} else {
			artifactContents.set([]);
		}
	};

	$: onHistoryChange(history, $theme);

	const dispatchCallOverlayAudio = (message: ExtendedChatMessage, final = false) => {
		if (!$showCallOverlay) {
			return;
		}

		const messageContentParts = getMessageContentParts(
			getAssistantText(message?.output as OutputItem[] | undefined, message?.content ?? ''),
			'clauses'
		);
		if (!final) {
			messageContentParts.pop();
		}

		const nextContentPart = messageContentParts.at(-1) ?? '';
		if (!nextContentPart || (!final && nextContentPart === message.lastSentence)) {
			return;
		}

		if (!final) {
			message.lastSentence = nextContentPart;
		}

		eventTarget.dispatchEvent(
			new CustomEvent('chat', {
				detail: {
					id: message.id,
					content: nextContentPart
				}
			})
		);
	};

	const loadPublishedArtifacts = async (id: string) => {
		const artifacts = await getArtifacts(localStorage.token);
		publishedArtifactIdMap.set(buildPublishedArtifactIdMap(artifacts, id));
	};

	const getContents = () => {
		const messages = history ? createMessagesList(history, history.currentId) : [];
		let contents: ArtifactContent[] = [];
		const publishedMap = get(publishedArtifactIdMap);
		const canvasTheme = resolveArtifactCanvasTheme(get(theme));

		const withPublishedId = (item: ArtifactContent) => ({
			...item,
			artifactId: resolvePublishedArtifactId(item.identifier, item.title, publishedMap)
		});

		const upsert = (item: ArtifactContent) => {
			contents = upsertArtifactContent(contents, withPublishedId(item));
		};

		messages.forEach((message) => {
			if (message?.role !== 'user') {
				const messageContent = getAssistantVisibleText({
					output: message?.output as OutputItem[] | undefined,
					content: message?.content ?? ''
				});
				if (!messageContent.trim()) {
					return;
				}

			// ── <antArtifact> tags (complete + in-progress streaming blocks) ──
			const antArtifacts = parseAntArtifactsForStream(messageContent);
			if (antArtifacts.length > 0) {
				antArtifacts.forEach((a) => {
					upsert(artifactToPanelContent(a, canvasTheme));
				});
				return; // don't also parse code fences from the same message
			}

				// ── Legacy: code fence artifacts (```html, ```svg) ──
				const { codeBlocks, htmlGroups } = getCodeBlockContents(messageContent) as CodeBlockContents;

				if (htmlGroups && htmlGroups.length > 0) {
					htmlGroups.forEach((group: CodeBlockGroup) => {
						const renderedContent = `
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
							<${''}style>
								body {
									background-color: white; /* Ensure the iframe has a white background */
								}

								${group.css}
							</${''}style>
                        </head>
                        <body>
                            ${group.html}

							<${''}script>
                            	${group.js}
							</${''}script>
                        </body>
                        </html>
                    `;
						upsert({ type: 'iframe', content: renderedContent });
					});
				} else {
					// Check for SVG content
					for (const block of codeBlocks) {
						if (block.lang === 'svg' || (block.lang === 'xml' && block.code.includes('<svg'))) {
							upsert({ type: 'svg', content: block.code });
						} else if (block.lang === 'html') {
							upsert({ type: 'iframe', content: block.code });
						}
					}
				}
			}
		});

		artifactContents.set(contents);

		if (contents.length > 0) {
			showArtifacts.set(true);
			showControls.set(true);
		}
	};

	//////////////////////////
	// Web functions
	//////////////////////////

	const initNewChat = async () => {
		console.log('initNewChat');
		resetWebSearchConfirmation();

		// Mark the outgoing chat as read before resetting; in-place created chats
		// keep chatIdProp undefined, so navigateHandler never marks them read.
		if ($chatId && !$temporaryChatEnabled) {
			updateLastReadAt($chatId);
		}

		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		}

		if ($settings?.temporaryChatByDefault ?? false) {
			if ($temporaryChatEnabled === false) {
				await temporaryChatEnabled.set(true);
			} else if ($temporaryChatEnabled === null) {
				// if set to null set to false; refer to temp chat toggle click handler
				await temporaryChatEnabled.set(false);
			}
		}

		if ($user?.role !== 'admin' && !$user?.permissions?.chat?.temporary) {
			await temporaryChatEnabled.set(false);
		}

		let skipModelResolution = false;

		if ($page.url.searchParams.get('models') || $page.url.searchParams.get('model')) {
			const urlModels = (
				$page.url.searchParams.get('models') ||
				$page.url.searchParams.get('model') ||
				''
			)?.split(',');

			if (urlModels.length === 1) {
				if (!$models.find((m) => m.id === urlModels[0])) {
					skipModelResolution = true;
					// Model not found; open model selector and prefill
					const modelSelectorButton = document.getElementById('model-selector-0-button');
					if (modelSelectorButton) {
						modelSelectorButton.click();
						await tick();

						const modelSelectorInput = document.getElementById('model-search-input') as HTMLInputElement | null;
						if (modelSelectorInput) {
							modelSelectorInput.focus();
							modelSelectorInput.value = urlModels[0];
							modelSelectorInput.dispatchEvent(new Event('input'));
						}
					}
				} else {
					// Model found; set it as selected
					selectedModels = urlModels;
				}
			} else {
				// Multiple models; set as selected
				selectedModels = urlModels;
			}

		} else {
			const projectModelIds = ($selectedProject?.data as { model_ids?: string[] } | undefined)?.model_ids;
			if (projectModelIds) {
				// Set from folder model IDs
				selectedModels = [...projectModelIds];
			} else {
				if (sessionStorage.selectedModels) {
					// Set from session storage (temporary selection)
					selectedModels = JSON.parse(sessionStorage.selectedModels);
				} else {
					if ($settings?.models) {
						// Set from user settings
						selectedModels = $settings?.models;
					} else if ($config?.default_models) {
						// Set from default models
						selectedModels = $config.default_models.split(',');
					}
				}
			}
		}

		if (!skipModelResolution && $models.length > 0) {
			selectedModels = resolveModels(selectedModels);
		}

		await showControls.set(false);
		await showCallOverlay.set(false);
		await showArtifacts.set(false);

		if ($page.url.pathname.includes('/c/')) {
			window.history.replaceState(window.history.state, '', `/`);
		}

		autoScroll = true;

		await resetInput();
		await chatId.set('');
		await chatTitle.set('');
		publishedArtifactIdMap.set({});

		history = {
			messages: {},
			currentId: null
		};

		chatFiles = [];
		taskIds = null;
		chatTasks = [];

		if ($page.url.searchParams.get('youtube')) {
			await uploadWeb(`https://www.youtube.com/watch?v=${$page.url.searchParams.get('youtube')}`);
		}

		if ($page.url.searchParams.get('load-url')) {
			await uploadWeb($page.url.searchParams.get('load-url') ?? '');
		}

		if ($page.url.searchParams.get('web-search') === 'true') {
			webSearchEnabled = true;
		}

		const toolsParam = $page.url.searchParams.get('tools') ?? $page.url.searchParams.get('tool-ids');
		if (toolsParam) {
			selectedToolIds = toolsParam
				.split(',')
				.map((id: string) => id.trim())
				.filter(Boolean);
		}

		// Restore tool selection after OAuth redirect
		const pendingToolId = sessionStorage.getItem('pendingOAuthToolId');
		if (pendingToolId) {
			sessionStorage.removeItem('pendingOAuthToolId');
			if (!selectedToolIds.includes(pendingToolId)) {
				selectedToolIds = [...selectedToolIds, pendingToolId];
			}
		}

		if ($page.url.searchParams.get('call') === 'true') {
			showCallOverlay.set(true);
			showControls.set(true);
		}

		// Consume one-shot desktop event (e.g. Spotlight query, call shortcut)
		if ($desktopEvent) {
			const event = $desktopEvent;
			desktopEvent.set(null);

			if (event.type === 'call') {
				// Defer to next macrotask so the call overlay isn't clobbered by
				// showControlsSubscribe's initial callback (value=false → set(false))
				// which runs as a pending microtask after this function.
				setTimeout(() => {
					showCallOverlay.set(true);
					showControls.set(true);
				}, 0);
			} else if (event.type === 'query') {
				const query = (event.data as { query?: string; files?: DesktopEventFile[] } | undefined)?.query;
				const eventFiles = (event.data as { query?: string; files?: DesktopEventFile[] } | undefined)?.files;

				// Attach screenshot images from desktop (e.g. Spotlight region capture)
				if (eventFiles?.length) {
					for (const ef of eventFiles) {
						files = [
							...files,
							{
								type: 'image',
								url: ef.dataUrl,
								name: ef.name
							}
						];
					}
				}

				if (query || eventFiles?.length) {
					if (query) {
						messageInput?.setText(query);
					}
					await tick();
					submitHandler(query || '');
				}
			}
		} else if ($page.url.searchParams.get('q')) {
			const q = $page.url.searchParams.get('q') ?? '';
			messageInput?.setText(q);

			if (q) {
				if (($page.url.searchParams.get('submit') ?? 'true') === 'true') {
					await tick();
					submitHandler(q);
				}
			}
		}

		if (!$showCallOverlay) {
			const chatInput = document.getElementById('chat-input');
			setTimeout(() => chatInput?.focus(), 0);
		}
	};

	const loadChat = async () => {
		chatId.set(chatIdProp);

		if ($temporaryChatEnabled) {
			temporaryChatEnabled.set(false);
		}

		chat = await getChatById(localStorage.token, $chatId).catch(async (_error) => {
			await goto('/');
			return null;
		});

		if (chat) {
			const chatContent = chat.chat;

			if (chatContent) {
				console.log(chatContent);

				selectedModels = chatContent.models?.length
					? [...chatContent.models]
					: [''];

				if ($user?.role !== 'admin') {
					selectedModels = selectedModels.length > 0 ? [selectedModels[0]] : [''];
				}

				selectedModels = resolveModels(selectedModels);

				oldSelectedModelIds = structuredClone(selectedModels);

				await loadPublishedArtifacts($chatId);

				const loadedHistory =
					chatContent.history ??
					(chatContent.messages
						? convertMessagesToHistory(chatContent.messages)
						: undefined);
				history = loadedHistory ?? { messages: {}, currentId: null };

				// Sanitize history: repair orphaned references and structurally-malformed
				// nodes from failed regenerations (#24424, #24157, #20474)
				sanitizeHistory(history);

				chatTitle.set(chatContent.title ?? '');

				// Only keep explicitly pinned files — message attachments are scoped to their turn
				chatFiles = (chatContent?.files ?? [])
					.filter((f) => f.pinned === true)
					.map((f) => ({ ...structuredClone(f), pinned: true }));

				// Load tasks from chat-level DB field
				chatTasks = Array.isArray(chat?.tasks) ? chat.tasks : [];

				autoScroll = true;
				await tick();

				// Mark all non-current assistant messages as done
				if (history.currentId) {
					for (const message of Object.values(history.messages)) {
						if (
							message &&
							message.role === 'assistant' &&
							message.id !== history.currentId &&
							message.done !== false
						) {
							message.done = true;
						}
					}
				}

				// Reconcile active tasks with message state:
				// If the response is already done, remaining tasks are just background
				// work (follow-ups, title gen) that shouldn't block the input.
				const activeTaskIds = taskIds;
				const pendingTaskIds = await getTaskIdsByChatId(localStorage.token, $chatId)
					.then((res) => res?.task_ids ?? [])
					.catch(() => []);
				if (taskIds !== activeTaskIds) {
					return;
				}
				const currentMessage = history.currentId ? history.messages[history.currentId] : null;
				const responseComplete = currentMessage?.role === 'assistant' && currentMessage?.done;

				if (pendingTaskIds.length > 0 && !responseComplete) {
					taskIds = pendingTaskIds;
				} else {
					taskIds = null;
					// No active tasks and message incomplete → generation was interrupted
					if (currentMessage?.role === 'assistant' && !currentMessage.done) {
						currentMessage.done = true;
					}
				}

				await tick();

				return true;
			} else {
				return null;
			}
		}
	};

	const scrollToBottom = async (behavior: 'auto' | 'smooth' = 'auto') => {
		await tick();
		if (messagesContainerElement) {
			messagesContainerElement.scrollTo({
				top: messagesContainerElement.scrollHeight,
				behavior
			});

			// content-visibility: auto causes the initial scrollHeight to be based on
			// estimated sizes (contain-intrinsic-size). After we scroll, previously
			// off-screen messages become visible and the browser resolves their actual
			// heights, which shifts scrollHeight. Re-layouts can cascade across frames
			// (new sizes reveal more content, triggering further size resolution), so
			// we re-scroll across two animation frames to land at the true bottom.
			requestAnimationFrame(() => {
				if (messagesContainerElement) {
					messagesContainerElement.scrollTo({
						top: messagesContainerElement.scrollHeight,
						behavior
					});
					requestAnimationFrame(() => {
						if (messagesContainerElement) {
							messagesContainerElement.scrollTo({
								top: messagesContainerElement.scrollHeight,
								behavior
							});
						}
					});
				}
			});
		}
	};

	const scrollToTop = async () => {
		await messagesRef?.scrollToTop();
	};

	let scrollRAF: number | null = null;
	let contentsRAF: ReturnType<typeof setTimeout> | null = null;
	const scheduleScrollToBottom = () => {
		if (!scrollRAF) {
			scrollRAF = requestAnimationFrame(async () => {
				scrollRAF = null;
				await scrollToBottom();
			});
		}
	};

	let processingQueueChats = new Set<string>();

	const processNextInQueue = async (targetChatId: string) => {
		if (processingQueueChats.has(targetChatId)) return;

		const queue = $chatRequestQueues[targetChatId];
		if (!queue || queue.length === 0) return;

		processingQueueChats.add(targetChatId);
		try {
			const combinedPrompt = queue.map((m) => m.prompt).join('\n\n');
			const combinedFiles = queue.flatMap((m) => m.files);

			chatRequestQueues.update((q) => {
				const { [targetChatId]: _, ...rest } = q;
				return rest;
			});

			await submitPrompt(combinedPrompt, combinedFiles);
		} finally {
			processingQueueChats.delete(targetChatId);
		}
	};

	const chatCompletedHandler = async (_chatId: string, _modelId: string, _responseMessageId: string, _messages: ExtendedChatMessage[]) => {
		// Backend handles outlet filters and persistence inline.
		// Just refresh the sidebar chat list.
		if ($chatId == _chatId && !$temporaryChatEnabled) {
			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
		}
	};

	const chatActionHandler = async (_chatId: string, actionId: string, modelId: string, responseMessageId: string, event: unknown = null) => {
		const messages = createMessagesList(history, responseMessageId);

		const res = await chatAction(localStorage.token, actionId, {
			model: modelId,
			messages: messages.map((m) => ({
				id: m.id,
				role: m.role,
				content: getOutputText(m.output as OutputItem[] | undefined) || m.content,
				info: m.info ? m.info : undefined,
				timestamp: m.timestamp,
				...(m.sources ? { sources: m.sources } : {})
			})),
			...(event ? { event: event } : {}),
			model_item: $models.find((m) => m.id === modelId),
			chat_id: _chatId,
			session_id: $socket?.id,
			id: responseMessageId
		}).catch((error) => {
			toast.error(`${error}`);
			const lastMessage = messages.at(-1);
			if (lastMessage) lastMessage.error = { content: error };
			return null;
		});

		if (res !== null && res.messages) {
			// Update chat history with the new messages
			for (const message of res.messages) {
				history.messages[message.id] = {
					...history.messages[message.id],
					...(history.messages[message.id].content !== message.content
						? { originalContent: history.messages[message.id].content }
						: {}),
					...message
				};
			}
		}

		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					messages: messages,
					history: history,
					files: chatFiles
				});

				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
			}
		}
	};

	const getChatEventEmitter = async (modelId: string, chatId: string = '') => {
		return setInterval(() => {
			$socket?.emit('usage', {
				action: 'chat',
				model: modelId,
				chat_id: chatId
			});
		}, 1000);
	};

	const createMessagePair = async (userPrompt: string) => {
		messageInput?.setText('');
		if (selectedModels.length === 0) {
			toast.error($i18n.t('Model not selected'));
		} else {
			const modelId = selectedModels[0];
			const model = $models.filter((m) => m.id === modelId).at(0);

			if (!model) {
				toast.error($i18n.t('Model not found'));
				return;
			}

			const messages = createMessagesList(history, history.currentId);
			const parentMessage = messages.length !== 0 ? messages.at(-1) : null;

			const userMessageId = uuidv4();
			const responseMessageId = uuidv4();

			const userMessage = {
				id: userMessageId,
				parentId: parentMessage ? parentMessage.id : null,
				childrenIds: [responseMessageId],
				role: 'user',
				content: userPrompt ? userPrompt : `[PROMPT] ${userMessageId}`,
				timestamp: Math.floor(Date.now() / 1000)
			};

			const responseMessage = {
				id: responseMessageId,
				parentId: userMessageId,
				childrenIds: [],
				role: 'assistant',
				content: `[RESPONSE] ${responseMessageId}`,
				done: true,

				model: modelId,
				modelName: model.name ?? model.id,
				modelIdx: 0,
				timestamp: Math.floor(Date.now() / 1000)
			};

			if (parentMessage) {
				(parentMessage.childrenIds ??= []).push(userMessageId);
				history.messages[parentMessage.id] = parentMessage;
			}
			history.messages[userMessageId] = userMessage;
			history.messages[responseMessageId] = responseMessage;

			history.currentId = responseMessageId;

			await tick();

			if (autoScroll) {
				scrollToBottom();
			}

			if (messages.length === 0) {
				await initChatHandler(history);
			} else {
				await saveChatHandler($chatId, history);
			}
		}
	};

	const addMessages = async ({ modelId, parentId, messages }: { modelId: string; parentId: string; messages: ExtendedChatMessage[] }) => {
		const model = $models.filter((m) => m.id === modelId).at(0);
		if (!model) {
			toast.error($i18n.t('Model not found'));
			return;
		}

		let parentMessage = history.messages[parentId];
		let currentParentId = parentMessage ? parentMessage.id : null;
		for (const message of messages) {
			let messageId = uuidv4();

			if (message.role === 'user') {
				const userMessage: ExtendedChatMessage = {
					...message,
					id: messageId,
					parentId: currentParentId,
					childrenIds: message.childrenIds ?? [],
					timestamp: Math.floor(Date.now() / 1000)
				};

				if (parentMessage) {
					(parentMessage.childrenIds ??= []).push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = userMessage;
				parentMessage = userMessage;
				currentParentId = messageId;
			} else {
				const responseMessage: ExtendedChatMessage = {
					...message,
					id: messageId,
					parentId: currentParentId,
					childrenIds: message.childrenIds ?? [],
					done: message.done ?? true,
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: message.modelIdx ?? 0,
					timestamp: Math.floor(Date.now() / 1000)
				};

				if (parentMessage) {
					(parentMessage.childrenIds ??= []).push(messageId);
					history.messages[parentMessage.id] = parentMessage;
				}

				history.messages[messageId] = responseMessage;
				parentMessage = responseMessage;
				currentParentId = messageId;
			}
		}

		history.currentId = currentParentId;
		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		if (messages.length === 0) {
			await initChatHandler(history);
		} else {
			await saveChatHandler($chatId, history);
		}
	};

	const chatCompletionEventHandler = async (data: ChatSocketPayload, message: ExtendedChatMessage, chatId: string) => {
		const { _id, done, choices, content, output, sources, selected_model_id, error, usage, status } =
			data as CompletionData;

		if (status?.action === 'chat_retry') {
			upsertMessageStatus(message, status);
		}

		// Store raw OR-aligned output items from backend
		if (output) {
			message.output = output as OutputItem[];
			message.content = getAssistantText(output as OutputItem[], message.content ?? '');
			dispatchCallOverlayAudio(message);
		}

		if (error) {
			await handleOpenAIError(error, message);
		}

		if (sources && !message?.sources) {
			message.sources = sources;
		}

		if (choices && !output) {
			if (choices[0]?.message?.content) {
				// Non-stream response
				message.content += choices[0]?.message?.content;
				dispatchCallOverlayAudio(message);
			} else {
				// Stream response
				let value = choices[0]?.delta?.content ?? '';
				if (message.content == '' && value == '\n') {
					console.log('Empty response');
				} else {
					message.content += value;

					if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
						navigator.vibrate(5);
					}
					dispatchCallOverlayAudio(message);
				}
			}
		}

		if (content && !output) {
			// REALTIME_CHAT_SAVE is disabled
			message.content = String(content);

			if (navigator.vibrate && ($settings?.hapticFeedback ?? false)) {
				navigator.vibrate(5);
			}
			dispatchCallOverlayAudio(message);
		}

		if (selected_model_id) {
			message.selectedModelId = String(selected_model_id);
			message.arena = true;
		}

		if (usage) {
			message.usage = usage;
		}

		history.messages[message.id] = message;

		if (done) {
			message.done = true;

			if (message.id === history.currentId) {
				taskIds = null;
			}

			const visibleContent = getAssistantText(message?.output, message?.content ?? '');

			if (!visibleContent.trim() && !message.error) {
				const lastStatus = message.statusHistory?.at(-1);
				if (lastStatus?.action === 'chat_retry' && lastStatus.done) {
					message.error = {
						content:
							lastStatus.description ||
							$i18n.t('The model did not return a response after multiple attempts.')
					};
				}
			}

			if ($settings.responseAutoCopy) {
				copyToClipboard(visibleContent);
			}

			if ($settings.responseAutoPlayback && !$showCallOverlay) {
				await tick();
				document.getElementById(`speak-button-${message.id}`)?.click();
			}

			// Emit chat event for TTS (only when call overlay is active)
			dispatchCallOverlayAudio(message, true);
			eventTarget.dispatchEvent(
				new CustomEvent('chat:finish', {
					detail: {
						id: message.id,
						content: visibleContent
					}
				})
			);

			history.messages[message.id] = message;

			await tick();
			if (autoScroll) {
				scrollToBottom();
			}

			// Fire-and-forget: run chatCompletedHandler for background work
			// (outlet filters, chat save, title gen, follow-ups, tags)
			// without blocking the user from sending new messages.
			chatCompletedHandler(
				chatId,
				String(message.model ?? ''),
				message.id,
				createMessagesList(history, message.id)
			);

			// Process next queued request if any
			await processNextInQueue(chatId);
		}

		console.log(data);
		await tick();

		if (shouldAutoScrollResponse()) {
			scheduleScrollToBottom();
		}
	};

	//////////////////////////
	// Chat functions
	//////////////////////////

	const submitPrompt = async (inputContent: string, inputFiles: ChatFile[]) => {
		const _files = structuredClone(inputFiles);

		// Create user message
		let userMessageId = uuidv4();
		let userMessage = {
			id: userMessageId,
			parentId: history.currentId ?? null,
			childrenIds: [],
			role: 'user',
			content: inputContent,
			files: _files.length > 0 ? _files : undefined,
			timestamp: Math.floor(Date.now() / 1000), // Unix epoch
			models: selectedModels
		};

		// Add message to history and Set currentId to messageId
		history.messages[userMessageId] = userMessage;

		// Append messageId to childrenIds of parent message
		if (history.currentId !== null && history.messages[history.currentId]) {
			const parent = history.messages[history.currentId];
			(parent.childrenIds ??= []).push(userMessageId);
			history.messages[history.currentId] = parent;
		}

		history.currentId = userMessageId;

		// focus on chat input (skip during voice call to avoid triggering mobile keyboard)
		if (!$showCallOverlay) {
			const chatInput = document.getElementById('chat-input');
			chatInput?.focus();
		}

		saveSessionSelectedModels();

		await sendMessage(history, userMessageId);
	};

	const submitHandler = async (userPrompt: string, { _raw = false }: { _raw?: boolean } = {}) => {
		console.log('submitHandler', userPrompt, $chatId);

		const availableModelIds = getAvailableModelIds($models);
		const hasValidSelection = selectedModels.some(
			(modelId) => modelId && availableModelIds.includes(modelId)
		);

		if (!hasValidSelection && $models.length > 0) {
			const _selectedModels = resolveModels(selectedModels);

			if (!equal(selectedModels, _selectedModels)) {
				selectedModels = _selectedModels;
			}
		}

		if (pendingOAuthTools.length > 0) {
			toast.warning($i18n.t('Please connect all required integrations before sending a message'));
			return;
		}
		if (userPrompt === '' && files.length === 0) {
			toast.error($i18n.t('Please enter a prompt'));
			return;
		}
		if (selectedModels.includes('')) {
			toast.error($i18n.t('Model not selected'));
			return;
		}

		if (
			files.length > 0 &&
			files.filter((file) => file.type !== 'image' && file.status === 'uploading').length > 0
		) {
			toast.error(
				$i18n.t(`Oops! There are files still uploading. Please wait for the upload to complete.`)
			);
			return;
		}

		if (
			($config?.file?.max_count ?? null) !== null &&
			files.length + chatFiles.length > ($config?.file?.max_count ?? Infinity)
		) {
			toast.error(
				$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
					maxCount: $config?.file?.max_count
				})
			);
			return;
		}

		if (
			$config?.features?.enable_web_search_confirmation &&
			webSearchActive &&
			!webSearchConfirmed
		) {
			pendingWebSearchPrompt = userPrompt ?? '';
			openWebSearchConfirm();
			return;
		}

		// Check if any assistant response is still in flight
		// (don't block on background tasks like title gen, follow-ups, tags)
		const isGenerating = hasResponseInProgress();

		if (isGenerating) {
			if ($settings?.enableMessageQueue ?? true) {
				// Enqueue the request
				const _files = structuredClone(files);
				chatRequestQueues.update((q) => ({
					...q,
					[$chatId]: [...(q[$chatId] ?? []), { id: uuidv4(), prompt: userPrompt, files: _files }]
				}));
				// Clear input
				messageInput?.setText('');
				prompt = '';
				files = [];
				return;
			} else {
				// Interrupt: stop current generation and proceed
				await stopResponse();
				await tick();
			}
		}

		if (history?.currentId) {
			const currentMessage = history.messages[history.currentId];

			if (currentMessage.error && !currentMessage.content) {
				// Error in response
				toast.error($i18n.t(`Oops! There was an error in the previous response.`));
				return;
			}
		}

		// Clear input and submit
		messageInput?.setText('');
		prompt = '';
		const _files = structuredClone(files);
		files = [];
		messageInput?.setText('');

		await submitPrompt(userPrompt, _files);
	};

	const sendMessage = async (
		_history: ExtendedChatHistory,
		parentId: string,
		{
			messages = null,
			modelId = null,
			modelIdx = null,
			regenerationPrompt = null
		}: {
			messages?: unknown[] | null;
			modelId?: string | null;
			modelIdx?: number | null;
			regenerationPrompt?: string | null;
		} = {}
	) => {
		if (autoScroll) {
			scrollToBottom();
		}

		let _chatId = JSON.parse(JSON.stringify($chatId));
		_history = structuredClone(_history);

		const responseMessageIds: Record<PropertyKey, string> = {};
		// If modelId is provided, use it, else use selected model
		let selectedModelIds = modelId
			? [modelId]
			: atSelectedModel !== undefined
				? [atSelectedModel.id]
				: selectedModels;

		// Create response messages for each selected model
		// Build message_ids list: [{model_id, message_id}, ...]
		// Uses an array instead of a dict to support duplicate model IDs in side-by-side chat.
		const messageIdsList: Array<{ model_id: string; message_id: string }> = [];
		for (const [_modelIdx, modelId] of selectedModelIds.entries()) {
			const model = $models.filter((m) => m.id === modelId).at(0);

			if (model) {
				let responseMessageId = uuidv4();
				let responseMessage = {
					parentId: parentId,
					id: responseMessageId,
					childrenIds: [],
					role: 'assistant',
					content: '',
					done: false,
					model: model.id,
					modelName: model.name ?? model.id,
					modelIdx: modelIdx ? modelIdx : _modelIdx,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				// Add message to history and Set currentId to messageId
				history.messages[responseMessageId] = responseMessage;
				history.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId !== null && history.messages[parentId]) {
					const parent = history.messages[parentId];
					parent.childrenIds = [...(parent.childrenIds ?? []), responseMessageId];
					history.messages[parentId] = parent;
				}

				responseMessageIds[`${modelId}-${modelIdx ? modelIdx : _modelIdx}`] = responseMessageId;
				messageIdsList.push({ model_id: modelId, message_id: responseMessageId });
			}
		}
		history = history;

		// New chat — backend generates the chat_id on first request
		if (!_chatId) {
			if ($temporaryChatEnabled) {
				_chatId = `local:${$socket?.id}`;
				await chatId.set(_chatId);
			}
			await tick();
		}

		await tick();

		// Re-clone history so sendMessageSocket gets the response messages we just added
		_history = structuredClone(history);

		// Vision capability check
		for (const mid of selectedModelIds) {
			const model = $models.filter((m) => m.id === mid).at(0);
			if (model) {
				const hasImages = createMessagesList(_history, parentId).some((message) =>
					message.files?.some(
						(file: ChatFile) => file.type === 'image' || (file?.content_type ?? '').startsWith('image/')
					)
				);

				if (
					hasImages &&
					!(model.info?.meta?.capabilities?.vision ?? true) &&
					!imageGenerationActive
				) {
					toast.error(
						$i18n.t('Model {{modelName}} is not vision capable', {
							modelName: model.name ?? model.id
						})
					);
				}
			}
		}

		// Single request — backend fans out to all models
		const primaryModelId = selectedModelIds[0];
		const primaryModel = $models.filter((m) => m.id === primaryModelId).at(0);
		const primaryResponseMessageId = messageIdsList[0]?.message_id;

		if (primaryModel && primaryResponseMessageId) {
			const chatEventEmitter = await getChatEventEmitter(primaryModel.id, _chatId);

			try {
				scrollToBottom();
				await sendMessageSocket(
					primaryModel,
					messages && messages.length > 0
						? (messages as ExtendedChatMessage[])
						: createMessagesList(_history, primaryResponseMessageId),
					_history,
					primaryResponseMessageId,
					_chatId,
					{
						messageIdsList: selectedModelIds.length > 1 ? messageIdsList : undefined,
						regenerationPrompt
					}
				);
			} finally {
				if (chatEventEmitter) clearInterval(chatEventEmitter);
			}
		}
	};

	const getFeatures = () => {
		let features = {};

		if ($config?.features)
			features = {
				voice: $showCallOverlay,
				image_generation: imageGenerationActive,
				code_interpreter: codeInterpreterActive,
				web_search: webSearchActive
			};

		if ($settings?.memory ?? $config?.features?.enable_memories ?? false) {
			features = { ...features, memory: true };
		}

		return features;
	};

	const sendMessageSocket = async (
		model: Model,
		_messages: ExtendedChatMessage[],
		_history: ExtendedChatHistory,
		responseMessageId: string,
		_chatId: string,
		{
			messageIdsList,
			regenerationPrompt,
			continueResponse = false
		}: {
			messageIdsList?: Array<{ model_id: string; message_id: string }>;
			regenerationPrompt?: string | null;
			continueResponse?: boolean;
		} = {}
	) => {
		const responseMessage = _history.messages[responseMessageId];
		const userMessage = responseMessage.parentId
			? _history.messages[responseMessage.parentId]
			: undefined;

		// RAG only for files attached to this message + explicitly pinned chat files
		let files = [
			...getRagFiles(chatFiles),
			...getRagFiles(userMessage?.files ?? [])
		];
		files = files.filter(
			(item, index, array) => array.findIndex((i) => i.id === item.id) === index
		);

		scrollToBottom();
		eventTarget.dispatchEvent(
			new CustomEvent('chat:start', {
				detail: {
					id: responseMessageId
				}
			})
		);
		await tick();

		let userLocation;
		if ($settings?.userLocation) {
			userLocation = await getAndUpdateUserLocation(localStorage.token).catch((err) => {
				console.error(err);
				return undefined;
			});
		}

		const stream = model?.info?.params?.stream_response ?? true;
		let messages: Record<string, unknown>[] = [];

		if ($temporaryChatEnabled) {
			const preparedMessages: ExtendedChatMessage[] = _messages.map((message) => ({
				...message,
				...(message.output && message.role === 'assistant'
					? { output: message.output }
					: { content: processDetails(message.content ?? '') })
			}));

			messages = preparedMessages
				.map((message) => {
					const imageFiles = (message?.files ?? []).filter(
						(file: ChatFile) => file.type === 'image' || (file?.content_type ?? '').startsWith('image/')
					);

					if (message.output && message.role === 'assistant') {
						return {
							role: message.role,
							output: message.output,
							...(message.content ? { content: message.content } : {})
						};
					}

					if (message.role === 'user' && imageFiles.length > 0) {
						return {
							role: message.role,
							content: [
								{
									type: 'text',
									text: message?.merged?.content ?? message.content
								},
								...imageFiles.map((file: ChatFile) => ({
									type: 'image_url',
									image_url: {
										url: file.url
									}
								}))
							]
						};
					}

					return {
						role: message.role,
						content: message?.merged?.content ?? message.content
					};
				})
				.filter((message) => {
					const content = message.content;
					const hasContent =
						typeof content === 'string'
							? content.trim().length > 0
							: Array.isArray(content) && content.length > 0;
					return message?.role === 'user' || hasContent || ('output' in message && (message.output?.length ?? 0) > 0);
				});
		}

		const toolIds: string[] = [];
		const toolServerIds: (string | number)[] = [];

		// Include this model's own attached tools so they apply in multi-model chats,
		// independent of the composer's selectedToolIds lifecycle.
		const modelDefaultToolIds = (model?.info?.meta?.toolIds ?? []).filter((id: string) =>
			($tools ?? []).find((t) => t.id === id)
		);
		for (const toolId of [...new Set([...selectedToolIds, ...modelDefaultToolIds])]) {
			if (toolId.startsWith('direct_server:')) {
				let serverId = toolId.replace('direct_server:', '');
				// Check if serverId is a number
				if (!isNaN(parseInt(serverId))) {
					toolServerIds.push(parseInt(serverId));
				} else {
					toolServerIds.push(serverId);
				}
			} else {
				toolIds.push(toolId);
			}
		}

		// Menu-selected skills are sent as IDs; inline <$skillId|label> mentions stay
		// in the message so the backend can inject their full content.
		const skillIds = [...selectedSkillIds];

		// Use the user-selected terminal from the dropdown
		const activeTerminalId = $selectedTerminalId ?? null;

		// Only send terminal_id if the model has terminal capability enabled
		const terminalEnabled = model.info?.meta?.capabilities?.terminal ?? true;

		const res = await generateOpenAIChatCompletion(
			localStorage.token,
			{
				stream: stream,
				model: model.id,
				...(messages.length > 0 ? { messages } : {}),
				params: {
					think: resolveThinkForRequest($settings, { voiceMode: $showCallOverlay })
				},

				files: (files?.length ?? 0) > 0 ? files : undefined,

				filter_ids: selectedFilterIds.length > 0 ? selectedFilterIds : undefined,
				tool_ids: toolIds.length > 0 ? toolIds : undefined,
				skill_ids: skillIds.length > 0 ? skillIds : undefined,
				terminal_id: terminalEnabled ? (activeTerminalId ?? undefined) : undefined,
				tool_servers: [
					...($toolServers ?? []).filter(
						(server, idx) => toolServerIds.includes(idx) || (server?.id != null && toolServerIds.includes(server.id))
					),
					// Direct terminal servers — always included when enabled (not routed through selectedToolIds)
					...($terminalServers ?? []).filter((t) => !t.id)
				],
				features: getFeatures(),
				variables: {
					...getPromptVariables(
						$user?.name ?? '',
						typeof userLocation === 'string' ? userLocation : '',
						$user?.email ?? ''
					)
				},
				model_item: $models.find((m) => m.id === model.id),

				session_id: $socket?.id,
				chat_id: _chatId || undefined,
				project_id: $selectedProject?.id ?? undefined,

				id: responseMessageId,
				...(messageIdsList ? { message_ids: messageIdsList } : {}),
				parent_id: userMessage?.parentId ?? null,
				user_message: userMessage,
				...(regenerationPrompt ? { regeneration_prompt: regenerationPrompt } : {}),
				...(continueResponse ? { assistant_message_id: responseMessageId } : {}),

				background_tasks: {
					...(!$temporaryChatEnabled && !_chatId && (userMessage?.parentId ?? null) === null
						? {
								title_generation: $settings?.title?.auto ?? true,
								tags_generation: $settings?.autoTags ?? true
							}
						: {}),
					follow_up_generation: $settings?.autoFollowUps ?? true
				},

				...(stream && (model.info?.meta?.capabilities?.usage ?? false)
					? {
							stream_options: {
								include_usage: true
							}
						}
					: {})
			},
			`${WEBUI_BASE_URL}/api`
		).catch(async (error) => {
			console.log(error);

			let errorMessage = error;
			if (error?.error?.message) {
				errorMessage = error.error.message;
			} else if (error?.message) {
				errorMessage = error.message;
			}

			if (typeof errorMessage === 'object') {
				errorMessage = $i18n.t(`Uh-oh! There was an issue with the response.`);
			}

			toast.error(`${errorMessage}`);
			responseMessage.error = {
				content: error
			};

			responseMessage.done = true;

			history.messages[responseMessageId] = responseMessage;
			history.currentId = responseMessageId;

			return null;
		});

		if (res) {
			if (res.error) {
				await handleOpenAIError(res.error, responseMessage);
			} else {
				// Backend returns task_ids (multi-model) or task_id (single model)
				const newTaskIds = res.task_ids ?? (res.task_id ? [res.task_id] : []);
				if (newTaskIds.length > 0) {
					taskIds = [...(taskIds ?? []), ...newTaskIds];
				}

				// Backend returns chat_id for new chats — set store + URL.
				// Only update if the user hasn't navigated to a different chat
				// while the request was in flight (prevents overwriting $chatId
				// and causing spurious toast notifications / state duplication).
				if (res.chat_id && $chatId !== res.chat_id && $chatId === _chatId) {
					await chatId.set(res.chat_id);
					if (!$temporaryChatEnabled) {
						window.history.replaceState(window.history.state, '', `/c/${res.chat_id}`);
						currentChatPage.set(1);
						await chats.set(await getChatList(localStorage.token, $currentChatPage));
					}
				}
			}
		}

		await tick();
		scrollToBottom();
	};

	const handleOpenAIError = async (error: unknown, responseMessage: ExtendedChatMessage) => {
		let errorMessage = '';
		const innerError = error ?? {};

		console.error(innerError);
		if (typeof innerError === 'object' && innerError !== null && 'detail' in innerError) {
			// FastAPI error
			const detail = String((innerError as { detail?: unknown }).detail ?? '');
			toast.error(detail);
			errorMessage = detail;
		} else if (typeof innerError === 'object' && innerError !== null && 'error' in innerError) {
			// OpenAI error
			const apiError = (innerError as { error?: Record<string, unknown> | string }).error;
			if (apiError && typeof apiError === 'object' && 'message' in apiError) {
				const msg = String(apiError.message ?? '');
				toast.error(msg);
				errorMessage = msg;
			} else {
				const msg = String(apiError ?? '');
				toast.error(msg);
				errorMessage = msg;
			}
		} else if (typeof innerError === 'object' && innerError !== null && 'message' in innerError) {
			// OpenAI error
			const msg = String((innerError as { message?: unknown }).message ?? '');
			toast.error(msg);
			errorMessage = msg;
		}

		responseMessage.error = {
			content: $i18n.t(`Uh-oh! There was an issue with the response.`) + '\n' + errorMessage
		};
		responseMessage.done = true;

		if (responseMessage.statusHistory) {
			responseMessage.statusHistory = responseMessage.statusHistory.filter(
				(status: MessageStatus) => status.action !== 'knowledge_search'
			);
		}

		history.messages[responseMessage.id] = responseMessage;
	};

	const stopResponse = async (processQueue = true) => {
		const responseInProgress = hasResponseInProgress();

		if (responseInProgress || taskIds) {
			if ($chatId) {
				await stopTasksByChatId(localStorage.token, $chatId).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			} else if (taskIds?.length) {
				for (const taskId of taskIds) {
					await stopTask(localStorage.token, taskId).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}
			}

			taskIds = null;

			// Mark every in-flight assistant response as done (not only history.currentId).
			for (const message of Object.values(history.messages)) {
				if (message?.role === 'assistant' && message?.done != true) {
					markOutputItemsCancelled(message);
					message.done = true;
				}
			}

			if (autoScroll) {
				scrollToBottom();
			}
		}

		if (generating) {
			generating = false;
			generationController?.abort();
			generationController = null;
		}

		if (processQueue) {
			await processNextInQueue($chatId);
		}
	};

	const findArtifactAssistantMessage = (fix: PendingArtifactFix) => {
		const messages = history ? createMessagesList(history, history.currentId) : [];
		for (let i = messages.length - 1; i >= 0; i--) {
			const message = messages[i];
			if (message?.role === 'user') continue;

			const messageContent = getAssistantText(
				message?.output as OutputItem[] | undefined,
				message?.content ?? ''
			);
			const artifacts = parseAntArtifacts(messageContent);
			const match = artifacts.find(
				(a) =>
					(fix.identifier && a.identifier === fix.identifier) ||
					(!fix.identifier &&
						fix.title &&
						a.title === fix.title &&
						(!fix.mimeType || a.type === fix.mimeType))
			);
			if (match) return message;
		}
		return null;
	};

	const handleArtifactFix = async (fix: PendingArtifactFix) => {
		const assistantMessage = findArtifactAssistantMessage(fix);
		if (!assistantMessage) {
			toast.error($i18n.t('Could not find the artifact message to fix'));
			return;
		}

		const prompt = buildArtifactFixPrompt({
			title: fix.title,
			identifier: fix.identifier,
			mimeType: fix.mimeType,
			errorKind: fix.errorKind,
			errorMessage: fix.errorMessage
		});

		await submitMessage(assistantMessage.id, prompt);
	};

	const submitMessage = async (parentId: string | null, prompt: string) => {
		let userPrompt = prompt;
		let userMessageId = uuidv4();

		let userMessage = {
			id: userMessageId,
			parentId: parentId,
			childrenIds: [],
			role: 'user',
			content: userPrompt,
			models: selectedModels,
			timestamp: Math.floor(Date.now() / 1000) // Unix epoch
		};

		if (parentId !== null && history.messages[parentId]) {
			const parent = history.messages[parentId];
			parent.childrenIds = [...(parent.childrenIds ?? []), userMessageId];
			history.messages[parentId] = parent;
		}

		history.messages[userMessageId] = userMessage;
		history.currentId = userMessageId;

		await tick();

		if (autoScroll) {
			scrollToBottom();
		}

		await sendMessage(history, userMessageId);
	};

	const regenerateResponse = async (message: ExtendedChatMessage, suggestionPrompt: string | null = null) => {
		console.log('regenerateResponse');

		if (history.currentId) {
			let userMessage = message.parentId ? history.messages[message.parentId] : undefined;

			if (!userMessage) {
				toast.error($i18n.t('Parent message not found'));
				return;
			}

			if (autoScroll) {
				scrollToBottom();
			}

			await sendMessage(history, userMessage.id, {
				...(suggestionPrompt
					? {
							messages: createMessagesList(history, message.id),
							regenerationPrompt: suggestionPrompt
						}
					: {}),
				...((Array.isArray(userMessage?.models) ? userMessage.models : selectedModels).length > 1
					? {
							// If multiple models are selected, use the model from the message
							modelId: message.model,
							modelIdx: message.modelIdx
						}
					: {})
			});
		}
	};

	const continueResponse = async () => {
		console.log('continueResponse');
		const _chatId = JSON.parse(JSON.stringify($chatId));

		if (history.currentId && history.messages[history.currentId].done == true) {
			const responseMessage = history.messages[history.currentId];
			responseMessage.done = false;
			await tick();

			const model = $models
				.filter((m) => m.id === (responseMessage?.selectedModelId ?? responseMessage.model))
				.at(0);

			if (model) {
				await sendMessageSocket(
					model,
					createMessagesList(history, responseMessage.id),
					history,
					responseMessage.id,
					_chatId,
					{ continueResponse: true }
				);
			}
		}
	};

	const mergeResponses = async (messageId: string, responses: string[], _chatId: string) => {
		console.log('mergeResponses', messageId, responses);
		const message = history.messages[messageId];
		const mergedResponse = {
			status: true,
			content: ''
		};
		message.merged = mergedResponse;
		history.messages[messageId] = message;

		try {
			generating = true;
			const [res, controller] = await generateMoACompletion(
				localStorage.token,
				String(message.model ?? ''),
				message.parentId ? (history.messages[message.parentId]?.content ?? '') : '',
				responses
			);

			if (res instanceof Response && res.ok && res.body && generating) {
				generationController = controller as AbortController;
				const textStream = await createOpenAITextStream(
					res.body,
					Boolean($settings?.splitLargeChunks ?? false)
				);
				for await (const update of textStream) {
					const { value, done, sources: _sources, error, usage: _usage } = update;
					if (error || done) {
						generating = false;
						generationController = null;
						break;
					}

					if (mergedResponse.content == '' && value == '\n') {
						continue;
					} else {
						mergedResponse.content += value;
						history.messages[messageId] = message;
					}

					if (shouldAutoScrollResponse()) {
						scheduleScrollToBottom();
					}
				}

				await saveChatHandler(_chatId, history);
			} else {
				console.error(res);
			}
		} catch (e) {
			console.error(e);
		}
	};

	const initChatHandler = async (history: ExtendedChatHistory) => {
		let _chatId = $chatId;

		if (!$temporaryChatEnabled) {
			chat = await createNewChat(
				localStorage.token,
				{
					id: _chatId,
					title: $i18n.t('New Chat'),
					models: selectedModels,
					history: history,
					messages: createMessagesList(history, history.currentId),
					tags: [],
					timestamp: Date.now()
				},
				String($selectedProject?.id ?? '')
			);

			_chatId = chat?.id ?? _chatId;
			await chatId.set(_chatId);

			window.history.replaceState(window.history.state, '', `/c/${_chatId}`);

			await tick();

			await chats.set(await getChatList(localStorage.token, $currentChatPage));
			currentChatPage.set(1);

			selectedProject.set(null);
		} else {
			_chatId = `local:${$socket?.id}`; // Use socket id for temporary chat
			await chatId.set(_chatId);
		}
		await tick();

		return _chatId;
	};

	const saveChatHandler = async (_chatId: string, history: ExtendedChatHistory) => {
		if ($chatId == _chatId) {
			if (!$temporaryChatEnabled) {
				chat = await updateChatById(localStorage.token, _chatId, {
					models: selectedModels,
					history: history,
					messages: createMessagesList(history, history.currentId),
					files: chatFiles
				});
			}
		}
	};

	const saveControls = async () => {
		if (!$chatId || $temporaryChatEnabled) return;
		const loaded = chat?.chat ?? {};
		if (equal(chatFiles, loaded.files ?? [])) return;

		const res = await updateChatById(localStorage.token, $chatId, {
			files: chatFiles
		}).catch((err) => {
			console.error('[controls autosave]', err);
			return null;
		});
		// Refresh the dedupe baseline so a later revert still saves.
		if (res) chat = res;
	};

	const MAX_DRAFT_LENGTH = 5000;
	let saveDraftTimeout: ReturnType<typeof setTimeout> | null = null;

	const saveDraft = async (draft: ChatDraft, chatId: string | null = null) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}

		if (draft.prompt !== null && draft.prompt.length < MAX_DRAFT_LENGTH) {
			saveDraftTimeout = setTimeout(async () => {
				await sessionStorage.setItem(
					`chat-input${chatId ? `-${chatId}` : ''}`,
					JSON.stringify(draft)
				);
			}, 500);
		} else {
			sessionStorage.removeItem(`chat-input${chatId ? `-${chatId}` : ''}`);
		}
	};

	const clearDraft = async (chatId: string | null = null) => {
		if (saveDraftTimeout) {
			clearTimeout(saveDraftTimeout);
		}
		await sessionStorage.removeItem(`chat-input${chatId ? `-${chatId}` : ''}`);
	};

	const moveChatHandler = async (chatId: string, projectId: string) => {
		if (chatId && projectId) {
			const res = await updateChatProjectIdById(localStorage.token, chatId, projectId).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				currentChatPage.set(1);
				await chats.set(await getChatList(localStorage.token, $currentChatPage));
				await pinnedChats.set(await getPinnedChatList(localStorage.token));

				toast.success($i18n.t('Chat moved successfully'));
			}
		} else {
			toast.error($i18n.t('Failed to move chat'));
		}
	};

	const archiveChatHandler = async (id: string) => {
		try {
			await archiveChatById(localStorage.token, id);
			currentChatPage.set(1);
			initNewChat();
			await goto('/');
			chats.set(await getChatList(localStorage.token, $currentChatPage));
			pinnedChats.set(await getPinnedChatList(localStorage.token));
			toast.success($i18n.t('Chat archived.'));
		} catch (error) {
			console.error('Error archiving chat:', error);
			toast.error($i18n.t('Failed to archive chat.'));
		}
	};

	let showDeleteConfirm = false;

	const confirmWebSearch = async () => {
		const userPrompt = pendingWebSearchPrompt;
		pendingWebSearchPrompt = null;
		webSearchConfirmed = true;

		if (userPrompt !== null) {
			await submitHandler(userPrompt);
		} else {
			webSearchEnabled = true;
		}
	};

	const deleteChatHandler = async (_id: string) => {
		showDeleteConfirm = true;
	};

	const confirmDeleteChat = async () => {
		const id = $chatId;
		if (!id) return;

		try {
			const res = await deleteChatById(localStorage.token, id);
			if (res) {
				currentChatPage.set(1);
				initNewChat();
				await goto('/');
				chats.set(await getChatList(localStorage.token, $currentChatPage));
				pinnedChats.set(await getPinnedChatList(localStorage.token));
				allTags.set(await getAllTags(localStorage.token));
				toast.success($i18n.t('Chat deleted.'));
			}
		} catch (error) {
			console.error('Error deleting chat:', error);
			toast.error(`${error}`);
		}
	};</script>

<svelte:head>
	<title>
		{$settings.showChatTitleInTab !== false && $chatTitle
			? `${$chatTitle.length > 30 ? `${$chatTitle.slice(0, 30)}...` : $chatTitle} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

<audio id="audioElement" style="display: none;" playsinline></audio>

<WebSearchConfirmDialog
	bind:show={showWebSearchConfirm}
	title={$i18n.t('Use Web Search?')}
	message={($config?.features?.web_search_confirmation_content ?? '').trim() !== ''
		? ($config?.features?.web_search_confirmation_content ?? '')
		: $i18n.t('Your query will be sent to the configured web search provider.')}
	confirmLabel={$i18n.t('Continue')}
	cancelLabel={$i18n.t('Cancel')}
	on:confirm={confirmWebSearch}
	on:cancel={() => {
		if (pendingWebSearchPrompt === null) {
			webSearchEnabled = false;
		}
		pendingWebSearchPrompt = null;
	}}
/>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete chat?')}
	on:confirm={() => {
		confirmDeleteChat();
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
		{$i18n.t('This will delete')} <span class="  font-semibold">{$chatTitle}</span>.
	</div>
</DeleteConfirmDialog>

<EventConfirmDialog
	bind:show={showEventConfirmation}
	title={eventConfirmationTitle}
	message={eventConfirmationMessage}
	input={eventConfirmationInput}
	inputPlaceholder={eventConfirmationInputPlaceholder}
	inputValue={eventConfirmationInputValue}
	inputType={eventConfirmationInputType}
	inputOptions={eventConfirmationInputOptions}
	on:confirm={(e) => {
		if (!eventCallback) return;
		if (eventConfirmationInput) {
			eventCallback(e.detail);
		} else if (e.detail) {
			eventCallback(e.detail);
		} else {
			eventCallback(true);
		}
	}}
	on:cancel={() => {
		eventCallback?.(false);
	}}
/>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? '  md:max-w-[calc(100%-var(--sidebar-width))]'
		: ' '} w-full max-w-full flex flex-col"
	id="chat-container"
>
	{#if !loading}
		<div in:fade={{ duration: 50 }} class="w-full h-full flex flex-col">
			{#if $selectedProject && ($selectedProject?.meta as { background_image_url?: string } | undefined)?.background_image_url}
				<div
					class="absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({($selectedProject?.meta as { background_image_url?: string } | undefined)?.background_image_url})  "></div>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"></div>
			{:else if $settings?.backgroundImageUrl ?? ($config?.license_metadata as { background_image_url?: string } | null | undefined)?.background_image_url ?? null}
				<div
					class="absolute top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
					style="background-image: url({$settings?.backgroundImageUrl ??
						($config?.license_metadata as { background_image_url?: string } | null | undefined)?.background_image_url})  "></div>

				<div
					class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"></div>
			{/if}

			<PaneGroup direction="horizontal" class="w-full h-full">
				<Pane defaultSize={50} minSize={30} class="h-full flex relative max-w-full flex-col">
					<FilesOverlay show={dragged} />
					<Navbar
						bind:this={navbarElement}
						{readOnly}
						showModelSelector={false}
						chat={{
							id: $chatId,
							chat: {
								title: $chatTitle,
								models: selectedModels,
								history: history,
								timestamp: Date.now()
							}
						}}
						{history}
						bind:selectedModels
						shareEnabled={!!history.currentId}
						{initNewChat}
						scrollToTop={!isNearTop ? scrollToTop : null}
						{archiveChatHandler}
						{deleteChatHandler}
						{moveChatHandler}
						onSaveTempChat={async () => {
							try {
								if (!history?.currentId || !Object.keys(history.messages).length) {
									toast.error($i18n.t('No conversation to save'));
									return;
								}
								const messages = createMessagesList(history, history.currentId);
								const title =
									messages.find((m) => m.role === 'user')?.content ?? $i18n.t('New Chat');

								const savedChat = await createNewChat(
									localStorage.token,
									{
										id: uuidv4(),
										title: title.length > 50 ? `${title.slice(0, 50)}...` : title,
										models: selectedModels,
										history: history,
										messages: messages,
										timestamp: Date.now()
									},
									null
								);

								if (savedChat) {
									temporaryChatEnabled.set(false);
									chatId.set(savedChat.id);
									chats.set(await getChatList(localStorage.token, $currentChatPage));

									await goto(`/c/${savedChat.id}`);
									toast.success($i18n.t('Conversation saved successfully'));
								}
							} catch (error) {
								console.error('Error saving conversation:', error);
								toast.error($i18n.t('Failed to save conversation'));
							}
						}}
					/>

					<div id="chat-pane" class="flex flex-col flex-auto z-10 w-full @container overflow-auto">
						{#if ($settings?.landingPageMode === 'chat' && !$selectedProject) || createMessagesList(history, history.currentId).length > 0}
							<div
								class=" pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
								id="messages-container"
								bind:this={messagesContainerElement}
								on:scroll={(_e) => {
									autoScroll =
										messagesContainerElement.scrollHeight - messagesContainerElement.scrollTop <=
										messagesContainerElement.clientHeight + 5;
									isNearTop = messagesContainerElement.scrollTop <= 100;
								}}
							>
								<div class=" h-full w-full flex flex-col">
									<Messages
										bind:this={messagesRef}
										chatId={$chatId}
										{readOnly}
										bind:history
										bind:autoScroll
										bind:prompt
										setInputText={(text) => {
											messageInput?.setText(String(text ?? ''));
										}}
										bind:selectedModels
										{atSelectedModel}
										sendMessage={toUnknownHandler(sendMessage)}
										showMessage={toUnknownHandler(showMessage)}
										submitMessage={toUnknownHandler(submitMessage)}
										continueResponse={toUnknownHandler(continueResponse)}
										regenerateResponse={toUnknownHandler(regenerateResponse)}
										mergeResponses={toUnknownHandler(mergeResponses)}
										chatActionHandler={toUnknownHandler(chatActionHandler)}
										addMessages={toUnknownHandler(addMessages)}
										pinFileToChat={toUnknownHandler(pinFileToChat)}
										{pinnedFileIds}
										topPadding={true}
										bottomPadding={files.length > 0}
										{onSelect}
									/>
								</div>
							</div>

							{#if readOnly}
								<div class="pb-6 z-10">
									<div class="text-xs text-gray-400 dark:text-gray-500 text-center">
										{$i18n.t('Read only')}
									</div>
								</div>
							{:else}
								<div class=" pb-2 pb-safe-bottom {dragged ? 'z-0' : 'z-10'}">
									<MessageInput
										bind:this={messageInput}
										{history}
										chatId={$chatId}
										onContextCompacted={toUnknownHandler(async () => {
											await loadChat();
										})}
										bind:selectedModels
										bind:files
										bind:prompt
										bind:autoScroll
										bind:selectedToolIds
										bind:selectedSkillIds
										bind:selectedFilterIds
										bind:webSearchEnabled
										bind:atSelectedModel
										bind:showCommands
										bind:dragged
										{generating}
										stopResponse={toUnknownHandler(stopResponse)}
										createMessagePair={toUnknownHandler(createMessagePair)}
										onUpload={toUnknownHandler(onUpload)}
										messageQueue={$chatRequestQueues[$chatId] ?? []}
										{chatTasks}
										onQueueSendNow={async (id: string) => {
											const queue = $chatRequestQueues[$chatId] ?? [];
											const item = queue.find((m) => m.id === id);
											if (item) {
												// Remove from queue
												chatRequestQueues.update((q) => ({
													...q,
													[$chatId]: queue.filter((m) => m.id !== id)
												}));
												await stopResponse(false);
												await tick();
												await submitPrompt(item.prompt, item.files);
											}
										}}
										onQueueEdit={(id: string) => {
											const queue = $chatRequestQueues[$chatId] ?? [];
											const item = queue.find((m) => m.id === id);
											if (item) {
												// Remove from queue
												chatRequestQueues.update((q) => ({
													...q,
													[$chatId]: queue.filter((m) => m.id !== id)
												}));
												// Set files and restore prompt to input
												files = item.files;
												messageInput?.setText(item.prompt);
											}
										}}
										onQueueDelete={(id: string) => {
											const queue = $chatRequestQueues[$chatId] ?? [];
											chatRequestQueues.update((q) => ({
												...q,
												[$chatId]: queue.filter((m) => m.id !== id)
											}));
										}}
										onChange={toUnknownHandler((data) => {
											if (!$temporaryChatEnabled) {
												saveDraft(data as ChatDraft, $chatId);
											}
										})}
										onWebSearchToggle={toUnknownHandler(handleWebSearchToggle)}
										on:submit={async (e: CustomEvent<string>) => {
											clearDraft($chatId);
											if (e.detail || files.length > 0) {
												await tick();

												submitHandler(e.detail);
											}
										}}
									/>

									<div
										class="absolute bottom-1 text-xs text-gray-500 text-center line-clamp-1 right-0 left-0"
									>
										<!-- {$i18n.t('LLMs can make mistakes. Verify important information.')} -->
									</div>
								</div>
							{/if}
						{:else}
							<div class="flex items-center h-full">
								<Placeholder
									{history}
									bind:selectedModels
									bind:messageInput
									bind:files
									bind:prompt
									bind:autoScroll
									bind:selectedToolIds
									bind:selectedSkillIds
									bind:selectedFilterIds
									bind:webSearchEnabled
									bind:atSelectedModel
									bind:showCommands
									bind:dragged
									{pendingOAuthTools}
									stopResponse={toUnknownHandler(stopResponse)}
									createMessagePair={toUnknownHandler(createMessagePair)}
									{onSelect}
									onUpload={toUnknownHandler(onUpload)}
									onWebSearchToggle={toUnknownHandler(handleWebSearchToggle)}
									onChange={(data) => {
										if (!$temporaryChatEnabled) {
											saveDraft(data as unknown as ChatDraft);
										}
									}}
									on:submit={async (e) => {
										clearDraft();
										if (e.detail || files.length > 0) {
											await tick();
											submitHandler(e.detail);
										}
									}}
								/>
							</div>
						{/if}
					</div>
				</Pane>

				<ChatControls
					bind:this={controlPaneComponent}
					bind:history
					bind:chatFiles
					bind:files
					bind:pane={controlPane}
					chatId={$chatId}
					modelId={selectedModelIds?.at(0) ?? null}
					models={selectedModelIds.reduce<Model[]>((a, e) => {
						const model = $models.find((m) => m.id === e);
						if (model) {
							return [...a, model];
						}
						return a;
					}, [])}
					submitPrompt={toUnknownHandler(submitHandler)}
					stopResponse={toUnknownHandler(stopResponse)}
					showMessage={toUnknownHandler(showMessage)}
					{eventTarget}
				/>
			</PaneGroup>
		</div>
	{:else if loading}
		<div class=" flex items-center justify-center h-full w-full">
			<div class="m-auto">
				<Spinner className="size-5" />
			</div>
		</div>
	{/if}
</div>

<style>
	::-webkit-scrollbar {
		height: 0.5rem;
		width: 0.5rem;
	}
</style>
