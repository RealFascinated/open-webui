<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { Pane, PaneGroup, PaneResizer } from 'paneforge';

	import { onDestroy, onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { v4 as uuidv4 } from 'uuid';
	import type { Writable } from 'svelte/store';

	import {
		chatId,
		channels,
		channelId as _channelId,
		showSidebar,
		socket,
		user
	} from '$lib/stores';
	import { getChannelById, getChannelMessages, sendMessage } from '$lib/apis/channels';
	import type { Handler } from '$lib/types';

	import Messages from './Messages.svelte';
	import MessageInput from './MessageInput.svelte';
	import Navbar from './Navbar.svelte';
	import Drawer from '../common/Drawer.svelte';
	import Thread from './Thread.svelte';
	import i18n from '$lib/i18n';
	import Spinner from '../common/Spinner.svelte';

	type SocketPayload = Record<string, unknown>;

	type ChannelSocketEvent = {
		channel_id: string;
		message_id?: string | null;
		created_at?: number;
		user: { id: string; name: string };
		channel?: { type?: string; name?: string };
		data?: { type?: string; data?: SocketPayload };
	};

	type ChannelUser = {
		id: string;
		name: string;
	};

	type ChannelSummary = {
		id: string;
		type?: string | null;
		name?: string;
		unread_count?: number;
		last_message_at?: number;
	};

	type ChannelDetail = {
		id: string;
		type?: string;
		name?: string;
		write_access?: boolean;
		users?: ChannelUser[];
		created_at?: number;
		[key: string]: unknown;
	};

	type ChannelMessage = {
		id: string;
		temp_id?: string | null;
		content?: string;
		data?: { files?: unknown[]; [key: string]: unknown };
		reply_to_id?: string | null;
		parent_id?: string | null;
		user_id?: string;
		user: { name: string; id?: string; [key: string]: unknown };
		reply_to_message?: ChannelMessage | null;
		created_at?: number;
		updated_at?: number;
		is_pinned?: boolean;
		pinned_by?: string | null;
		pinned_at?: number | null;
		[key: string]: unknown;
	};

	type TypingUser = {
		id: string;
		name: string;
	};

	type MessageSubmitPayload = {
		content: string;
		data?: { files?: unknown[]; [key: string]: unknown };
	};

	export let id = '';

	let currentId: string | null = null;

	let scrollEnd = true;
	let messagesContainerElement: HTMLDivElement | null = null;
	let chatInputElement: HTMLTextAreaElement | null = null;

	let top = false;

	let channel: ChannelDetail | null = null;
	let messages: ChannelMessage[] | null = null;

	let replyToMessage: ChannelMessage | null = null;
	let threadId: string | null = null;

	let typingUsers: TypingUser[] = [];
	let typingUsersTimeout: Record<string, ReturnType<typeof setTimeout>> = {};

	$: if (id) {
		initHandler();
	}

	const scrollToBottom = () => {
		if (messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}
	};

	const updateLastReadAt = async (channelId: string) => {
		$socket?.emit('events:channel', {
			channel_id: channelId,
			message_id: null,
			data: {
				type: 'last_read_at'
			}
		});

		channels.set(
			($channels as ChannelSummary[]).map((channelItem) => {
				if (channelItem.id === channelId) {
					return {
						...channelItem,
						unread_count: 0
					};
				}
				return channelItem;
			}) as never
		);
	};

	const pinHandler = (
		messageId: string,
		pinned: boolean,
		pinnedBy: string | null = pinned ? ($user?.id ?? null) : null,
		pinnedAt: number | null = pinned ? Date.now() * 1000000 : null
	) => {
		if (messages) {
			messages = messages.map((message) => {
				if (message.id === messageId) {
					return {
						...message,
						is_pinned: pinned,
						pinned_by: pinnedBy,
						pinned_at: pinnedAt
					};
				}
				return message;
			});
		}
	};

	const messagesOnPin: Handler = (...args: unknown[]) => {
		const [messageId, pinned, pinnedBy, pinnedAt] = args;
		if (typeof messageId === 'string' && typeof pinned === 'boolean') {
			pinHandler(
				messageId,
				pinned,
				typeof pinnedBy === 'string' || pinnedBy === null ? pinnedBy : undefined,
				typeof pinnedAt === 'number' || pinnedAt === null ? pinnedAt : undefined
			);
		}
	};

	const threadOnPin: () => void = (...args: unknown[]) => {
		messagesOnPin(...args);
	};

	const handleSubmit: Handler = (payload: unknown) => submitHandler(payload as MessageSubmitPayload);

	const initHandler = async () => {
		if (currentId) {
			updateLastReadAt(currentId);
		}

		currentId = id;
		updateLastReadAt(id);
		(_channelId as Writable<string | null>).set(id);

		top = false;
		messages = null;
		channel = null;
		threadId = null;

		typingUsers = [];
		typingUsersTimeout = {};

		channel = await getChannelById(localStorage.token, id).catch((_error) => {
			return null;
		});

		if (channel) {
			messages = await getChannelMessages(localStorage.token, id, 0);

			if (messages) {
				scrollToBottom();

				if (messages.length < 50) {
					top = true;
				}
			}
		} else {
			goto('/');
		}
	};

	const channelEventHandler = async (event: ChannelSocketEvent) => {
		if (event.channel_id === id) {
			const type = event?.data?.type ?? null;
			const data = event?.data?.data ?? null;

			if (type === 'message') {
				if ((data?.parent_id ?? null) === null && messages !== null) {
					const tempId = (data?.temp_id as string | null | undefined) ?? null;
					messages = [
						{ ...(data as ChannelMessage), temp_id: null },
						...messages.filter((m) => !tempId || m?.temp_id !== tempId)
					];

					if (typingUsers.find((typingUser) => typingUser.id === event.user.id)) {
						typingUsers = typingUsers.filter((typingUser) => typingUser.id !== event.user.id);
					}

					await tick();
					if (scrollEnd) {
						scrollToBottom();
					}
				}
			} else if (type === 'message:update' && messages !== null && data) {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = data as ChannelMessage;
				}
			} else if (type === 'message:delete' && messages !== null && data) {
				messages = messages.filter((message) => message.id !== data.id);

				if (threadId === data.id) {
					threadId = null;
				}
			} else if (type === 'message:reply' && messages !== null && data) {
				const idx = messages.findIndex((message) => message.id === data.id);

				if (idx !== -1) {
					messages[idx] = data as ChannelMessage;
				}
			} else if (type?.includes('message:reaction') && messages !== null && data) {
				const idx = messages.findIndex((message) => message.id === data.id);
				if (idx !== -1) {
					messages[idx] = data as ChannelMessage;
				}
			} else if (type === 'typing' && event.message_id === null && data) {
				if (event.user.id === $user?.id) {
					return;
				}

				const typingData = data as { typing?: boolean };

				typingUsers = typingData.typing
					? [
							...typingUsers,
							...(typingUsers.find((typingUser) => typingUser.id === event.user.id)
								? []
								: [
										{
											id: event.user.id,
											name: event.user.name
										}
									])
						]
					: typingUsers.filter((typingUser) => typingUser.id !== event.user.id);

				if (typingUsersTimeout[event.user.id]) {
					clearTimeout(typingUsersTimeout[event.user.id]);
				}

				typingUsersTimeout[event.user.id] = setTimeout(() => {
					typingUsers = typingUsers.filter((typingUser) => typingUser.id !== event.user.id);
				}, 5000);
			}
		}
	};

	const submitHandler = async ({ content, data }: MessageSubmitPayload) => {
		if (!content && (data?.files ?? []).length === 0) {
			return;
		}

		const tempId = uuidv4();

		const message = {
			temp_id: tempId,
			content,
			data: data as object | undefined,
			reply_to_id: replyToMessage?.id
		};

		const ts = Date.now() * 1000000; // nanoseconds
		const sessionUser = ($user ?? { id: '', name: '' }) as ChannelMessage['user'];
		const optimisticMessage: ChannelMessage = {
			id: tempId,
			temp_id: tempId,
			content,
			data,
			reply_to_id: replyToMessage?.id ?? null,
			user_id: sessionUser.id ?? '',
			user: sessionUser,
			reply_to_message: replyToMessage ?? null,
			created_at: ts,
			updated_at: ts
		};
		messages = [optimisticMessage, ...(messages ?? [])];

		const res = await sendMessage(localStorage.token, id, message).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res && messagesContainerElement) {
			messagesContainerElement.scrollTop = messagesContainerElement.scrollHeight;
		}

		replyToMessage = null;
	};

	const onChange = async () => {
		$socket?.emit('events:channel', {
			channel_id: id,
			message_id: null,
			data: {
				type: 'typing',
				data: {
					typing: true
				}
			}
		});

		updateLastReadAt(id);
	};

	let mediaQuery: MediaQueryList | undefined;
	let largeScreen = false;

	const handleMediaQuery = (query: MediaQueryList | MediaQueryListEvent) => {
		largeScreen = query.matches;
	};

	onMount(() => {
		if ($chatId) {
			chatId.set('');
		}

		$socket?.on('events:channel', channelEventHandler);

		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);
	});

	onDestroy(() => {
		// last read at
		updateLastReadAt(id);
		(_channelId as Writable<string | null>).set(null);
		$socket?.off('events:channel', channelEventHandler);
	});
</script>

<svelte:head>
	{#if channel?.type === 'dm'}
		<title
			>{channel?.name?.trim() ||
				channel?.users?.reduce((a: string, e: ChannelUser, _i: number, _arr: ChannelUser[]) => {
					if (e.id === $user?.id) {
						return a;
					}

					if (a) {
						return `${a}, ${e.name}`;
					} else {
						return e.name;
					}
				}, '')} • Open WebUI</title
		>
	{:else}
		<title>#{channel?.name ?? 'Channel'} • Open WebUI</title>
	{/if}
</svelte:head>

<div
	class="h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} w-full max-w-full flex flex-col"
	id="channel-container"
>
	<PaneGroup direction="horizontal" class="w-full h-full">
		<Pane defaultSize={50} minSize={50} class="h-full flex flex-col w-full relative">
			<Navbar
				{channel}
				onPin={pinHandler}
				onUpdate={async () => {
					channel = await getChannelById(localStorage.token, id).catch((_error) => {
						return null;
					});
				}}
			/>

			{#if channel && messages !== null}
				<div class="flex-1 overflow-y-auto">
					<div
						class=" pb-2.5 max-w-full z-10 scrollbar-hidden w-full h-full pt-6 flex-1 flex flex-col-reverse overflow-auto"
						id="messages-container"
						bind:this={messagesContainerElement}
						on:scroll={(_e) => {
							if (messagesContainerElement) {
								scrollEnd = Math.abs(messagesContainerElement.scrollTop) <= 50;
							}
						}}
					>
						{#key id}
							<Messages
								channel={channel as never}
								{top}
								messages={messages as never}
								replyToMessage={replyToMessage as never}
								onReply={async (message) => {
									replyToMessage = message as ChannelMessage;
									await tick();
									chatInputElement?.focus();
								}}
								onThread={(messageId) => {
									threadId = messageId as string;
								}}
								onPin={messagesOnPin}
								onLoad={async () => {
									if (!messages) {
										return;
									}

									const newMessages = await getChannelMessages(
										localStorage.token,
										id,
										messages.length
									);

									messages = [...messages, ...(newMessages ?? [])];

									if ((newMessages?.length ?? 0) < 50) {
										top = true;
										return;
									}
								}}
							/>
						{/key}
					</div>
				</div>

				<div class=" pb-[1rem] px-2.5">
					<MessageInput
						id={'root' as never}
						bind:chatInputElement
						bind:replyToMessage
						{typingUsers}
						channel={channel as never}
						userSuggestions={true}
						channelSuggestions={true}
						disabled={!channel?.write_access}
						placeholder={!channel?.write_access
							? $i18n.t('You do not have permission to send messages in this channel.')
							: $i18n.t('Type here...')}
						{onChange}
						onSubmit={handleSubmit}
						{scrollToBottom}
						{scrollEnd}
					/>
				</div>
			{:else}
				<div class=" flex items-center justify-center h-full w-full">
					<div class="m-auto">
						<Spinner className="size-5" />
					</div>
				</div>
			{/if}
		</Pane>

		{#if !largeScreen}
			{#if threadId !== null}
				<Drawer
					show={threadId !== null}
					onClose={() => {
						threadId = null;
					}}
				>
					<div class=" {threadId !== null ? ' h-screen  w-full' : 'px-6 py-4'} h-full">
						<Thread
							threadId={threadId as never}
							channel={channel as never}
							onPin={threadOnPin}
							onClose={() => {
								threadId = null;
							}}
						/>
					</div>
				</Drawer>
			{/if}
		{:else if threadId !== null}
			<PaneResizer
				class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800  transition z-20"
				id="controls-resizer"
			>
				<div
					class=" absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"></div>
			</PaneResizer>

			<Pane defaultSize={50} minSize={30} class="h-full w-full">
				<div class="h-full w-full shadow-xl">
					<Thread
						threadId={threadId as never}
						channel={channel as never}
						onPin={threadOnPin}
						onClose={() => {
							threadId = null;
						}}
					/>
				</div>
			</Pane>
		{/if}
	</PaneGroup>
</div>
