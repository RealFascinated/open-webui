<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import {
		PERMISSION_PRESETS,
		PERMISSION_PRESET_IDS,
		type PermissionPresetId
	} from '$lib/utils/permissionPresets';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{ apply: PermissionPresetId }>();

	export let activePreset: PermissionPresetId | null = null;
</script>

<div class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-gray-50/50 dark:bg-gray-900/50 p-3">
	<div class="text-xs font-medium text-gray-500 dark:text-gray-500 mb-2">
		{$i18n.t('Permission Presets')}
	</div>
	<div class="flex flex-wrap gap-2">
		{#each PERMISSION_PRESET_IDS as presetId (presetId)}
			{@const preset = PERMISSION_PRESETS[presetId]}
			<button
				type="button"
				class="px-3 py-1.5 rounded-xl text-xs font-medium border transition {activePreset === presetId
					? 'bg-gray-100 dark:bg-gray-850 border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white'
					: 'bg-white dark:bg-gray-900 border-gray-100/30 dark:border-gray-850/30 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850/60'}"
				title={$i18n.t(preset.description)}
				on:click={() => {
					dispatch('apply', presetId);
				}}
			>
				{$i18n.t(preset.label)}
			</button>
		{/each}
	</div>
	<p class="mt-2 text-xs text-gray-500 dark:text-gray-500">
		{$i18n.t('Apply a preset as a starting point, then customize individual permissions below.')}
	</p>
</div>
