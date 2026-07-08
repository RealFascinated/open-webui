<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import DOMPurify from 'dompurify';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';

	import { selectedProject } from '$lib/stores';

	import {
		deleteProjectById,
		getProjectById,
		updateProjectById,
		createNewProject
	} from '$lib/apis/projects';
	import { getChatsByProjectId } from '$lib/apis/chats';

	import ProjectModal from '$lib/components/layout/Sidebar/Projects/ProjectModal.svelte';
	import ProjectShareModal from '$lib/components/layout/Sidebar/Projects/ProjectShareModal.svelte';

	import Folder from '$lib/components/icons/Folder.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ProjectMenu from '$lib/components/layout/Sidebar/Projects/ProjectMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';

	export let project = null;
	export let readOnly: boolean = false;

	export let onUpdate: (...args: unknown[]) => unknown = (projectId) => {};
	export let onDelete: (...args: unknown[]) => unknown = (projectId) => {};

	let showProjectModal = false;
	let showCreateSubProjectModal = false;
	let showShareModal = false;
	let showDeleteConfirm = false;
	let deleteProjectContents = true;

	const updateHandler = async ({ name, meta, data }) => {
		if (name === '') {
			toast.error($i18n.t('Project name cannot be empty.'));
			return;
		}

		const currentName = project.name;

		name = name.trim();
		project.name = name;

		const res = await updateProjectById(localStorage.token, project.id, {
			name,
			...(meta ? { meta } : {}),
			...(data ? { data } : {})
		}).catch((error) => {
			toast.error(`${error}`);

			project.name = currentName;
			return null;
		});

		if (res) {
			project.name = name;
			if (data) {
				project.data = data;
			}

			toast.success($i18n.t('Project updated successfully'));

			const _project = await getProjectById(localStorage.token, project.id).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			await selectedProject.set(_project);
			onUpdate(_project);
		}
	};

	const updateIconHandler = async (iconName) => {
		const res = await updateProjectById(localStorage.token, project.id, {
			meta: {
				icon: iconName ?? ''
			}
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			project.meta = { ...project.meta, icon: iconName ?? '' };

			toast.success($i18n.t('Project updated successfully'));

			const _project = await getProjectById(localStorage.token, project.id).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			await selectedProject.set(_project);
			onUpdate(_project);
		}
	};

	const deleteHandler = async () => {
		const res = await deleteProjectById(localStorage.token, project.id, deleteProjectContents).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			toast.success($i18n.t('Project deleted successfully'));
			onDelete(project);
		}
	};

	const exportHandler = async () => {
		const chats = await getChatsByProjectId(localStorage.token, project.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!chats) {
			return;
		}

		const blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});

		saveAs(blob, `project-${project.name}-export-${Date.now()}.json`);
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
			onUpdate();
		}
	};
</script>

{#if project}
	<ProjectModal
		bind:show={showProjectModal}
		edit={true}
		projectId={project.id}
		onSubmit={updateHandler}
	/>

	<ProjectModal
		bind:show={showCreateSubProjectModal}
		parentId={project.id}
		onSubmit={createSubProjectHandler}
	/>

	<ProjectShareModal bind:show={showShareModal} {project} />

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete project?')}
		on:confirm={() => {
			deleteHandler();
		}}
	>
		<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3 mb-2">
			<!-- {$i18n.t('This will delete <strong>{{NAME}}</strong> and <strong>all its contents</strong>.', {
				NAME: project.name
			})} -->

			{$i18n.t(`Are you sure you want to delete "{{NAME}}"?`, {
				NAME: project.name
			})}
		</div>

		<div class="flex items-center gap-1.5">
			<input type="checkbox" bind:checked={deleteProjectContents} />

			<div class="text-xs text-gray-500">
				{$i18n.t('Delete all contents inside this project')}
			</div>
		</div>
	</DeleteConfirmDialog>

	<div class="mb-3 px-6 @md:max-w-3xl justify-between w-full flex relative group items-center">
		<div class="text-center flex gap-3.5 items-center">
			{#if readOnly}
				<div
					class="rounded-full bg-gray-50 dark:bg-gray-800 size-11 flex justify-center items-center"
				>
					{#if project?.meta?.icon}
						<Emoji className="size-6" shortCode={project.meta.icon} />
					{:else}
						<Folder className="size-4.5" strokeWidth="2" />
					{/if}
				</div>
			{:else}
				<EmojiPicker
					onClose={() => {}}
					selected={project?.meta?.icon ?? null}
					onSubmit={(name) => {
						console.log(name);
						updateIconHandler(name);
					}}
				>
					<button
						aria-label={$i18n.t('Change project icon')}
						class=" rounded-full bg-gray-50 dark:bg-gray-800 size-11 flex justify-center items-center"
					>
						{#if project?.meta?.icon}
							<Emoji className="size-6" shortCode={project.meta.icon} />
						{:else}
							<Folder className="size-4.5" strokeWidth="2" />
						{/if}
					</button>
				</EmojiPicker>
			{/if}

			<div class="text-3xl line-clamp-1">
				{project.name}
			</div>
		</div>

		{#if !readOnly}
			<div class="flex items-center translate-x-2.5">
				<ProjectMenu
					align="end"
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
						showCreateSubProjectModal = true;
					}}
				>
					<button
						class="p-1.5 dark:hover:bg-gray-850 rounded-full touch-auto"
						aria-label={$i18n.t('Project options')}
						on:click={(e) => {}}
					>
						<EllipsisHorizontal className="size-4" strokeWidth="2.5" />
					</button>
				</ProjectMenu>
			</div>
		{/if}
	</div>
{/if}
