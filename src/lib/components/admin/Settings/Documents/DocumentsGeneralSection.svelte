<script lang="ts">
	import { getContext } from 'svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AdminSettingsCard from '../../AdminSettingsCard.svelte';

	const i18n = getContext('i18n');

	export let RAGConfig: Record<string, unknown>;
	export let RAG_EMBEDDING_ENGINE = '';
	export let showExternalDocumentLoaderHeadersHint = false;
</script>

<AdminSettingsCard
	title="General"
	description="Content extraction, chunking, and document processing."
	className="mb-3"
>
					<div class="mb-2.5 flex flex-col w-full justify-between">
						<div class="flex w-full justify-between mb-1">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Content Extraction Engine')}
							</div>
							<div class="">
								<select
									class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
									bind:value={RAGConfig.CONTENT_EXTRACTION_ENGINE}
								>
									<option value="">{$i18n.t('Default')}</option>
									<option value="external">{$i18n.t('External')}</option>
									<option value="tika">{$i18n.t('Tika')}</option>
									<option value="docling">{$i18n.t('Docling')}</option>
									<option value="datalab_marker">{$i18n.t('Datalab Marker API')}</option>
									<option value="document_intelligence">{$i18n.t('Document Intelligence')}</option>
									<option value="mistral_ocr">{$i18n.t('Mistral OCR')}</option>
									<option value="paddleocr_vl">{$i18n.t('PaddleOCR-vl')}</option>
									<option value="mineru">{$i18n.t('MinerU')}</option>
								</select>
							</div>
						</div>

						{#if RAGConfig.CONTENT_EXTRACTION_ENGINE === ''}
							<div class="flex w-full mt-1">
								<div class="flex-1 flex justify-between">
									<div class=" self-center text-xs font-medium">
										{$i18n.t('PDF Extract Images (OCR)')}
									</div>
									<div class="flex items-center relative">
										<Switch bind:state={RAGConfig.PDF_EXTRACT_IMAGES} />
									</div>
								</div>
							</div>

							<div class="flex w-full mt-2">
								<div class="flex-1 flex justify-between">
									<div class=" self-center text-xs font-medium">
										<Tooltip
											content={$i18n.t(
												'Page mode creates one document per page. Single mode combines all pages into one document for better chunking across page boundaries.'
											)}
											placement="top-start"
										>
											{$i18n.t('PDF Loader Mode')}
										</Tooltip>
									</div>
									<div class="">
										<select
											class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
											bind:value={RAGConfig.PDF_LOADER_MODE}
										>
											<option value="page">{$i18n.t('Page')}</option>
											<option value="single">{$i18n.t('Single')}</option>
										</select>
									</div>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'datalab_marker'}
							<div class="my-0.5 flex gap-2 pr-2">
								<Tooltip
									content={$i18n.t(
										'API Base URL for Datalab Marker service. Defaults to: https://www.datalab.to/api/v1/marker'
									)}
									placement="top-start"
									className="w-full"
								>
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										placeholder={$i18n.t('Enter Datalab Marker API Base URL')}
										bind:value={RAGConfig.DATALAB_MARKER_API_BASE_URL}
									/>
								</Tooltip>
							</div>
							<div class="my-0.5 flex gap-2 pr-2">
								<SensitiveInput
									placeholder={$i18n.t('Enter Datalab Marker API Key')}
									required={false}
									bind:value={RAGConfig.DATALAB_MARKER_API_KEY}
								/>
							</div>

							<div class="flex flex-col gap-2 mt-2">
								<div class=" flex flex-col w-full justify-between">
									<div class=" mb-1 text-xs font-medium">
										{$i18n.t('Additional Config')}
									</div>
									<div class="flex w-full items-center relative">
										<Tooltip
											content={$i18n.t(
												'Additional configuration options for marker. This should be a JSON string with key-value pairs. For example, \'{"key": "value"}\'. Supported keys include: disable_links, keep_pageheader_in_output, keep_pagefooter_in_output, filter_blank_pages, drop_repeated_text, layout_coverage_threshold, merge_threshold, height_tolerance, gap_threshold, image_threshold, min_line_length, level_count, default_level'
											)}
											placement="top-start"
											className="w-full"
										>
											<Textarea
												bind:value={RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG}
												placeholder={$i18n.t('Enter JSON config (e.g., {"disable_links": true})')}
											/>
										</Tooltip>
									</div>
								</div>
							</div>

							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Significantly improves accuracy by using an LLM to enhance tables, forms, inline math, and layout detection. Will increase latency. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Use LLM')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_USE_LLM} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t('Skip the cache and re-run the inference. Defaults to False.')}
										placement="top-start"
									>
										{$i18n.t('Skip Cache')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_SKIP_CACHE} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Force OCR on all pages of the PDF. This can lead to worse results if you have good text in your PDFs. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Force OCR')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_FORCE_OCR} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Whether to paginate the output. Each page will be separated by a horizontal rule and page number. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Paginate')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_PAGINATE} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Strip existing OCR text from the PDF and re-run OCR. Ignored if Force OCR is enabled. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Strip Existing OCR')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_STRIP_EXISTING_OCR} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Disable image extraction from the PDF. If Use LLM is enabled, images will be automatically captioned. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Disable Image Extraction')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Format the lines in the output. Defaults to False. If set to True, the lines will be formatted to detect inline math and styles.'
										)}
										placement="top-start"
									>
										{$i18n.t('Format Lines')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_FORMAT_LINES} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											"The output format for the text. Can be 'json', 'markdown', or 'html'. Defaults to 'markdown'."
										)}
										placement="top-start"
									>
										{$i18n.t('Output Format')}
									</Tooltip>
								</div>
								<div class="">
									<select
										class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
										bind:value={RAGConfig.DATALAB_MARKER_OUTPUT_FORMAT}
									>
										<option value="markdown">{$i18n.t('Markdown')}</option>
										<option value="json">{$i18n.t('JSON')}</option>
										<option value="html">{$i18n.t('HTML')}</option>
									</select>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'external'}
							<div class="my-0.5 flex flex-col gap-2 pr-2">
								<div class="flex gap-2">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										placeholder={$i18n.t('Enter External Document Loader URL')}
										bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_URL}
									/>
									<SensitiveInput
										placeholder={$i18n.t('Enter External Document Loader API Key')}
										required={false}
										bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_API_KEY}
									/>
								</div>
								<div class="flex flex-col">
									<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Headers')}</div>
									<Tooltip
										content={$i18n.t(
											'Enter additional headers in JSON format (e.g. {"X-Custom-Header": "value"}'
										)}
									>
										<Textarea
											className="w-full text-sm outline-hidden"
											bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS}
											placeholder={$i18n.t('Enter additional headers in JSON format')}
											required={false}
										/>
									</Tooltip>
									<button
										type="button"
										class="mt-1 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition w-fit"
										on:click={() =>
											(showExternalDocumentLoaderHeadersHint =
												!showExternalDocumentLoaderHeadersHint)}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-3 h-3 transition-transform {showExternalDocumentLoaderHeadersHint
												? 'rotate-90'
												: ''}"
										>
											<path
												fill-rule="evenodd"
												d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
												clip-rule="evenodd"
											/>
										</svg>
										{$i18n.t('Header variables')}
									</button>
									{#if showExternalDocumentLoaderHeadersHint}
										<div class="mt-1 text-xs text-gray-500 dark:text-gray-400 leading-5">
											<div>
												{$i18n.t('No additional headers are sent unless configured.')}
											</div>
											<div>
												{$i18n.t('Example')}:
												<code class="text-gray-700 dark:text-gray-300"
													>{'{"X-OpenWebUI-File-Id": "{{FILE_ID}}"}'}</code
												>
											</div>
											<div>
												{$i18n.t('Available variables')}:
												<code class="text-gray-700 dark:text-gray-300">{'{{FILE_ID}}'}</code>,
												<code class="text-gray-700 dark:text-gray-300">{'{{FILE_NAME}}'}</code>,
												<code class="text-gray-700 dark:text-gray-300"
													>{'{{FILE_CONTENT_TYPE}}'}</code
												>
											</div>
										</div>
									{/if}
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'tika'}
							<div class="flex w-full mt-1">
								<div class="flex-1 mr-2">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										placeholder={$i18n.t('Enter Tika Server URL')}
										bind:value={RAGConfig.TIKA_SERVER_URL}
									/>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'docling'}
							<div class="my-0.5 flex gap-2 pr-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter Docling Server URL')}
									bind:value={RAGConfig.DOCLING_SERVER_URL}
								/>
								<SensitiveInput
									placeholder={$i18n.t('Enter Docling API Key')}
									bind:value={RAGConfig.DOCLING_API_KEY}
									required={false}
								/>
							</div>

							<div class="flex flex-col gap-2 mt-2">
								<div class=" flex flex-col w-full justify-between">
									<div class=" mb-1 text-xs font-medium">
										{$i18n.t('Parameters')}
									</div>
									<div class="flex w-full items-center relative">
										<Textarea
											bind:value={RAGConfig.DOCLING_PARAMS}
											placeholder={$i18n.t('Enter additional parameters in JSON format')}
											minSize={100}
										/>
									</div>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'document_intelligence'}
							<div class="my-0.5 flex gap-2 pr-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter Document Intelligence Endpoint')}
									bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_ENDPOINT}
								/>
								<SensitiveInput
									placeholder={$i18n.t('Enter Document Intelligence Key')}
									bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_KEY}
									required={false}
								/>
							</div>
							<div class="my-0.5 flex flex-col w-full">
								<div class=" mb-1 text-xs font-medium">
									{$i18n.t('Document Intelligence Model')}
								</div>
								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											placeholder={$i18n.t('Enter Document Intelligence Model')}
											bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_MODEL}
										/>
									</div>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mistral_ocr'}
							<div class="my-0.5 flex gap-2 pr-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter Mistral API Base URL')}
									bind:value={RAGConfig.MISTRAL_OCR_API_BASE_URL}
								/>
								<SensitiveInput
									placeholder={$i18n.t('Enter Mistral API Key')}
									bind:value={RAGConfig.MISTRAL_OCR_API_KEY}
								/>
							</div>
							<div class="flex justify-between w-full mt-2 pr-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Send the PDF as a base64 data URL instead of uploading it first.'
										)}
										placement="top-start"
									>
										{$i18n.t('Use Base64')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.MISTRAL_OCR_USE_BASE64} />
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'paddleocr_vl'}
							<div class="my-0.5 flex gap-2 pr-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter PaddleOCR-vl API Base URL')}
									bind:value={RAGConfig.PADDLEOCR_VL_BASE_URL}
								/>
								<SensitiveInput
									placeholder={$i18n.t('Enter PaddleOCR-vl API Token')}
									bind:value={RAGConfig.PADDLEOCR_VL_TOKEN}
									required={false}
								/>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mineru'}
							<!-- API Mode Selection -->
							<div class="flex w-full mt-2">
								<div class="flex-1 flex justify-between">
									<div class="self-center text-xs font-medium">
										{$i18n.t('API Mode')}
									</div>
									<select
										class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden"
										bind:value={RAGConfig.MINERU_API_MODE}
										on:change={() => {
											// Auto-update URL when switching modes if it's empty or matches the opposite mode's default
											const cloudUrl = 'https://mineru.net/api/v4';
											const localUrl = 'http://localhost:8000';

											if (RAGConfig.MINERU_API_MODE === 'cloud') {
												if (!RAGConfig.MINERU_API_URL || RAGConfig.MINERU_API_URL === localUrl) {
													RAGConfig.MINERU_API_URL = cloudUrl;
												}
											} else {
												if (!RAGConfig.MINERU_API_URL || RAGConfig.MINERU_API_URL === cloudUrl) {
													RAGConfig.MINERU_API_URL = localUrl;
												}
											}
										}}
									>
										<option value="local">{$i18n.t('local')}</option>
										<option value="cloud">{$i18n.t('cloud')}</option>
									</select>
								</div>
							</div>

							<!-- API URL -->
							<div class="flex w-full mt-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={RAGConfig.MINERU_API_MODE === 'cloud'
										? $i18n.t('https://mineru.net/api/v4')
										: $i18n.t('http://localhost:8000')}
									bind:value={RAGConfig.MINERU_API_URL}
								/>
							</div>

							<div class="flex w-full mt-2">
								<SensitiveInput
									placeholder={$i18n.t('Enter MinerU API Key')}
									bind:value={RAGConfig.MINERU_API_KEY}
								/>
							</div>

							<div class="flex w-full mt-2">
								<div class="flex-1 flex justify-between">
									<div class="self-center text-xs font-medium">
										{$i18n.t('API Timeout')}
									</div>
									<input
										class="w-16 text-sm bg-transparent outline-hidden text-right"
										type="number"
										min="1"
										bind:value={RAGConfig.MINERU_API_TIMEOUT}
										placeholder="60"
									/>
								</div>
							</div>

							<!-- Parameters -->
							<div class="flex flex-col justify-between w-full mt-2">
								<div class="text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Advanced parameters for MinerU parsing (enable_ocr, enable_formula, enable_table, language, model_version, page_ranges)'
										)}
										placement="top-start"
									>
										{$i18n.t('Parameters')}
									</Tooltip>
								</div>
								<div class="mt-1.5">
									<Textarea
										bind:value={RAGConfig.MINERU_PARAMS}
										placeholder={`{\n  "enable_ocr": false,\n  "enable_formula": true,\n  "enable_table": true,\n  "language": "en",\n  "model_version": "pipeline",\n  "page_ranges": ""\n}`}
										minSize={100}
									/>
								</div>
							</div>

							<!-- File Extensions -->
							<div class="flex flex-col justify-between w-full mt-2">
								<div class="text-xs font-medium mb-1">
									<Tooltip
										content={$i18n.t(
											'Comma-separated list of file extensions MinerU will handle (e.g. pdf, docx, pptx, xlsx)'
										)}
										placement="top-start"
									>
										{$i18n.t('File Extensions')}
									</Tooltip>
								</div>
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('pdf, docx, pptx, xlsx')}
									bind:value={RAGConfig.MINERU_FILE_EXTENSIONS}
								/>
							</div>
						{/if}
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							<Tooltip content={$i18n.t('Full Context Mode')} placement="top-start">
								{$i18n.t('Bypass Embedding and Retrieval')}
							</Tooltip>
						</div>
						<div class="flex items-center relative">
							<Tooltip
								content={RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL
									? $i18n.t(
											'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
										)
									: $i18n.t(
											'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
										)}
							>
								<Switch bind:state={RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL} />
							</Tooltip>
						</div>
					</div>

					{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Text Splitter')}</div>
							<div class="flex items-center relative">
								<select
									class="w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
									bind:value={RAGConfig.TEXT_SPLITTER}
								>
									<option value="">{$i18n.t('Default')} ({$i18n.t('Character')})</option>
									<option value="token">{$i18n.t('Token')} ({$i18n.t('Tiktoken')})</option>
									<option value="token_transformers">
										{$i18n.t('Token')} ({$i18n.t('Transformers')})
									</option>
								</select>
							</div>
						</div>

						{#if RAGConfig.TEXT_SPLITTER === 'token_transformers'}
							<div class="mb-2.5 flex flex-col w-full justify-between">
								<div class="self-center text-xs font-medium min-w-fit mb-1 w-full">
									{$i18n.t('Tokenizer Model')}
								</div>
								<div class="self-center w-full">
									<input
										class="w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter Tokenizer Model')}
										bind:value={RAGConfig.RAG_TOKENIZER_MODEL}
										autocomplete="off"
										required={RAG_EMBEDDING_ENGINE !== ''}
									/>
								</div>
							</div>
						{/if}

						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								<Tooltip
									placement="top-start"
									content={$i18n.t(
										'Split documents by markdown headers before applying character/token splitting.'
									)}
								>
									{$i18n.t('Markdown Header Text Splitter')}
								</Tooltip>
							</div>
							<div class="flex items-center relative">
								<Switch bind:state={RAGConfig.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER} />
							</div>
						</div>

						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" flex gap-1.5 w-full">
								<div class="  w-full justify-between">
									<div class="self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Chunk Size')}
									</div>
									<div class="self-center">
										<input
											class=" w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											type="number"
											placeholder={$i18n.t('Enter Chunk Size')}
											bind:value={RAGConfig.CHUNK_SIZE}
											autocomplete="off"
											min="0"
										/>
									</div>
								</div>

								<div class="w-full">
									<div class=" self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Chunk Overlap')}
									</div>

									<div class="self-center">
										<input
											class="w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											type="number"
											placeholder={$i18n.t('Enter Chunk Overlap')}
											bind:value={RAGConfig.CHUNK_OVERLAP}
											autocomplete="off"
											min="0"
										/>
									</div>
								</div>
							</div>
						</div>

						{#if RAGConfig.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER}
							<div class="  mb-2.5 flex w-full justify-between">
								<div class=" flex gap-1.5 w-full">
									<div class="w-full">
										<div class="self-center text-xs font-medium min-w-fit mb-1">
											<Tooltip
												placement="top-start"
												content={$i18n.t(
													'Chunks smaller than this threshold will be merged with neighboring chunks when possible. Set to 0 to disable merging.'
												)}
											>
												{$i18n.t('Chunk Min Size Target')}
											</Tooltip>
										</div>
										<div class="self-center">
											<input
												class="w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												type="number"
												placeholder={$i18n.t('Enter Chunk Min Size Target')}
												bind:value={RAGConfig.CHUNK_MIN_SIZE_TARGET}
												autocomplete="off"
												min="0"
											/>
										</div>
									</div>
								</div>
							</div>
						{/if}
					{/if}
</AdminSettingsCard>
