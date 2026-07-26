<script lang="ts">
	import {getContext} from 'svelte';
	import type {Writable} from 'svelte/store';

	const i18n: Writable<unknown> = getContext('i18n');

	import {user} from '$lib/stores';

	import ChatList from './ChatList.svelte';
	import ProjectKnowledge from './ProjectKnowledge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import {getChatListByProjectId} from '$lib/apis/chats';
	import {getSharedProjectChats} from '$lib/apis/projects';

	export let project: unknown = null;

	let selectedTab = 'chats';

	let page = 1;

	let chats: unknown[] | null = null;
	let chatListLoading = false;
	let allChatsLoaded = false;

	$: hasKnowledge = (project?.data?.files ?? []).length > 0;

	$: showOwnerInfo = Boolean(
		project?.shared ||
		(project?.user_id && project.user_id !== $user?.id) ||
		(project?.access_grants?.length ?? 0) > 0
	);

	const loadChats = async () => {
		allChatsLoaded = true;
	};

	const setChatList = async () => {
		chats = null;
		page = 1;
		allChatsLoaded = false;
		chatListLoading = false;

		if (project && project.id) {
			const res = await getSharedProjectChats(localStorage.token, project.id).catch((error) => {
				console.error(error);
				return null;
			});
			if (res && res.chats) {
				chats = res.chats;
				allChatsLoaded = true;
			} else {
				const fallback = await getChatListByProjectId(localStorage.token, project.id, page).catch(
					() => []
				);
				chats = fallback || [];
			}
		} else {
			chats = [];
		}
	};

	$: if (project) {
		setChatList();
	}
</script>

<div>
	{#if hasKnowledge}
		<div class="mb-1">
			<div
				class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
			>
				<button
					class="min-w-fit p-1.5 {selectedTab === 'knowledge'
						? ''
						: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
					type="button"
					on:click={() => {
						selectedTab = 'knowledge';
					}}>{$i18n.t('Knowledge')}</button
				>

				<button
					class="min-w-fit p-1.5 {selectedTab === 'chats'
						? ''
						: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
					type="button"
					on:click={() => {
						selectedTab = 'chats';
					}}
				>
					{$i18n.t('Chats')}
				</button>
			</div>
		</div>
	{/if}

	<div class="">
		{#if selectedTab === 'knowledge' && hasKnowledge}
			<ProjectKnowledge {project} />
		{:else if selectedTab === 'chats'}
			{#if chats !== null}
				<ChatList
					{chats}
					{chatListLoading}
					{allChatsLoaded}
					loadHandler={loadChats}
					{showOwnerInfo}
				/>
			{:else}
				<div class="py-10">
					<Spinner />
				</div>
			{/if}
		{/if}
	</div>
</div>
