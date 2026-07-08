<script lang="ts">
	import type { AntArtifact } from '$lib/utils/ant-artifact';
	import {
		artifactSelectionFromAntArtifact,
		getArtifactVersionPosition,
		type ArtifactSelection
	} from '$lib/utils/artifact-contents';
	import { artifactContents } from '$lib/stores';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let artifact: AntArtifact;
	export let streaming = false;
	export let onPreview: (selection: ArtifactSelection) => void = () => {};

	$: isStreaming = streaming || artifact.complete === false;
	$: selection = artifactSelectionFromAntArtifact(artifact);
	$: versionInfo = !isStreaming
		? getArtifactVersionPosition($artifactContents, selection)
		: null;

	const openPreview = () => onPreview(selection);
</script>

{#if artifact.artifactType}
	<div
		class="group w-full flex items-center gap-3 px-3.5 py-3 rounded-xl border transition-colors cursor-pointer my-1
			{isStreaming
			? 'border-sky-200 dark:border-sky-900/50 bg-sky-50/70 dark:bg-sky-950/20 hover:bg-sky-50 dark:hover:bg-sky-950/30'
			: 'border-gray-200 dark:border-gray-800 bg-gray-50 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850'}"
		on:click={openPreview}
		on:keydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				openPreview();
			}
		}}
		role="button"
		tabindex="0"
	>
		<div
			class="shrink-0 flex items-center justify-center size-8 rounded-lg border
				{isStreaming
				? 'border-sky-200 dark:border-sky-800 bg-white dark:bg-sky-950/40 text-sky-500 dark:text-sky-400'
				: artifact.artifactType === 'react'
					? 'border-gray-200 dark:border-gray-700 bg-sky-50 dark:bg-sky-900/30 text-sky-500 dark:text-sky-400'
					: 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400'}"
		>
			{#if isStreaming}
				<Spinner className="size-4" />
			{:else if artifact.artifactType === 'markdown'}
				<Document className="size-4" />
			{:else}
				<Cube className="size-4" />
			{/if}
		</div>
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate leading-snug">
				{artifact.title}
			</div>
			<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-none flex items-center gap-1.5 flex-wrap">
				{#if isStreaming}
					<span>Building artifact…</span>
				{:else}
					<span>
						{#if artifact.artifactType === 'react'}
							React component
						{:else if artifact.artifactType === 'svg'}
							SVG image
						{:else if artifact.artifactType === 'markdown'}
							Markdown document
						{:else}
							HTML page
						{/if}
					</span>
					{#if versionInfo}
						<span
							class="tabular-nums px-1.5 py-0.5 rounded-md bg-gray-200/80 dark:bg-gray-800 text-gray-600 dark:text-gray-300 font-medium"
							title={versionInfo.total > 1
								? `Version ${versionInfo.version} of ${versionInfo.total}`
								: 'Version 1'}
						>
							v{versionInfo.version}{versionInfo.total > 1 ? `/${versionInfo.total}` : ''}
						</span>
					{/if}
				{/if}
			</div>
		</div>
		<div
			class="shrink-0 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="size-4"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"></path>
			</svg>
		</div>
	</div>
{:else}
	<div
		class="my-1 rounded-xl border border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/30 px-3.5 py-3 text-sm text-amber-900 dark:text-amber-200"
	>
		<div class="font-medium">Unsupported artifact type</div>
		<div class="text-xs mt-1 text-amber-800/80 dark:text-amber-300/80">
			{artifact.type || 'unknown'} is not supported in the artifact panel. Use text/html, application/vnd.ant.react,
			image/svg+xml, or text/markdown.
		</div>
	</div>
{/if}
