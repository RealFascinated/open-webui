<script lang="ts">
	import { getContext } from 'svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AdminSettingsCard from '../../AdminSettingsCard.svelte';

	const i18n = getContext('i18n');

	export let RAGConfig: Record<string, unknown>;
</script>

<AdminSettingsCard
	title="Retrieval"
	description="Query settings, reranking, and RAG templates."
	className="mb-3"
>
					{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Full Context Mode')}</div>
							<div class="flex items-center relative">
								<Tooltip
									content={RAGConfig.RAG_FULL_CONTEXT
										? $i18n.t(
												'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
											)
										: $i18n.t(
												'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
											)}
								>
									<Switch bind:state={RAGConfig.RAG_FULL_CONTEXT} />
								</Tooltip>
							</div>
						</div>

						{#if !RAGConfig.RAG_FULL_CONTEXT}
							<div class="  mb-2.5 flex w-full justify-between">
								<div class=" self-center text-xs font-medium">{$i18n.t('Hybrid Search')}</div>
								<div class="flex items-center relative">
									<Switch bind:state={RAGConfig.ENABLE_RAG_HYBRID_SEARCH} />
								</div>
							</div>

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class="mb-2.5 flex w-full justify-between">
									<div class="self-center text-xs font-medium">
										{$i18n.t('Enrich Hybrid Search Text')}
									</div>
									<div class="flex items-center relative">
										<Tooltip
											content={$i18n.t(
												'Adds filenames, titles, sections, and snippets into the BM25 text to improve lexical recall.'
											)}
										>
											<Switch bind:state={RAGConfig.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS} />
										</Tooltip>
									</div>
								</div>

								<div class="  mb-2.5 flex flex-col w-full justify-between">
									<div class="flex w-full justify-between">
										<div class=" self-center text-xs font-medium">
											{$i18n.t('Reranking Engine')}
										</div>
										<div class="flex items-center relative">
											<select
												class="w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
												bind:value={RAGConfig.RAG_RERANKING_ENGINE}
												placeholder={$i18n.t('Select a reranking model engine')}
												on:change={(e) => {
													if (e.target.value === 'external') {
														RAGConfig.RAG_RERANKING_MODEL = '';
													} else if (e.target.value === '') {
														RAGConfig.RAG_RERANKING_MODEL = 'BAAI/bge-reranker-v2-m3';
													}
												}}
											>
												<option value="">{$i18n.t('Default (SentenceTransformers)')}</option>
												<option value="external">{$i18n.t('External')}</option>
											</select>
										</div>
									</div>

									{#if RAGConfig.RAG_RERANKING_ENGINE === 'external'}
										<div class="my-0.5 flex gap-2 pr-2">
											<input
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
												placeholder={$i18n.t('API Base URL')}
												bind:value={RAGConfig.RAG_EXTERNAL_RERANKER_URL}
												required
											/>

											<SensitiveInput
												placeholder={$i18n.t('API Key')}
												bind:value={RAGConfig.RAG_EXTERNAL_RERANKER_API_KEY}
												required={false}
											/>
										</div>
									{/if}
								</div>

								<div class="  mb-2.5 flex flex-col w-full">
									<div class=" mb-1 text-xs font-medium">{$i18n.t('Reranking Model')}</div>

									<div class="">
										<div class="flex w-full">
											<div class="flex-1 mr-2">
												<input
													class="flex-1 w-full text-sm bg-transparent outline-hidden"
													placeholder={$i18n.t('Set reranking model (e.g. {{model}})', {
														model: 'BAAI/bge-reranker-v2-m3'
													})}
													bind:value={RAGConfig.RAG_RERANKING_MODEL}
												/>
											</div>
										</div>
									</div>
								</div>
							{/if}

							<div class="  mb-2.5 flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Reranking Batch Size')}
								</div>

								<div class="">
									<input
										bind:value={RAGConfig.RAG_RERANKING_BATCH_SIZE}
										type="number"
										class=" bg-transparent text-center w-14 outline-none"
										min="1"
										max="16000"
										step="1"
									/>
								</div>
							</div>

							<div class="  mb-2.5 flex w-full justify-between">
								<div class=" self-center text-xs font-medium">{$i18n.t('Top K')}</div>
								<div class="flex items-center relative">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										type="number"
										placeholder={$i18n.t('Enter Top K')}
										bind:value={RAGConfig.TOP_K}
										autocomplete="off"
										min="0"
									/>
								</div>
							</div>

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class="mb-2.5 flex w-full justify-between">
									<div class="self-center text-xs font-medium">{$i18n.t('Top K Reranker')}</div>
									<div class="flex items-center relative">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											type="number"
											placeholder={$i18n.t('Enter Top K Reranker')}
											bind:value={RAGConfig.TOP_K_RERANKER}
											autocomplete="off"
											min="0"
										/>
									</div>
								</div>
							{/if}

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class="  mb-2.5 flex flex-col w-full justify-between">
									<div class=" flex w-full justify-between">
										<div class=" self-center text-xs font-medium">
											{$i18n.t('Relevance Threshold')}
										</div>
										<div class="flex items-center relative">
											<input
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
												type="number"
												step="0.01"
												placeholder={$i18n.t('Enter Score')}
												bind:value={RAGConfig.RELEVANCE_THRESHOLD}
												autocomplete="off"
												min="0.0"
												title={$i18n.t(
													'The score should be a value between 0.0 (0%) and 1.0 (100%).'
												)}
											/>
										</div>
									</div>
									<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
										{$i18n.t(
											'Note: If you set a minimum score, the search will only return documents with a score greater than or equal to the minimum score.'
										)}
									</div>
								</div>
							{/if}

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class=" mb-2.5 py-0.5 w-full justify-between">
									<Tooltip
										content={$i18n.t(
											'The Weight of BM25 Hybrid Search. 0 more semantic, 1 more lexical. Default 0.5'
										)}
										placement="top-start"
										className="inline-tooltip"
									>
										<div class="flex w-full justify-between">
											<div class=" self-center text-xs font-medium">
												{$i18n.t('BM25 Weight')}
											</div>
											<button
												class="p-1 px-3 text-xs flex rounded-sm transition shrink-0 outline-hidden"
												type="button"
												on:click={() => {
													RAGConfig.HYBRID_BM25_WEIGHT =
														(RAGConfig?.HYBRID_BM25_WEIGHT ?? null) === null ? 0.5 : null;
												}}
											>
												{#if (RAGConfig?.HYBRID_BM25_WEIGHT ?? null) === null}
													<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
												{:else}
													<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
												{/if}
											</button>
										</div>
									</Tooltip>

									{#if (RAGConfig?.HYBRID_BM25_WEIGHT ?? null) !== null}
										<div class="flex mt-0.5 space-x-2">
											<div class=" flex-1">
												<input
													id="steps-range"
													type="range"
													min="0"
													max="1"
													step="0.05"
													bind:value={RAGConfig.HYBRID_BM25_WEIGHT}
													class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
												/>

												<div class="py-0.5">
													<div class="flex w-full justify-between">
														<div class=" text-left text-xs font-small">
															{$i18n.t('semantic')}
														</div>
														<div class=" text-right text-xs font-small">
															{$i18n.t('lexical')}
														</div>
													</div>
												</div>
											</div>
											<div>
												<input
													bind:value={RAGConfig.HYBRID_BM25_WEIGHT}
													type="number"
													class=" bg-transparent text-center w-14"
													min="0"
													max="1"
													step="any"
												/>
											</div>
										</div>
									{/if}
								</div>
							{/if}
						{/if}
					{/if}

					<div class="  mb-2.5 flex flex-col w-full justify-between">
						<div class=" mb-1 text-xs font-medium">{$i18n.t('RAG Template')}</div>
						<div class="flex w-full items-center relative">
							<Tooltip
								content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
								placement="top-start"
								className="w-full"
							>
								<Textarea
									bind:value={RAGConfig.RAG_TEMPLATE}
									placeholder={$i18n.t(
										'Leave empty to use the default prompt, or enter a custom prompt'
									)}
								/>
							</Tooltip>
						</div>

						{#if RAGConfig.RAG_TEMPLATE && (RAGConfig.RAG_TEMPLATE.match(/\[context\]/g) || []).length + (RAGConfig.RAG_TEMPLATE.match(/\{\{CONTEXT\}\}/g) || []).length > 1}
							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t(
									'This template contains multiple context placeholders ([context] or {{CONTEXT}}). Context will be injected at each occurrence.'
								)}
							</div>
						{/if}
					</div>
</AdminSettingsCard>
