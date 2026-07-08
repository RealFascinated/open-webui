<script lang="ts">
	import { getContext } from 'svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import AdminSettingsCard from '../../AdminSettingsCard.svelte';

	const i18n = getContext('i18n');

	export let RAGConfig: Record<string, unknown>;
</script>

<AdminSettingsCard
	title="Integration"
	description="Cloud storage connectors for document import."
	className="mb-3"
>
	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('Google Drive')}</div>
		<div class="flex items-center relative">
			<Switch bind:state={RAGConfig.ENABLE_GOOGLE_DRIVE_INTEGRATION} />
		</div>
	</div>

	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('OneDrive')}</div>
		<div class="flex items-center relative">
			<Switch bind:state={RAGConfig.ENABLE_ONEDRIVE_INTEGRATION} />
		</div>
	</div>
</AdminSettingsCard>
