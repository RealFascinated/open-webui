<script>
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import DOMPurify from 'dompurify';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { chatId, mobile, selectedProject, showSidebar, user } from '$lib/stores';

	import {
		deleteProjectById,
		updateProjectIsExpandedById,
		updateProjectById,
		updateProjectParentIdById,
		getProjectById,
		createNewProject,
		getSharedProjectChats
	} from '$lib/apis/projects';
	import {
		getChatById,
		getChatsByProjectId,
		getChatListByProjectId,
		updateChatProjectIdById,
		importChats
	} from '$lib/apis/chats';

	import ChevronDown from '../../icons/ChevronDown.svelte';
	import ChevronRight from '../../icons/ChevronRight.svelte';
	import Collapsible from '../../common/Collapsible.svelte';
	import DragGhost from '$lib/components/common/DragGhost.svelte';

	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

	import ChatItem from './ChatItem.svelte';
	import ProjectMenu from './Projects/ProjectMenu.svelte';
	import ProjectShareModal from './Projects/ProjectShareModal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ProjectModal from './Projects/ProjectModal.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let projectRegistry = {};
	export let open = false;

	export let projects;
	export let projectId;
	export let shiftKey = false;

	export let className = '';

	export let deleteProjectContents = true;

	export let parentDragged = false;

	export let onDelete = (e) => {};
	export let onItemMove = (e) => {};

	let projectElement;

	let showProjectModal = false;
	let showShareModal = false;
	let edit = false;

	let showCreateSubProjectModal = false;
	let createSubProjectParentId = null;

	let draggedOver = false;
	let dragged = false;

	let clickTimer = null;

	let name = '';

	const onDragOver = (e) => {
		e.preventDefault();
		e.stopPropagation();
		if (dragged || parentDragged || projects[projectId]?.shared) {
			return;
		}
		draggedOver = true;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		e.stopPropagation();
		if (dragged || parentDragged) {
			return;
		}

		if (projectElement.contains(e.target)) {
			console.log('Dropped on the Button');

			if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
				// Iterate over all items in the DataTransferItemList use functional programming
				for (const item of Array.from(e.dataTransfer.items)) {
					// If dropped items aren't files, reject them
					if (item.kind === 'file') {
						const file = item.getAsFile();
						if (file && file.type === 'application/json') {
							console.log('Dropped file is a JSON file!');

							// Read the JSON file with FileReader
							const reader = new FileReader();
							reader.onload = async function (event) {
								try {
									const fileContent = JSON.parse(event.target.result);
									open = true;
									dispatch('import', {
										projectId: projectId,
										items: fileContent
									});
								} catch (error) {
									console.error('Error parsing JSON file:', error);
								}
							};

							// Start reading the file
							reader.readAsText(file);
						} else {
							console.error('Only JSON file types are supported.');
						}

						console.log(file);
					} else {
						// Handle the drag-and-drop data for projects or chats (same as before)
						const dataTransfer = e.dataTransfer.getData('text/plain');

						try {
							const data = JSON.parse(dataTransfer);
							console.log(data);

							const { type, id, item } = data;

							if (type === 'project') {
								open = true;
								if (id === projectId) {
									return;
								}
								// Move the folder
								const res = await updateProjectParentIdById(localStorage.token, id, projectId).catch(
									(error) => {
										toast.error(`${error}`);
										return null;
									}
								);

								if (res) {
									dispatch('update');
								}
							} else if (type === 'chat') {
								open = true;

								let chat = await getChatById(localStorage.token, id).catch((error) => {
									return null;
								});
								if (!chat && item) {
									if (!($user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true))) {
										toast.error($i18n.t('Access prohibited'));
										return;
									}

									chat = await importChats(localStorage.token, [
										{
											chat: item.chat,
											meta: item?.meta ?? {},
											pinned: false,
											project_id: null,
											created_at: item?.created_at ?? null,
											updated_at: item?.updated_at ?? null
										}
									]).catch((error) => {
										toast.error(`${error}`);
										return null;
									});
								}

								if (chat) {
									// Move the chat
									const res = await updateChatProjectIdById(
										localStorage.token,
										chat.id,
										projectId
									).catch((error) => {
										toast.error(`${error}`);
										return null;
									});

									onItemMove({
										originProjectId: chat.project_id,
										targetProjectId: projectId,
										e
									});

									if (res) {
										dispatch('update');
									}
								}
							}
						} catch (error) {
							console.log('Error parsing dataTransfer:', error);
						}

						// Only process the first non-file item; all share the same
						// text/plain payload, so continuing would duplicate the move.
						break;
					}
				}
			}

			setProjectItems();
			draggedOver = false;
		}
	};

	const onDragLeave = (e) => {
		e.preventDefault();
		if (dragged || parentDragged) {
			return;
		}

		draggedOver = false;
	};

	const dragImage = new Image();
	dragImage.src =
		'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

	let x;
	let y;

	const onDragStart = (event) => {
		event.stopPropagation();
		event.dataTransfer.setDragImage(dragImage, 0, 0);

		// Set the data to be transferred
		event.dataTransfer.setData(
			'text/plain',
			JSON.stringify({
				type: 'project',
				id: projectId
			})
		);
		event.dataTransfer.setData('application/x-open-webui-drag', '');

		dragged = true;
		projectElement.style.opacity = '0.5'; // Optional: Visual cue to show it's being dragged
	};

	const onDrag = (event) => {
		event.stopPropagation();

		x = event.clientX;
		y = event.clientY;
	};

	const onDragEnd = (event) => {
		event.stopPropagation();

		projectElement.style.opacity = '1'; // Reset visual cue after drag
		dragged = false;
	};

	onMount(async () => {
		open = projects[projectId].is_expanded;
		projectRegistry[projectId] = {
			setProjectItems: () => {
				setProjectItems();
			}
		};
		if (projectElement) {
			projectElement.addEventListener('dragover', onDragOver);
			projectElement.addEventListener('drop', onDrop);
			projectElement.addEventListener('dragleave', onDragLeave);

			// Event listener for when dragging starts
			projectElement.addEventListener('dragstart', onDragStart);
			// Event listener for when dragging occurs (optional)
			projectElement.addEventListener('drag', onDrag);
			// Event listener for when dragging ends
			projectElement.addEventListener('dragend', onDragEnd);
		}

		if (projects[projectId]?.new) {
			delete projects[projectId].new;
			await tick();
			renameHandler();
		}
	});

	onDestroy(() => {
		if (projectElement) {
			projectElement.addEventListener('dragover', onDragOver);
			projectElement.removeEventListener('drop', onDrop);
			projectElement.removeEventListener('dragleave', onDragLeave);

			projectElement.removeEventListener('dragstart', onDragStart);
			projectElement.removeEventListener('drag', onDrag);
			projectElement.removeEventListener('dragend', onDragEnd);
		}
	});

	let showDeleteConfirm = false;

	const deleteHandler = async () => {
		const res = await deleteProjectById(localStorage.token, projectId, deleteProjectContents).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			toast.success($i18n.t('Project deleted successfully'));
			onDelete(projectId);
		}
	};

	const updateHandler = async ({ name, meta, data }) => {
		if (name === '') {
			toast.error($i18n.t('Project name cannot be empty.'));
			return;
		}

		const currentName = projects[projectId].name;

		name = name.trim();
		projects[projectId].name = name;

		const res = await updateProjectById(localStorage.token, projectId, {
			name,
			...(meta ? { meta } : {}),
			...(data ? { data } : {})
		}).catch((error) => {
			toast.error(`${error}`);

			projects[projectId].name = currentName;
			return null;
		});

		if (res) {
			projects[projectId].name = name;
			if (data) {
				projects[projectId].data = data;
			}

			// toast.success($i18n.t('Project name updated successfully'));
			toast.success($i18n.t('Project updated successfully'));

			if ($selectedProject?.id === projectId) {
				const fetchedProject = await getProjectById(localStorage.token, projectId).catch((error) => {
					toast.error(`${error}`);
					return null;
				});

				if (fetchedProject) {
					await selectedProject.set(fetchedProject);
				}
			}
			dispatch('update');
		}
	};

	const isExpandedUpdateHandler = async () => {
		const res = await updateProjectIsExpandedById(localStorage.token, projectId, open).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);
	};

	let isExpandedUpdateTimeout;

	const isExpandedUpdateDebounceHandler = () => {
		clearTimeout(isExpandedUpdateTimeout);
		isExpandedUpdateTimeout = setTimeout(() => {
			isExpandedUpdateHandler();
		}, 500);
	};

	let chats = null;
	export const setProjectItems = async () => {
		await tick();
		if (open) {
			// Always use getSharedProjectChats so owners also see chats
			// created by users who have write access to this folder.
			try {
				const res = await getSharedProjectChats(localStorage.token, projectId);
				chats = res?.chats ?? [];
			} catch (error) {
				// Fallback to regular API
				chats = await getChatListByProjectId(localStorage.token, projectId).catch((error) => {
					toast.error(`${error}`);
					return [];
				});
			}
		} else {
			chats = null;
		}
	};

	$: if (open) {
		setProjectItems();
	}

	const renameHandler = async () => {
		console.log('Edit');
		await tick();
		name = projects[projectId].name;
		edit = true;

		await tick();
		await tick();

		const input = document.getElementById(`folder-${projectId}-input`);
		if (input) {
			input.focus();
			input.select();
		}
	};

	const exportHandler = async () => {
		const chats = await getChatsByProjectId(localStorage.token, projectId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!chats) {
			return;
		}

		const blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});

		saveAs(blob, `folder-${projects[projectId].name}-export-${Date.now()}.json`);
	};

	const createSubProjectHandler = async ({ name, meta, data, parent_id }) => {
		if (name === '') {
			toast.error($i18n.t('Project name cannot be empty.'));
			return;
		}

		name = name.trim();

		const res = await createNewProject(localStorage.token, {
			name,
			data,
			meta,
			parent_id
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Project created successfully'));
			dispatch('update');
		}
	};
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete project?')}
	on:confirm={() => {
		deleteHandler();
	}}
>
	<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3 mb-2">
		<!-- {$i18n.t('This will delete <strong>{{NAME}}</strong> and <strong>all its contents</strong>.', {
				NAME: projects[projectId].name
			})} -->

		{$i18n.t(`Are you sure you want to delete "{{NAME}}"?`, {
			NAME: projects[projectId].name
		})}
	</div>

	<div class="flex items-center gap-1.5">
		<input type="checkbox" bind:checked={deleteProjectContents} />

		<div class="text-xs text-gray-500">
			{$i18n.t('Delete all contents inside this project')}
		</div>
	</div>
</DeleteConfirmDialog>

<ProjectModal bind:show={showProjectModal} edit={true} {projectId} onSubmit={updateHandler} />

<ProjectModal
	bind:show={showCreateSubProjectModal}
	parentId={createSubProjectParentId}
	onSubmit={createSubProjectHandler}
/>

<ProjectShareModal bind:show={showShareModal} project={projects[projectId]} />

{#if dragged && x && y}
	<DragGhost {x} {y}>
		<div class=" bg-black/80 backdrop-blur-2xl px-2 py-1 rounded-lg w-fit max-w-40">
			<div class="flex items-center gap-1">
				<FolderOpen className="size-3.5" strokeWidth="2" />
				<div class=" text-xs text-white line-clamp-1">
					{projects[projectId].name}
				</div>
			</div>
		</div>
	</DragGhost>
{/if}

<div bind:this={projectElement} class="relative {className}" draggable={!projects[projectId]?.shared}>
	{#if draggedOver}
		<div
			class="absolute top-0 left-0 w-full h-full rounded-xs bg-gray-100/50 dark:bg-gray-700/20 bg-opacity-50 dark:bg-opacity-10 z-50 pointer-events-none touch-none"
		></div>
	{/if}

	<Collapsible
		bind:open
		className="w-full"
		buttonClassName="w-full"
		onChange={(state) => {
			dispatch('open', state);
		}}
	>
		<div class="w-full group">
			<div
				id="folder-{projectId}-button"
				class="relative w-full py-1 px-1.5 rounded-xl flex items-center gap-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition {$selectedProject?.id ===
				projectId
					? 'bg-gray-100 dark:bg-gray-900 selected'
					: ''}"
				role="button"
				tabindex="0"
				on:dblclick={(e) => {
					if (projects[projectId]?.shared) return;
					if (clickTimer) {
						clearTimeout(clickTimer); // cancel the single-click action
						clickTimer = null;
					}
					renameHandler();
				}}
				on:click={async (e) => {
					e.stopPropagation();
					if (clickTimer) {
						clearTimeout(clickTimer);
						clickTimer = null;
					}

					clickTimer = setTimeout(async () => {
						const fetchedProject = await getProjectById(localStorage.token, projectId).catch((error) => {
							toast.error(`${error}`);
							return null;
						});

						if (fetchedProject) {
							await selectedProject.set({ ...projects[projectId], ...fetchedProject });
						}

						await goto('/');

						if ($mobile) {
							showSidebar.set(!$showSidebar);
						}
						clickTimer = null;
					}, 100); // 100ms delay (typical double-click threshold)
				}}
				on:keydown={(e) => {
					if (e.key === 'Enter' || e.key === ' ') {
						e.preventDefault();
						e.currentTarget.click();
					}
				}}
				on:pointerup={(e) => {
					e.stopPropagation();
				}}
			>
				<button
					class="text-gray-500 dark:text-gray-500 transition-all p-1 hover:bg-gray-200 dark:hover:bg-gray-850 rounded-lg"
					on:click={(e) => {
						e.stopPropagation();
						e.stopImmediatePropagation();
						open = !open;
						isExpandedUpdateDebounceHandler();
					}}
				>
					{#if projects[projectId]?.meta?.icon}
						<div class="flex group-hover:hidden transition-all">
							<Emoji className="size-3.5" shortCode={projects[projectId].meta.icon} />
						</div>

						<div class="hidden group-hover:flex transition-all p-[1px]">
							{#if open}
								<ChevronDown className=" size-3" strokeWidth="2.5" />
							{:else}
								<ChevronRight className=" size-3" strokeWidth="2.5" />
							{/if}
						</div>
					{:else}
						<div class="p-[1px]">
							{#if open}
								<ChevronDown className=" size-3" strokeWidth="2.5" />
							{:else}
								<ChevronRight className=" size-3" strokeWidth="2.5" />
							{/if}
						</div>
					{/if}
				</button>

				<div class="translate-y-[0.5px] flex-1 justify-start text-start line-clamp-1">
					{#if edit}
						<input
							id="folder-{projectId}-input"
							type="text"
							bind:value={name}
							on:blur={() => {
								console.log('Blur');
								updateHandler({ name });
								edit = false;
							}}
							on:click={(e) => {
								// Prevent accidental collapse toggling when clicking inside input
								e.stopPropagation();
							}}
							on:mousedown={(e) => {
								// Prevent accidental collapse toggling when clicking inside input
								e.stopPropagation();
							}}
							on:keydown={(e) => {
								if (e.key === 'Enter') {
									updateHandler({ name });
									edit = false;
								}
							}}
							class="w-full h-full bg-transparent outline-hidden"
						/>
					{:else}
						{projects[projectId].name}
					{/if}
				</div>

				{#if !projects[projectId]?.shared}
					<button
						class="absolute z-10 right-2 invisible group-hover:visible self-center flex items-center dark:text-gray-300"
					>
						<ProjectMenu
							onEdit={() => {
								showProjectModal = true;
							}}
							onShare={() => {
								showShareModal = true;
							}}
							onDelete={() => {
								showDeleteConfirm = true;
							}}
							onExport={() => {
								exportHandler();
							}}
							onCreateSubProject={() => {
								createSubProjectParentId = projectId;
								showCreateSubProjectModal = true;
							}}
						>
							<div class="p-1 dark:hover:bg-gray-850 rounded-lg touch-auto">
								<EllipsisHorizontal className="size-4" strokeWidth="2.5" />
							</div>
						</ProjectMenu>
					</button>
				{/if}
			</div>
		</div>

		<div slot="content" class="w-full">
			{#if (projects[projectId]?.childrenIds ?? []).length > 0 || (chats ?? []).length > 0}
				<div
					class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900"
				>
					{#if projects[projectId]?.childrenIds}
						{@const children = projects[projectId]?.childrenIds
							.map((id) => projects[id])
							.sort((a, b) =>
								a.name.localeCompare(b.name, undefined, {
									numeric: true,
									sensitivity: 'base'
								})
							)}

						{#each children as childFolder (`${projectId}-${childFolder.id}`)}
							<svelte:self
								bind:projectRegistry
								{projects}
								projectId={childFolder.id}
								{shiftKey}
								parentDragged={dragged}
								{onItemMove}
								{onDelete}
								on:import={(e) => {
									dispatch('import', e.detail);
								}}
								on:update={(e) => {
									dispatch('update', e.detail);
								}}
								on:change={(e) => {
									dispatch('change', e.detail);
								}}
							/>
						{/each}
					{/if}

					{#each chats ?? [] as chat (chat.id)}
						<ChatItem
							id={chat.id}
							title={chat.title}
							createdAt={chat.created_at}
							updatedAt={chat.updated_at}
							lastReadAt={chat.last_read_at}
							ownerName={projects[projectId]?.shared ? (chat.owner_name ?? null) : null}
							ownerUserId={projects[projectId]?.shared && chat.owner_name ? chat.user_id : null}
							readonly={chat.user_id !== $user?.id}
							{shiftKey}
							on:change={(e) => {
								dispatch('change', e.detail);
							}}
						/>
					{/each}
				</div>
			{/if}

			{#if chats === null}
				<div class="flex justify-center items-center p-2">
					<Spinner className="size-4 text-gray-500" />
				</div>
			{/if}
		</div>
	</Collapsible>
</div>
