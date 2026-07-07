<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { getArtifacts, deleteArtifact } from '$lib/apis/artifacts';
	import type { ArtifactItem } from '$lib/apis/artifacts';
	import { artifactDisplayLabel } from '$lib/utils/artifact-render';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let artifacts: ArtifactItem[] = [];
	let loaded = false;
	let pendingDelete: ArtifactItem | null = null;
	let showDeleteConfirm = false;

	onMount(async () => {
		await load();
	});

	async function load() {
		loaded = false;
		artifacts = await getArtifacts(localStorage.token);
		loaded = true;
	}

	async function confirmDelete() {
		if (!pendingDelete) return;
		const ok = await deleteArtifact(localStorage.token, pendingDelete.id);
		if (ok) {
			toast.success($i18n.t('Artifact unpublished'));
			artifacts = artifacts.filter((a) => a.id !== pendingDelete!.id);
		} else {
			toast.error($i18n.t('Failed to unpublish artifact'));
		}
		pendingDelete = null;
		showDeleteConfirm = false;
	}

	function formatDate(ns: number) {
		return new Date(ns / 1_000_000).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}
</script>

{#if !loaded}
	<div class="flex items-center justify-center h-48">
		<Spinner />
	</div>
{:else if artifacts.length === 0}
	<div class="flex flex-col items-center justify-center h-64 gap-3 text-gray-400 dark:text-gray-500">
		<Cube className="size-10" strokeWidth="1" />
		<p class="text-sm">{$i18n.t('No published artifacts yet')}</p>
		<p class="text-xs">{$i18n.t('Publish an artifact from the chat panel to see it here')}</p>
	</div>
{:else}
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-4">
		{#each artifacts as artifact (artifact.id)}
			<div
				class="group relative flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
				role="button"
				tabindex="0"
				on:click={() => goto(`/artifacts/${artifact.id}`)}
				on:keydown={(e) => e.key === 'Enter' && goto(`/artifacts/${artifact.id}`)}
			>
				<!-- Preview thumbnail -->
				<div class="w-full h-36 bg-gray-50 dark:bg-gray-800 flex items-center justify-center border-b border-gray-200 dark:border-gray-700">
				<Cube className="size-8 text-gray-300 dark:text-gray-600" strokeWidth="1" />
				</div>

				<!-- Metadata -->
				<div class="flex flex-col gap-1 p-3">
					<div class="flex items-start justify-between gap-2">
						<span class="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 leading-snug">
							{artifact.title ?? $i18n.t('Untitled Artifact')}
						</span>

						<Tooltip content={$i18n.t('Unpublish')}>
							<button
								class="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 shrink-0"
								on:click|stopPropagation={() => {
									pendingDelete = artifact;
									showDeleteConfirm = true;
								}}
							>
								<XMark className="size-3.5" />
							</button>
						</Tooltip>
					</div>

					<div class="flex items-center gap-2">
						<span
							class="text-[10px] uppercase tracking-wide font-medium px-1.5 py-0.5 rounded
								{artifactDisplayLabel(artifact.type, artifact.meta) === 'React'
								? 'bg-sky-100 dark:bg-sky-900/40 text-sky-600 dark:text-sky-400'
								: 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}"
						>
							{artifactDisplayLabel(artifact.type, artifact.meta)}
						</span>
						<span class="text-xs text-gray-400 dark:text-gray-500">
							{formatDate(artifact.updated_at)}
						</span>
					</div>
				</div>
			</div>
		{/each}
	</div>
{/if}

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Unpublish "{{title}}"?', { title: pendingDelete?.title ?? 'Untitled Artifact' })}
	message={$i18n.t(
		'This removes the artifact from your library and **permanently deletes** all saved storage data. This cannot be undone.'
	)}
	confirmLabel={$i18n.t('Unpublish')}
	on:confirm={confirmDelete}
	on:cancel={() => {
		pendingDelete = null;
		showDeleteConfirm = false;
	}}
/>
