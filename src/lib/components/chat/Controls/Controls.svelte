<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	export const models = [];
	export let chatFiles = [];
	export let embed = false;

	const getOpen = (key: string, fallback = true): boolean => {
		const v = localStorage.getItem(`chatControls.${key}`);
		return v !== null ? v === 'true' : fallback;
	};
	const setOpen = (key: string) => (open: boolean) => {
		localStorage.setItem(`chatControls.${key}`, String(open));
	};

	let showFiles = getOpen('files');
</script>

<div class=" dark:text-white">
	{#if !embed}
		<div class=" flex items-center justify-between dark:text-gray-100 mb-2">
			<div class=" text-md self-center font-primary">{$i18n.t('Controls')}</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close chat controls')}
				on:click={() => {
					dispatch('close');
				}}
			>
				<XMark className="size-3.5" />
			</button>
		</div>
	{/if}

	<div class=" dark:text-gray-200 text-sm py-0.5 px-0.5">
		{#if chatFiles.length > 0}
			<Collapsible
				title={$i18n.t('Pinned Files')}
				bind:open={showFiles}
				onChange={setOpen('files')}
				buttonClassName="w-full"
			>
				<div slot="content">
					<p class="text-xs text-gray-500 dark:text-gray-500 mb-1.5">
						{$i18n.t('Pinned files are included in every message, like project knowledge.')}
					</p>
					<div class="flex flex-col gap-1">
						{#each chatFiles as file, fileIdx}
							<FileItem
								className="w-full"
								item={file}
								edit={true}
								url={file?.url ? file.url : null}
								name={file.name}
								type={file.type}
								size={file?.size}
								dismissible={true}
								small={true}
								on:dismiss={() => {
									chatFiles.splice(fileIdx, 1);
									chatFiles = chatFiles;
								}}
								on:click={() => {
									console.log(file);
								}}
							/>
						{/each}
					</div>
				</div>
			</Collapsible>
		{/if}
	</div>
</div>
