<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let dirty = false;
	export let saving = false;
	export let saveLabel = 'Save';
	export let onSave: () => void = () => {};
	export let onDiscard: (() => void) | null = null;
</script>

{#if dirty || saving}
<div class="sticky bottom-0 z-10 mt-4 pb-1">
	<div
		class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white/95 dark:bg-gray-950/95 backdrop-blur-xl px-4 py-3.5"
	>
		<div class="flex items-center justify-between gap-3">
			<div class="text-xs text-gray-500 dark:text-gray-500 min-w-0">
				{#if dirty}
					{$i18n.t('You have unsaved changes')}
				{:else}
					{$i18n.t('Saving...')}
				{/if}
			</div>

			<div class="flex items-center gap-2 shrink-0">
				{#if dirty && onDiscard}
					<button
						class="px-3 py-1.5 text-xs font-medium rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						type="button"
						disabled={saving}
						on:click={onDiscard}
					>
						{$i18n.t('Discard')}
					</button>
				{/if}

				<button
					class="px-3.5 py-1.5 text-xs font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 disabled:opacity-50"
					type="button"
					disabled={saving || !dirty}
					on:click={onSave}
				>
					{#if saving}
						<Spinner className="size-3" />
					{/if}
					{$i18n.t(saveLabel)}
				</button>
			</div>
		</div>
	</div>
</div>
{/if}
