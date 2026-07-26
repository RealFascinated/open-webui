<script lang="ts">
	import {toast} from 'svelte-sonner';

	import {onMount, getContext, createEventDispatcher} from 'svelte';
	import {page} from '$app/stores';

	const dispatch = createEventDispatcher();

	import {resetVectorDB, getEmbeddingConfig, updateEmbeddingConfig, getRAGConfig, updateRAGConfig} from '$lib/apis/retrieval';

	import {reindexKnowledgeFiles} from '$lib/apis/knowledge';
	import {deleteAllFiles} from '$lib/apis/files';

	import ResetUploadDirConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ResetVectorDBConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ReindexKnowledgeFilesConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import DocumentsSubNav from './DocumentsSubNav.svelte';
	import DocumentsIntegrationSection from './Documents/DocumentsIntegrationSection.svelte';
	import DocumentsDangerSection from './Documents/DocumentsDangerSection.svelte';
	import DocumentsGeneralSection from './Documents/DocumentsGeneralSection.svelte';
	import DocumentsEmbeddingSection from './Documents/DocumentsEmbeddingSection.svelte';
	import VectorDBStatusCard from '../VectorDBStatusCard.svelte';
	import DocumentsRetrievalSection from './Documents/DocumentsRetrievalSection.svelte';
	import DocumentsFilesSection from './Documents/DocumentsFilesSection.svelte';
	import AdminSaveBar from '../AdminSaveBar.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import {isDocumentSection} from './documentsSections';

	const i18n = getContext('i18n');

	let formElement: HTMLFormElement;
	let dirty = false;
	let saving = false;

	$: activeSection = isDocumentSection($page.url.searchParams.get('section'))
		? $page.url.searchParams.get('section')
		: 'general';

	const markDirty = () => {
		dirty = true;
	};

	let updateEmbeddingModelLoading = false;

	let showResetConfirm = false;
	let showResetUploadDirConfirm = false;
	let showReindexConfirm = false;
	let showExternalDocumentLoaderHeadersHint = false;

	let RAG_EMBEDDING_ENGINE = '';
	let RAG_EMBEDDING_MODEL = '';
	let RAG_EMBEDDING_BATCH_SIZE = 1;
	let ENABLE_ASYNC_EMBEDDING = true;
	let RAG_EMBEDDING_CONCURRENT_REQUESTS = 0;

	let OpenAIUrl = '';
	let OpenAIKey = '';

	let AzureOpenAIUrl = '';
	let AzureOpenAIKey = '';
	let AzureOpenAIVersion = '';

	let OllamaUrl = '';
	let OllamaKey = '';

	let _querySettings = {
		template: '',
		r: 0.0,
		k: 4,
		k_reranker: 4,
		hybrid: false
	};

	let RAGConfig: Record<string, unknown> = null;

	const embeddingModelUpdateHandler = async () => {
		if (RAG_EMBEDDING_ENGINE === '' && RAG_EMBEDDING_MODEL.split('/').length - 1 > 1) {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}
		if (RAG_EMBEDDING_ENGINE === 'ollama' && RAG_EMBEDDING_MODEL === '') {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}

		if (RAG_EMBEDDING_ENGINE === 'openai' && RAG_EMBEDDING_MODEL === '') {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}

		if (
			RAG_EMBEDDING_ENGINE === 'azure_openai' &&
			(AzureOpenAIKey === '' || AzureOpenAIUrl === '' || AzureOpenAIVersion === '')
		) {
			toast.error($i18n.t('OpenAI URL/Key required.'));
			return;
		}

		console.debug('Update embedding model attempt:', {
			RAG_EMBEDDING_ENGINE,
			RAG_EMBEDDING_MODEL,
			RAG_EMBEDDING_BATCH_SIZE,
			ENABLE_ASYNC_EMBEDDING,
			RAG_EMBEDDING_CONCURRENT_REQUESTS
		});

		updateEmbeddingModelLoading = true;
		const res = await updateEmbeddingConfig(localStorage.token, {
			RAG_EMBEDDING_ENGINE: RAG_EMBEDDING_ENGINE,
			RAG_EMBEDDING_MODEL: RAG_EMBEDDING_MODEL,
			RAG_EMBEDDING_BATCH_SIZE: RAG_EMBEDDING_BATCH_SIZE,
			ENABLE_ASYNC_EMBEDDING: ENABLE_ASYNC_EMBEDDING,
			RAG_EMBEDDING_CONCURRENT_REQUESTS: RAG_EMBEDDING_CONCURRENT_REQUESTS,
			ollama_config: {
				key: OllamaKey,
				url: OllamaUrl
			},
			openai_config: {
				key: OpenAIKey,
				url: OpenAIUrl
			},
			azure_openai_config: {
				key: AzureOpenAIKey,
				url: AzureOpenAIUrl,
				version: AzureOpenAIVersion
			}
		}).catch(async (error) => {
			toast.error(`${error}`);
			await setEmbeddingConfig();
			return null;
		});
		updateEmbeddingModelLoading = false;

		if (res) {
			console.debug('embeddingModelUpdateHandler:', res);
		}
	};

	const submitHandler = async () => {
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'external' &&
			RAGConfig.EXTERNAL_DOCUMENT_LOADER_URL === ''
		) {
			toast.error($i18n.t('External Document Loader URL required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'external' &&
			RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS
		) {
			try {
				const headers = JSON.parse(RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS);
				if (headers === null || typeof headers !== 'object' || Array.isArray(headers)) {
					throw new Error('Headers must be a valid JSON object');
				}
				RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS = JSON.stringify(headers, null, 2);
			} catch (_error) {
				toast.error($i18n.t('Headers must be a valid JSON object'));
				return;
			}
		}
		if (RAGConfig.CONTENT_EXTRACTION_ENGINE === 'tika' && RAGConfig.TIKA_SERVER_URL === '') {
			toast.error($i18n.t('Tika Server URL required.'));
			return;
		}
		if (RAGConfig.CONTENT_EXTRACTION_ENGINE === 'docling' && RAGConfig.DOCLING_SERVER_URL === '') {
			toast.error($i18n.t('Docling Server URL required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'datalab_marker' &&
			RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG &&
			RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG.trim() !== ''
		) {
			try {
				JSON.parse(RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG);
			} catch (_e) {
				toast.error($i18n.t('Invalid JSON format in Additional Config'));
				return;
			}
		}

		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'document_intelligence' &&
			RAGConfig.DOCUMENT_INTELLIGENCE_ENDPOINT === ''
		) {
			toast.error($i18n.t('Document Intelligence endpoint required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mistral_ocr' &&
			RAGConfig.MISTRAL_OCR_API_KEY === ''
		) {
			toast.error($i18n.t('Mistral OCR API Key required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'paddleocr_vl' &&
			RAGConfig.PADDLEOCR_VL_BASE_URL === ''
		) {
			toast.error($i18n.t('PaddleOCR-vl API URL required.'));
			return;
		}

		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mineru' &&
			RAGConfig.MINERU_API_MODE === 'cloud' &&
			RAGConfig.MINERU_API_KEY === ''
		) {
			toast.error($i18n.t('MinerU API Key required for Cloud API mode.'));
			return;
		}

		if (!RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL) {
			await embeddingModelUpdateHandler();
		}

		if (RAGConfig.DOCLING_PARAMS) {
			try {
				JSON.parse(RAGConfig.DOCLING_PARAMS);
			} catch (_e) {
				toast.error(
					$i18n.t('Invalid JSON format in {{NAME}}', {
						NAME: $i18n.t('Docling Parameters')
					})
				);
				return;
			}
		}
		if (RAGConfig.MINERU_PARAMS) {
			try {
				JSON.parse(RAGConfig.MINERU_PARAMS);
			} catch (_e) {
				toast.error($i18n.t('Invalid JSON format in MinerU Parameters'));
				return;
			}
		}

		saving = true;
		const res = await updateRAGConfig(localStorage.token, {
			...RAGConfig,
			// Convert null (from cleared number inputs) to empty string so the backend
			// can distinguish "clear this field" from "don't change this field"
			FILE_MAX_SIZE: RAGConfig.FILE_MAX_SIZE ?? '',
			FILE_MAX_COUNT: RAGConfig.FILE_MAX_COUNT ?? '',
			FILE_IMAGE_COMPRESSION_WIDTH: RAGConfig.FILE_IMAGE_COMPRESSION_WIDTH ?? '',
			FILE_IMAGE_COMPRESSION_HEIGHT: RAGConfig.FILE_IMAGE_COMPRESSION_HEIGHT ?? '',
			ALLOWED_FILE_EXTENSIONS: RAGConfig.ALLOWED_FILE_EXTENSIONS.split(',')
				.map((ext) => ext.trim())
				.filter((ext) => ext !== ''),
			DOCLING_PARAMS:
				typeof RAGConfig.DOCLING_PARAMS === 'string' && RAGConfig.DOCLING_PARAMS.trim() !== ''
					? JSON.parse(RAGConfig.DOCLING_PARAMS)
					: {},
			EXTERNAL_DOCUMENT_LOADER_HEADERS:
				typeof RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS === 'string' &&
				RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS.trim() !== ''
					? JSON.parse(RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS)
					: {},
			MINERU_PARAMS:
				typeof RAGConfig.MINERU_PARAMS === 'string' && RAGConfig.MINERU_PARAMS.trim() !== ''
					? JSON.parse(RAGConfig.MINERU_PARAMS)
					: {},
			MINERU_FILE_EXTENSIONS: RAGConfig.MINERU_FILE_EXTENSIONS.split(',')
				.map((ext) => ext.trim())
				.filter((ext) => ext !== '')
		});
		if (res) {
			dirty = false;
		}
		saving = false;
		dispatch('save');
	};

	const setEmbeddingConfig = async () => {
		const embeddingConfig = await getEmbeddingConfig(localStorage.token);

		if (embeddingConfig) {
			RAG_EMBEDDING_ENGINE = embeddingConfig.RAG_EMBEDDING_ENGINE;
			RAG_EMBEDDING_MODEL = embeddingConfig.RAG_EMBEDDING_MODEL;
			RAG_EMBEDDING_BATCH_SIZE = embeddingConfig.RAG_EMBEDDING_BATCH_SIZE ?? 1;
			ENABLE_ASYNC_EMBEDDING = embeddingConfig.ENABLE_ASYNC_EMBEDDING ?? true;
			RAG_EMBEDDING_CONCURRENT_REQUESTS = embeddingConfig.RAG_EMBEDDING_CONCURRENT_REQUESTS ?? 0;

			OpenAIKey = embeddingConfig.openai_config.key;
			OpenAIUrl = embeddingConfig.openai_config.url;

			OllamaKey = embeddingConfig.ollama_config.key;
			OllamaUrl = embeddingConfig.ollama_config.url;

			AzureOpenAIKey = embeddingConfig.azure_openai_config.key;
			AzureOpenAIUrl = embeddingConfig.azure_openai_config.url;
			AzureOpenAIVersion = embeddingConfig.azure_openai_config.version;
		}
	};
	onMount(async () => {
		await setEmbeddingConfig();

		const config = await getRAGConfig(localStorage.token);
		config.ALLOWED_FILE_EXTENSIONS = (config?.ALLOWED_FILE_EXTENSIONS ?? []).join(', ');

		config.DOCLING_PARAMS =
			typeof config.DOCLING_PARAMS === 'object'
				? JSON.stringify(config.DOCLING_PARAMS ?? {}, null, 2)
				: config.DOCLING_PARAMS;

		config.MINERU_PARAMS =
			typeof config.MINERU_PARAMS === 'object'
				? JSON.stringify(config.MINERU_PARAMS ?? {}, null, 2)
				: config.MINERU_PARAMS;

		config.EXTERNAL_DOCUMENT_LOADER_HEADERS =
			typeof config.EXTERNAL_DOCUMENT_LOADER_HEADERS === 'object'
				? Object.keys(config.EXTERNAL_DOCUMENT_LOADER_HEADERS ?? {}).length > 0
					? JSON.stringify(config.EXTERNAL_DOCUMENT_LOADER_HEADERS, null, 2)
					: ''
				: config.EXTERNAL_DOCUMENT_LOADER_HEADERS;

		config.MINERU_FILE_EXTENSIONS = (config?.MINERU_FILE_EXTENSIONS ?? ['pdf']).join(', ');
		config.RAG_TOKENIZER_MODEL = config?.RAG_TOKENIZER_MODEL ?? '';

		RAGConfig = config;
	});
</script>

<ResetUploadDirConfirmDialog
	title={$i18n.t('Reset Upload Directory')}
	message={$i18n.t(
		'Are you sure you want to reset the upload directory? All uploaded files will be deleted. This action cannot be undone.'
	)}
	bind:show={showResetUploadDirConfirm}
	on:confirm={async () => {
		const res = await deleteAllFiles(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Success'));
		}
	}}
/>

<ResetVectorDBConfirmDialog
	title={$i18n.t('Reset Vector Storage/Knowledge')}
	message={$i18n.t(
		'Are you sure you want to reset vector storage? All embedded knowledge will be removed. This action cannot be undone.'
	)}
	bind:show={showResetConfirm}
	on:confirm={() => {
		const res = resetVectorDB(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Success'));
		}
	}}
/>

<ReindexKnowledgeFilesConfirmDialog
	title={$i18n.t('Reindex Knowledge Base Vectors')}
	message={$i18n.t(
		'Are you sure you want to reindex all knowledge base vectors? This may take a while.'
	)}
	bind:show={showReindexConfirm}
	on:confirm={async () => {
		const res = await reindexKnowledgeFiles(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Success'));
		}
	}}
/>

<form
	bind:this={formElement}
	class="flex flex-col space-y-3 text-sm"
	on:input={markDirty}
	on:change={markDirty}
	on:submit|preventDefault={() => {
		submitHandler();
	}}
>
	{#if RAGConfig}
		<DocumentsSubNav {activeSection} />

		<div class=" space-y-2.5 pr-1.5">
			<div class:hidden={activeSection !== 'general'}>
				<DocumentsGeneralSection
					bind:RAGConfig
					bind:RAG_EMBEDDING_ENGINE
					bind:showExternalDocumentLoaderHeadersHint
				/>
			</div>

			<div class:hidden={activeSection !== 'embedding'}>
				<VectorDBStatusCard bypassMode={!!RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL} />

				{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
					<DocumentsEmbeddingSection
						bind:RAG_EMBEDDING_ENGINE
						bind:RAG_EMBEDDING_MODEL
						bind:OpenAIUrl
						bind:OpenAIKey
						bind:AzureOpenAIUrl
						bind:AzureOpenAIKey
						bind:AzureOpenAIVersion
						bind:OllamaUrl
						bind:OllamaKey
						bind:RAG_EMBEDDING_BATCH_SIZE
						bind:ENABLE_ASYNC_EMBEDDING
						bind:RAG_EMBEDDING_CONCURRENT_REQUESTS
						bind:updateEmbeddingModelLoading
						on:updateEmbeddingModel={embeddingModelUpdateHandler}
					/>
				{/if}
			</div>

			<div class:hidden={activeSection !== 'retrieval'}>
				<DocumentsRetrievalSection bind:RAGConfig />
			</div>

			<div class:hidden={activeSection !== 'files'}>
				<DocumentsFilesSection bind:RAGConfig />
			</div>

			<div class:hidden={activeSection !== 'integration'}>
				<DocumentsIntegrationSection bind:RAGConfig />
			</div>

			<div class:hidden={activeSection !== 'danger'}>
				<DocumentsDangerSection
					on:resetUpload={() => {
						showResetUploadDirConfirm = true;
					}}
					on:resetVector={() => {
						showResetConfirm = true;
					}}
					on:reindex={() => {
						showReindexConfirm = true;
					}}
				/>
			</div>
		</div>
		<AdminSaveBar
			{dirty}
			{saving}
			onSave={() => {
				formElement?.requestSubmit();
			}}
			onDiscard={() => {
				window.location.reload();
			}}
		/>
	{:else}
		<div class="flex items-center justify-center h-full py-16">
			<Spinner className="size-5" />
		</div>
	{/if}
</form>