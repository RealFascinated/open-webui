<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { goto } from '$app/navigation';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import {
		artifactCode,
		chatId,
		config,
		settings,
		theme,
		showArtifacts,
		showControls,
		artifactContents,
		publishedArtifactIdMap,
		pendingArtifactFix,
		type ArtifactContent
	} from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';
	import { injectCsp } from '$lib/utils/csp';
	import { injectStorageBridge } from '$lib/utils/artifact-storage-bridge';
	import {
		injectArtifactErrorBridge,
		type ArtifactErrorKind
	} from '$lib/utils/artifact-error-bridge';
	import { artifactPublishMeta, publishedArtifactLookupKey } from '$lib/utils/artifact-render';
	import {
		injectArtifactCanvasTheme,
		resolveArtifactCanvasTheme
	} from '$lib/utils/artifact-theme';
	import {
		getArtifactVersionIndices,
		navigateArtifactVersion,
		preserveArtifactSelectionIndex,
		resolveArtifactContentIndex
	} from '$lib/utils/artifact-contents';
	import {
		publishArtifact,
		deleteArtifact,
		getArtifactStorageItem,
		setArtifactStorageItem,
		deleteArtifactStorageItem,
		listArtifactStorageItems
	} from '$lib/apis/artifacts';

	import XMark from '../icons/XMark.svelte';
	import ArrowsPointingOut from '../icons/ArrowsPointingOut.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import SvgPanZoom from '../common/SVGPanZoom.svelte';
	import Download from '../icons/Download.svelte';
	import Cube from '../icons/Cube.svelte';
	import Markdown from '../chat/Messages/Markdown.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import Spinner from '../common/Spinner.svelte';

	export let overlay = false;

	let contents: ArtifactContent[] = [];
	let selectedContentIdx = 0;

	let copied = false;
	let publishing = false;
	let showUnpublishConfirm = false;
	let iframeElement: HTMLIFrameElement;
	let artifactError: { kind: ArtifactErrorKind; message: string } | null = null;
	let fixingArtifact = false;

	// View / Code toggle
	let viewMode: 'preview' | 'code' = 'preview';

	// ── Derived helpers ──────────────────────────────────────────────

	$: currentContent = contents[selectedContentIdx] ?? null;
	$: currentArtifactId = currentContent?.artifactId ?? null;
	$: versionIndices = getArtifactVersionIndices(contents, currentContent?.identifier);
	$: versionPosition =
		versionIndices.indexOf(selectedContentIdx) === -1
			? Math.max(versionIndices.length - 1, 0)
			: versionIndices.indexOf(selectedContentIdx);
	$: effectiveViewMode =
		currentContent?.streaming && currentContent?.mimeType === 'application/vnd.ant.react'
			? 'code'
			: viewMode;

	let previewSrcdoc = '';
	let previewFrameKey = 0;
	let previewIframeLoading = false;
	let previewTimer: ReturnType<typeof setTimeout> | undefined;
	let previewGeneration = 0;
	let lastEffectiveViewMode: 'preview' | 'code' = 'preview';

	$: artifactCanvasTheme = resolveArtifactCanvasTheme($theme);

	$: showPreviewLoader =
		currentContent?.type === 'iframe' &&
		effectiveViewMode === 'preview' &&
		(!previewSrcdoc || previewIframeLoading);

	const buildPreviewSrcdoc = (content: ArtifactContent | null, canvasTheme = artifactCanvasTheme): string => {
		if (!content) return '';
		let html = content.content;
		html = injectArtifactErrorBridge(html);
		if (content.artifactId) {
			html = injectStorageBridge(html, content.artifactId);
		}
		html = injectArtifactCanvasTheme(html, canvasTheme);
		return injectCsp(html, $config?.ui?.iframe_csp ?? '');
	};

	const applyPreviewSrcdoc = (
		content: ArtifactContent | null,
		canvasTheme = artifactCanvasTheme
	) => {
		if (!content || content.type !== 'iframe') {
			if (previewSrcdoc !== '') {
				previewSrcdoc = '';
				previewFrameKey += 1;
			}
			previewIframeLoading = false;
			return;
		}

		const next = buildPreviewSrcdoc(content, canvasTheme);
		if (next !== previewSrcdoc) {
			previewSrcdoc = next;
			previewFrameKey += 1;
			if (next && !content.streaming) {
				previewIframeLoading = true;
			}
		}
	};

	$: {
		const content = currentContent;
		const canvasTheme = artifactCanvasTheme;
		clearTimeout(previewTimer);
		const generation = ++previewGeneration;

		if (!content || content.type !== 'iframe') {
			applyPreviewSrcdoc(null);
		} else if (content.streaming) {
			previewTimer = setTimeout(() => {
				if (generation !== previewGeneration) return;
				applyPreviewSrcdoc(content, canvasTheme);
			}, 120);
		} else {
			applyPreviewSrcdoc(content, canvasTheme);
		}
	}

	// Remount iframe when switching back to preview (e.g. React artifact just finished streaming).
	$: if (
		effectiveViewMode === 'preview' &&
		lastEffectiveViewMode !== 'preview' &&
		currentContent?.type === 'iframe'
	) {
		tick().then(() => applyPreviewSrcdoc(currentContent));
	}
	$: lastEffectiveViewMode = effectiveViewMode;

	function navigateContent(direction: 'prev' | 'next') {
		selectedContentIdx = navigateArtifactVersion(contents, selectedContentIdx, direction);
	}

	// ── iframe load ──────────────────────────────────────────────────

	const canAccessIframeWindow = (iframe: HTMLIFrameElement | undefined): boolean => {
		if (!iframe?.contentWindow) return false;
		try {
			// Sandboxed srcdoc without allow-same-origin is an opaque origin.
			void iframe.contentWindow.document;
			return true;
		} catch {
			return false;
		}
	};

	const iframeLoadHandler = () => {
		previewIframeLoading = false;
		artifactError = null;
		if (!canAccessIframeWindow(iframeElement)) return;

		try {
			const contentWindow = iframeElement.contentWindow;
			if (!contentWindow) return;

			contentWindow.addEventListener(
				'click',
				function (e) {
					const target = (e.target as Element).closest('a') as HTMLAnchorElement | null;
					if (target && target.href) {
						e.preventDefault();
						const url = new URL(target.href, iframeElement.baseURI);
						if (url.origin === window.location.origin) {
							contentWindow.history.pushState(
								null,
								'',
								url.pathname + url.search + url.hash
							);
						} else {
							console.info('External navigation blocked:', url.href);
						}
					}
				},
				true
			);

			contentWindow.addEventListener('dragstart', (event) => {
				event.preventDefault();
			});
		} catch {
			// Preview still works via srcdoc; bridges use postMessage.
		}
	};

	// ── Storage bridge (parent side) ────────────────────────────────

	async function handleStorageMessage(e: MessageEvent) {
		if (!iframeElement) return;
		let frameWindow: Window | null = null;
		try {
			frameWindow = iframeElement.contentWindow;
		} catch {
			return;
		}
		if (!frameWindow || e.source !== frameWindow) return;
		const data = e.data;
		if (!data?._owsStorage || !data._owsArtifactId) return;

		// Only service requests for the currently displayed published artifact
		if (data._owsArtifactId !== currentArtifactId) return;

		const { method, args, _owsRequestId: reqId } = data;
		const scope: 'personal' | 'shared' = args?.shared ? 'shared' : 'personal';

		try {
			let result: unknown = null;
			const token = localStorage.token;
			const aid = data._owsArtifactId as string;

			if (method === 'get') {
				result = await getArtifactStorageItem(token, aid, args.key, scope);
			} else if (method === 'set') {
				result = await setArtifactStorageItem(token, aid, args.key, args.value, scope);
			} else if (method === 'delete') {
				result = await deleteArtifactStorageItem(token, aid, args.key, scope);
			} else if (method === 'list') {
				result = await listArtifactStorageItems(token, aid, args.prefix ?? '', scope);
			}

			frameWindow.postMessage({ _owsRequestId: reqId, result }, '*');
		} catch (err: unknown) {
			const errMsg = err instanceof Error ? err.message : 'Storage error';
			frameWindow?.postMessage({ _owsRequestId: reqId, error: errMsg }, '*');
		}
	}

	function handleArtifactErrorMessage(e: MessageEvent) {
		if (!iframeElement) return;
		let frameWindow: Window | null = null;
		try {
			frameWindow = iframeElement.contentWindow;
		} catch {
			return;
		}
		if (!frameWindow || e.source !== frameWindow) return;
		const data = e.data;
		if (!data?._owsArtifactError) return;

		artifactError = {
			kind: data.kind ?? 'runtime',
			message: data.message ?? 'Unknown error'
		};
	}

	const requestArtifactFix = () => {
		if (!currentContent || !artifactError || fixingArtifact) return;
		fixingArtifact = true;
		pendingArtifactFix.set({
			identifier: currentContent.identifier,
			title: currentContent.title,
			mimeType: currentContent.mimeType,
			errorKind: artifactError.kind,
			errorMessage: artifactError.message
		});
		artifactError = null;
		setTimeout(() => {
			fixingArtifact = false;
		}, 1000);
	};

	// ── iframe load ──────────────────────────────────────────────────

	const showFullScreen = () => {
		const el = iframeElement as HTMLIFrameElement & {
			webkitRequestFullscreen?: () => void;
		};
		if (el?.requestFullscreen) {
			el.requestFullscreen();
		} else if (el?.webkitRequestFullscreen) {
			el.webkitRequestFullscreen();
		}
	};

	const downloadArtifact = () => {
		const blob = new Blob([currentContent?.content ?? ''], { type: 'text/html' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `artifact-${$chatId}-${selectedContentIdx}.html`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	};

	const publishCurrentArtifact = async () => {
		if (!currentContent || publishing) return;
		publishing = true;
		try {
			const result = await publishArtifact(localStorage.token, {
				chat_id: $chatId ?? undefined,
				title: currentContent.title ?? `Artifact ${selectedContentIdx + 1}`,
				type: currentContent.type,
				code: currentContent.content,
				meta: artifactPublishMeta(currentContent)
			});
			if (result) {
				const lookupKey = publishedArtifactLookupKey(
					currentContent.identifier,
					currentContent.title ?? `Artifact ${selectedContentIdx + 1}`
				);
				if (lookupKey) {
					publishedArtifactIdMap.update((map) => ({ ...map, [lookupKey]: result.id }));
				}
				// Attach the stable ID to this content slot
				artifactContents.update((prev) => {
					if (!prev) return prev;
					const updated = [...prev];
					updated[selectedContentIdx] = {
						...updated[selectedContentIdx],
						artifactId: result.id
					};
					return updated;
				});
				toast.success($i18n.t('Artifact saved'), {
					action: {
						label: $i18n.t('View'),
						onClick: () => goto(`/artifacts/${result.id}`)
					}
				});
			} else {
				toast.error($i18n.t('Failed to save artifact'));
			}
		} finally {
			publishing = false;
		}
	};

	const unpublishCurrentArtifact = async () => {
		if (!currentArtifactId) return;
		const ok = await deleteArtifact(localStorage.token, currentArtifactId);
		if (ok) {
			const lookupKey = publishedArtifactLookupKey(
				currentContent?.identifier,
				currentContent?.title
			);
			publishedArtifactIdMap.update((map) => {
				const next = { ...map };
				if (lookupKey) delete next[lookupKey];
				for (const [key, id] of Object.entries(next)) {
					if (id === currentArtifactId) delete next[key];
				}
				return next;
			});
			artifactContents.update((prev) => {
				if (!prev) return prev;
				const updated = [...prev];
				updated[selectedContentIdx] = {
					...updated[selectedContentIdx],
					artifactId: undefined
				};
				return updated;
			});
			toast.success($i18n.t('Artifact unpublished'));
		} else {
			toast.error($i18n.t('Failed to unpublish artifact'));
		}
	};

	// ── Lifecycle ────────────────────────────────────────────────────

	onMount(() => {
		window.addEventListener('message', handleStorageMessage);
		window.addEventListener('message', handleArtifactErrorMessage);

		const unsubscribeArtifactCode = artifactCode.subscribe((value) => {
			if (!value || contents.length === 0) return;
			const codeIdx = resolveArtifactContentIndex(contents, value);
			if (codeIdx !== -1) {
				selectedContentIdx = codeIdx;
			}
		});

		const unsubscribeArtifactContents = artifactContents.subscribe((value) => {
			const newContents = value ?? [];

			if (newContents.length === 0) {
				showControls.set(false);
				showArtifacts.set(false);
				selectedContentIdx = 0;
			} else {
				selectedContentIdx = preserveArtifactSelectionIndex(
					contents,
					selectedContentIdx,
					newContents
				);

				if (
					newContents.length > contents.length &&
					!contents[selectedContentIdx]?.identifier
				) {
					selectedContentIdx = newContents.length - 1;
				}
			}

			contents = newContents;
		});

		return () => {
			clearTimeout(previewTimer);
			unsubscribeArtifactCode();
			unsubscribeArtifactContents();
		};
	});

	onDestroy(() => {
		clearTimeout(previewTimer);
		window.removeEventListener('message', handleStorageMessage);
		window.removeEventListener('message', handleArtifactErrorMessage);
	});
</script>

<div
	class="w-full h-full relative flex flex-col bg-white dark:bg-gray-850"
	id="artifacts-container"
>
	<div class="w-full h-full flex flex-col flex-1 relative">
			{#if contents.length > 0}
			<!-- ── Toolbar ─────────────────────────────────────────────────── -->
			<div class="pointer-events-auto z-20 flex items-center gap-2 px-2.5 py-2 border-b border-gray-100 dark:border-gray-800 text-gray-900 dark:text-white">

				<!-- Version nav -->
				<div class="flex items-center gap-0.5 shrink-0" dir="ltr">
					<button
						aria-label={$i18n.t('Previous')}
						class="p-1 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition disabled:opacity-30 disabled:cursor-not-allowed"
						on:click={() => navigateContent('prev')}
						disabled={versionIndices.length <= 1 || versionPosition <= 0}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" class="size-3.5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
						</svg>
					</button>
					<span class="text-xs tabular-nums select-none px-0.5">
						{versionPosition + 1}/{versionIndices.length}
					</span>
					<button
						aria-label={$i18n.t('Next')}
						class="p-1 rounded-md hover:bg-black/5 dark:hover:bg-white/5 transition disabled:opacity-30 disabled:cursor-not-allowed"
						on:click={() => navigateContent('next')}
						disabled={versionIndices.length <= 1 || versionPosition >= versionIndices.length - 1}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" class="size-3.5">
							<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
						</svg>
					</button>
				</div>

			<!-- React badge -->
			{#if currentContent?.mimeType === 'application/vnd.ant.react'}
				<span class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-sky-100 dark:bg-sky-900/40 text-sky-600 dark:text-sky-400">
					React
				</span>
			{/if}

			{#if currentContent?.streaming}
				<span class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
					{$i18n.t('Building…')}
				</span>
			{/if}

			<!-- View / Code pill toggle -->
			<div class="flex items-center rounded-lg bg-gray-100 dark:bg-gray-800 p-0.5 text-xs gap-0.5">
					<button
						class="px-2.5 py-1 rounded-md transition font-medium {effectiveViewMode === 'preview'
							? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white'
							: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}"
						on:click={() => (viewMode = 'preview')}
					>
						{$i18n.t('Preview')}
					</button>
					<button
						class="px-2.5 py-1 rounded-md transition font-medium {effectiveViewMode === 'code'
							? 'bg-white dark:bg-gray-700 shadow-sm text-gray-900 dark:text-white'
							: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}"
						on:click={() => (viewMode = 'code')}
					>
						{$i18n.t('Code')}
					</button>
				</div>

				<!-- Spacer -->
				<div class="flex-1"></div>

				{#if artifactError}
					<div class="flex items-center gap-1.5 min-w-0 max-w-[50%]">
						<span class="text-xs text-red-600 dark:text-red-400 truncate" title={artifactError.message}>
							{$i18n.t('Preview error')}
						</span>
						<button
							class="shrink-0 text-xs px-2 py-1 rounded-md bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 transition font-medium disabled:opacity-40"
							on:click={requestArtifactFix}
							disabled={fixingArtifact}
						>
							{fixingArtifact ? $i18n.t('Sending…') : $i18n.t('Fix with AI')}
						</button>
					</div>
				{/if}

				<!-- Action buttons -->
				<div class="flex items-center gap-1">
					{#if currentArtifactId}
						<Tooltip content={$i18n.t('Open saved artifact')}>
							<button
								class="flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:hover:bg-blue-900/40 text-blue-600 dark:text-blue-400 transition font-medium"
								on:click={() => goto(`/artifacts/${currentArtifactId}`)}
							>
								<Cube className="size-3" />
								{$i18n.t('Saved')}
							</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Remove from Artifacts')}>
							<button
								class="text-xs px-2 py-1 rounded-md text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
								on:click={() => (showUnpublishConfirm = true)}
							>
								{$i18n.t('Unsave')}
							</button>
						</Tooltip>
					{:else}
						<Tooltip content={$i18n.t('Save to Artifacts — enables persistent storage')}>
							<button
								class="flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition font-medium disabled:opacity-40"
								on:click={publishCurrentArtifact}
								disabled={publishing}
							>
								<Cube className="size-3" />
								{publishing ? $i18n.t('Saving…') : $i18n.t('Save')}
							</button>
						</Tooltip>
					{/if}

					<Tooltip content={$i18n.t('Copy')}>
						<button
							class="p-1.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
							on:click={() => {
								copyToClipboard(currentContent?.content ?? '');
								copied = true;
								setTimeout(() => (copied = false), 2000);
							}}
						>
							{#if copied}
								<svg xmlns="http://www.w3.org/2000/svg" class="size-3.5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" class="size-3.5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" /></svg>
							{/if}
						</button>
					</Tooltip>

					<Tooltip content={$i18n.t('Download')}>
						<button
							class="p-1.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
							on:click={downloadArtifact}
						>
							<Download className="size-3.5" />
						</button>
					</Tooltip>

					{#if currentContent?.type === 'iframe' && effectiveViewMode === 'preview'}
						<Tooltip content={$i18n.t('Full screen')}>
							<button
								class="p-1.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
								on:click={showFullScreen}
							>
								<ArrowsPointingOut className="size-3.5" />
							</button>
						</Tooltip>
					{/if}
				</div>

				<!-- Close -->
				<button
					class="p-1.5 rounded-md text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				on:click={() => {
					showControls.set(false);
					showArtifacts.set(false);
				}}
				>
					<XMark className="size-3.5" />
				</button>
			</div>
		{/if}

		{#if overlay}
			<div class="absolute top-0 left-0 right-0 bottom-0 z-10"></div>
		{/if}

		<div class="flex-1 w-full h-full min-h-0">
			<div class="h-full flex flex-col">
				{#if contents.length > 0}
					<div class="max-w-full w-full h-full">
					{#if effectiveViewMode === 'code'}
						<!-- Raw source view: prefer sourceCode (e.g. JSX) over the generated wrapper HTML -->
						<pre class="w-full h-full overflow-auto p-4 text-xs font-mono text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-900 leading-relaxed whitespace-pre-wrap break-all">{currentContent?.sourceCode ?? currentContent?.content ?? ''}</pre>
						{:else if currentContent?.type === 'markdown'}
							<!-- Rendered markdown prose -->
							<div class="w-full h-full overflow-y-auto px-6 py-5">
								<div class="prose dark:prose-invert max-w-3xl mx-auto">
									<Markdown
										id="artifact-md"
										content={currentContent.content}
										done={currentContent.complete !== false}
									/>
								</div>
							</div>
						{:else if currentContent?.type === 'iframe'}
							<div class="relative w-full h-full min-h-0">
								{#if previewSrcdoc}
									{#key `${selectedContentIdx}-${previewFrameKey}`}
										<iframe
											bind:this={iframeElement}
											title="Content"
											srcdoc={previewSrcdoc}
											class="w-full border-0 h-full rounded-none"
											sandbox="allow-scripts allow-downloads{($settings?.iframeSandboxAllowForms ?? false)
												? ' allow-forms'
												: ''}{
												// Never allow-same-origin when storage is active: that combination
												// lets the iframe's JS remove its own sandbox attribute (MDN).
												!currentArtifactId && ($settings?.iframeSandboxAllowSameOrigin ?? false)
													? ' allow-same-origin'
													: ''}"
											on:load={iframeLoadHandler}
										></iframe>
									{/key}
								{/if}
								{#if showPreviewLoader}
									<div
										class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-white dark:bg-gray-850"
										aria-live="polite"
										aria-busy="true"
									>
										<Spinner className="size-8 text-gray-400 dark:text-gray-500" />
										<p class="text-xs text-gray-400 dark:text-gray-500">
											{$i18n.t('Loading preview…')}
										</p>
									</div>
								{/if}
							</div>
						{:else if currentContent?.type === 'svg'}
							<SvgPanZoom
								className="w-full h-full max-h-full overflow-hidden"
								svg={currentContent.content}
							/>
						{/if}
					</div>
				{:else}
					<div class="m-auto font-medium text-xs text-gray-900 dark:text-white">
						{$i18n.t('No HTML, CSS, or JavaScript content found.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<ConfirmDialog
	bind:show={showUnpublishConfirm}
	title={$i18n.t('Unsave "{{title}}"?', {
		title: currentContent?.title ?? $i18n.t('Untitled Artifact')
	})}
	message={$i18n.t(
		'This removes the artifact from your library and **permanently deletes** all saved storage data (progress, settings, and other key–value data). The preview in this chat stays open, but persistent storage stops working until you save again.'
	)}
	confirmLabel={$i18n.t('Unsave')}
	on:confirm={unpublishCurrentArtifact}
	on:cancel={() => (showUnpublishConfirm = false)}
/>
