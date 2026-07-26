<script lang="ts">
	import DOMPurify from 'dompurify';
	import {toast} from 'svelte-sonner';

	import {marked} from 'marked';
	import {v4 as uuidv4} from 'uuid';
	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import {onMount, tick, getContext, createEventDispatcher} from 'svelte';
	import type {Component} from 'svelte';
	import {get, type Writable} from 'svelte/store';

	import {createPicker} from '$lib/utils/google-drive-picker';
	import {pickAndDownloadFile} from '$lib/utils/onedrive-file-picker';
	import {KokoroWorker} from '$lib/workers/KokoroWorker';

	const dispatch = createEventDispatcher();

	import {
		type Model,
		type Settings,
		mobile,
		settings,
		models,
		config,
		showCallOverlay,
		tools,
		skills,
		toolServers,
		terminalServers,
		user as _user,
		showControls,
		selectedTerminalId,
		TTSWorker,
		temporaryChatEnabled
	} from '$lib/stores';
	import type {ChatFile, ChatHistory, ChatMessage, Handler} from '$lib/types';
	import type {AppConfig} from '$lib/types/config';
	import type {UsageModel} from '$lib/utils/usage';

	import {convertHeicToJpeg, compressImage, createMessagesList, extractContentFromFile, extractCurlyBraceWords, extractInputVariables, getAge, getCurrentDateTime, getFormattedDate, getFormattedTime, getUserPosition, getUserTimezone, getWeekday} from '$lib/utils';
	import {uploadFile} from '$lib/apis/files';
	import {generateAutoCompletion} from '$lib/apis';
	
	import {getChatById} from '$lib/apis/chats';
	import {getProjectById} from '$lib/apis/projects';
	import {getNoteById} from '$lib/apis/notes';
	import {getSessionUser} from '$lib/apis/auths';

	import {WEBUI_API_BASE_URL, PASTED_TEXT_CHARACTER_LIMIT} from '$lib/constants';

	import {createNoteHandler} from '../notes/utils';
	import {getSuggestionRenderer} from '../common/RichTextInput/suggestions';

	import InputMenu from './MessageInput/InputMenu.svelte';
	import VoiceRecording from './MessageInput/VoiceRecording.svelte';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import FileItem from '../common/FileItem.svelte';
	import Image from '../common/Image.svelte';
	import Spinner from '../common/Spinner.svelte';

	import XMark from '../icons/XMark.svelte';

	import InputVariablesModal from './MessageInput/InputVariablesModal.svelte';
	import Voice from '../icons/Voice.svelte';
	import PlusAlt from '../icons/PlusAlt.svelte';
import CommandSuggestionList from './MessageInput/CommandSuggestionList.svelte';
	import ValvesModal from '../workspace/common/ValvesModal.svelte';
	import Note from '../icons/Note.svelte';
	import {goto} from '$app/navigation';
	import InputModal from '../common/InputModal.svelte';
	import Expand from '../icons/Expand.svelte';
	import QueuedMessageItem from './MessageInput/QueuedMessageItem.svelte';
	import TaskList from './Messages/ResponseMessage/TaskList.svelte';
	import UsageMenu from './MessageInput/UsageMenu.svelte';
	import ModelThinkingMenu from './MessageInput/ModelThinkingMenu.svelte';
	import {getLatestConversationUsage, resolveUsageModel} from '$lib/utils/usage';

	const i18n = getContext('i18n');

	type RichTextInputContent = {
		md: string;
		html: string;
		json?: unknown;
	};

	type RichTextInputHandle = {
		setText: (text?: string, options?: { focus?: boolean }) => void | Promise<void>;
		setContent: (content: unknown) => void;
		replaceVariables: (variables: Record<string, unknown>) => void;
		replaceCommandWithText: (text: string) => void | Promise<void>;
		insertContent: (content: string, options?: { focus?: boolean }) => void | Promise<void>;
		getWordAtDocPos: () => string;
		focus: () => void;
		blur: () => void;
	};

	type InputFileItem = Omit<ChatFile, 'id' | 'type' | 'content_type'> & {
		type?: string;
		content_type?: string;
		file?: unknown;
		id?: string | null;
		url?: string;
		name?: string;
		collection_name?: string;
		status?: string;
		size?: number;
		error?: string;
		itemId?: string;
		content?: string;
	};

	type ModelFilter = { id: string; [key: string]: unknown };

	type ModelWithFilters = Model & { filters?: ModelFilter[] };

	type SuggestionCommandEvent = {
		type: string;
		data: unknown;
	};

	type ChatTask = {
		id: string;
		content: string;
		status: string;
	};

	type MessageInputSettings = Settings & {
		showFormattingToolbar?: boolean;
		insertPromptAsRichText?: boolean;
		imageCompressionSize?: { width?: string | number | null; height?: string | number | null };
	};

	type PickerFileData = {
		blob: Blob;
		name: string;
	};

	type ClipboardCapableWindow = Window & {
		clipboardData?: DataTransfer | null;
	};

	type LegacyNavigator = Navigator & {
		msMaxTouchPoints?: number;
	};

	type RichTextDetailEvent<T extends Event = Event> = CustomEvent<{ event: T }>;

	const toDimensionNumber = (
		value: string | number | null | undefined
	): number | undefined => {
		if (value === null || value === undefined || value === '') return undefined;
		const num = typeof value === 'number' ? value : Number(value);
		return Number.isFinite(num) ? num : undefined;
	};

	const toFileBlob = (value: Blob | Blob[] | File): Blob =>
		Array.isArray(value) ? value[0] : value;

	const suggestionComponent = CommandSuggestionList as unknown as Component;

	const toChatDirection = (
		direction: string | undefined
	): 'ltr' | 'rtl' | 'auto' | null | undefined => {
		if (direction === 'LTR') return 'ltr';
		if (direction === 'RTL') return 'rtl';
		if (direction === 'auto') return 'auto';
		return direction?.toLowerCase() as 'ltr' | 'rtl' | 'auto' | undefined;
	};

	const getMessageInputSettings = (): MessageInputSettings => $settings as MessageInputSettings;

	export let onUpload: Handler = () => {};
	export let onChange: Handler = () => {};
	export let onWebSearchToggle: Handler = () => {};

	export let createMessagePair: Handler;
	export let stopResponse: Handler;

	export let autoScroll = false;
	export let generating = false;
	export let uploadPending = false;

	export let atSelectedModel: Model | undefined = undefined;
	export let selectedModels: string[] = [''];

	let selectedModelIds: string[] = [];
	$: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

	$: currentModel = atSelectedModel ?? $models.find((model) => model.id === selectedModelIds[0]);
	$: latestUsageInfo = getLatestConversationUsage(history?.messages);
	$: conversationUsage = latestUsageInfo?.usage ?? null;
	$: usageModel = resolveUsageModel(
		((latestUsageInfo?.modelId
			? $models.find((model) => model.id === latestUsageInfo.modelId)
			: null) ?? currentModel) as UsageModel,
		$models as UsageModel[]
	);

	export let history: ChatHistory;
	export let chatId: string | null = null;
	export let onContextCompacted: Handler = () => {};

	$: responseInProgress = Object.values(history?.messages ?? {}).some(
		(message: ChatMessage) => message?.role === 'assistant' && message?.done != true
	);
	$: isActive = generating || responseInProgress;

	export let prompt = '';
	export let files: InputFileItem[] = [];

	export let selectedToolIds: string[] = [];
	export let selectedSkillIds: string[] = [];
	export let selectedFilterIds: string[] = [];

	export let webSearchEnabled = false;

	export let messageQueue: { id: string; prompt: string; files: ChatFile[] }[] = [];
	export let onQueueSendNow: (id: string) => void = () => {};
	export let onQueueEdit: (id: string) => void = () => {};
	export let onQueueDelete: (id: string) => void = () => {};

	export let chatTasks: ChatTask[] = [];

	let inputContent: RichTextInputContent | null = null;

	let showInputVariablesModal = false;
	let inputVariablesModalCallback = (_variableValues: Record<string, unknown>) => {};
	let inputVariables: Record<string, unknown> = {};
	let inputVariableValues: Record<string, unknown> = {};

	let showValvesModal = false;
	let selectedValvesType = 'tool'; // 'tool' or 'function'
	let selectedValvesItemId: string | null = null;

	$: onChange({
		prompt,
		files: files
			.filter((file) => file.type !== 'image')
			.map((file) => {
				return {
					...file,
					user: undefined,
					access_grants: undefined
				};
			}),
		selectedToolIds,
		selectedSkillIds,
		selectedFilterIds,
		webSearchEnabled
	});

	const inputVariableHandler = async (text: string): Promise<string> => {
		inputVariables = extractInputVariables(text);

		// No variables? return the original text immediately.
		if (Object.keys(inputVariables).length === 0) {
			return text;
		}

		// Show modal and wait for the user's input.
		showInputVariablesModal = true;
		return await new Promise<string>((resolve) => {
			inputVariablesModalCallback = (variableValues) => {
				inputVariableValues = { ...inputVariableValues, ...variableValues };
				replaceVariables(inputVariableValues);
				showInputVariablesModal = false;
				resolve(text);
			};
		});
	};

	const textVariableHandler = async (text: string) => {
		if (text.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch((_err) => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});

			const clipboardItems = await navigator.clipboard.read().catch((err) => {
				console.error('Failed to read clipboard items:', err);
				return [];
			});

			for (const item of clipboardItems) {
				for (const type of item.types) {
					if (type.startsWith('image/')) {
						const blob = await item.getType(type);
						const file = new File([blob], `clipboard-image.${type.split('/')[1]}`, {
							type: type
						});

						inputFilesHandler([file]);
					}
				}
			}

			text = text.replaceAll('{{CLIPBOARD}}', clipboardText.replaceAll('\r\n', '\n'));
		}

		if (text.includes('{{USER_LOCATION}}')) {
			let location;
			try {
				location = await getUserPosition();
			} catch (_error) {
				toast.error($i18n.t('Location access not allowed'));
				location = 'LOCATION_UNKNOWN';
			}
			text = text.replaceAll('{{USER_LOCATION}}', String(location));
		}

		const sessionUser = await getSessionUser(localStorage.token);

		if (text.includes('{{USER_NAME}}')) {
			const name = sessionUser?.name || 'User';
			text = text.replaceAll('{{USER_NAME}}', name);
		}

		if (text.includes('{{USER_EMAIL}}')) {
			const email = sessionUser?.email || '';

			if (email) {
				text = text.replaceAll('{{USER_EMAIL}}', email);
			}
		}

		if (text.includes('{{USER_BIO}}')) {
			const bio = sessionUser?.bio || '';

			if (bio) {
				text = text.replaceAll('{{USER_BIO}}', bio);
			}
		}

		if (text.includes('{{USER_GENDER}}')) {
			const gender = sessionUser?.gender || '';

			if (gender) {
				text = text.replaceAll('{{USER_GENDER}}', gender);
			}
		}

		if (text.includes('{{USER_BIRTH_DATE}}')) {
			const birthDate = sessionUser?.date_of_birth || '';

			if (birthDate) {
				text = text.replaceAll('{{USER_BIRTH_DATE}}', birthDate);
			}
		}

		if (text.includes('{{USER_AGE}}')) {
			const birthDate = sessionUser?.date_of_birth || '';

			if (birthDate) {
				// calculate age using date
				const age = getAge(birthDate);
				text = text.replaceAll('{{USER_AGE}}', age);
			}
		}

		if (text.includes('{{USER_LANGUAGE}}')) {
			const language = localStorage.getItem('locale') || 'en-US';
			text = text.replaceAll('{{USER_LANGUAGE}}', language);
		}

		if (text.includes('{{CURRENT_DATE}}')) {
			const date = getFormattedDate();
			text = text.replaceAll('{{CURRENT_DATE}}', date);
		}

		if (text.includes('{{CURRENT_TIME}}')) {
			const time = getFormattedTime();
			text = text.replaceAll('{{CURRENT_TIME}}', time);
		}

		if (text.includes('{{CURRENT_DATETIME}}')) {
			const dateTime = getCurrentDateTime();
			text = text.replaceAll('{{CURRENT_DATETIME}}', dateTime);
		}

		if (text.includes('{{CURRENT_TIMEZONE}}')) {
			const timezone = getUserTimezone();
			text = text.replaceAll('{{CURRENT_TIMEZONE}}', timezone);
		}

		if (text.includes('{{CURRENT_WEEKDAY}}')) {
			const weekday = getWeekday();
			text = text.replaceAll('{{CURRENT_WEEKDAY}}', weekday);
		}

		return text;
	};

	const replaceVariables = (variables: Record<string, unknown>) => {
		console.log('Replacing variables:', variables);

		const chatInput = document.getElementById('chat-input');

		if (chatInput) {
			getChatInputHandle()?.replaceVariables(variables);
			if (shouldFocusChatInput()) getChatInputHandle()?.focus();
		}
	};

	export const setText = async (text?: string, cb?: (text: string) => void) => {
		const chatInput = document.getElementById('chat-input');

		if (chatInput) {
			if (text !== '') {
				text = await textVariableHandler(text || '');
			}

			getChatInputHandle()?.setText(text ?? '', { focus: shouldFocusChatInput() });

			if (text !== '') {
				text = await inputVariableHandler(text);
			}

			await tick();
			if (cb) await cb(text);
		}
	};

	const getCommand = () => {
		const chatInput = document.getElementById('chat-input');
		let word = '';

		if (chatInput) {
			word = getChatInputHandle()?.getWordAtDocPos() ?? '';
		}

		return word;
	};

	const replaceCommandWithText = (text: string) => {
		const chatInput = document.getElementById('chat-input');
		if (!chatInput) return;

		getChatInputHandle()?.replaceCommandWithText(text);
	};

	const insertTextAtCursor = async (text: string) => {
		const chatInput = document.getElementById('chat-input');
		if (!chatInput) return;

		text = await textVariableHandler(text);

		if (command) {
			replaceCommandWithText(text);
		} else {
			getChatInputHandle()?.insertContent(text, { focus: shouldFocusChatInput() });
		}

		await tick();
		text = await inputVariableHandler(text);
		await tick();

		const chatInputContainer = document.getElementById('chat-input-container');
		if (chatInputContainer) {
			chatInputContainer.scrollTop = chatInputContainer.scrollHeight;
		}

		await tick();
		if (chatInput && shouldFocusChatInput()) {
			chatInput.focus();
			chatInput.dispatchEvent(new Event('input'));

			const words = extractCurlyBraceWords(prompt);

			if (words.length > 0) {
				const _word = words.at(0);
				await tick();
			} else {
				chatInput.scrollTop = chatInput.scrollHeight;
			}
		}
	};

	let command = '';
	export let showCommands = false;
	$: showCommands =
		['/', '#', '@', '$', ':'].includes(command?.charAt(0)) || '\\#' === command?.slice(0, 2);
	let suggestions: Record<string, unknown>[] | null = null;

	let loaded = false;
	let recording = false;

	let isComposing = false;
	// Safari has a bug where compositionend is not triggered correctly #16615
	// when using the virtual keyboard on iOS.
	let compositionEndedAt = -2e8;
	const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
	function inOrNearComposition(event: Event) {
		if (isComposing) {
			return true;
		}
		// See https://www.stum.de/2016/06/24/handling-ime-events-in-javascript/.
		// On Japanese input method editors (IMEs), the Enter key is used to confirm character
		// selection. On Safari, when Enter is pressed, compositionend and keydown events are
		// emitted. The keydown event triggers newline insertion, which we don't want.
		// This method returns true if the keydown event should be ignored.
		// We only ignore it once, as pressing Enter a second time *should* insert a newline.
		// Furthermore, the keydown event timestamp must be close to the compositionEndedAt timestamp.
		// This guards against the case where compositionend is triggered without the keyboard
		// (e.g. character confirmation may be done with the mouse), and keydown is triggered
		// afterwards- we wouldn't want to ignore the keydown event in this case.
		if (isSafari && Math.abs(event.timeStamp - compositionEndedAt) < 500) {
			compositionEndedAt = -2e8;
			return true;
		}
		return false;
	}

	let chatInputElement: unknown = null;

	const getChatInputHandle = () => chatInputElement as RichTextInputHandle | null;

	const shouldFocusChatInput = () => !$showCallOverlay;

	const blurChatInput = () => {
		getChatInputHandle()?.blur?.();
		(document.activeElement as HTMLElement | null)?.blur?.();
	};

	$: if ($showCallOverlay) {
		blurChatInput();
	}

	let filesInputElement: HTMLInputElement | null = null;

	let inputFiles: FileList | null = null;

	let showInputModal = false;

	export let dragged = false;
	let shiftKey = false;

	export let placeholder = '';

	type ModelCapability = 'vision' | 'file_upload' | 'web_search' | 'terminal';
	type ModelCapabilitiesById = Record<string, Partial<Record<ModelCapability, boolean>>>;

	let modelCapabilitiesById: ModelCapabilitiesById = {};
	$: modelCapabilitiesById = Object.fromEntries(
		($models ?? []).map((model) => [model.id, model.info?.meta?.capabilities ?? {}])
	);

	const getCapableModelIds = (
		modelIds: string[],
		capability: ModelCapability,
		capabilitiesById: ModelCapabilitiesById
	) => modelIds.filter((id: string) => capabilitiesById[id]?.[capability] ?? true);

	let visionCapableModels = [];
	$: visionCapableModels = getCapableModelIds(selectedModelIds, 'vision', modelCapabilitiesById);

	let fileUploadCapableModels = [];
	$: fileUploadCapableModels = getCapableModelIds(
		selectedModelIds,
		'file_upload',
		modelCapabilitiesById
	);

	let webSearchCapableModels = [];
	$: webSearchCapableModels = getCapableModelIds(
		selectedModelIds,
		'web_search',
		modelCapabilitiesById
	);

	let terminalCapableModels = [];
	$: terminalCapableModels = getCapableModelIds(
		selectedModelIds,
		'terminal',
		modelCapabilitiesById
	);

	let showTerminalButton = false;
	$: showTerminalButton =
		terminalCapableModels.length > 0 &&
		(($terminalServers ?? []).some((t) => t.id) ||
			(($_user?.role === 'admin' ||
				($_user?.permissions?.features?.direct_tool_servers ?? true)) &&
				(($terminalServers ?? []).some((t) => !t.id) ||
					($settings?.terminalServers ?? []).some((s) => s.url))));

	let toggleFilters: ModelFilter[] = [];
	$: toggleFilters = (atSelectedModel?.id ? [atSelectedModel.id] : selectedModels)
		.map(
			(id: string) =>
				(($models.find((model) => model.id === id) ?? {}) as ModelWithFilters).filters ?? []
		)
		.reduce(
			(acc: ModelFilter[], filters: ModelFilter[]) =>
				acc.filter((f1) => filters.some((f2) => f2.id === f1.id)),
			[] as ModelFilter[]
		);

	let showToolsButton = false;
	$: showToolsButton = ($tools ?? []).length > 0 || ($toolServers ?? []).length > 0;

	let showSkillsButton = false;
	$: showSkillsButton = Boolean(($skills ?? []).some((skill) => skill.is_active));

	let showWebSearchButton = false;
	$: showWebSearchButton = Boolean(
		selectedModelIds.length === webSearchCapableModels.length &&
			$config?.features?.enable_web_search &&
			($_user?.role === 'admin' || $_user?.permissions?.features?.web_search)
	);

	$: inputMenuToggleFilters = toggleFilters as {
		id: string;
		name: string;
		description?: string;
		icon?: string;
	}[];
	$: showIntegrationsButton =
		showToolsButton ||
		showSkillsButton ||
		(toggleFilters && toggleFilters.length > 0);

	// Clear selected terminal when model doesn't support terminal
	$: if ($selectedTerminalId && terminalCapableModels.length === 0) {
		selectedTerminalId.set(null);
	}

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		element?.scrollTo({
			top: element.scrollHeight,
			behavior: 'smooth'
		});
	};

	const screenCaptureHandler = async () => {
		try {
			// Request screen media
			const mediaStream = await navigator.mediaDevices.getDisplayMedia({
				video: true,
				audio: false
			});
			// Once the user selects a screen, temporarily create a video element
			const video = document.createElement('video');
			video.srcObject = mediaStream;
			// Ensure the video loads without affecting user experience or tab switching
			await video.play();
			// Set up the canvas to match the video dimensions
			const canvas = document.createElement('canvas');
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			// Grab a single frame from the video stream using the canvas
			const context = canvas.getContext('2d');
			if (!context) return;
			context.drawImage(video, 0, 0, canvas.width, canvas.height);
			// Stop all video tracks (stop screen sharing) after capturing the image
			mediaStream.getTracks().forEach((track) => track.stop());

			// bring back focus to this current tab, so that the user can see the screen capture
			window.focus();

			// Convert the canvas to a Base64 image URL
			const imageUrl = canvas.toDataURL('image/png');
			const blob = await (await fetch(imageUrl)).blob();
			const file = new File([blob], `screen-capture-${Date.now()}.png`, { type: 'image/png' });
			inputFilesHandler([file]);
			// Clean memory: Clear video srcObject
			video.srcObject = null;
		} catch (error) {
			// Handle any errors (e.g., user cancels screen sharing)
			console.error('Error capturing screen:', error);
		}
	};

	const uploadFileHandler = async (
		file: File,
		process = true,
		itemData: Partial<InputFileItem> = {}
	) => {
		if ($_user?.role !== 'admin' && !($_user?.permissions?.chat?.file_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload files.'));
			return null;
		}

		if (fileUploadCapableModels.length !== selectedModelIds.length) {
			toast.error($i18n.t('Model(s) do not support file upload'));
			return null;
		}

		const tempItemId = uuidv4();
		const fileItem: InputFileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId: tempItemId,
			...itemData
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		files = [...files, fileItem];

		if (!$temporaryChatEnabled) {
			try {
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

				// During the file upload, file content is automatically extracted.
				const uploadedFile = await uploadFile(localStorage.token, file, metadata, process);

				if (uploadedFile) {
					console.log('File upload completed:', {
						id: uploadedFile.id,
						name: fileItem.name,
						collection: uploadedFile?.meta?.collection_name
					});

					if (uploadedFile.error) {
						console.warn('File upload warning:', uploadedFile.error);
						toast.warning(uploadedFile.error);
					}

					fileItem.status = 'uploaded';
					fileItem.file = uploadedFile;
					fileItem.id = uploadedFile.id != null ? String(uploadedFile.id) : undefined;
					fileItem.collection_name =
						uploadedFile?.meta?.collection_name || uploadedFile?.collection_name;
					fileItem.content_type = uploadedFile.meta?.content_type || uploadedFile.content_type;
					fileItem.url = `${uploadedFile.id}`;

					files = files;
				} else {
					files = files.filter((item) => item?.itemId !== tempItemId);
				}
			} catch (e) {
				toast.error(`${e}`);
				files = files.filter((item) => item?.itemId !== tempItemId);
			}
		} else {
			// If temporary chat is enabled, we just add the file to the list without uploading it.

			const content = await extractContentFromFile(file).catch((error) => {
				toast.error(
					$i18n.t('Failed to extract content from the file: {{error}}', { error: error })
				);
				return null;
			});

			if (content === null) {
				toast.error($i18n.t('Failed to extract content from the file.'));
				files = files.filter((item) => item?.itemId !== tempItemId);
				return null;
			} else {
				console.log('Extracted content from file:', {
					name: file.name,
					size: file.size,
					content: content
				});

				fileItem.status = 'uploaded';
				fileItem.type = 'text';
				fileItem.content = typeof content === 'string' ? content : String(content);
				fileItem.id = uuidv4(); // Temporary ID for the file

				files = files;
			}
		}
	};

	const inputFilesHandler = async (inputFiles: File[]) => {
		console.log('Input files handler called with:', inputFiles);

		const maxCount = $config?.file?.max_count;
		if (maxCount != null && files.length + inputFiles.length > maxCount) {
			toast.error(
				$i18n.t(`You can only chat with a maximum of {{maxCount}} file(s) at a time.`, {
					maxCount
				})
			);
			return;
		}

		inputFiles.forEach(async (file: File) => {
			console.log('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.log('File exceeds max size limit:', {
					fileSize: file.size,
					maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
				});
				toast.error(
					$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
						maxSize: $config?.file?.max_size
					})
				);
				return;
			}

			if (file.type.startsWith('image/')) {
				if (visionCapableModels.length === 0) {
					toast.error($i18n.t('Selected model(s) do not support image inputs'));
					return;
				}

				const compressImageHandler = async (
					imageUrl: string,
					inputSettings: MessageInputSettings = getMessageInputSettings(),
					inputConfig: AppConfig | undefined = $config
				) => {
					// Quick shortcut so we don’t do unnecessary work.
					const settingsCompression = inputSettings?.imageCompression ?? false;
					const configWidth = inputConfig?.file?.image_compression?.width ?? null;
					const configHeight = inputConfig?.file?.image_compression?.height ?? null;

					// If neither settings nor config wants compression, return original URL.
					if (!settingsCompression && !configWidth && !configHeight) {
						return imageUrl;
					}

					// Default to null (no compression unless set)
					let width: number | undefined;
					let height: number | undefined;

					// If user/settings want compression, pick their preferred size.
					if (settingsCompression) {
						width = toDimensionNumber(inputSettings?.imageCompressionSize?.width);
						height = toDimensionNumber(inputSettings?.imageCompressionSize?.height);
					}

					// Apply config limits as an upper bound if any
					if (configWidth != null && (width == null || width > configWidth)) {
						width = configWidth;
					}
					if (configHeight != null && (height == null || height > configHeight)) {
						height = configHeight;
					}

					// Do the compression if required
					if (width || height) {
						return await compressImage(imageUrl, width, height);
					}
					return imageUrl;
				};

				let reader = new FileReader();

				reader.onload = async (event: ProgressEvent<FileReader>) => {
					const result = event.target?.result;
					if (typeof result !== 'string') return;

					let imageUrl: string = result;

					// Compress the image if settings or config require it
					imageUrl = await compressImageHandler(imageUrl, getMessageInputSettings(), $config);

					if ($temporaryChatEnabled) {
						files = [
							...files,
							{
								type: 'image',
								url: imageUrl
							}
						];
					} else {
						const blob = await (await fetch(imageUrl)).blob();
						const compressedFile = new File([blob], file.name, { type: file.type });

						uploadFileHandler(compressedFile, false);
					}
				};

				reader.readAsDataURL(
					file.type === 'image/heic'
						? toFileBlob(await convertHeicToJpeg(file))
						: file
				);
			} else {
				uploadFileHandler(file);
			}
		});
	};

	const createNote = async () => {
		if (inputContent?.md.trim() === '' && inputContent?.html.trim() === '') {
			toast.error($i18n.t('Cannot create an empty note.'));
			return;
		}

		const res = await createNoteHandler(
			dayjs().format('YYYY-MM-DD'),
			inputContent?.md ?? '',
			inputContent?.html ?? ''
		);

		if (res) {
			// Clear the input content saved in session storage.
			sessionStorage.removeItem('chat-input');
			goto(`/notes/${res.id}`);
		}
	};

	const onDragOver = (e: DragEvent) => {
		e.preventDefault();

		// Check if a file or a sidebar chat/folder item is being dragged.
		// Use a custom MIME type to distinguish intentional drags from SortableJS reorder drags
		// (e.g. Notes, Workspace, pinned Models), which also set 'text/plain'.
		if (
			e.dataTransfer?.types?.includes('Files') ||
			e.dataTransfer?.types?.includes('application/x-open-webui-drag')
		) {
			dragged = true;
		} else {
			dragged = false;
		}
	};

	const onDragLeave = (e: DragEvent) => {
		if ((e.currentTarget as HTMLElement)?.contains(e.relatedTarget as Node)) {
			return;
		}
		dragged = false;
	};

	const onDrop = async (e: DragEvent) => {
		e.preventDefault();
		console.log(e);

		// Check if the dropped data is a sidebar chat, project, note, or model item
		const textData = e.dataTransfer?.getData('text/plain');
		if (textData) {
			try {
				const data = JSON.parse(textData);
				if (data.type === 'chat' && data.id) {
					// Fetch the chat to get its title, then add as a reference chat
					const chat = await getChatById(localStorage.token, data.id);
					if (chat) {
						const chatItem = {
							type: 'chat',
							id: chat.id,
							name: chat.title,
							collection_name: '',
							status: 'processed'
						};
						if (!files.find((f) => f.id === chatItem.id)) {
							files = [...files, chatItem];
						}
					}
					dragged = false;
					e.stopPropagation();
					return;
				} else if (data.type === 'project' && data.id) {
					// Fetch the project to get its name, then add as a reference project
					const project = await getProjectById(localStorage.token, data.id);
					if (project) {
						const projectItem = {
							type: 'project',
							id: project.id,
							name: project.name,
							status: 'processed'
						};
						if (!files.find((f) => f.id === projectItem.id)) {
							files = [...files, projectItem];
						}
					}
					dragged = false;
					e.stopPropagation();
					return;
				} else if (data.type === 'note' && data.id) {
					// Fetch the note to get its title, then add as a reference note
					const note = await getNoteById(localStorage.token, data.id);
					if (note) {
						const noteItem = {
							type: 'note',
							id: note.id,
							name: note.title,
							status: 'processed'
						};
						if (!files.find((f) => f.id === noteItem.id)) {
							files = [...files, noteItem];
						}
					}
					dragged = false;
					e.stopPropagation();
					return;
				} else if (data.type === 'model' && data.id) {
					// Find the model from the store and set as @-selected model
					const model = $models.find((m) => m.id === data.id);
					if (model) {
						atSelectedModel = model;
					}
					dragged = false;
					e.stopPropagation();
					return;
				}
			} catch (_) {
				// Not valid JSON — fall through to file handling
			}
		}

		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);
			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				inputFilesHandler(inputFiles);
			}
		}

		dragged = false;
	};

	const onKeyDown = (e: KeyboardEvent) => {
		if (e.key === 'Shift') {
			shiftKey = true;
		}

		// Cmd/Ctrl+Shift+L to toggle dictation
		if (e.key.toLowerCase() === 'l' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
			e.preventDefault();
			if (recording) {
				// Confirm and stop recording
				document.getElementById('confirm-recording-button')?.click();
			} else {
				// Start recording (same logic as voice-input-button click)
				document.getElementById('voice-input-button')?.click();
			}
			return;
		}

		if (e.key === 'Escape') {
			console.log('Escape');
			dragged = false;
		}
	};

	const onKeyUp = (e: KeyboardEvent) => {
		if (e.key === 'Shift') {
			shiftKey = false;
		}
	};

	const onFocus = () => {};

	const onBlur = () => {
		shiftKey = false;
	};

	const handleSuggestionSelect = (e: SuggestionCommandEvent) => {
		const { type, data } = e;

		if (type === 'model') {
			atSelectedModel = data as Model;
		}

		if (shouldFocusChatInput()) document.getElementById('chat-input')?.focus();
	};

	const handleSuggestionUpload = (e: SuggestionCommandEvent) => {
		const { type, data } = e;

		if (type === 'file') {
			const fileData = data as InputFileItem;
			if (files.find((f) => f.id === fileData.id)) {
				return;
			}
			files = [
				...files,
				{
					...fileData,
					status: 'processed'
				}
			];
		} else {
			if (files.find((f) => f.url === data || f.name === data)) {
				return;
			}
			onUpload(e);
		}
	};

	const handleInputModalChange = (content: RichTextInputContent) => {
		console.log(content);
		getChatInputHandle()?.setContent(content?.json ?? null);
	};

	const uploadOneDriveHandler: Handler = async (authorityType) => {
		try {
			const fileData = (await pickAndDownloadFile(
				authorityType as 'personal' | 'organizations' | undefined
			)) as PickerFileData | null;
			if (fileData) {
				const file = new File([fileData.blob], fileData.name, {
					type: fileData.blob.type || 'application/octet-stream'
				});
				await uploadFileHandler(file);
			} else {
				console.log('No file was selected from OneDrive');
			}
		} catch (error: unknown) {
			console.error('OneDrive Error:', error);
		}
	};

	onMount(() => {
		suggestions = [
			{
				char: '@',
				render: getSuggestionRenderer(suggestionComponent, {
					i18n,
					onSelect: handleSuggestionSelect,
					insertTextHandler: insertTextAtCursor,
					onUpload: handleSuggestionUpload
				})
			},
			{
				char: '/',
				render: getSuggestionRenderer(suggestionComponent, {
					i18n,
					onSelect: handleSuggestionSelect,
					insertTextHandler: insertTextAtCursor,
					onUpload: handleSuggestionUpload
				})
			},
			{
				char: '#',
				render: getSuggestionRenderer(suggestionComponent, {
					i18n,
					onSelect: handleSuggestionSelect,
					insertTextHandler: insertTextAtCursor,
					onUpload: handleSuggestionUpload
				})
			},
			{
				char: '$',
				render: getSuggestionRenderer(suggestionComponent, {
					i18n,
					onSelect: (_e: SuggestionCommandEvent) => {
						if (shouldFocusChatInput()) document.getElementById('chat-input')?.focus();
					},
					insertTextHandler: insertTextAtCursor,
					onUpload: () => {}
				})
			},
			{
				char: ':',
				allowSpaces: false,
				command: ({
					editor,
					range,
					props
				}: {
					editor: {
						chain: () => {
							focus: () => {
								deleteRange: (range: unknown) => {
									insertContent: (emoji: string) => { run: () => void };
								};
							};
						};
					};
					range: unknown;
					props: { id: string };
				}) => {
					// Convert the Unicode hex codepoint (e.g. "1F44B") to the actual emoji character (👋)
					const codepoint = props.id;
					const emoji = String.fromCodePoint(parseInt(codepoint, 16));
					editor.chain().focus().deleteRange(range).insertContent(emoji).run();
				},
				render: getSuggestionRenderer(suggestionComponent, {
					i18n,
					onSelect: (_e: SuggestionCommandEvent) => {
						if (shouldFocusChatInput()) document.getElementById('chat-input')?.focus();
					},
					insertTextHandler: insertTextAtCursor,
					onUpload: () => {}
				})
			}
		];
		loaded = true;

		window.setTimeout(() => {
			if (shouldFocusChatInput()) {
				document.getElementById('chat-input')?.focus();
			}
		}, 0);

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		let isDestroyed = false;
		let dropzoneElement: HTMLElement | null = null;
		const initialize = async () => {
			await tick();
			if (isDestroyed) return;

			dropzoneElement = document.getElementById('chat-pane');
			if (dropzoneElement) {
				dropzoneElement.addEventListener('dragover', onDragOver, true);
				dropzoneElement.addEventListener('drop', onDrop, true);
				dropzoneElement.addEventListener('dragleave', onDragLeave);
			}
		};
		initialize();

		return () => {
			isDestroyed = true;

			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);

			window.removeEventListener('focus', onFocus);
			window.removeEventListener('blur', onBlur);

			if (dropzoneElement) {
				dropzoneElement.removeEventListener('dragover', onDragOver, true);
				dropzoneElement.removeEventListener('drop', onDrop, true);
				dropzoneElement.removeEventListener('dragleave', onDragLeave);
			}
		};
	});
</script>

<InputVariablesModal
	bind:show={showInputVariablesModal}
	variables={inputVariables}
	onSave={inputVariablesModalCallback as unknown as (_e: Event) => void}
/>

<ValvesModal
	bind:show={showValvesModal}
	userValves={true}
	type={selectedValvesType}
	id={selectedValvesItemId as never}
	on:save={async () => {
		await tick();
	}}
/>

<InputModal
	bind:show={showInputModal}
	value={prompt as never}
	inputContent={inputContent as never}
	onChange={handleInputModalChange as () => void}
	onClose={async () => {
		await tick();
		if (shouldFocusChatInput()) getChatInputHandle()?.focus();
	}}
/>

{#if loaded}
	<div class="w-full font-primary">
		<div class=" mx-auto inset-x-0 bg-transparent flex justify-center">
			<div
				class="flex flex-col px-3 {($settings?.widescreenMode ?? null)
					? 'max-w-full'
					: 'max-w-6xl'} w-full"
			>
				<div class="relative">
					{#if autoScroll === false && history?.currentId}
						<div
							class=" absolute -top-12 left-0 right-0 flex justify-center z-30 pointer-events-none"
						>
							<button
								aria-label={$i18n.t('Scroll to bottom')}
								class=" bg-white border border-gray-100 dark:border-none dark:bg-white/20 p-1.5 rounded-full pointer-events-auto"
								on:click={() => {
									autoScroll = true;
									scrollToBottom();
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-5 h-5"
								>
									<path
										fill-rule="evenodd"
										d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
										clip-rule="evenodd"></path>
								</svg>
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class="bg-transparent">
			<div
				class="{($settings?.widescreenMode ?? null)
					? 'max-w-full'
					: 'max-w-6xl'} px-2.5 mx-auto inset-x-0"
			>
				<div class="">
					<input
						bind:this={filesInputElement}
						bind:files={inputFiles}
						type="file"
						hidden
						multiple
						on:change={async () => {
							if (inputFiles && inputFiles.length > 0) {
								const _inputFiles = Array.from(inputFiles);
								inputFilesHandler(_inputFiles);
							} else {
								toast.error($i18n.t(`File not found.`));
							}

							if (filesInputElement) {
								filesInputElement.value = '';
							}
						}}
					/>

					<div class={recording ? '' : 'hidden'}>
						<VoiceRecording
							bind:recording
							onCancel={async () => {
								recording = false;

								await tick();
								if (shouldFocusChatInput()) document.getElementById('chat-input')?.focus();
							}}
							onConfirm={async (data) => {
								const { text, _filename } = data;

								recording = false;

								await tick();
								await insertTextAtCursor(`${text}`);
								await tick();
								if (shouldFocusChatInput()) document.getElementById('chat-input')?.focus();

								if ($settings?.speechAutoSend ?? false) {
									dispatch('submit', prompt);
								}
							}}
						/>
					</div>
					<form
						class="w-full flex flex-col gap-1.5 {recording ? 'hidden' : ''}"
						on:submit|preventDefault={() => {
							// check if selectedModels support image input
							dispatch('submit', prompt);
						}}
					>
						<button
							id="generate-message-pair-button"
							class="hidden"
							aria-label={$i18n.t('Generate message pair')}
							on:click={() => createMessagePair(prompt)}
						></button>

						<!-- Task list display -->
						{#if isActive && chatTasks.length > 0}
							<div class="mx-1">
								<TaskList tasks={chatTasks} />
							</div>
						{/if}

						<!-- Queued messages display -->
						{#if messageQueue.length > 0}
							<div
								class="mb-1 mx-2 py-0.5 px-1.5 rounded-2xl bg-white dark:bg-gray-900/60 border border-gray-100 dark:border-gray-800/50 overflow-x-hidden overflow-y-auto max-h-[25vh]"
							>
								{#each messageQueue as queuedMessage (queuedMessage.id)}
									<QueuedMessageItem
										id={queuedMessage.id}
										content={queuedMessage.prompt}
										files={queuedMessage.files}
										onSendNow={onQueueSendNow}
										onEdit={onQueueEdit}
										onDelete={onQueueDelete}
									/>
								{/each}
							</div>
						{/if}

						<div
							id="message-input-container"
							class="flex-1 flex flex-col relative w-full shadow-lg rounded-3xl border {$temporaryChatEnabled
								? 'border-dashed border-gray-100 dark:border-gray-800 hover:border-gray-200 focus-within:border-gray-200 hover:dark:border-gray-700 focus-within:dark:border-gray-700'
								: ' border-gray-100/30 dark:border-gray-850/30 hover:border-gray-200 focus-within:border-gray-100 hover:dark:border-gray-800 focus-within:dark:border-gray-800'}  transition px-1 bg-white/5 dark:bg-gray-500/5 backdrop-blur-sm dark:text-gray-100"
							dir={toChatDirection($settings?.chatDirection)}
						>
							{#if atSelectedModel !== undefined}
								<div class="px-3 pt-3 text-left w-full flex flex-col z-10">
									<div class="flex items-center justify-between w-full">
										<div class="pl-[1px] flex items-center gap-2 text-sm dark:text-gray-500">
											<img
												alt="model profile"
												class="size-3.5 max-w-[28px] object-cover rounded-full"
												src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${$models.find((model) => model.id === atSelectedModel?.id)?.id ?? ''}&lang=${$i18n.language}`}
											/>
											<div class="translate-y-[0.5px]">
												<span class="">{atSelectedModel.name}</span>
											</div>
										</div>
										<div>
											<button
												class="flex items-center dark:text-gray-500"
												on:click={() => {
													atSelectedModel = undefined;
												}}
											>
												<XMark />
											</button>
										</div>
									</div>
								</div>
							{/if}

							{#if files.length > 0}
								<div
									class="mx-2 mt-2.5 pb-1.5 flex items-center flex-wrap gap-2"
									dir={toChatDirection($settings?.chatDirection)}
								>
									{#each files as file, fileIdx}
										{#if file.type === 'image' || String(file?.content_type ?? '').startsWith('image/')}
											{@const fileUrl =
												(file.url?.startsWith('data') || file.url?.startsWith('http')
													? file.url
													: `${WEBUI_API_BASE_URL}/files/${file.url ?? ''}${file?.content_type ? '/content' : ''}`) ?? ''}
											<div class=" relative group">
												<div class="relative flex items-center">
													<Image
														src={fileUrl}
														alt=""
														imageClassName=" size-10 rounded-xl object-cover"
													/>
													{#if selectedModelIds.length !== visionCapableModels.length}
														<Tooltip
															className=" absolute top-1 left-1"
															content={$i18n.t('{{ models }}', {
																models: selectedModelIds
																	.filter((id) => !visionCapableModels.includes(id))
																	.join(', ')
															})}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 24 24"
																fill="currentColor"
																aria-hidden="true"
																class="size-4 fill-yellow-300"
															>
																<path
																	fill-rule="evenodd"
																	d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
																	clip-rule="evenodd"></path>
															</svg>
														</Tooltip>
													{/if}
												</div>
												<div class=" absolute -top-1 -right-1">
													<button
														class=" bg-white text-black border border-white rounded-full {($settings?.highContrastMode ??
														false)
															? ''
															: 'outline-hidden focus:outline-hidden group-hover:visible invisible transition'}"
														type="button"
														aria-label={$i18n.t('Remove file')}
														on:click={() => {
															files.splice(fileIdx, 1);
															files = files;
														}}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 20 20"
															fill="currentColor"
															aria-hidden="true"
															class="size-4"
														>
															<path
																d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"></path>
														</svg>
													</button>
												</div>
											</div>
										{:else}
											<FileItem
												item={file as never}
												name={file.name ?? ''}
												type={file.type ?? 'file'}
												size={file.size ?? 0}
												loading={file.status === 'uploading'}
												dismissible={true}
												edit={true}
												small={true}
												modal={['file', 'collection'].includes(file?.type ?? '')}
												on:dismiss={async () => {
													// Remove from UI state
													files.splice(fileIdx, 1);
													files = files;
												}}
												on:click={() => {
													console.log(file);
												}}
											/>
										{/if}
									{/each}
								</div>
							{/if}

							<div class="px-2.5">
								<div
									class="scrollbar-hidden rtl:text-right ltr:text-left bg-transparent dark:text-gray-100 outline-hidden w-full pb-1 px-1 resize-none h-fit max-h-96 overflow-auto {files.length ===
									0
										? atSelectedModel !== undefined
											? 'pt-1.5'
											: 'pt-2.5'
										: ''}"
									id="chat-input-container"
								>
									{#if prompt.split('\n').length > 2}
										<div class="fixed top-0 right-0 z-20">
											<div class="mt-2.5 mr-3">
												<button
													type="button"
													class="p-1 rounded-lg hover:bg-gray-100/50 dark:hover:bg-gray-800/50"
													aria-label={$i18n.t('Expand input')}
													on:click={async () => {
														showInputModal = true;
													}}
												>
													<Expand />
												</button>
											</div>
										</div>
									{/if}

									{#if suggestions}
										{#key $settings?.richTextInput ?? true}
											{#key getMessageInputSettings().showFormattingToolbar ?? false}
												<RichTextInput
													bind:this={chatInputElement}
													id="chat-input"
													editable={!showInputModal && !$showCallOverlay}
											autofocusEnabled={!$showCallOverlay}
													onChange={((
														content: RichTextInputContent
													) => {
														prompt = content.md;
														inputContent = content;
														command = getCommand();
													}) as unknown as (_e: Event) => void}
													json={true}
													richText={$settings?.richTextInput ?? true}
													messageInput={true}
													showFormattingToolbar={getMessageInputSettings().showFormattingToolbar ?? false}
													floatingMenuPlacement={'top-start'}
													insertPromptAsRichText={getMessageInputSettings().insertPromptAsRichText ?? false}
													shiftEnter={!($settings?.ctrlEnterToSend ?? false) &&
														!$mobile &&
														!(
															'ontouchstart' in window ||
															navigator.maxTouchPoints > 0 ||
															((navigator as LegacyNavigator).msMaxTouchPoints ?? 0) > 0
														)}
													placeholder={placeholder ? placeholder : $i18n.t('Send a Message')}
													largeTextAsFile={($settings?.largeTextAsFile ?? false) && !shiftKey}
													autocomplete={$config?.features?.enable_autocomplete_generation &&
														($settings?.promptAutocomplete ?? false)}
													generateAutoCompletion={((async (text: string) => {
														if (selectedModelIds.length === 0 || !selectedModelIds.at(0)) {
															return null;
														}

														const modelId = selectedModelIds.at(0);
														if (!modelId) {
															return null;
														}

														const res = await generateAutoCompletion(
															localStorage.token,
															modelId,
															text,
															history?.currentId
																? (createMessagesList(
																		history,
																		history.currentId
																	) as object[])
																: undefined
														).catch((error) => {
															console.log(error);

															return null;
														});

														console.log(res);
														return res;
													}) as Handler)}
													suggestions={suggestions as never}
													oncompositionstart={() => (isComposing = true)}
													oncompositionend={(e) => {
														compositionEndedAt = e.timeStamp;
														isComposing = false;
													}}
													on:keydown={async (e: RichTextDetailEvent<KeyboardEvent>) => {
														const event = e.detail.event;

														const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac
														const suggestionsContainerElement =
															document.getElementById('suggestions-container');

														if (event.key === 'Escape') {
															stopResponse();
														}

														if (prompt === '' && event.key == 'ArrowUp') {
															event.preventDefault();

															const userMessageElement = [
																...document.getElementsByClassName('user-message')
															]?.at(-1);

															if (userMessageElement) {
																userMessageElement.scrollIntoView({ block: 'center' });
																const editButton = [
																	...document.getElementsByClassName('edit-user-message-button')
																]?.at(-1) as HTMLElement | undefined;

																editButton?.click();
															}
														}

														if (!suggestionsContainerElement) {
															if (
																!$mobile ||
																!(
																	'ontouchstart' in window ||
																	navigator.maxTouchPoints > 0 ||
																	((navigator as LegacyNavigator).msMaxTouchPoints ?? 0) > 0
																)
															) {
																if (inOrNearComposition(event)) {
																	return;
																}

																// Uses keyCode '13' for Enter key for chinese/japanese keyboards.
																//
																// Depending on the user's settings, it will send the message
																// either when Enter is pressed or when Ctrl+Enter is pressed.
																const enterPressed =
																	($settings?.ctrlEnterToSend ?? false)
																		? (event.key === 'Enter' || event.keyCode === 13) &&
																			isCtrlPressed
																		: (event.key === 'Enter' || event.keyCode === 13) &&
																			!event.shiftKey;

																if (enterPressed) {
																	event.preventDefault();
																	if (prompt !== '' || files.length > 0) {
																		dispatch('submit', prompt);
																	}
																}
															}
														}

														if (event.key === 'Escape') {
															console.log('Escape');
															atSelectedModel = undefined;
															selectedToolIds = [];
															selectedFilterIds = [];

															webSearchEnabled = false;
														}
													}}
													on:paste={async (e: RichTextDetailEvent<ClipboardEvent>) => {
														const event = e.detail.event;
														console.log(event);

														const clipboardData =
															event.clipboardData ||
															(window as ClipboardCapableWindow).clipboardData;

														if (clipboardData && clipboardData.items) {
															for (const item of clipboardData.items) {
																if (item.type === 'text/plain') {
																	if (($settings?.largeTextAsFile ?? false) && !shiftKey) {
																		const text = clipboardData.getData('text/plain');

																		if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
																			event.preventDefault();
																			const blob = new Blob([text], { type: 'text/plain' });
																			const file = new File(
																				[blob],
																				`Pasted_Text_${Date.now()}.txt`,
																				{
																					type: 'text/plain'
																				}
																			);

																			await uploadFileHandler(file, true);
																		}
																	}
																} else {
																	const file = item.getAsFile();
																	if (file) {
																		await inputFilesHandler([file]);
																		event.preventDefault();
																	}
																}
															}
														}
													}}
												/>
											{/key}
										{/key}
									{/if}
								</div>
							</div>

							<div class=" flex justify-between mt-0.5 mb-2.5 mx-0.5 max-w-full" dir="ltr">
								<div class="ml-1 self-end flex items-center shrink-0">
									<InputMenu
										bind:files
										selectedModels={selectedModelIds}
										{fileUploadCapableModels}
										{showWebSearchButton}
										bind:webSearchEnabled
										{onWebSearchToggle}
										{showTerminalButton}
										{showIntegrationsButton}
										toggleFilters={inputMenuToggleFilters}
										bind:selectedToolIds
										bind:selectedSkillIds
										bind:selectedFilterIds
										onShowValves={(e: unknown) => {
											const { type, id } = e as { type: string; id: string };
											selectedValvesType = type;
											selectedValvesItemId = id;
											showValvesModal = true;
										}}
										{screenCaptureHandler}
										inputFilesHandler={inputFilesHandler as Handler}
										uploadFilesHandler={() => {
											filesInputElement?.click();
										}}
										uploadGoogleDriveHandler={async () => {
											try {
												const fileData = (await createPicker()) as PickerFileData | null;
												if (fileData) {
													const file = new File([fileData.blob], fileData.name, {
														type: fileData.blob.type
													});
													await uploadFileHandler(file);
												} else {
													console.log('No file was selected from Google Drive');
												}
											} catch (error: unknown) {
												console.error('Google Drive Error:', error);
												const message = error instanceof Error ? error.message : String(error);
												toast.error(
													$i18n.t('Error accessing Google Drive: {{error}}', {
														error: message
													})
												);
											}
										}}
										uploadOneDriveHandler={uploadOneDriveHandler}
										{onUpload}
										onClose={async () => {
											await tick();

											const chatInput = document.getElementById('chat-input');
											if (shouldFocusChatInput()) chatInput?.focus();
										}}
									>
										<button
											type="button"
											id="input-menu-button"
											class="bg-transparent hover:bg-gray-100 text-gray-700 dark:text-white dark:hover:bg-gray-800 rounded-full size-8 flex justify-center items-center outline-hidden focus:outline-hidden shrink-0"
											aria-label={$i18n.t('More')}
										>
											<PlusAlt className="size-5.5" />
										</button>
									</InputMenu>
								</div>

								<div
									class="self-end flex items-center space-x-1 mr-1 gap-[0.5px] {$mobile
										? 'min-w-0 shrink'
										: 'shrink-0'}"
								>
									{#if isActive && prompt === '' && files.length === 0}
										<div class=" flex items-center">
											<Tooltip content={$i18n.t('Stop')}>
												<button
													aria-label={$i18n.t('Stop')}
													class="bg-white hover:bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-1.5"
													on:click={() => {
														stopResponse();
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 24 24"
														fill="currentColor"
														class="size-5"
													>
														<path
															fill-rule="evenodd"
															d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm6-2.438c0-.724.588-1.312 1.313-1.312h4.874c.725 0 1.313.588 1.313 1.313v4.874c0 .725-.588 1.313-1.313 1.313H9.564a1.312 1.312 0 01-1.313-1.313V9.564z"
															clip-rule="evenodd"></path>
													</svg>
												</button>
											</Tooltip>
										</div>
									{:else}
										{#if prompt !== '' && !history?.currentId && !$selectedTerminalId && ($config?.features?.enable_notes ?? false) && ($_user?.role === 'admin' || ($_user?.permissions?.features?.notes ?? true))}
											<!-- {$i18n.t('Create Note')}  -->
											<Tooltip content={$i18n.t('Create note')} className=" flex items-center">
												<button
													id="create-note-button"
													class=" text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 transition rounded-full p-1.5 -mr-1 self-center"
													type="button"
													disabled={prompt === '' && files.length === 0}
													on:click={() => {
														createNote();
													}}
												>
													<Note className="size-4.5 translate-y-[0.5px]" />
												</button>
											</Tooltip>
										{/if}

										{#if !history?.currentId || history.messages[history.currentId]?.done == true}
											{#if atSelectedModel === undefined}
												<ModelThinkingMenu bind:selectedModels />
											{/if}

											{#if conversationUsage}
												<UsageMenu
													usage={conversationUsage}
													model={usageModel}
													{chatId}
													generating={generating || responseInProgress}
													on:compacted={() => onContextCompacted()}
												/>
											{/if}

											{#if $_user?.role === 'admin' || ($_user?.permissions?.chat?.stt ?? true)}
												<!-- {$i18n.t('Record voice')} -->
												<Tooltip content={$i18n.t('Dictate')}>
													<button
														id="voice-input-button"
														class=" text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition rounded-full p-1.5 self-center mr-0.5"
														type="button"
														on:click={async () => {
															try {
																let stream = await navigator.mediaDevices
																	.getUserMedia({ audio: true })
																	.catch(function (err) {
																		toast.error(
																			$i18n.t(
																				`Permission denied when accessing microphone: {{error}}`,
																				{
																					error: err
																				}
																			)
																		);
																		return null;
																	});

																if (stream) {
																	recording = true;
																	const tracks = stream.getTracks();
																	tracks.forEach((track) => track.stop());
																}
																stream = null;
															} catch {
																toast.error($i18n.t('Permission denied when accessing microphone'));
															}
														}}
														aria-label={$i18n.t('Voice Input')}
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 20 20"
															fill="currentColor"
															class="size-5 translate-y-[0.5px]"
														>
															<path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z"></path>
															<path
																d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"></path>
														</svg>
													</button>
												</Tooltip>
											{/if}
										{/if}

										{#if prompt === '' && files.length === 0 && ($_user?.role === 'admin' || ($_user?.permissions?.chat?.call ?? true))}
											<div class=" flex items-center">
												<!-- {$i18n.t('Call')} -->
												<Tooltip content={$i18n.t('Voice mode')}>
													<button
														class=" bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full p-1.5 self-center"
														type="button"
														on:click={async () => {
															if (selectedModels.length > 1) {
																toast.error($i18n.t('Select only one model to call'));

																return;
															}

															if ($config?.audio?.stt?.engine === 'web') {
																toast.error(
																	$i18n.t('Call feature is not supported when using Web STT engine')
																);

																return;
															}
															// check if user has access to getUserMedia
															try {
																let stream: MediaStream | null = await navigator.mediaDevices.getUserMedia({
																	audio: true
																});
																// If the user grants the permission, proceed to show the call overlay

																if (stream) {
																	const tracks = stream.getTracks();
																	tracks.forEach((track) => track.stop());
																}

																stream = null;

																const ttsSettings = getMessageInputSettings().audio?.tts as
																	| Record<string, unknown>
																	| undefined;
																if (ttsSettings?.engine === 'browser-kokoro') {
																	// If the user has not initialized the TTS worker, initialize it
																	if (!get(TTSWorker)) {
																		const engineConfig = ttsSettings?.engineConfig as
																			| Record<string, unknown>
																			| undefined;
																		const dtype =
																			typeof engineConfig?.dtype === 'string'
																				? engineConfig.dtype
																				: 'fp32';
																		await (
																			TTSWorker as Writable<KokoroWorker | null>
																		).set(new KokoroWorker(dtype));
																	}

																	const worker = get(TTSWorker as Writable<KokoroWorker | null>);
																	await worker?.init();
																}

																showCallOverlay.set(true);
																showControls.set(true);
															} catch (_err) {
																// If the user denies the permission or an error occurs, show an error message
																toast.error(
																	$i18n.t('Permission denied when accessing media devices')
																);
															}
														}}
														aria-label={$i18n.t('Voice mode')}
													>
														<Voice className="size-5" strokeWidth="2.5" />
													</button>
												</Tooltip>
											</div>
										{:else}
											<div class=" flex items-center">
												<Tooltip
													content={uploadPending
														? $i18n.t('Waiting for upload...')
														: $i18n.t('Send message')}
												>
													<button
														id="send-message-button"
														aria-label={uploadPending
															? $i18n.t('Waiting for upload...')
															: $i18n.t('Send message')}
														aria-busy={uploadPending}
														class="{!(prompt === '' && files.length === 0) || uploadPending
															? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
															: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 self-center"
														type="submit"
														disabled={(prompt === '' && files.length === 0) || uploadPending}
													>
														{#if uploadPending}
															<Spinner className="size-5" />
														{:else}
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																class="size-5"
															>
																<path
																	fill-rule="evenodd"
																	d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
																	clip-rule="evenodd"></path>
															</svg>
														{/if}
													</button>
												</Tooltip>
											</div>
										{/if}
									{/if}
								</div>
							</div>
						</div>

						{#if $config?.license_metadata?.input_footer}
							<div class=" text-xs text-gray-500 text-center line-clamp-1 marked">
								<!-- eslint-disable-next-line svelte/no-at-html-tags -->
								{@html DOMPurify.sanitize(
									marked(String($config?.license_metadata?.input_footer ?? ''))
								)}
							</div>
						{:else}
							<div class="mb-1" ></div>
						{/if}
					</form>
				</div>
			</div>
		</div>
	</div>
{/if}
