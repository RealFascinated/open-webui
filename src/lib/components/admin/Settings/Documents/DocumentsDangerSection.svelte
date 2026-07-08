<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import AdminDangerZone from '../../AdminDangerZone.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{
		resetUpload: void;
		resetVector: void;
		reindex: void;
	}>();
</script>

<AdminDangerZone
	title="Danger Zone"
	description="Destructive actions for uploads, vector storage, and knowledge reindexing."
>
	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('Reset Upload Directory')}</div>
		<div class="flex items-center relative">
			<button class="text-xs" type="button" on:click={() => dispatch('resetUpload')}>
				{$i18n.t('Reset')}
			</button>
		</div>
	</div>

	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">
			{$i18n.t('Reset Vector Storage/Knowledge')}
		</div>
		<div class="flex items-center relative">
			<button class="text-xs" type="button" on:click={() => dispatch('resetVector')}>
				{$i18n.t('Reset')}
			</button>
		</div>
	</div>

	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">
			{$i18n.t('Reindex Knowledge Base Vectors')}
		</div>
		<div class="flex items-center relative">
			<button class="text-xs" type="button" on:click={() => dispatch('reindex')}>
				{$i18n.t('Reindex')}
			</button>
		</div>
	</div>
</AdminDangerZone>
