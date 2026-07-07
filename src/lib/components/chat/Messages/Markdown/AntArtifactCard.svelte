<script lang="ts">
	import type { AntArtifact } from '$lib/utils/ant-artifact';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Document from '$lib/components/icons/Document.svelte';

	export let artifact: AntArtifact;
	export let onPreview: (content: string) => void = () => {};
</script>

{#if artifact.artifactType}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div
		class="group w-full flex items-center gap-3 px-3.5 py-3 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition-colors cursor-pointer my-1"
		on:click={() => onPreview(artifact.content)}
	>
		<div
			class="shrink-0 flex items-center justify-center size-8 rounded-lg border border-gray-200 dark:border-gray-700
				{artifact.artifactType === 'react'
				? 'bg-sky-50 dark:bg-sky-900/30 text-sky-500 dark:text-sky-400'
				: 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400'}"
		>
			{#if artifact.artifactType === 'markdown'}
				<Document className="size-4" />
			{:else}
				<Cube className="size-4" />
			{/if}
		</div>
		<div class="flex-1 min-w-0">
			<div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate leading-snug">
				{artifact.title}
			</div>
			<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-none">
				{artifact.artifactType === 'react'
					? 'React component'
					: artifact.artifactType === 'svg'
						? 'SVG image'
						: artifact.artifactType === 'markdown'
							? 'Markdown document'
							: 'HTML page'}
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
				<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
			</svg>
		</div>
	</div>
{/if}
