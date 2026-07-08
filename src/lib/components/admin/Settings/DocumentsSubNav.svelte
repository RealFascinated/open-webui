<script lang="ts">
	import { getContext } from 'svelte';
	import { DOCUMENT_SECTIONS, type DocumentSectionId } from './documentsSections';

	const i18n = getContext('i18n');

	export let activeSection: DocumentSectionId = 'general';
</script>

<div
	class="flex gap-1 overflow-x-auto scrollbar-none pb-3 mb-1 border-b border-gray-100/30 dark:border-gray-850/30"
>
	{#each DOCUMENT_SECTIONS as section (section.id)}
		<a
			href="/admin/settings/documents?section={section.id}"
			class="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition {activeSection ===
			section.id
				? 'bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-white font-medium'
				: 'text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-900/60'}"
		>
			{$i18n.t(section.label)}
		</a>
	{/each}
</div>
