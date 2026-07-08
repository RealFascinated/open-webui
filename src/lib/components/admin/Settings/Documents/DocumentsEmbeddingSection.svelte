<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AdminSettingsCard from '../../AdminSettingsCard.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{ updateEmbeddingModel: void }>();

	export let RAGConfig: Record<string, unknown>;
	export let RAG_EMBEDDING_ENGINE = '';
	export let RAG_EMBEDDING_MODEL = '';
	export let OpenAIUrl = '';
	export let OpenAIKey = '';
	export let AzureOpenAIUrl = '';
	export let AzureOpenAIKey = '';
	export let AzureOpenAIVersion = '';
	export let OllamaUrl = '';
	export let OllamaKey = '';
	export let RAG_EMBEDDING_BATCH_SIZE = 1;
	export let ENABLE_ASYNC_EMBEDDING = true;
	export let RAG_EMBEDDING_CONCURRENT_REQUESTS = 0;
	export let updateEmbeddingModelLoading = false;

	const embeddingModelUpdateHandler = () => dispatch('updateEmbeddingModel');
</script>

<AdminSettingsCard
	title="Embedding"
	description="Embedding model engine, batching, and vector storage."
	className="mb-3"
>
						<div class="  mb-2.5 flex flex-col w-full justify-between">
							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Embedding Model Engine')}
								</div>
								<div class="flex items-center relative">
									<select
										class="w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
										bind:value={RAG_EMBEDDING_ENGINE}
										placeholder={$i18n.t('Select an embedding model engine')}
										on:change={(e) => {
											if (e.target.value === 'ollama') {
												RAG_EMBEDDING_MODEL = '';
											} else if (e.target.value === 'openai') {
												RAG_EMBEDDING_MODEL = 'text-embedding-3-small';
											} else if (e.target.value === 'azure_openai') {
												RAG_EMBEDDING_MODEL = 'text-embedding-3-small';
											} else if (e.target.value === '') {
												RAG_EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2';
											}
										}}
									>
										<option value="">{$i18n.t('Default (SentenceTransformers)')}</option>
										<option value="ollama">{$i18n.t('Ollama')}</option>
										<option value="openai">{$i18n.t('OpenAI')}</option>
										<option value="azure_openai">{$i18n.t('Azure OpenAI')}</option>
									</select>
								</div>
							</div>

							{#if RAG_EMBEDDING_ENGINE === 'openai'}
								<div class="my-0.5 flex gap-2 pr-2">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										placeholder={$i18n.t('API Base URL')}
										bind:value={OpenAIUrl}
										required
									/>

									<SensitiveInput
										placeholder={$i18n.t('API Key')}
										bind:value={OpenAIKey}
										required={false}
									/>
								</div>
							{:else if RAG_EMBEDDING_ENGINE === 'ollama'}
								<div class="my-0.5 flex gap-2 pr-2">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										placeholder={$i18n.t('API Base URL')}
										bind:value={OllamaUrl}
										required
									/>

									<SensitiveInput
										placeholder={$i18n.t('API Key')}
										bind:value={OllamaKey}
										required={false}
									/>
								</div>
							{:else if RAG_EMBEDDING_ENGINE === 'azure_openai'}
								<div class="my-0.5 flex flex-col gap-2 pr-2 w-full">
									<div class="flex gap-2">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											placeholder={$i18n.t('API Base URL')}
											bind:value={AzureOpenAIUrl}
											required
										/>
										<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={AzureOpenAIKey} />
									</div>
									<div class="flex gap-2">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											placeholder={$i18n.t('Version')}
											bind:value={AzureOpenAIVersion}
											required
										/>
									</div>
								</div>
							{/if}
						</div>

						<div class="  mb-2.5 flex flex-col w-full">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('Embedding Model')}</div>

							<div class="">
								{#if RAG_EMBEDDING_ENGINE === 'ollama'}
									<div class="flex w-full">
										<div class="flex-1 mr-2">
											<input
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
												bind:value={RAG_EMBEDDING_MODEL}
												placeholder={$i18n.t('Set embedding model')}
												required
											/>
										</div>
									</div>
								{:else}
									<div class="flex w-full">
										<div class="flex-1 mr-2">
											<input
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
												placeholder={$i18n.t('Set embedding model (e.g. {{model}})', {
													model: RAG_EMBEDDING_MODEL.slice(-40)
												})}
												bind:value={RAG_EMBEDDING_MODEL}
											/>
										</div>

										{#if RAG_EMBEDDING_ENGINE === ''}
											<button
												class="px-2.5 bg-transparent text-gray-800 dark:bg-transparent dark:text-gray-100 rounded-lg transition"
												on:click={embeddingModelUpdateHandler}
												disabled={updateEmbeddingModelLoading}
											>
												{#if updateEmbeddingModelLoading}
													<div class="self-center">
														<Spinner />
													</div>
												{:else}
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 16 16"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
														/>
														<path
															d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
														/>
													</svg>
												{/if}
											</button>
										{/if}
									</div>
								{/if}
							</div>

							<div class="mt-1 mb-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t(
									'After updating or changing the embedding model, you must reindex the knowledge base for the changes to take effect. You can do this using the "Reindex" button below.'
								)}
							</div>
						</div>

						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" self-center text-xs font-medium">
								{$i18n.t('Embedding Batch Size')}
							</div>

							<div class="">
								<input
									bind:value={RAG_EMBEDDING_BATCH_SIZE}
									type="number"
									class=" bg-transparent text-center w-14 outline-none"
									min="-2"
									max="16000"
									step="1"
								/>
							</div>
						</div>

						{#if RAG_EMBEDDING_ENGINE === 'ollama' || RAG_EMBEDDING_ENGINE === 'openai' || RAG_EMBEDDING_ENGINE === 'azure_openai'}
							<div class="  mb-2.5 flex w-full justify-between">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Runs embedding tasks concurrently to speed up processing. Turn off if rate limits become an issue.'
										)}
										placement="top-start"
									>
										{$i18n.t('Async Embedding Processing')}
									</Tooltip>
								</div>
								<div class="flex items-center relative">
									<Switch bind:state={ENABLE_ASYNC_EMBEDDING} />
								</div>
							</div>

							<div class="  mb-2.5 flex w-full justify-between">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Limits the number of concurrent embedding requests. Set to 0 for unlimited.'
										)}
										placement="top-start"
									>
										{$i18n.t('Embedding Concurrent Requests')}
									</Tooltip>
								</div>
								<div class="">
									<input
										bind:value={RAG_EMBEDDING_CONCURRENT_REQUESTS}
										type="number"
										class=" bg-transparent text-center w-14 outline-none"
										min="0"
										step="1"
									/>
								</div>
							</div>
						{/if}
</AdminSettingsCard>
