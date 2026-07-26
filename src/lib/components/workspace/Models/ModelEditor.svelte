<script lang="ts">
	import {toast} from 'svelte-sonner';

	import {onMount, getContext, tick} from 'svelte';
	import {models, tools, functions, user} from '$lib/stores';
	import type {Model} from '$lib/stores';
	import type {PromptSuggestion} from '$lib/types';
	import type {ModelParams} from '$lib/apis';
	import {WEBUI_BASE_URL, DEFAULT_CAPABILITIES} from '$lib/constants';

	import {getTools} from '$lib/apis/tools';
	import {getSkills} from '$lib/apis/skills';
	import {getFunctions} from '$lib/apis/functions';
	import {getModelsDefaults} from '$lib/apis/configs';
	import {getBaseModelTags, getModelTags} from '$lib/apis/models';
	import {getVoices} from '$lib/apis/audio';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import ModelEditorSection from '$lib/components/workspace/Models/ModelEditorSection.svelte';
	import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import SkillsSelector from '$lib/components/workspace/Models/SkillsSelector.svelte';
	import FiltersSelector from '$lib/components/workspace/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workspace/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
import Spinner from '$lib/components/common/Spinner.svelte';
import Modal from '$lib/components/common/Modal.svelte';
import DefaultFiltersSelector from './DefaultFiltersSelector.svelte';
	import DefaultFeatures from './DefaultFeatures.svelte';
	import BuiltinTools from './BuiltinTools.svelte';
	import PromptSuggestions from './PromptSuggestions.svelte';
	import TerminalSelector from './TerminalSelector.svelte';
	import TTSVoiceInput from './TTSVoiceInput.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group';
		principal_id: string;
		permission: 'read' | 'write';
	};

	type ModelTag = {
		name: string;
	};

	type KnowledgeItem = {
		id?: string | null;
		name?: string;
		type?: string;
		status?: string;
		collection_name?: string;
		collection_names?: string[];
		legacy?: boolean;
		[key: string]: unknown;
	};

	type ModelCapabilities = typeof DEFAULT_CAPABILITIES & Record<string, boolean | undefined>;

	type ModelEditorMeta = {
		profile_image_url: string;
		description: string | null;
		suggestion_prompts: PromptSuggestion[] | null;
		tags: ModelTag[];
		knowledge?: KnowledgeItem[];
		toolIds?: string[];
		skillIds?: string[];
		filterIds?: string[];
		defaultFilterIds?: string[];
		actionIds?: string[];
		defaultFeatureIds?: string[];
		builtinTools?: Record<string, boolean>;
		terminalId?: string;
		tts?: { voice?: string };
		capabilities?: Partial<ModelCapabilities>;
	};

	type ModelEditorInfo = {
		id: string;
		base_model_id: string | null;
		name: string;
		meta: ModelEditorMeta;
		params: ModelParams;
		access_grants?: AccessGrant[];
	};

	type WorkspaceModel = ModelEditorInfo & {
		[key: string]: unknown;
	};

	type ListedModel = Model & {
		preset?: boolean;
		arena?: boolean;
		base_model_id?: string | null;
		meta?: Record<string, unknown>;
		params?: ModelParams;
		access_grants?: AccessGrant[];
	};

	type Tool = {
		id: string;
		name?: string;
		meta?: {
			description?: string;
		};
	};

	type Skill = {
		id: string;
		name?: string;
		description?: string;
	};

	type FunctionItem = {
		id: string;
		name?: string;
		type?: string;
		is_global?: boolean;
		meta?: {
			description?: string;
			toggle?: boolean;
		};
	};

	type AdvancedParamsState = Omit<ReturnType<typeof createDefaultAdvancedParams>, 'stop'> & {
		stop?: string | string[] | null;
	};

	const normalizeStopParam = (stop: string | string[] | null | undefined): string[] | null => {
		if (!stop) {
			return null;
		}

		const values = typeof stop === 'string' ? stop.split(',') : stop;
		const trimmed = values.map((value) => value.trim()).filter(Boolean);
		return trimmed.length > 0 ? trimmed : null;
	};

	const formatStopParam = (stop: string | string[] | null | undefined): string | null => {
		if (!stop) {
			return null;
		}

		return typeof stop === 'string' ? stop : stop.join(',');
	};

	const createDefaultAdvancedParams = () => ({
		stream_response: null,
		stream_delta_chunk_size: null,
		compact_context_percent: null,
		function_calling: null,
		reasoning_tags: null,
		seed: null,
		stop: null,
		temperature: null,
		reasoning_effort: null,
		logit_bias: null,
		max_tokens: null,
		top_k: null,
		top_p: null,
		min_p: null,
		frequency_penalty: null,
		presence_penalty: null,
		mirostat: null,
		mirostat_eta: null,
		mirostat_tau: null,
		repeat_last_n: null,
		tfs_z: null,
		repeat_penalty: null,
		use_mmap: null,
		use_mlock: null,
		think: null,
		format: null,
		keep_alive: null,
		num_keep: null,
		num_ctx: null,
		num_batch: null,
		num_thread: null,
		num_gpu: null
	});

	const createDefaultInfo = (): ModelEditorInfo => ({
		id: '',
		base_model_id: null,
		name: '',
		meta: {
			profile_image_url: `${WEBUI_BASE_URL}/static/favicon.png`,
			description: '',
			suggestion_prompts: null,
			tags: []
		},
		params: {
			system: ''
		}
	});

	const listFunctions = (): FunctionItem[] => ($functions ?? []) as FunctionItem[];

	const i18n = getContext('i18n');

	export let onSubmit: (info: ModelEditorInfo) => void | Promise<void>;
	export let onBack: null | (() => void) = null;

	export let model: WorkspaceModel | null = null;
	export let edit = false;

	export let preset = false;

	let loading = false;

	let filesInputElement: HTMLInputElement | undefined;
	let inputFiles: FileList | null | undefined;

	let showAdvanced = false;
	let showPreview = false;
	let showAccessControlModal = false;
	let activeSection = 'profile';
	let initialSnapshot = '';
	let loaded = false;

	// ///////////
	// model
	// ///////////

	let id = '';
	let name = '';

	let enableDescription = true;
	let descriptionDraft = '';

	$: if (!edit) {
		if (name) {
			id = name
				.replace(/\s+/g, '-')
				.replace(/[^a-zA-Z0-9-]/g, '')
				.toLowerCase();
		}
	}

	let system = '';
	let info: ModelEditorInfo = createDefaultInfo();

	let advancedParams: ReturnType<typeof createDefaultAdvancedParams> = createDefaultAdvancedParams();

	let knowledge: KnowledgeItem[] = [];
	let toolIds: string[] = [];
	let skillIds: string[] = [];
	let skillsList: Skill[] = [];

	let filterIds: string[] = [];
	let defaultFilterIds: string[] = [];

	let capabilities: ModelCapabilities = { ...DEFAULT_CAPABILITIES };
	let defaultFeatureIds: string[] = [];
	let builtinTools: Record<string, boolean> = {};

	let actionIds: string[] = [];
	let accessGrants: AccessGrant[] = [];
	let terminalId = '';
	let tts = { voice: '' };
	export let suggestionTags: ModelTag[] = [];
	let voices: { id: string; name?: string }[] = [];

	$: toolsList = ($tools ?? []) as Tool[];
	$: filterFunctions = listFunctions().filter((func) => func.type === 'filter');
	$: actionFunctions = listFunctions().filter((func) => func.type === 'action');
	$: toggleableFilters = listFunctions().filter(
		(func) =>
			func.type === 'filter' &&
			(filterIds.includes(func.id) || func.is_global) &&
			func.meta?.toggle
	);
	$: enabledCapabilityFeatures = (Object.keys(capabilities) as (keyof ModelCapabilities)[])
		.filter((key) => capabilities[key])
		.filter((key) => key === 'web_search');

	type EditorSection = {
		id: string;
		label: string;
	};

	const editorSections: EditorSection[] = [
		{ id: 'profile', label: 'Profile' },
		{ id: 'behavior', label: 'Behavior' },
		{ id: 'prompts', label: 'Prompts' },
		{ id: 'integrations', label: 'Integrations' },
		{ id: 'capabilities', label: 'Capabilities' },
		{ id: 'voice', label: 'Voice' }
	];

	const PARAM_PRESETS = {
		balanced: {},
		creative: { temperature: 1.0, top_p: 0.95, top_k: 40 },
		precise: { temperature: 0.3, top_p: 0.85, top_k: 20 },
		longform: { max_tokens: 4096, temperature: 0.7 }
	} as const;

	const scrollToSection = (sectionId: string) => {
		activeSection = sectionId;
		document.getElementById(`model-editor-${sectionId}`)?.scrollIntoView({
			behavior: 'smooth',
			block: 'start'
		});
	};

	const applyParamPreset = (presetKey: keyof typeof PARAM_PRESETS) => {
		const defaults = createDefaultAdvancedParams();
		const presetValues = PARAM_PRESETS[presetKey];

		advancedParams = {
			...defaults,
			...Object.fromEntries(
				Object.entries(presetValues).map(([key, value]) => [key, value])
			)
		};
		showAdvanced = true;
	};

	const countCustomParams = (params: Record<string, unknown>) =>
		Object.entries(params).filter(
			([key, value]) => key !== 'system' && value !== null && value !== '' && value !== undefined
		).length;

	const isPublicModel = (grants: AccessGrant[]) =>
		grants.some(
			(grant) => grant.principal_type === 'user' && grant.principal_id === '*' && grant.permission === 'read'
		);

	const assembleModelInfo = (): ModelEditorInfo => {
		const assembled: ModelEditorInfo = JSON.parse(JSON.stringify(info));

		assembled.id = id;
		assembled.name = name;
		assembled.params = { ...assembled.params, ...advancedParams };
		assembled.access_grants = accessGrants;
		assembled.meta.capabilities = capabilities;

		if (enableDescription) {
			assembled.meta.description = descriptionDraft.trim() === '' ? null : descriptionDraft;
		} else {
			assembled.meta.description = null;
		}

		if (knowledge.length > 0) {
			assembled.meta.knowledge = knowledge;
		} else {
			delete assembled.meta.knowledge;
		}

		if (toolIds.length > 0) {
			assembled.meta.toolIds = toolIds;
		} else {
			delete assembled.meta.toolIds;
		}

		if (skillIds.length > 0) {
			assembled.meta.skillIds = skillIds;
		} else {
			delete assembled.meta.skillIds;
		}

		if (filterIds.length > 0) {
			assembled.meta.filterIds = filterIds;
		} else {
			delete assembled.meta.filterIds;
		}

		if (defaultFilterIds.length > 0) {
			assembled.meta.defaultFilterIds = defaultFilterIds;
		} else {
			delete assembled.meta.defaultFilterIds;
		}

		if (actionIds.length > 0) {
			assembled.meta.actionIds = actionIds;
		} else {
			delete assembled.meta.actionIds;
		}

		if (defaultFeatureIds.length > 0) {
			assembled.meta.defaultFeatureIds = defaultFeatureIds;
		} else {
			delete assembled.meta.defaultFeatureIds;
		}

		if (Object.keys(builtinTools).length > 0) {
			assembled.meta.builtinTools = builtinTools;
		} else {
			delete assembled.meta.builtinTools;
		}

		if (terminalId) {
			assembled.meta.terminalId = terminalId;
		} else {
			delete assembled.meta.terminalId;
		}

		if (tts.voice !== '') {
			if (!assembled.meta.tts) assembled.meta.tts = {};
			assembled.meta.tts.voice = tts.voice;
		} else if (assembled.meta.tts?.voice) {
			delete assembled.meta.tts.voice;
			if (Object.keys(assembled.meta.tts).length === 0) {
				delete assembled.meta.tts;
			}
		}

		assembled.params.system = system.trim() === '' ? null : system;
		assembled.params.stop = normalizeStopParam((advancedParams as AdvancedParamsState).stop);
		Object.keys(assembled.params).forEach((key) => {
			if (assembled.params[key] === '' || assembled.params[key] === null) {
				delete assembled.params[key];
			}
		});

		return assembled;
	};

	const getSnapshot = () => JSON.stringify(assembleModelInfo());

	$: previewInfo = assembleModelInfo();
	$: customParamCount = countCustomParams(advancedParams as Record<string, unknown>);
	$: enabledCapabilities = Object.entries(capabilities).filter(([, enabled]) => enabled).length;
	$: dirty = loaded && initialSnapshot !== '' && getSnapshot() !== initialSnapshot;

	$: summaryChips = [
		...(system.trim() ? [{ label: $i18n.t('System prompt') }] : []),
		...(customParamCount > 0
			? [{ label: `${customParamCount} ${$i18n.t('custom params')}` }]
			: []),
		...(advancedParams.temperature != null
			? [{ label: `${$i18n.t('Temperature')}: ${advancedParams.temperature}` }]
			: []),
		...(knowledge.length > 0
			? [{ label: `${knowledge.length} ${$i18n.t('knowledge')}` }]
			: []),
		...(toolIds.length > 0 ? [{ label: `${toolIds.length} ${$i18n.t('tools')}` }] : []),
		...(skillIds.length > 0 ? [{ label: `${skillIds.length} ${$i18n.t('skills')}` }] : []),
		...(enabledCapabilities > 0
			? [{ label: `${enabledCapabilities} ${$i18n.t('capabilities')}` }]
			: []),
		...(tts.voice ? [{ label: `${$i18n.t('Voice')}: ${tts.voice}` }] : []),
		{
			label: isPublicModel(accessGrants) ? $i18n.t('Public') : $i18n.t('Private')
		}
	];

	const getBaseModelItems = (modelsList: Model[] = []) => {
		const currentModelId = model?.id;

		return modelsList
			.filter((baseModel) => {
				const listedModel = baseModel as ListedModel;

				return (
					(!currentModelId ||
						listedModel.id !== currentModelId ||
						(edit && listedModel.id === info.base_model_id)) &&
					(!listedModel.preset || (edit && listedModel.id === info.base_model_id)) &&
					(listedModel.owned_by as string) !== 'arena' &&
					($user?.role === 'admin' ||
						!((listedModel.info?.meta as { hidden?: boolean } | undefined)?.hidden ?? false) ||
						listedModel.id === info.base_model_id)
				);
			})
			.map((baseModel) => ({
				value: baseModel.id,
				label: baseModel.name,
				model: baseModel
			}));
	};

	const loadSuggestionTags = async () => {
		const res: string[] = await (preset ? getModelTags : getBaseModelTags)(
			localStorage.token
		).catch(() => []);
		suggestionTags = res.map((tag) => ({ name: tag }));
	};

	const loadVoices = async () => {
		const res = await getVoices(localStorage.token).catch(() => null);
		voices = res?.voices ?? [];
	};

	const submitHandler = async () => {
		loading = true;

		if (id === '') {
			toast.error($i18n.t('Model ID is required.'));
			loading = false;

			return;
		}

		if (name === '') {
			toast.error($i18n.t('Model Name is required.'));
			loading = false;

			return;
		}

		if (preset && !info.base_model_id) {
			toast.error($i18n.t('Base Model is required.'));
			loading = false;

			return;
		}

		if (knowledge.some((item) => item.status === 'uploading')) {
			toast.error($i18n.t('Please wait until all files are uploaded.'));
			loading = false;

			return;
		}

		info = assembleModelInfo();
		await onSubmit(info);
		initialSnapshot = getSnapshot();

		loading = false;
	};

	onMount(async () => {
		if (!$tools) {
			await tools.set(await getTools(localStorage.token));
		}
		skillsList = ((await getSkills(localStorage.token).catch(() => null)) ?? []) as Skill[];
		if (!$functions) {
			await functions.set(await getFunctions(localStorage.token));
		}
		if (suggestionTags.length === 0) {
			await loadSuggestionTags();
		}
		if (voices.length === 0) {
			await loadVoices();
		}

		// Fetch admin-configured default model metadata so the editor
		// reflects the actual defaults rather than hardcoded values
		const modelsConfig = await getModelsDefaults(localStorage.token).catch(() => null);
		const defaultMeta = modelsConfig?.DEFAULT_MODEL_METADATA ?? {};

		// Use admin defaults as base, falling back to hardcoded defaults
		capabilities = { ...DEFAULT_CAPABILITIES, ...(defaultMeta.capabilities ?? {}) };
		defaultFeatureIds = defaultMeta.defaultFeatureIds ?? [];
		builtinTools = defaultMeta.builtinTools ?? {};

		// Scroll to top 'workspace-container' element
		const workspaceContainer = document.getElementById('workspace-container');
		if (workspaceContainer) {
			workspaceContainer.scrollTop = 0;
		}

		if (model) {
			name = model.name;
			await tick();

			id = model.id;

			enableDescription = model.meta?.description != null;
			descriptionDraft = model.meta?.description ?? '';

			if (model.base_model_id) {
				const base_model = $models
					.filter((m) => {
						const listedModel = m as ListedModel;
						return (
							(!listedModel.preset && !(listedModel.arena ?? false)) ||
							(edit && m.id === model.base_model_id)
						);
					})
					.find((m) =>
						[model.base_model_id, `${model.base_model_id}:latest`].includes(m.id)
					);

				console.log('base_model', base_model);

				if (base_model) {
					model.base_model_id = base_model.id;
				} else if (!edit) {
					model.base_model_id = null;
				}
			}

			const modelSystem = model.params?.system;
			system = typeof modelSystem === 'string' ? modelSystem : '';

			advancedParams = {
				...advancedParams,
				...(model.params ?? {})
			} as ReturnType<typeof createDefaultAdvancedParams>;
			const formattedStop = formatStopParam(
				model.params?.stop as string | string[] | null | undefined
			);
			if (formattedStop !== null) {
				(advancedParams as AdvancedParamsState).stop = formattedStop;
			}

			knowledge = (model.meta?.knowledge ?? []).map((item: KnowledgeItem) => {
				if (item?.collection_name && item?.type !== 'file') {
					return {
						id: item.collection_name,
						name: item.name,
						legacy: true
					};
				} else if (item?.collection_names) {
					return {
						name: item.name,
						type: 'collection',
						collection_names: item.collection_names,
						legacy: true
					};
				} else {
					return item;
				}
			});

			toolIds = model.meta?.toolIds ?? [];
			skillIds = model.meta?.skillIds ?? [];
			filterIds = model.meta?.filterIds ?? [];
			defaultFilterIds = model.meta?.defaultFilterIds ?? [];
			actionIds = model.meta?.actionIds ?? [];

			// Per-model overrides take precedence over admin defaults
			capabilities = {
				...capabilities,
				...(model.meta?.capabilities ?? {})
			} as ModelCapabilities;
			defaultFeatureIds = model.meta?.defaultFeatureIds ?? defaultFeatureIds;
			builtinTools = model.meta?.builtinTools ?? builtinTools;
			terminalId = model.meta?.terminalId ?? '';
			tts = { voice: model.meta?.tts?.voice ?? '' };

			accessGrants = model.access_grants ?? [];

			info = {
				...info,
				...JSON.parse(JSON.stringify(model))
			};

			console.log(model);
		}

		loaded = true;
		await tick();
		initialSnapshot = getSnapshot();
	});</script>

{#if loaded}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessGrants
		accessRoles={preset ? ['read', 'write'] : ['read']}
		share={$user?.permissions?.sharing?.models || $user?.role === 'admin'}
		sharePublic={$user?.permissions?.sharing?.public_models || $user?.role === 'admin'}
		shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	/>

	{#if onBack}
		<button
			class="flex space-x-1"
			on:click={() => {
				onBack();
			}}
		>
			<div class=" self-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
				>
					<path
						fill-rule="evenodd"
						d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
						clip-rule="evenodd"></path>
				</svg>
			</div>
			<div class=" self-center text-sm font-medium">{$i18n.t('Back')}</div>
		</button>
	{/if}

	<div class="w-full max-h-full flex justify-center">
		<input
			bind:this={filesInputElement}
			bind:files={inputFiles}
			type="file"
			hidden
			accept="image/*"
			on:change={() => {
				let reader = new FileReader();
				reader.onload = (event) => {
					const result = event.target?.result;
					if (typeof result !== 'string') {
						return;
					}

					let originalImageUrl = result;

					// For animated formats (gif, webp), skip resizing to preserve animation
					const fileType = inputFiles?.[0]?.type;
					if (fileType === 'image/gif' || fileType === 'image/webp') {
						info.meta.profile_image_url = originalImageUrl;
						inputFiles = null;
						if (filesInputElement) {
							filesInputElement.value = '';
						}
						return;
					}

					const img = new Image();
					img.src = originalImageUrl;

					img.onload = function () {
						const canvas = document.createElement('canvas');
						const ctx = canvas.getContext('2d');
						if (!ctx) {
							return;
						}

						// Calculate the aspect ratio of the image
						const aspectRatio = img.width / img.height;

						// Calculate the new width and height to fit within 100x100
						let newWidth, newHeight;
						if (aspectRatio > 1) {
							newWidth = 250 * aspectRatio;
							newHeight = 250;
						} else {
							newWidth = 250;
							newHeight = 250 / aspectRatio;
						}

						// Set the canvas size
						canvas.width = 250;
						canvas.height = 250;

						// Calculate the position to center the image
						const offsetX = (250 - newWidth) / 2;
						const offsetY = (250 - newHeight) / 2;

						// Draw the image on the canvas
						ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

						// Get the base64 representation of the compressed image
						const compressedSrc = canvas.toDataURL('image/webp', 0.8);

						// Display the compressed image
						info.meta.profile_image_url = compressedSrc;

						inputFiles = null;
						if (filesInputElement) {
							filesInputElement.value = '';
						}
					};
				};

				if (
					inputFiles &&
					inputFiles.length > 0 &&
					['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/svg+xml'].includes(
						inputFiles[0].type
					)
				) {
					reader.readAsDataURL(inputFiles[0]);
				} else {
					console.log(`Unsupported File Type '${inputFiles?.[0]?.type}'.`);
					inputFiles = null;
				}
			}}
		/>

		{#if !edit || (edit && model)}
			<form
				class="flex flex-col w-full px-1"
				on:submit|preventDefault={() => {
					submitHandler();
				}}
			>
				<div class="flex flex-col lg:flex-row w-full gap-4 lg:gap-6">
					<nav
						class="lg:w-40 shrink-0 flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible scrollbar-none pb-1 lg:pb-0 lg:sticky lg:top-4 lg:self-start"
						aria-label={$i18n.t('Model settings sections')}
					>
						{#each editorSections as section}
							<button
								type="button"
								class="px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition text-left {activeSection ===
								section.id
									? 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100'
									: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850/50'}"
								on:click={() => scrollToSection(section.id)}
							>
								{$i18n.t(section.label)}
							</button>
						{/each}
					</nav>

					<div class="flex-1 min-w-0 space-y-3 pb-28">
						<ModelEditorSection
							id="model-editor-profile"
							title="Profile"
							description="Model identity, description, and access."
							status={isPublicModel(accessGrants) ? $i18n.t('Public') : $i18n.t('Private')}
						>
							<div class="flex flex-row gap-4 md:gap-6 w-full">
								<div class="self-start flex justify-center shrink-0">
									<div class="self-center">
										<button
											class="rounded-2xl flex shrink-0 items-center {info.meta.profile_image_url !==
											`${WEBUI_BASE_URL}/static/favicon.png`
												? 'bg-transparent'
												: 'bg-white'} shadow-xl group relative"
											type="button"
											aria-label={$i18n.t('Upload profile image')}
											on:click={() => {
												filesInputElement?.click();
											}}
										>
											{#if info.meta.profile_image_url}
												<img
													src={info.meta.profile_image_url}
													alt="model profile"
													class="rounded-xl size-20 md:size-32 object-cover shrink-0"
												/>
											{:else}
												<img
													src="{WEBUI_BASE_URL}/static/favicon.png"
													alt="model profile"
													class="rounded-xl size-20 md:size-32 object-cover shrink-0"
												/>
											{/if}

											<div class="absolute bottom-0 right-0 z-10">
												<div class="m-1.5">
													<div
														class="shadow-xl p-1 rounded-full border-2 border-white bg-gray-800 text-white group-hover:bg-gray-600 transition dark:border-black dark:bg-white dark:group-hover:bg-gray-200 dark:text-black"
													>
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 16 16"
															fill="currentColor"
															class="size-5"
														>
															<path
																fill-rule="evenodd"
																d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
																clip-rule="evenodd"
															></path>
														</svg>
													</div>
												</div>
											</div>
										</button>

										<div class="flex w-full mt-1 justify-end">
											<button
												class="px-2 py-1 text-gray-500 rounded-lg text-xs"
												on:click={() => {
													info.meta.profile_image_url = `${WEBUI_BASE_URL}/static/favicon.png`;
												}}
												type="button"
											>
												{$i18n.t('Reset Image')}
											</button>
										</div>
									</div>
								</div>

								<div class="flex flex-col w-full flex-1 min-w-0">
									<div class="flex justify-between items-start gap-3">
										<div class="flex flex-col w-full min-w-0">
											<input
												class="text-2xl w-full bg-transparent outline-hidden"
												placeholder={$i18n.t('Model Name')}
												bind:value={name}
												required
											/>
											<input
												class="text-xs w-full bg-transparent outline-hidden mt-1"
												placeholder={$i18n.t('Model ID')}
												bind:value={id}
												disabled={edit}
												required
											/>
										</div>

										<button
											class="bg-gray-50 shrink-0 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
											type="button"
											on:click={() => {
												showAccessControlModal = true;
											}}
										>
											<LockClosed strokeWidth="2.5" className="size-3.5 shrink-0" />
											<div class="text-sm font-medium shrink-0">{$i18n.t('Access')}</div>
										</button>
									</div>

									{#if preset}
										<div class="mt-3">
											<div class="text-xs font-medium mb-1 text-gray-500">
												{$i18n.t('Base Model (From)')}
											</div>
											<ModelSelector
												id="workspace-base-model"
												placeholder={$i18n.t('Select a base model (e.g. llama3, gpt-4o)')}
												searchPlaceholder={$i18n.t('Search a model')}
												items={getBaseModelItems($models)}
												className="w-full max-w-lg"
												triggerClassName="text-sm"
												selectionOnly
												includeHidden={$user?.role === 'admin'}
												bind:value={info.base_model_id}
											/>
										</div>
									{/if}

									<div class="mt-3">
										<div class="mb-1 flex w-full justify-between items-center">
											<div class="text-xs font-medium text-gray-500">{$i18n.t('Description')}</div>
											<button
												class="min-w-[4.5rem] px-2 py-1 text-[11px] rounded-md transition {enableDescription
													? 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 font-medium'
													: 'text-gray-500'}"
												type="button"
												on:click={() => {
													enableDescription = !enableDescription;
												}}
											>
												{enableDescription ? $i18n.t('Custom') : $i18n.t('Default')}
											</button>
										</div>

										{#if enableDescription}
											<Textarea
												className="text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden"
												placeholder={$i18n.t('Add a short description about what this model does')}
												bind:value={descriptionDraft}
											/>
										{/if}
									</div>

									<div class="mt-3">
										<Tags
											tags={info?.meta?.tags ?? []}
											{suggestionTags}
											on:delete={(e) => {
												const tagName = e.detail;
												info.meta.tags = info.meta.tags.filter((tag) => tag.name !== tagName);
											}}
											on:add={(e) => {
												const tagName = e.detail;
												if (!(info?.meta?.tags ?? null)) {
													info.meta.tags = [{ name: tagName }];
												} else {
													info.meta.tags = [...info.meta.tags, { name: tagName }];
												}
											}}
										/>
									</div>
								</div>
							</div>

							{#if summaryChips.length > 0}
								<div class="flex flex-wrap gap-1.5 pt-1">
									{#each summaryChips as chip}
										<span
											class="text-[11px] px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"
										>
											{chip.label}
										</span>
									{/each}
								</div>
							{/if}
						</ModelEditorSection>

						<ModelEditorSection
							id="model-editor-behavior"
							title="Behavior"
							description="System prompt and generation parameters."
							status={system.trim() || customParamCount > 0
								? $i18n.t('Configured')
								: $i18n.t('Default')}
						>
							<div>
								<div class="text-xs font-medium mb-2">{$i18n.t('System Prompt')}</div>
								<Textarea
									className="text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden"
									placeholder={$i18n.t(
										'Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.'
									)}
									rows={4}
									bind:value={system}
								/>
							</div>

							<div>
								<div class="flex flex-wrap items-center justify-between gap-2 mb-2">
									<div class="text-xs font-medium">{$i18n.t('Advanced Params')}</div>
									<div class="flex flex-wrap gap-1">
										{#each Object.keys(PARAM_PRESETS) as presetKey}
											<button
												type="button"
												class="px-2 py-1 text-[11px] rounded-md text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850/50 transition capitalize"
												on:click={() => applyParamPreset(presetKey as keyof typeof PARAM_PRESETS)}
											>
												{presetKey}
											</button>
										{/each}
										<button
											type="button"
											class="min-w-[4.5rem] px-2 py-1 text-[11px] rounded-md transition {showAdvanced
												? 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 font-medium'
												: 'text-gray-500'}"
											on:click={() => {
												showAdvanced = !showAdvanced;
											}}
										>
											{showAdvanced ? $i18n.t('Hide') : $i18n.t('Show')}
										</button>
									</div>
								</div>

								{#if showAdvanced}
									<AdvancedParams admin={true} custom={true} params={advancedParams} />
								{/if}
							</div>
						</ModelEditorSection>

						<ModelEditorSection
							id="model-editor-prompts"
							title="Prompts"
							description="Starter prompts shown in the chat placeholder."
							status={(info?.meta?.suggestion_prompts ?? null) === null
								? $i18n.t('Default')
								: $i18n.t('Custom')}
							collapsible={true}
							open={(info?.meta?.suggestion_prompts ?? null) !== null}
						>
							<div class="flex justify-end">
								<button
									class="min-w-[4.5rem] px-2 py-1 text-[11px] rounded-md transition {(info?.meta
										?.suggestion_prompts ?? null) === null
										? 'text-gray-500'
										: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 font-medium'}"
									type="button"
									on:click={() => {
										if ((info?.meta?.suggestion_prompts ?? null) === null) {
											info.meta.suggestion_prompts = [{ content: '', title: ['', ''] }];
										} else {
											info.meta.suggestion_prompts = null;
										}
									}}
								>
									{(info?.meta?.suggestion_prompts ?? null) === null
										? $i18n.t('Default')
										: $i18n.t('Custom')}
								</button>
							</div>

							{#if info?.meta?.suggestion_prompts}
								<PromptSuggestions bind:promptSuggestions={info.meta.suggestion_prompts} />
							{/if}
						</ModelEditorSection>

						<ModelEditorSection
							id="model-editor-integrations"
							title="Integrations"
							description="Knowledge, tools, skills, filters, and actions."
							status={knowledge.length + toolIds.length + skillIds.length + filterIds.length + actionIds.length > 0
								? String(
										knowledge.length +
											toolIds.length +
											skillIds.length +
											filterIds.length +
											actionIds.length
									)
								: null}
						>
							<Knowledge bind:selectedItems={knowledge} />
							<ToolsSelector bind:selectedToolIds={toolIds} tools={toolsList} />
							<SkillsSelector bind:selectedSkillIds={skillIds} skills={skillsList} />

							{#if filterFunctions.length > 0}
								<FiltersSelector bind:selectedFilterIds={filterIds} filters={filterFunctions} />

								{#if toggleableFilters.length > 0}
									<DefaultFiltersSelector
										bind:selectedFilterIds={defaultFilterIds}
										filters={toggleableFilters}
									/>
								{/if}
							{/if}

							{#if actionFunctions.length > 0}
								<ActionsSelector bind:selectedActionIds={actionIds} actions={actionFunctions} />
							{/if}
						</ModelEditorSection>

						<ModelEditorSection
							id="model-editor-capabilities"
							title="Capabilities"
							description="Features this model can use in chat."
							status={enabledCapabilities > 0 ? String(enabledCapabilities) : $i18n.t('Default')}
						>
							<Capabilities bind:capabilities />

							{#if enabledCapabilityFeatures.length > 0}
								<div class="pt-2 border-t border-gray-100/30 dark:border-gray-850/30">
									<DefaultFeatures
										availableFeatures={enabledCapabilityFeatures}
										bind:featureIds={defaultFeatureIds}
									/>
								</div>
							{/if}

							{#if capabilities.builtin_tools}
								<div class="pt-2 border-t border-gray-100/30 dark:border-gray-850/30">
									<BuiltinTools bind:builtinTools />
								</div>
							{/if}

							{#if capabilities.terminal}
								<div class="pt-2 border-t border-gray-100/30 dark:border-gray-850/30">
									<TerminalSelector bind:terminalId />
								</div>
							{/if}
						</ModelEditorSection>

						<ModelEditorSection
							id="model-editor-voice"
							title="Voice"
							description="Text-to-speech voice for this model."
							status={tts.voice || $i18n.t('Default')}
							collapsible={true}
							open={tts.voice !== ''}
						>
							<TTSVoiceInput
								bind:value={tts.voice}
								{voices}
								placeholder={$i18n.t('e.g. alloy, echo, shimmer')}
							/>
						</ModelEditorSection>
					</div>
				</div>

				<div
					class="sticky bottom-0 z-20 py-3 mt-2 border-t border-gray-100/30 dark:border-gray-850/30 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm"
				>
					<div class="flex items-center justify-between gap-3">
						<div class="flex items-center gap-2 min-w-0">
							{#if dirty}
								<span class="text-xs text-amber-600 dark:text-amber-400 truncate">
									{$i18n.t('Unsaved changes')}
								</span>
							{/if}
						</div>

						<div class="flex items-center gap-2 shrink-0">
							<button
								type="button"
								class="px-3 py-1.5 text-xs font-medium rounded-lg text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850/50 transition"
								on:click={() => {
									showPreview = true;
								}}
							>
								{$i18n.t('View JSON')}
							</button>

							<button
								class="text-sm px-4 py-2 transition rounded-lg {loading
									? 'cursor-not-allowed bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'
									: 'bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'}"
								type="submit"
								disabled={loading}
							>
								<span class="font-medium flex items-center gap-1.5">
									{#if edit}
										{$i18n.t('Save & Update')}
									{:else}
										{$i18n.t('Save & Create')}
									{/if}
									{#if loading}
										<Spinner />
									{/if}
								</span>
							</button>
						</div>
					</div>
				</div>
			</form>
		{/if}
	</div>

	<Modal size="lg" bind:show={showPreview}>
		<div class="px-5 pt-4 pb-2">
			<div class="text-lg font-medium">{$i18n.t('JSON Preview')}</div>
		</div>
		<div class="px-5 pb-5">
			<textarea
				class="text-xs w-full bg-transparent outline-hidden resize-none font-mono rounded-xl border border-gray-100/30 dark:border-gray-850/30 p-3"
				rows="18"
				value={JSON.stringify(previewInfo, null, 2)}
				readonly
			></textarea>
		</div>
	</Modal>
{/if}
