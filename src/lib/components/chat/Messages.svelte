<script lang="ts">
	import {v4 as uuidv4} from 'uuid';
	import {chats, settings, user as _user, currentChatPage, temporaryChatEnabled} from '$lib/stores';
	import type {Model, SessionUser} from '$lib/stores';
	import {tick, getContext, onDestroy} from 'svelte';
	import {toast} from 'svelte-sonner';
	import {deleteChatMessageById, getChatList, updateChatById} from '$lib/apis/chats';
	import type {ChatFile, ChatHistory, ChatMessage} from '$lib/types/chat';
	import type {OutputItem} from './Messages/structuredOutput';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';

	import ChatPlaceholder from './ChatPlaceholder.svelte';

	type MessagesChatMessage = ChatMessage & {
		annotation?: Record<string, unknown>;
		output?: OutputItem[];
		originalContent?: string;
	};

	type MessagesHistory = Omit<ChatHistory, 'messages'> & {
		messages: Record<string, MessagesChatMessage>;
	};

	const i18n = getContext('i18n');

	export let className = 'h-full flex pt-8';

	export let chatId = '';
	export let user: SessionUser | undefined = $_user;

	export let prompt = '';
	export let history: MessagesHistory = { messages: {}, currentId: null };
	export let selectedModels: string[];
	export let atSelectedModel: Model | undefined = undefined;

	let messages: MessagesChatMessage[] = [];

	export let setInputText: (...args: unknown[]) => unknown = () => {};

	export let sendMessage: (...args: unknown[]) => unknown;
	export let continueResponse: (...args: unknown[]) => unknown;
	export let regenerateResponse: (...args: unknown[]) => unknown;
	export let mergeResponses: (...args: unknown[]) => unknown;

	export let chatActionHandler: (...args: unknown[]) => unknown;
	export const showMessage: (...args: unknown[]) => unknown = () => {};
	export let submitMessage: (...args: unknown[]) => unknown = () => {};
	export let addMessages: (...args: unknown[]) => unknown = () => {};
	export let pinFileToChat: (...args: unknown[]) => unknown = () => {};
	export let pinnedFileIds: string[] = [];

	export let readOnly = false;
	export let editCodeBlock = true;

	export let topPadding = false;
	export let bottomPadding = false;
	export let autoScroll: boolean | undefined = undefined;

	export let onSelect = (_e: Event) => {};

	export let messagesCount: number | null = 8;
	let messagesLoading = false;

	const updateAutoScrollFromContainer = (element: HTMLElement | null) => {
		if (element) {
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
		}
	};

	onDestroy(() => {
		if (pendingRebuild !== null) {
			cancelAnimationFrame(pendingRebuild);
		}
	});

	const loadMoreMessages = async () => {
		// scroll slightly down to disable continuous loading
		const element = document.getElementById('messages-container');
		if (!element) return;

		element.scrollTop = element.scrollTop + 100;

		messagesLoading = true;
		if (messagesCount !== null) {
			messagesCount += 8;
		}

		buildMessages();

		await tick();

		messagesLoading = false;
	};

	let pendingRebuild: number | null = null;
	let lastCurrentId: string | null = null;

	const buildMessages = () => {
		let _messages: MessagesChatMessage[] = [];

		let message = history.currentId ? history.messages[history.currentId] : undefined;
		const visitedMessageIds = new Set<string>();

		while (message && (messagesCount !== null ? _messages.length <= messagesCount : true)) {
			if (visitedMessageIds.has(message.id)) {
				console.warn('Circular dependency detected in message history', message.id);
				break;
			}
			visitedMessageIds.add(message.id);

			_messages.push(message);
			message = message.parentId != null ? history.messages[message.parentId] : undefined;
		}

		messages = _messages.reverse();
	};

	// Throttle message list rebuilds to once per animation frame during streaming.
	// Structural changes (currentId change) always rebuild immediately.
	const handleHistoryChange = (
		currentId: string | null,
		_messages: Record<string, MessagesChatMessage>
	) => {
		if (!currentId) {
			messages = [];
			return;
		}

		const currentIdChanged = currentId !== lastCurrentId;
		lastCurrentId = currentId;

		if (currentIdChanged) {
			// Structural change: new chat, navigation, new message — rebuild immediately
			if (pendingRebuild !== null) {
				cancelAnimationFrame(pendingRebuild);
			}
			pendingRebuild = null;
			buildMessages();
		} else if (_messages) {
			// Content update (streaming) — throttle to once per frame
			if (pendingRebuild === null) {
				pendingRebuild = requestAnimationFrame(() => {
					pendingRebuild = null;
					buildMessages();
				});
			}
		}
	};

	$: handleHistoryChange(history.currentId, history.messages);

	$: if (autoScroll && bottomPadding && ($settings?.chatResponseAutoScroll ?? true)) {
		(async () => {
			await tick();
			scrollToBottom();
		})();
	}

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		if (element) {
			element.scrollTop = element.scrollHeight;

			// Follow-up scroll to account for content-visibility: auto re-layouts
			requestAnimationFrame(() => {
				if (element) {
					element.scrollTop = element.scrollHeight;
				}
			});
		}
	};

	export const scrollToTop = async () => {
		messagesCount = null;
		buildMessages();
		await tick();
		if (messages.length > 0) {
			const firstMessageEl = document.getElementById(`message-${messages[0].id}`);
			if (firstMessageEl) {
				firstMessageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		}
	};

	const updateChat = async () => {
		if (!$temporaryChatEnabled) {
			history = history;
			await tick();
			const res = await updateChatById(localStorage.token, chatId, {
				history: history,
				messages: messages
			});

			// Keep local plain-content edits aligned with the saved chat response.
			if (res?.chat?.history?.messages) {
				for (const [id, msg] of Object.entries(res.chat.history.messages)) {
					const savedMessage = msg as MessagesChatMessage;
					if (history.messages[id] && savedMessage.content) {
						history.messages[id].content = savedMessage.content;
					}
				}
				history = history;
			}

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
		}
	};

	const gotoMessage = async (message: MessagesChatMessage, idx: number) => {
		// Determine the correct sibling list (either parent's children or root messages)
		let siblings: string[];
		if (message.parentId != null) {
			siblings = history.messages[message.parentId]?.childrenIds ?? [];
		} else {
			siblings = Object.values(history.messages)
				.filter((msg) => msg.parentId == null)
				.map((msg) => msg.id);
		}

		// Clamp index to a valid range
		idx = Math.max(0, Math.min(idx, siblings.length - 1));

		let messageId = siblings[idx];

		// If we're navigating to a different message
		if (message.id !== messageId) {
			// Drill down to the deepest child of that branch
			let messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];
			while (messageChildrenIds.length !== 0) {
				const nextId = messageChildrenIds.at(-1);
				if (!nextId) break;
				messageId = nextId;
				messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];
			}

			history.currentId = messageId;
		}

		await tick();

		// Optional auto-scroll
		if ($settings?.scrollOnBranchChange ?? true) {
			updateAutoScrollFromContainer(document.getElementById('messages-container'));

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const showPreviousMessage = async (message: MessagesChatMessage) => {
		if (message.parentId != null) {
			const parentChildren = history.messages[message.parentId]?.childrenIds ?? [];
			let messageId =
				parentChildren[Math.max(parentChildren.indexOf(message.id) - 1, 0)];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];

				while (messageChildrenIds.length !== 0) {
					const nextId = messageChildrenIds.at(-1);
					if (!nextId) break;
					messageId = nextId;
					messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];
				}

				history.currentId = messageId;
			}
		} else {
			let childrenIds = Object.values(history.messages)
				.filter((msg) => msg.parentId == null)
				.map((msg) => msg.id);
			let messageId = childrenIds[Math.max(childrenIds.indexOf(message.id) - 1, 0)];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];

				while (messageChildrenIds.length !== 0) {
					const nextId = messageChildrenIds.at(-1);
					if (!nextId) break;
					messageId = nextId;
					messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];
				}

				history.currentId = messageId;
			}
		}

		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			updateAutoScrollFromContainer(document.getElementById('messages-container'));

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const showNextMessage = async (message: MessagesChatMessage) => {
		if (message.parentId != null) {
			const parentChildren = history.messages[message.parentId]?.childrenIds ?? [];
			let messageId =
				parentChildren[
					Math.min(parentChildren.indexOf(message.id) + 1, parentChildren.length - 1)
				];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];

				while (messageChildrenIds.length !== 0) {
					const nextId = messageChildrenIds.at(-1);
					if (!nextId) break;
					messageId = nextId;
					messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];
				}

				history.currentId = messageId;
			}
		} else {
			let childrenIds = Object.values(history.messages)
				.filter((msg) => msg.parentId == null)
				.map((msg) => msg.id);
			let messageId =
				childrenIds[Math.min(childrenIds.indexOf(message.id) + 1, childrenIds.length - 1)];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];

				while (messageChildrenIds.length !== 0) {
					const nextId = messageChildrenIds.at(-1);
					if (!nextId) break;
					messageId = nextId;
					messageChildrenIds = history.messages[messageId]?.childrenIds ?? [];
				}

				history.currentId = messageId;
			}
		}

		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			updateAutoScrollFromContainer(document.getElementById('messages-container'));

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const rateMessage = async (messageId: string, rating: number) => {
		history.messages[messageId].annotation = {
			...history.messages[messageId].annotation,
			rating: rating
		};

		await updateChat();
	};

	const editMessage = async (
		messageId: string,
		{
			content,
			files,
			output = undefined
		}: { content: string; files?: ChatFile[]; output?: OutputItem[] },
		submit = true
	) => {
		if ((selectedModels ?? []).filter((id: string) => id).length === 0) {
			toast.error($i18n.t('Model not selected'));
			return;
		}
		if (history.messages[messageId].role === 'user') {
			if (submit) {
				// New user message
				let userPrompt = content;
				let userMessageId = uuidv4();

				let userMessage = {
					id: userMessageId,
					parentId: history.messages[messageId].parentId,
					childrenIds: [],
					role: 'user',
					content: userPrompt,
					...(files && { files: files }),
					models: selectedModels,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				let messageParentId = history.messages[messageId].parentId;

				if (messageParentId != null) {
					history.messages[messageParentId].childrenIds = [
						...(history.messages[messageParentId].childrenIds ?? []),
						userMessageId
					];
				}

				history.messages[userMessageId] = userMessage;
				history.currentId = userMessageId;

				await tick();
				await sendMessage(history, userMessageId);
			} else {
				// Edit user message
				history.messages[messageId].content = content;
				history.messages[messageId].files = files;
				await updateChat();
			}
		} else {
			if (submit) {
				// New response message (Save As Copy)
				const responseMessageId = uuidv4();
				const message = history.messages[messageId];
				const parentId = message.parentId;

				const responseMessage = {
					...message,
					id: responseMessageId,
					parentId: parentId,
					childrenIds: [],
					files: undefined,
					content: output !== undefined ? '' : content,
					...(output !== undefined ? { output } : {}),
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				history.messages[responseMessageId] = responseMessage;
				history.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId != null) {
					history.messages[parentId].childrenIds = [
						...(history.messages[parentId].childrenIds ?? []),
						responseMessageId
					];
				}

				await updateChat();
			} else {
				// Edit response message
				if (content !== undefined) {
					history.messages[messageId].originalContent = history.messages[messageId].content;
					history.messages[messageId].content = content;
				}
				if (output !== undefined) {
					history.messages[messageId].output = output;
					history.messages[messageId].content = '';
				}
				await updateChat();
			}
		}
	};

	const actionMessage = async (
		actionId: string,
		message: MessagesChatMessage,
		event: Event | null = null
	) => {
		await chatActionHandler(chatId, actionId, message.model, message.id, event);
	};

	const saveMessage = async (messageId: string, message: MessagesChatMessage) => {
		if (!history.messages?.[messageId]) {
			return;
		}

		history.messages[messageId] = message;
		await updateChat();
	};

	const deleteMessage = async (messageId: string) => {
		const messageToDelete = history.messages[messageId];
		const parentMessageId = messageToDelete.parentId;
		const childMessageIds = messageToDelete.childrenIds ?? [];

		// Collect all grandchildren
		const grandchildrenIds = childMessageIds.flatMap(
			(childId: string) => history.messages[childId]?.childrenIds ?? []
		);

		// Update parent's children
		if (parentMessageId != null && history.messages[parentMessageId]) {
			history.messages[parentMessageId].childrenIds = [
				...(history.messages[parentMessageId].childrenIds ?? []).filter(
					(id: string) => id !== messageId
				),
				...grandchildrenIds
			];
		}

		// Update grandchildren's parent
		grandchildrenIds.forEach((grandchildId: string) => {
			if (history.messages[grandchildId]) {
				history.messages[grandchildId].parentId = parentMessageId;
			}
		});

		// Delete the message and its children
		[messageId, ...childMessageIds].forEach((id: string) => {
			delete history.messages[id];
		});

		let nextMessageId: string | null = parentMessageId ?? null;
		let nextChildrenIds =
			nextMessageId === null
				? Object.keys(history.messages).filter(
						(id: string) => history.messages[id].parentId == null
					)
				: (history.messages[nextMessageId]?.childrenIds ?? []);
		while (nextChildrenIds.length > 0) {
			const nextId = nextChildrenIds.at(-1);
			if (!nextId) break;
			nextMessageId = nextId;
			nextChildrenIds = history.messages[nextMessageId]?.childrenIds ?? [];
		}
		history.currentId = nextMessageId;
		history = history;

		if (!$temporaryChatEnabled) {
			const res = await deleteChatMessageById(localStorage.token, chatId, messageId);
			if (res?.chat?.history) {
				history = res.chat.history as MessagesHistory;
			}

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
		}
	};

	const triggerScroll = () => {
		if (autoScroll) {
			updateAutoScrollFromContainer(document.getElementById('messages-container'));
			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};
</script>

<div class={className} data-prompt={prompt}>
	{#if Object.keys(history?.messages ?? {}).length == 0}
		<ChatPlaceholder modelIds={selectedModels} {atSelectedModel} {onSelect} />
	{:else}
		<div class="w-full pt-2">
			{#key chatId}
				<section class="w-full" aria-labelledby="chat-conversation">
					<h2 class="sr-only" id="chat-conversation">{$i18n.t('Chat Conversation')}</h2>
					{#if messages.at(0)?.parentId !== null}
						<Loader
							on:visible={(_e) => {
								console.log('visible');
								if (!messagesLoading) {
									loadMoreMessages();
								}
							}}
						>
							<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
								<Spinner className=" size-4" />
								<div class=" ">{$i18n.t('Loading...')}</div>
							</div>
						</Loader>
					{/if}
					<ul role="log" aria-live="polite" aria-relevant="additions" aria-atomic="false">
						{#each messages as message, messageIdx (message.id)}
							<Message
								{chatId}
								bind:history
								{selectedModels}
								messageId={message.id}
								idx={messageIdx}
								{user}
								{setInputText}
								{gotoMessage}
								{showPreviousMessage}
								{showNextMessage}
								{updateChat}
								{editMessage}
								{deleteMessage}
								{rateMessage}
								{actionMessage}
								{saveMessage}
								{submitMessage}
								{regenerateResponse}
								{continueResponse}
								{mergeResponses}
								{addMessages}
								{pinFileToChat}
								{pinnedFileIds}
								{triggerScroll}
								{readOnly}
								{editCodeBlock}
								{topPadding}
								{autoScroll}
							/>
						{/each}
					</ul>
				</section>
				<div class="pb-18"></div>
				{#if bottomPadding}
					<div class="  pb-6"></div>
				{/if}
			{/key}
		</div>
	{/if}
</div>
