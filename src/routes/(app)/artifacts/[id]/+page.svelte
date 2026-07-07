<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { showSidebar } from '$lib/stores';
	import ArtifactViewer from '$lib/components/artifacts/ArtifactViewer.svelte';

	let loaded = false;

	onMount(() => {
		loaded = true;
	});
</script>

{#if loaded}
	<div
		id="artifact-container"
		class="w-full h-full {$showSidebar ? 'md:max-w-[calc(100%-var(--sidebar-width))]' : ''}"
	>
		<ArtifactViewer id={$page.params.id} />
	</div>
{/if}
