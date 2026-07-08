<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';

	import { config, user, tools as _tools, skills, toolServers, mobile, knowledge, selectedTerminalId, settings, terminalServers } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import { createPicker } from '$lib/utils/google-drive-picker';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUp from '$lib/components/icons/DocumentArrowUp.svelte';
	import Camera from '$lib/components/icons/Camera.svelte';
	import Note from '$lib/components/icons/Note.svelte';
	import Clip from '$lib/components/icons/Clip.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import Refresh from '$lib/components/icons/Refresh.svelte';
	import Agile from '$lib/components/icons/Agile.svelte';
	import ClockRotateRight from '$lib/components/icons/ClockRotateRight.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import Chats from './InputMenu/Chats.svelte';
	import Files from './InputMenu/Files.svelte';
	import Notes from './InputMenu/Notes.svelte';
	import Knowledge from './InputMenu/Knowledge.svelte';
	import AttachWebpageModal from './AttachWebpageModal.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import TerminalMenuPanel from './TerminalMenuPanel.svelte';
	import IntegrationsMenuPanel from './IntegrationsMenuPanel.svelte';
	import MenuFlyoutPanel from './MenuFlyoutPanel.svelte';

	const i18n = getContext('i18n');

	export let files = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let showWebSearchButton = false;
	export let webSearchEnabled = false;
	export let onWebSearchToggle: (...args: unknown[]) => unknown = () => {};

	export let showTerminalButton = false;

	export let showIntegrationsButton = false;
	export let selectedToolIds: string[] = [];
	export let selectedSkillIds: string[] = [];
	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] =
		[];
	export let selectedFilterIds: string[] = [];
	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;
	export let onShowValves: (...args: unknown[]) => unknown = () => {};

	$: showExtrasSection = showIntegrationsButton || showTerminalButton || showWebSearchButton;

	$: showBooleanTogglesSection =
		(toggleFilters && toggleFilters.length > 0) ||
		showImageGenerationButton ||
		showCodeInterpreterButton ||
		showWebSearchButton;

	$: showIntegrationsNavSection =
		(($_tools ?? []).length > 0 || ($toolServers ?? []).length > 0) ||
		(($skills ?? []).some((skill) => skill.is_active));

	$: showNavigationExtrasSection = showTerminalButton || showIntegrationsNavSection;

	$: showIntegrationsTogglesSection =
		(toggleFilters && toggleFilters.length > 0) ||
		showImageGenerationButton ||
		showCodeInterpreterButton;

	$: systemTerminals = ($terminalServers ?? []).filter((t) => t.id);
	$: directTerminals = ($settings?.terminalServers ?? []).filter((s) => s.url);
	$: selectedSystemTerminal = systemTerminals.find((t) => t.id === $selectedTerminalId);
	$: selectedDirectTerminal = directTerminals.find((t) => t.url === $selectedTerminalId);
	$: selectedTerminalLabel =
		selectedSystemTerminal?.name ||
		selectedSystemTerminal?.id ||
		selectedDirectTerminal?.name ||
		selectedDirectTerminal?.url?.replace(/^https?:\/\//, '') ||
		'';

	export let screenCaptureHandler: (...args: unknown[]) => unknown;
	export let uploadFilesHandler: (...args: unknown[]) => unknown;
	export let inputFilesHandler: (...args: unknown[]) => unknown;

	export let uploadGoogleDriveHandler: (...args: unknown[]) => unknown;
	export let uploadOneDriveHandler: (...args: unknown[]) => unknown;

	export let onUpload: (...args: unknown[]) => unknown;
	export let onClose: (...args: unknown[]) => unknown;

	let show = false;
	let tab = '';
	let activeSubmenu: string | null = null;

	let terminalTriggerElement: HTMLElement | null = null;
	let terminalFlyoutPanel: MenuFlyoutPanel | null = null;
	let terminalCloseTimer: ReturnType<typeof setTimeout> | null = null;

	$: terminalFlyoutOpen = activeSubmenu === 'terminal';

	const openTerminalFlyout = () => {
		if (terminalCloseTimer) {
			clearTimeout(terminalCloseTimer);
			terminalCloseTimer = null;
		}
		activeSubmenu = 'terminal';
		terminalFlyoutPanel?.updatePlacement();
	};

	const closeTerminalFlyout = () => {
		if (terminalCloseTimer) clearTimeout(terminalCloseTimer);
		terminalCloseTimer = setTimeout(() => {
			if (activeSubmenu === 'terminal') activeSubmenu = null;
			terminalCloseTimer = null;
		}, 120);
	};

	const toggleTerminalFlyout = () => {
		if (terminalFlyoutOpen) {
			if (terminalCloseTimer) clearTimeout(terminalCloseTimer);
			terminalCloseTimer = null;
			activeSubmenu = null;
		} else {
			openTerminalFlyout();
		}
	};

	const openTerminal = () => {
		if (terminalFlyoutPanel?.canOpenAsSideFlyout(terminalTriggerElement)) {
			toggleTerminalFlyout();
		} else {
			activeSubmenu = null;
			tab = 'terminal';
		}
	};

	let showAttachWebpageModal = false;

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	let webUploadEnabled = true;
	$: webUploadEnabled = $user?.role === 'admin' || ($user?.permissions?.chat?.web_upload ?? true);

	$: if (!fileUploadEnabled && files.length > 0) {
		files = [];
	}

	const detectMobile = () => {
		const userAgent = navigator.userAgent || navigator.vendor || window.opera;
		return /android|iphone|ipad|ipod|windows phone/i.test(userAgent);
	};

	const handleFileChange = (event) => {
		const inputFiles = Array.from(event.target?.files);
		if (inputFiles && inputFiles.length > 0) {
			console.log(inputFiles);
			inputFilesHandler(inputFiles);
		}
	};

	const onSelect = (item) => {
		if (files.find((f) => f.id === item.id)) {
			return;
		}
		files = [
			...files,
			{
				...item,
				status: 'processed'
			}
		];

		show = false;
	};
</script>

<AttachWebpageModal
	bind:show={showAttachWebpageModal}
	onSubmit={(e) => {
		onUpload(e);
	}}
/>

<!-- Hidden file input used to open the camera on mobile -->
<input
	id="camera-input"
	type="file"
	accept="image/*"
	capture="environment"
	on:change={handleFileChange}
	style="display: none;"
/>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			tab = '';
			activeSubmenu = null;
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<div
			class="w-70 rounded-2xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg max-h-[min(32rem,calc(100dvh-5rem))] overflow-y-auto overflow-x-hidden scrollbar-thin transition"
		>
			{#if tab === ''}
				<div in:fly={{ x: -20, duration: 150 }}>
					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<button
							class="flex w-full gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							type="button"
							on:click={() => {
								if (fileUploadEnabled) {
									uploadFilesHandler();
									show = false;
								}
							}}
						>
							<Clip />

							<div class="line-clamp-1">{$i18n.t('Upload Files')}</div>
						</button>
					</Tooltip>

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<button
							class="flex w-full gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							type="button"
							on:click={() => {
								if (fileUploadEnabled) {
									if (!detectMobile()) {
										screenCaptureHandler();
									} else {
										const cameraInputElement = document.getElementById('camera-input');

										if (cameraInputElement) {
											cameraInputElement.click();
										}
									}
									show = false;
								}
							}}
						>
							<Camera />
							<div class=" line-clamp-1">{$i18n.t('Capture')}</div>
						</button>
					</Tooltip>

					<Tooltip
						content={!webUploadEnabled
							? $i18n.t('You do not have permission to upload web content.')
							: ''}
						className="w-full"
					>
						<button
							class="flex w-full gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl {!webUploadEnabled
								? 'opacity-50'
								: ''}"
							type="button"
							on:click={() => {
								if (webUploadEnabled) {
									showAttachWebpageModal = true;
									show = false;
								}
							}}
						>
							<GlobeAlt />
							<div class="line-clamp-1">{$i18n.t('Attach Webpage')}</div>
						</button>
					</Tooltip>

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<button
							class="flex gap-2 w-full items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								if (fileUploadEnabled) {
									tab = 'files';
								}
							}}
						>
							<DocumentArrowUp />

							<div class="flex items-center w-full justify-between">
								<div class="line-clamp-1">
									{$i18n.t('Attach Files')}
								</div>

								<div class="text-gray-500">
									<ChevronRight />
								</div>
							</div>
						</button>
					</Tooltip>

					{#if $config?.features?.enable_notes ?? false}
						<Tooltip
							content={fileUploadCapableModels.length !== selectedModels.length
								? $i18n.t('Model(s) do not support file upload')
								: !fileUploadEnabled
									? $i18n.t('You do not have permission to upload files.')
									: ''}
							className="w-full"
						>
							<button
								class="flex gap-2 w-full items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl {!fileUploadEnabled
									? 'opacity-50'
									: ''}"
								on:click={() => {
									tab = 'notes';
								}}
							>
								<PageEdit />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Attach Notes')}
									</div>

									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>
						</Tooltip>
					{/if}

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<button
							class="flex gap-2 w-full items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								tab = 'knowledge';
							}}
						>
							<Database />

							<div class="flex items-center w-full justify-between">
								<div class=" line-clamp-1">
									{$i18n.t('Attach Knowledge')}
								</div>

								<div class="text-gray-500">
									<ChevronRight />
								</div>
							</div>
						</button>
					</Tooltip>

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<button
							class="flex gap-2 w-full items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								tab = 'chats';
							}}
						>
							<ClockRotateRight />

							<div class="flex items-center w-full justify-between">
								<div class=" line-clamp-1">
									{$i18n.t('Reference Chats')}
								</div>

								<div class="text-gray-500">
									<ChevronRight />
								</div>
							</div>
						</button>
					</Tooltip>

					{#if fileUploadEnabled}
						{#if $config?.features?.enable_google_drive_integration}
							<button
								class="flex w-full gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl"
								type="button"
								on:click={() => {
									uploadGoogleDriveHandler();
									show = false;
								}}
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 87.3 78" class="w-4">
									<path
										d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z"
										fill="#0066da"
									/>
									<path
										d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z"
										fill="#00ac47"
									/>
									<path
										d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z"
										fill="#ea4335"
									/>
									<path
										d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z"
										fill="#00832d"
									/>
									<path
										d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z"
										fill="#2684fc"
									/>
									<path
										d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z"
										fill="#ffba00"
									/>
								</svg>
								<div class="line-clamp-1">{$i18n.t('Google Drive')}</div>
							</button>
						{/if}

						{#if $config?.features?.enable_onedrive_integration && ($config?.features?.enable_onedrive_personal || $config?.features?.enable_onedrive_business)}
							<button
								class="flex gap-2 w-full items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl {!fileUploadEnabled
									? 'opacity-50'
									: ''}"
								on:click={() => {
									tab = 'microsoft_onedrive';
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 32 32"
									class="size-4"
									fill="none"
								>
									<mask
										id="mask0_87_7796"
										style="mask-type:alpha"
										maskUnits="userSpaceOnUse"
										x="0"
										y="6"
										width="32"
										height="20"
									>
										<path
											d="M7.82979 26C3.50549 26 0 22.5675 0 18.3333C0 14.1921 3.35322 10.8179 7.54613 10.6716C9.27535 7.87166 12.4144 6 16 6C20.6308 6 24.5169 9.12183 25.5829 13.3335C29.1316 13.3603 32 16.1855 32 19.6667C32 23.0527 29 26 25.8723 25.9914L7.82979 26Z"
											fill="#C4C4C4"
										/>
									</mask>
									<g mask="url(#mask0_87_7796)">
										<path
											d="M7.83017 26.0001C5.37824 26.0001 3.18957 24.8966 1.75391 23.1691L18.0429 16.3335L30.7089 23.4647C29.5926 24.9211 27.9066 26.0001 26.0004 25.9915C23.1254 26.0001 12.0629 26.0001 7.83017 26.0001Z"
											fill="url(#paint0_linear_87_7796)"
										/>
										<path
											d="M25.5785 13.3149L18.043 16.3334L30.709 23.4647C31.5199 22.4065 32.0004 21.0916 32.0004 19.6669C32.0004 16.1857 29.1321 13.3605 25.5833 13.3337C25.5817 13.3274 25.5801 13.3212 25.5785 13.3149Z"
											fill="url(#paint1_linear_87_7796)"
										/>
										<path
											d="M7.06445 10.7028L18.0423 16.3333L25.5779 13.3148C24.5051 9.11261 20.6237 6 15.9997 6C12.4141 6 9.27508 7.87166 7.54586 10.6716C7.3841 10.6773 7.22358 10.6877 7.06445 10.7028Z"
											fill="url(#paint2_linear_87_7796)"
										/>
										<path
											d="M1.7535 23.1687L18.0425 16.3331L7.06471 10.7026C3.09947 11.0792 0 14.3517 0 18.3331C0 20.1665 0.657197 21.8495 1.7535 23.1687Z"
											fill="url(#paint3_linear_87_7796)"
										/>
									</g>
									<defs>
										<linearGradient
											id="paint0_linear_87_7796"
											x1="4.42591"
											y1="24.6668"
											x2="27.2309"
											y2="23.2764"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#2086B8" />
											<stop offset="1" stop-color="#46D3F6" />
										</linearGradient>
										<linearGradient
											id="paint1_linear_87_7796"
											x1="23.8302"
											y1="19.6668"
											x2="30.2108"
											y2="15.2082"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#1694DB" />
											<stop offset="1" stop-color="#62C3FE" />
										</linearGradient>
										<linearGradient
											id="paint2_linear_87_7796"
											x1="8.51037"
											y1="7.33333"
											x2="23.3335"
											y2="15.9348"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#0D3D78" />
											<stop offset="1" stop-color="#063B83" />
										</linearGradient>
										<linearGradient
											id="paint3_linear_87_7796"
											x1="-0.340429"
											y1="19.9998"
											x2="14.5634"
											y2="14.4649"
											gradientUnits="userSpaceOnUse"
										>
											<stop stop-color="#16589B" />
											<stop offset="1" stop-color="#1464B7" />
										</linearGradient>
									</defs>
								</svg>

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Microsoft OneDrive')}
									</div>

									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>
						{/if}
					{/if}

					{#if showExtrasSection}
						<div class="my-1 mx-2 border-t border-gray-100 dark:border-gray-800" ></div>
					{/if}

					{#if showIntegrationsNavSection}
						<IntegrationsMenuPanel
							bind:tab
							bind:activeSubmenu
							rootOnly
							rootSection="nav"
							active={show}
							{selectedModels}
							bind:selectedToolIds
							bind:selectedSkillIds
							{toggleFilters}
							bind:selectedFilterIds
							{showImageGenerationButton}
							bind:imageGenerationEnabled
							{showCodeInterpreterButton}
							bind:codeInterpreterEnabled
							{onShowValves}
						/>
					{/if}

					{#if showTerminalButton}
						<div bind:this={terminalTriggerElement} class="relative">
							<button
								class="flex gap-2 w-full items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl"
								type="button"
								on:mouseenter={() =>
									terminalFlyoutPanel?.canOpenAsSideFlyout(terminalTriggerElement) &&
									openTerminalFlyout()}
								on:mouseleave={closeTerminalFlyout}
								on:click={openTerminal}
							>
								<Cloud className="size-4" strokeWidth="2" />

								<div class="flex items-center w-full justify-between min-w-0">
									<div class="line-clamp-1">
										{$i18n.t('Terminal')}
										{#if $selectedTerminalId && selectedTerminalLabel}
											<span class="text-gray-500"> · {selectedTerminalLabel}</span>
										{/if}
									</div>

									<div class="text-gray-500 shrink-0">
										<ChevronRight />
									</div>
								</div>
							</button>

							<MenuFlyoutPanel
								bind:this={terminalFlyoutPanel}
								show={terminalFlyoutOpen}
								anchor={terminalTriggerElement}
								onMouseEnter={openTerminalFlyout}
								onMouseLeave={closeTerminalFlyout}
							>
								<TerminalMenuPanel
									on:selected={() => {
										show = false;
										activeSubmenu = null;
										tab = '';
									}}
								/>
							</MenuFlyoutPanel>
						</div>
					{/if}

					{#if showBooleanTogglesSection}
						{#if showNavigationExtrasSection}
							<div class="my-1 mx-2 border-t border-gray-100 dark:border-gray-800" ></div>
						{/if}

						{#if showIntegrationsTogglesSection}
							<IntegrationsMenuPanel
								bind:tab
								rootOnly
								rootSection="toggles"
								active={show}
								{selectedModels}
								bind:selectedToolIds
								bind:selectedSkillIds
								{toggleFilters}
								bind:selectedFilterIds
								{showImageGenerationButton}
								bind:imageGenerationEnabled
								{showCodeInterpreterButton}
								bind:codeInterpreterEnabled
								{onShowValves}
							/>
						{/if}

						{#if showWebSearchButton}
						<Tooltip content={$i18n.t('Search the internet')} placement="top-start">
							<button
								class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
								aria-pressed={webSearchEnabled}
								aria-label={webSearchEnabled
									? $i18n.t('Disable Web Search')
									: $i18n.t('Enable Web Search')}
								type="button"
								on:click={() => {
									webSearchEnabled = !webSearchEnabled;
									onWebSearchToggle(webSearchEnabled);
								}}
							>
								<div class="flex-1 truncate">
									<div class="flex flex-1 gap-2 items-center">
										<div class="shrink-0">
											<GlobeAlt />
										</div>

										<div class="truncate">{$i18n.t('Web Search')}</div>
									</div>
								</div>

								<div class="shrink-0">
									<Switch
										state={webSearchEnabled}
										on:change={async (e) => {
											const state = e.detail;
											webSearchEnabled = state;
											onWebSearchToggle(state);
											await tick();
										}}
									/>
								</div>
							</button>
						</Tooltip>
					{/if}
					{/if}
				</div>
			{:else if tab === 'knowledge'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Knowledge')}
							</div>
						</div>
					</button>

					<Knowledge {onSelect} />
				</div>
			{:else if tab === 'notes'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Notes')}
							</div>
						</div>
					</button>

					<Notes {onSelect} />
				</div>
			{:else if tab === 'files'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Files')}
							</div>
						</div>
					</button>

					<Files {onSelect} />
				</div>
			{:else if tab === 'chats'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Chats')}
							</div>
						</div>
					</button>

					<Chats {onSelect} />
				</div>
			{:else if tab === 'microsoft_onedrive'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Microsoft OneDrive')}
							</div>
						</div>
					</button>

					{#if $config?.features?.enable_onedrive_personal}
						<button
							class="flex w-full gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl text-left"
							type="button"
							on:click={() => {
								uploadOneDriveHandler('personal');
								show = false;
							}}
						>
							<div class="flex flex-col">
								<div class="line-clamp-1">{$i18n.t('Microsoft OneDrive (personal)')}</div>
							</div>
						</button>
					{/if}

					{#if $config?.features?.enable_onedrive_business}
						<button
							class="flex w-full gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl text-left"
							type="button"
							on:click={() => {
								uploadOneDriveHandler('organizations');
								show = false;
							}}
						>
							<div class="flex flex-col">
								<div class="line-clamp-1">
									{$i18n.t('Microsoft OneDrive (work/school)')}
								</div>
								<div class="text-xs text-gray-500">{$i18n.t('Includes SharePoint')}</div>
							</div>
						</button>
					{/if}
				</div>
			{:else if tab === 'tools'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<IntegrationsMenuPanel
						bind:tab
						bind:activeSubmenu
						active={show}
						selectedModels={selectedModels}
						bind:selectedToolIds
						bind:selectedSkillIds
						{toggleFilters}
						bind:selectedFilterIds
						{showImageGenerationButton}
						bind:imageGenerationEnabled
						{showCodeInterpreterButton}
						bind:codeInterpreterEnabled
						{onShowValves}
					/>
				</div>
			{:else if tab === 'terminal'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm select-none cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Terminal')}
							</div>
						</div>
					</button>

					<TerminalMenuPanel
						on:selected={() => {
							show = false;
							activeSubmenu = null;
							tab = '';
						}}
					/>
				</div>
			{:else if tab === 'skills'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<IntegrationsMenuPanel
						bind:tab
						bind:activeSubmenu
						active={show}
						selectedModels={selectedModels}
						bind:selectedToolIds
						bind:selectedSkillIds
						{toggleFilters}
						bind:selectedFilterIds
						{showImageGenerationButton}
						bind:imageGenerationEnabled
						{showCodeInterpreterButton}
						bind:codeInterpreterEnabled
						{onShowValves}
					/>
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
