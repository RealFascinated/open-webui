<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import {
		getArtifactById,
		updateArtifact,
		deleteArtifact,
		getArtifactStorageItem,
		setArtifactStorageItem,
		deleteArtifactStorageItem,
		listArtifactStorageItems
	} from '$lib/apis/artifacts';
	import type { ArtifactWithCode } from '$lib/apis/artifacts';

	import { config, settings } from '$lib/stores';
	import { injectCsp } from '$lib/utils/csp';
	import { injectStorageBridge } from '$lib/utils/artifact-storage-bridge';
	import {
		artifactEditableSource,
		artifactPreviewHtml,
		artifactDisplayLabel,
		artifactIsMarkdown
	} from '$lib/utils/artifact-render';
	import { copyToClipboard } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	const i18n = getContext('i18n');

	export let id: string;

	let artifact: ArtifactWithCode | null = null;
	let loaded = false;
	let iframeElement: HTMLIFrameElement;

	let editingTitle = false;
	let titleInput: HTMLInputElement;
	let titleDraft = '';
	let showDeleteConfirm = false;
	let copied = false;

	onMount(async () => {
		artifact = await getArtifactById(localStorage.token, id);
		loaded = true;

		if (!artifact) {
			toast.error($i18n.t('Artifact not found'));
			goto('/artifacts');
			return;
		}

		titleDraft = artifact.title ?? '';
		window.addEventListener('message', handleStorageMessage);
	});

	onDestroy(() => {
		window.removeEventListener('message', handleStorageMessage);
	});

	async function handleStorageMessage(e: MessageEvent) {
		if (!iframeElement || e.source !== iframeElement.contentWindow) return;
		const data = e.data;
		if (!data?._owsStorage || data._owsArtifactId !== id) return;

		const { method, args, _owsRequestId: reqId } = data;
		const scope: 'personal' | 'shared' = args?.shared ? 'shared' : 'personal';

		try {
			let result: unknown = null;

			if (method === 'get') {
				result = await getArtifactStorageItem(localStorage.token, id, args.key, scope);
			} else if (method === 'set') {
				result = await setArtifactStorageItem(
					localStorage.token,
					id,
					args.key,
					args.value,
					scope
				);
			} else if (method === 'delete') {
				result = await deleteArtifactStorageItem(localStorage.token, id, args.key, scope);
			} else if (method === 'list') {
				result = await listArtifactStorageItems(localStorage.token, id, args.prefix ?? '', scope);
			}

			iframeElement.contentWindow?.postMessage({ _owsRequestId: reqId, result }, '*');
		} catch (err: unknown) {
			const message = err instanceof Error ? err.message : 'Storage error';
			iframeElement.contentWindow?.postMessage(
				{ _owsRequestId: reqId, error: message },
				'*'
			);
		}
	}

	$: editableSource = artifact
		? artifactEditableSource(artifact.code, artifact.meta, artifact.type)
		: null;

	$: isMarkdown = artifact ? artifactIsMarkdown(artifact.type, artifact.meta) : false;
	$: isIframe = artifact ? artifact.type === 'iframe' && !isMarkdown : false;
	$: isSvg = artifact?.type === 'svg';

	$: displayLabel = artifact ? artifactDisplayLabel(artifact.type, artifact.meta) : '';

	$: srcdoc = (() => {
		if (!artifact || isMarkdown || isSvg) return '';
		let html = artifactPreviewHtml(artifact.code, artifact.meta, artifact.type);
		html = injectStorageBridge(html, id);
		html = injectCsp(html, $config?.ui?.iframe_csp ?? '');
		return html;
	})();

	$: if (editingTitle && titleInput) {
		titleInput.focus();
	}

	async function saveTitle() {
		if (!artifact) return;
		const updated = await updateArtifact(localStorage.token, id, { title: titleDraft });
		if (updated) {
			artifact = { ...artifact, title: updated.title };
			toast.success($i18n.t('Title saved'));
		}
		editingTitle = false;
	}

	async function confirmDelete() {
		const ok = await deleteArtifact(localStorage.token, id);
		if (ok) {
			toast.success($i18n.t('Artifact unpublished'));
			goto('/artifacts');
		} else {
			toast.error($i18n.t('Failed to unpublish'));
		}
		showDeleteConfirm = false;
	}

	function download() {
		if (!artifact || !editableSource) return;
		const mime =
			editableSource.extension === 'jsx'
				? 'text/javascript'
				: editableSource.extension === 'md'
					? 'text/markdown'
					: editableSource.extension === 'svg'
						? 'image/svg+xml'
						: 'text/html';
		const blob = new Blob([editableSource.content], { type: mime });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `${artifact.title ?? 'artifact'}.${editableSource.extension}`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	function fullscreen() {
		if (iframeElement?.requestFullscreen) {
			iframeElement.requestFullscreen();
		}
	}

	function goBack() {
		if (artifact?.chat_id) {
			goto(`/c/${artifact.chat_id}`);
		} else {
			goto('/artifacts');
		}
	}
</script>

{#if !loaded}
	<div class="flex items-center justify-center h-full">
		<Spinner />
	</div>
{:else if artifact}
	<div class="flex flex-col h-full w-full">
		<div class="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 shrink-0">
			<div class="flex items-center gap-2 min-w-0">
				<Tooltip content={artifact.chat_id ? $i18n.t('Back to chat') : $i18n.t('Back')}>
					<button
						class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition shrink-0"
						aria-label={artifact.chat_id ? $i18n.t('Back to chat') : $i18n.t('Back')}
						on:click={goBack}
					>
						<ChevronLeft strokeWidth="2.5" />
					</button>
				</Tooltip>

				{#if editingTitle}
					<input
						bind:this={titleInput}
						class="text-sm font-medium bg-transparent border-b border-gray-400 dark:border-gray-500 outline-none text-gray-900 dark:text-white px-0.5 min-w-0 w-48"
						bind:value={titleDraft}
						on:keydown={(e) => {
							if (e.key === 'Enter') saveTitle();
							if (e.key === 'Escape') editingTitle = false;
						}}
					/>
					<button
						class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-green-500"
						on:click={saveTitle}
					>
						<Check className="size-3.5" />
					</button>
					<button
						class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400"
						on:click={() => (editingTitle = false)}
					>
						<XMark className="size-3.5" />
					</button>
				{:else}
					<span class="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs">
						{artifact.title ?? $i18n.t('Untitled Artifact')}
					</span>
					<Tooltip content={$i18n.t('Rename')}>
						<button
							class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 opacity-0 group-hover:opacity-100"
							on:click={() => {
								titleDraft = artifact?.title ?? '';
								editingTitle = true;
							}}
						>
							<Pencil className="size-3" />
						</button>
					</Tooltip>
				{/if}

				<span
					class="text-[10px] uppercase tracking-wide font-medium px-1.5 py-0.5 rounded shrink-0
						{displayLabel === 'React'
						? 'bg-sky-100 dark:bg-sky-900/40 text-sky-600 dark:text-sky-400'
						: 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}"
				>
					{displayLabel}
				</span>
			</div>

			<div class="flex items-center gap-1">
				<button
					class="text-xs px-2 py-1 rounded-md bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition text-gray-700 dark:text-gray-300"
					on:click={() => {
						copyToClipboard(editableSource?.content ?? artifact?.code ?? '');
						copied = true;
						setTimeout(() => (copied = false), 2000);
					}}
				>
					{copied ? $i18n.t('Copied') : $i18n.t('Copy')}
				</button>

				<Tooltip content={$i18n.t('Download')}>
					<button
						class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition"
						on:click={download}
					>
						<Download className="size-4" />
					</button>
				</Tooltip>

				{#if isIframe}
					<Tooltip content={$i18n.t('Full screen')}>
						<button
							class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition"
							on:click={fullscreen}
						>
							<ArrowsPointingOut className="size-4" />
						</button>
					</Tooltip>
				{/if}

				<Tooltip content={$i18n.t('Unpublish')}>
					<button
						class="p-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 transition"
						on:click={() => (showDeleteConfirm = true)}
					>
						<XMark className="size-4" />
					</button>
				</Tooltip>
			</div>
		</div>

		<div class="flex-1 min-h-0 w-full">
			{#if isMarkdown}
				<div class="w-full h-full overflow-y-auto px-6 py-5">
					<div class="prose dark:prose-invert max-w-3xl mx-auto">
						<Markdown id="library-artifact-md" content={artifact.code} done={true} />
					</div>
				</div>
			{:else if isIframe}
				<iframe
					bind:this={iframeElement}
					title={artifact.title ?? 'Artifact'}
					{srcdoc}
					class="w-full h-full border-0"
					sandbox="allow-scripts allow-downloads{($settings?.iframeSandboxAllowForms ?? false)
						? ' allow-forms'
						: ''}"
				></iframe>
			{:else if isSvg}
				<div class="w-full h-full overflow-auto p-4">
					<!-- eslint-disable-next-line svelte/no-at-html-tags -->
					{@html artifact.code}
				</div>
			{/if}
		</div>
	</div>
{/if}

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Unpublish "{{title}}"?', { title: artifact?.title ?? 'Untitled Artifact' })}
	message={$i18n.t(
		'This removes the artifact from your library and **permanently deletes** all saved storage data. This cannot be undone.'
	)}
	confirmLabel={$i18n.t('Unpublish')}
	on:confirm={confirmDelete}
	on:cancel={() => (showDeleteConfirm = false)}
/>
