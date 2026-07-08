<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AdminSettingsCard from '../../AdminSettingsCard.svelte';

	const i18n = getContext('i18n');

	export let RAGConfig: Record<string, unknown>;
</script>

<AdminSettingsCard
	title="Files"
	description="Upload limits, allowed extensions, and image compression."
	className="mb-3"
>
	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('Allowed File Extensions')}</div>
		<div class="flex items-center relative">
			<Tooltip
				content={$i18n.t(
					'Allowed file extensions for upload. Separate multiple extensions with commas. Leave empty for all file types.'
				)}
				placement="top-start"
			>
				<input
					class="flex-1 w-full text-sm bg-transparent outline-hidden"
					type="text"
					placeholder={$i18n.t('e.g. pdf, docx, txt')}
					bind:value={RAGConfig.ALLOWED_FILE_EXTENSIONS}
					autocomplete="off"
				/>
			</Tooltip>
		</div>
	</div>

	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('Max Upload Size')}</div>
		<div class="flex items-center relative">
			<Tooltip
				content={$i18n.t(
					'The maximum file size in MB. If the file size exceeds this limit, the file will not be uploaded.'
				)}
				placement="top-start"
			>
				<input
					class="flex-1 w-full text-sm bg-transparent outline-hidden"
					type="number"
					placeholder={$i18n.t('Leave empty for unlimited')}
					bind:value={RAGConfig.FILE_MAX_SIZE}
					autocomplete="off"
					min="0"
				/>
			</Tooltip>
		</div>
	</div>

	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('Max Upload Count')}</div>
		<div class="flex items-center relative">
			<Tooltip
				content={$i18n.t(
					'The maximum number of files that can be used at once in chat. If the number of files exceeds this limit, the files will not be uploaded.'
				)}
				placement="top-start"
			>
				<input
					class="flex-1 w-full text-sm bg-transparent outline-hidden"
					type="number"
					placeholder={$i18n.t('Leave empty for unlimited')}
					bind:value={RAGConfig.FILE_MAX_COUNT}
					autocomplete="off"
					min="0"
				/>
			</Tooltip>
		</div>
	</div>

	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('Image Compression Width')}</div>
		<div class="flex items-center relative">
			<Tooltip
				content={$i18n.t(
					'The width in pixels to compress images to. Leave empty for no compression.'
				)}
				placement="top-start"
			>
				<input
					class="flex-1 w-full text-sm bg-transparent outline-hidden"
					type="number"
					placeholder={$i18n.t('Leave empty for no compression')}
					bind:value={RAGConfig.FILE_IMAGE_COMPRESSION_WIDTH}
					autocomplete="off"
					min="0"
				/>
			</Tooltip>
		</div>
	</div>

	<div class="mb-2.5 flex w-full justify-between">
		<div class="self-center text-xs font-medium">{$i18n.t('Image Compression Height')}</div>
		<div class="flex items-center relative">
			<Tooltip
				content={$i18n.t(
					'The height in pixels to compress images to. Leave empty for no compression.'
				)}
				placement="top-start"
			>
				<input
					class="flex-1 w-full text-sm bg-transparent outline-hidden"
					type="number"
					placeholder={$i18n.t('Leave empty for no compression')}
					bind:value={RAGConfig.FILE_IMAGE_COMPRESSION_HEIGHT}
					autocomplete="off"
					min="0"
				/>
			</Tooltip>
		</div>
	</div>
</AdminSettingsCard>
