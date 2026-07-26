<script context="module" lang="ts">
	let savedTab: 'controls' | 'files' | 'overview' = 'controls';
</script>

<script lang="ts">
	
	
	import {Pane, PaneResizer} from 'paneforge';
	import {v4 as uuidv4} from 'uuid';

	import {onMount, tick, getContext} from 'svelte';
	import {get} from 'svelte/store';
	import {config, terminalServers, showControls, showCallOverlay, showArtifacts, showEmbeds, settings, showFileNavPath, selectedTerminalId, terminalServersLoaded, user} from '$lib/stores';

	import {uploadFile} from '$lib/apis/files';
	import {toast} from 'svelte-sonner';

	import Controls from './Controls/Controls.svelte';
	import CallOverlay from './MessageInput/CallOverlay.svelte';
	import Drawer from '../common/Drawer.svelte';
	import Artifacts from './Artifacts.svelte';
	import Embeds from './ChatControls/Embeds.svelte';
	import FileNav from './FileNav.svelte';
	import PyodideFileNav from './PyodideFileNav.svelte';
	import Overview from './Overview.svelte';

	const i18n = getContext('i18n');

	const CONTROLS_MIN_WIDTH_PX = 380;
	const ARTIFACT_MIN_WIDTH_PX = 560;
	const ARTIFACT_DEFAULT_WIDTH_PX = 720;
	const ARTIFACT_DEFAULT_WIDTH_PERCENT = 48;

	export let history;
	export let models = [];

	export let chatId: string | null = null;

	export let chatFiles = [];

	export let eventTarget: EventTarget;
	export let submitPrompt: (...args: unknown[]) => unknown;
	export let stopResponse: (...args: unknown[]) => unknown;
	export let showMessage: (...args: unknown[]) => unknown;
	export let files;
	export let modelId;

	export let pane: Pane | null = null;

	let largeScreen = false;
	let dragged = false;
	let controlsMinSize = 0;
	let artifactMinSize = 0;
	let paneReady = false;
	let wasShowingArtifacts = false;

	$: effectiveMinSize = $showArtifacts ? artifactMinSize : controlsMinSize;

	// Tab state for Controls+Files panel
	let activeTab = savedTab;
	// svelte-ignore reactive_declaration_module_script_dependency
	$: {
		savedTab = activeTab;
	}

	$: hasMessages = history?.messages && Object.keys(history.messages).length > 0;

	$: showControlsTab = chatFiles.length > 0;
	$: hasDirectToolServerAccess =
		$user?.role === 'admin' || ($user?.permissions?.features?.direct_tool_servers ?? true);
	$: selectedSystemTerminalAvailable = ($terminalServers ?? []).some(
		(t) => t.id && t.id === $selectedTerminalId
	);
	$: selectedDirectTerminalAvailable = ($settings?.terminalServers ?? []).some(
		(s) => s.url === $selectedTerminalId
	);
	$: codeInterpreterActive =
		!$selectedTerminalId &&
		Boolean($config?.features?.enable_code_interpreter) &&
		($user?.role === 'admin' || $user?.permissions?.features?.code_interpreter) &&
		models.some((model) => model.info?.meta?.capabilities?.code_interpreter ?? true);

	$: showFilesTab =
		($selectedTerminalId && (selectedSystemTerminalAvailable || hasDirectToolServerAccess)) ||
		(codeInterpreterActive && $config?.code?.interpreter_engine !== 'jupyter');
	$: showOverviewTab = hasMessages;

	// Tab fallback: if active tab becomes hidden, switch to next available
	$: if (!showOverviewTab && activeTab === 'overview') activeTab = 'controls';
	$: if (!showFilesTab && activeTab === 'files') activeTab = 'controls';
	$: if (!showControlsTab && activeTab === 'controls') {
		if (showFilesTab) activeTab = 'files';
		else if (showOverviewTab) activeTab = 'overview';
	}

	// Auto-close if there are no visible tabs
	$: if (!showControlsTab && !showFilesTab && !showOverviewTab) {
		showControls.set(false);
	}

	// Auto-switch to Files tab when display_file is triggered
	$: if ($showFileNavPath) {
		activeTab = 'files';
		showControls.set(true);
	}

	// Auto-open Files tab when a terminal is selected (suppress panel open when full-screen)
	$: if ($selectedTerminalId && showFilesTab) {
		activeTab = 'files';
		if (largeScreen) {
			showControls.set($settings?.showFilesOnTerminalSelect ?? true);
		}
	}

	$: if ($selectedTerminalId && selectedDirectTerminalAvailable && !hasDirectToolServerAccess) {
		selectedTerminalId.set(null);
	}

	$: if (
		$terminalServersLoaded &&
		$selectedTerminalId &&
		!selectedSystemTerminalAvailable &&
		!selectedDirectTerminalAvailable
	) {
		selectedTerminalId.set(null);
	}

	// Attach a terminal file to the chat input
	const handleTerminalAttach = async (blob: Blob, name: string, contentType: string) => {
		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name,
			collection_name: '',
			status: 'uploading',
			error: '',
			itemId: tempItemId,
			size: blob.size
		};

		files = [...files, fileItem];

		try {
			const file = new File([blob], name, { type: contentType || 'application/octet-stream' });
			const uploaded = await uploadFile(localStorage.token, file);
			if (!uploaded) throw new Error('Upload failed');

			const idx = files.findIndex((f) => f.itemId === tempItemId);
			if (idx !== -1) {
				files[idx] = {
					...fileItem,
					status: 'uploaded',
					file: uploaded,
					id: uploaded.id,
					url: `${uploaded.id}`,
					collection_name: uploaded?.meta?.collection_name
				};
				files = files;
			}
			toast.success($i18n.t('File attached to chat'));
		} catch (_e) {
			files = files.filter((f) => f.itemId !== tempItemId);
			toast.error($i18n.t('Failed to attach file'));
		}
	};

	export const openPane = (mode: 'controls' | 'artifact' = 'controls') => {
		const container = document.getElementById('chat-container');
		if (!container || !pane) return;

		pane.expand();

		const width = container.clientWidth;
		const minPercent = mode === 'artifact' ? artifactMinSize : controlsMinSize;
		const savedPx = parseInt(localStorage?.chatControlsSize ?? '0', 10);
		const savedPercent = savedPx > 0 ? Math.floor((savedPx / width) * 100) : 0;

		let targetPercent = minPercent;
		if (mode === 'artifact') {
			const defaultPercent = Math.max(
				artifactMinSize,
				Math.floor((ARTIFACT_DEFAULT_WIDTH_PX / width) * 100),
				ARTIFACT_DEFAULT_WIDTH_PERCENT
			);
			targetPercent =
				savedPercent >= artifactMinSize ? savedPercent : Math.max(defaultPercent, artifactMinSize);
		} else if (savedPercent >= controlsMinSize) {
			targetPercent = savedPercent;
		}

		pane.resize(Math.max(targetPercent, minPercent));
	};

	const handleMediaQuery = async (e: Event) => {
		if (e.matches) {
			largeScreen = true;
			if ($showCallOverlay) {
				showCallOverlay.set(false);
				await tick();
				showCallOverlay.set(true);
			}
		} else {
			largeScreen = false;
			if ($showCallOverlay) {
				showCallOverlay.set(false);
				await tick();
				showCallOverlay.set(true);
			}
			pane = null;
		}
	};

	const onMouseDown = () => {
		dragged = true;
	};
	const onMouseUp = () => {
		dragged = false;
	};

	onMount(() => {
		const mediaQuery = window.matchMedia('(min-width: 1024px)');
		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		let resizeObserver: ResizeObserver | null = null;
		let isDestroyed = false;

		// Wait for Svelte to render the Pane after largeScreen changed
		const init = async () => {
			await tick();

			if (isDestroyed) return;

			// If controls were persisted as open, set the pane to the saved size
			if ($showControls && pane) {
				openPane(get(showArtifacts) ? 'artifact' : 'controls');
			}

			setTimeout(() => {
				paneReady = true;
			}, 0);

			const container = document.getElementById('chat-container') as HTMLElement;
			if (!container) return;

			const updateMinSizes = (width: number) => {
				controlsMinSize = Math.floor((CONTROLS_MIN_WIDTH_PX / width) * 100);
				artifactMinSize = Math.floor((ARTIFACT_MIN_WIDTH_PX / width) * 100);
			};

			updateMinSizes(container.clientWidth);
			resizeObserver = new ResizeObserver((entries) => {
				for (let entry of entries) {
					const width = entry.contentRect.width;
					updateMinSizes(width);
					if ($showControls && pane) {
						const minPercent = get(showArtifacts) ? artifactMinSize : controlsMinSize;
						if (pane.isExpanded() && pane.getSize() < minPercent) {
							pane.resize(minPercent);
						} else {
							const savedPx = parseInt(localStorage?.chatControlsSize ?? '0', 10);
							const savedPercent =
								savedPx > 0 ? Math.floor((savedPx / width) * 100) : 0;
							if (savedPercent > 0 && savedPercent < minPercent) {
								pane.resize(minPercent);
							}
						}
					}
				}
			});
			resizeObserver.observe(container);
		};
		init();

		document.addEventListener('mousedown', onMouseDown);
		document.addEventListener('mouseup', onMouseUp);

		return () => {
			isDestroyed = true;
			paneReady = false;
			resizeObserver?.disconnect();
			if (!largeScreen) {
				showControls.set(false);
			}
			mediaQuery.removeEventListener('change', handleMediaQuery);
			document.removeEventListener('mousedown', onMouseDown);
			document.removeEventListener('mouseup', onMouseUp);
		};
	});

	const closeHandler = () => {
		if (!largeScreen) {
			showControls.set(false);
		}
		showArtifacts.set(false);
		showEmbeds.set(false);
		if ($showCallOverlay) showCallOverlay.set(false);
	};

	$: if (paneReady && !chatId) closeHandler();

	// Auto-open and size the artifact panel when generation starts.
	$: if (paneReady && largeScreen && pane && $showArtifacts && !wasShowingArtifacts) {
		wasShowingArtifacts = true;
		if (!$showControls) {
			showControls.set(true);
		}
		tick().then(() => openPane('artifact'));
	} else if (!$showArtifacts) {
		wasShowingArtifacts = false;
	}

	// Helper: is a "special" full-screen panel active?
	$: specialPanel = $showCallOverlay || $showArtifacts || $showEmbeds;
</script>

{#if !largeScreen}
	{#if $showControls}
		<Drawer
			show={$showControls}
			onClose={() => showControls.set(false)}
			className="min-h-[100dvh] !bg-white dark:!bg-gray-850"
		>
			<div class="h-[100dvh] flex flex-col">
				{#if $showCallOverlay}
					<div
						class="h-full max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
					>
						<CallOverlay
							bind:files
							{submitPrompt}
							{stopResponse}
							{modelId}
							{chatId}
							{eventTarget}
							on:close={() => showControls.set(false)}
						/>
					</div>
				{:else if $showEmbeds}
					<Embeds />
				{:else if $showArtifacts}
					<Artifacts {history} />
				{:else}
					<!-- Controls + Files tabs -->
					<div class="flex flex-col h-full min-h-0">
						<!-- Tab bar -->
						<div class="flex items-center justify-between px-2 pt-2 pb-2 shrink-0">
							<div class="flex gap-1 min-w-0 overflow-x-auto scrollbar-hidden">
								{#if showControlsTab}
									<button
										class="px-2.5 py-1 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
										'controls'
											? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
											: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
										on:click={() => (activeTab = 'controls')}
									>
										{$i18n.t('Controls')}
									</button>
								{/if}
								{#if showFilesTab}
									<button
										class="px-2.5 py-1 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
										'files'
											? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
											: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
										on:click={() => (activeTab = 'files')}
									>
										{$i18n.t('Files')}
									</button>
								{/if}
								{#if showOverviewTab}
									<button
										class="px-2.5 py-1 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
										'overview'
											? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
											: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
										on:click={() => (activeTab = 'overview')}
									>
										{$i18n.t('Overview')}
									</button>
								{/if}
							</div>
							<button
								class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
								on:click={() => showControls.set(false)}
								aria-label={$i18n.t('Close')}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									class="size-4"
								>
									<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"></path>
								</svg>
							</button>
						</div>

						<div
							class="flex-1 min-h-0 {activeTab === 'overview'
								? 'h-full'
								: activeTab === 'controls'
									? 'overflow-y-auto px-3 pt-1'
									: ''}"
						>
							{#if activeTab === 'overview'}
								<Overview
									{history}
									onNodeClick={(e) => {
										const node = e.node;
										showMessage(node.data.message, true);
									}}
									onClose={() => showControls.set(false)}
								/>
							{:else if activeTab === 'files' && $selectedTerminalId}
								<FileNav onAttach={handleTerminalAttach} {chatId} />
							{:else if activeTab === 'files' && codeInterpreterActive}
								<PyodideFileNav />
							{:else}
								<Controls embed={true} {models} bind:chatFiles />
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</Drawer>
	{/if}
{:else}
	{#if $showControls}
		<PaneResizer
			class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20"
			id="controls-resizer"
		>
			<div
				class="absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"></div>
		</PaneResizer>
	{/if}

	<Pane
		bind:pane
		defaultSize={0}
		onResize={(size) => {
			if ($showControls && pane.isExpanded()) {
				if (size < effectiveMinSize) pane.resize(effectiveMinSize);
				if (size < effectiveMinSize) {
					localStorage.chatControlsSize = 0;
				} else {
					const container = document.getElementById('chat-container');
					localStorage.chatControlsSize = Math.floor((size / 100) * container.clientWidth);
				}
			}
		}}
		onCollapse={() => {
			if (paneReady) showControls.set(false);
		}}
		collapsible={true}
		class="z-10 bg-white dark:bg-gray-850"
	>
		{#if $showControls}
			<div class="flex max-h-full min-h-full">
				<div
					class="w-full {specialPanel && !$showCallOverlay
						? ' '
						: 'bg-white dark:shadow-lg dark:bg-gray-850'} z-40 pointer-events-auto {activeTab ===
					'files'
						? ''
						: 'overflow-y-auto'} scrollbar-hidden"
					id="controls-container"
				>
					{#if $showCallOverlay}
						<div class="w-full h-full flex justify-center">
							<CallOverlay
								bind:files
								{submitPrompt}
								{stopResponse}
								{modelId}
								{chatId}
								{eventTarget}
								on:close={() => showControls.set(false)}
							/>
						</div>
					{:else if $showEmbeds}
						<Embeds overlay={dragged} />
					{:else if $showArtifacts}
						<Artifacts {history} overlay={dragged} />
					{:else}
						<!-- Controls + Files tabs -->
						<div class="flex flex-col h-full min-h-0">
							<!-- Tab bar -->
							<div class="flex items-center justify-between px-2 pt-2 pb-2 shrink-0">
								<div class="flex gap-1 min-w-0 overflow-x-auto scrollbar-hidden">
									{#if showControlsTab}
										<button
											class="px-2.5 py-1 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
											'controls'
												? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
												: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
											on:click={() => (activeTab = 'controls')}
										>
											{$i18n.t('Controls')}
										</button>
									{/if}
									{#if showFilesTab}
										<button
											class="px-2.5 py-1 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
											'files'
												? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
												: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
											on:click={() => (activeTab = 'files')}
										>
											{$i18n.t('Files')}
										</button>
									{/if}
									{#if showOverviewTab}
										<button
											class="px-2.5 py-1 text-sm rounded-lg transition whitespace-nowrap {activeTab ===
											'overview'
												? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-white'
												: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
											on:click={() => (activeTab = 'overview')}
										>
											{$i18n.t('Overview')}
										</button>
									{/if}
								</div>
								<button
									class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
									on:click={() => showControls.set(false)}
									aria-label={$i18n.t('Close')}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class="size-4"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"></path>
									</svg>
								</button>
							</div>

							<div
								class="flex-1 min-h-0 {activeTab === 'overview'
									? 'h-full'
									: activeTab === 'controls'
										? 'overflow-y-auto px-3 pt-1'
										: ''}"
							>
								{#if activeTab === 'overview'}
									<Overview
										{history}
										onNodeClick={(e) => {
											const node = e.node;
											if (node?.data?.message?.favorite) {
												history.messages[node.data.message.id].favorite = true;
											} else {
												history.messages[node.data.message.id].favorite = null;
											}
											showMessage(node.data.message, true);
										}}
										onClose={() => showControls.set(false)}
									/>
								{:else if activeTab === 'files' && $selectedTerminalId}
									<FileNav onAttach={handleTerminalAttach} overlay={dragged} {chatId} />
								{:else if activeTab === 'files' && codeInterpreterActive}
									<PyodideFileNav overlay={dragged} />
								{:else}
									<Controls embed={true} {models} bind:chatFiles />
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</Pane>
{/if}
