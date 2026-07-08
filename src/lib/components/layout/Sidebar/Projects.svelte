<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import RecursiveProject from './RecursiveProject.svelte';
	import { chatId, selectedProject } from '$lib/stores';

	export let projectRegistry = {};

	export let projects = {};
	export let shiftKey = false;

	export let onDelete = (projectId) => {};

	let ownedList = [];
	let sharedList = [];

	$: {
		const rootKeys = Object.keys(projects)
			.filter((key) => {
				const f = projects[key];
				if (!f.name) return false;
				// Root folder: no parent, or shared folder whose parent isn't in our projects
				if (f.shared) {
					return !f.parent_id || !projects[f.parent_id];
				}
				return f.parent_id === null;
			})
			.sort((a, b) =>
				(projects[a].name ?? '').localeCompare(projects[b].name ?? '', undefined, {
					numeric: true,
					sensitivity: 'base'
				})
			);
		ownedList = rootKeys.filter((key) => !projects[key].shared);
		sharedList = rootKeys.filter((key) => projects[key].shared);
	}

	const onItemMove = (e) => {
		if (e.originProjectId) {
			projectRegistry[e.originProjectId]?.setProjectItems();
		}
	};

	const loadFolderItems = () => {
		for (const projectId of Object.keys(projects)) {
			projectRegistry[projectId]?.setProjectItems();
		}
	};

	$: if (projects || ($selectedProject && $chatId)) {
		loadFolderItems();
	}
</script>

{#each ownedList as projectId (projectId)}
	<RecursiveProject
		className=""
		bind:projectRegistry
		{projects}
		{projectId}
		{shiftKey}
		{onDelete}
		{onItemMove}
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

{#if sharedList.length > 0}
	<div class="w-full pl-2.5 text-[11px] text-gray-400 dark:text-gray-600 pt-2 pb-0.5">
		{$i18n.t('Shared')}
	</div>
	{#each sharedList as projectId (projectId)}
		<RecursiveProject
			className=""
			bind:projectRegistry
			{projects}
			{projectId}
			{shiftKey}
			{onDelete}
			{onItemMove}
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
