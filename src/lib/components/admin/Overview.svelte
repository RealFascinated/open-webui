<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { config, models } from '$lib/stores';
	import { getSummary } from '$lib/apis/analytics';
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaConfig, verifyOllamaConnection } from '$lib/apis/ollama';
	import { getOpenAIConfig, verifyOpenAIConnection } from '$lib/apis/openai';
	import { getEmbeddingConfig, getRAGConfig, getVectorDBStatus, getWebSearchStatus } from '$lib/apis/retrieval';
	import { getAdminConfig, getLdapConfig, getLdapServer } from '$lib/apis/auths';
	import { WEBUI_VERSION } from '$lib/constants';
	import { compareVersion, formatNumber } from '$lib/utils';
	import {
		evaluateAuthHealth,
		evaluateVectorDBHealth,
		evaluateWebSearchHealth,
		formatEmbeddingSecondaryDetail,
		formatRerankerSecondaryDetail
	} from '$lib/utils/adminHealth';

	import AdminPageHeader from './AdminPageHeader.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let updateAvailable: boolean | null = null;
	let latestVersion = WEBUI_VERSION;

	let summary = {
		total_messages: 0,
		total_chats: 0,
		total_models: 0,
		total_users: 0
	};

	let modelCount = 0;

	type HealthState = 'loading' | 'ok' | 'warning' | 'error' | 'disabled';

	type HealthCheck = {
		id: string;
		label: string;
		state: HealthState;
		detail: string;
		secondaryDetail?: string;
		href?: string;
	};

	let healthChecks: HealthCheck[] = [
		{ id: 'ollama', label: 'Ollama', state: 'loading', detail: 'Checking...' },
		{ id: 'openai', label: 'OpenAI API', state: 'loading', detail: 'Checking...' },
		{ id: 'embedding', label: 'Embedding', state: 'loading', detail: 'Checking...' },
		{ id: 'vector_db', label: 'Vector DB', state: 'loading', detail: 'Checking...' },
		{ id: 'reranker', label: 'Reranker', state: 'loading', detail: 'Checking...' },
		{ id: 'web_search', label: 'Web Search', state: 'loading', detail: 'Checking...' },
		{ id: 'authentication', label: 'Authentication', state: 'loading', detail: 'Checking...' },
		{ id: 'models', label: 'Models', state: 'loading', detail: 'Checking...' }
	];

	const healthDotClass = (state: HealthState) => {
		if (state === 'ok') return 'bg-emerald-500';
		if (state === 'warning') return 'bg-amber-500';
		if (state === 'error') return 'bg-red-500';
		if (state === 'disabled') return 'bg-gray-300 dark:bg-gray-600';
		return 'bg-gray-300 dark:bg-gray-600 animate-pulse';
	};

	const checkConnectionsHealth = async (token: string) => {
		const [
			ollamaConfig,
			openaiConfig,
			embeddingConfig,
			ragConfig,
			vectorDbStatus,
			webSearchStatus,
			adminConfig,
			ldapConfig,
			ldapServer
		] = await Promise.all([
			getOllamaConfig(token).catch(() => null),
			getOpenAIConfig(token).catch(() => null),
			getEmbeddingConfig(token).catch(() => null),
			getRAGConfig(token).catch(() => null),
			getVectorDBStatus(token).catch(() => null),
			getWebSearchStatus(token).catch(() => null),
			getAdminConfig(token).catch(() => null),
			getLdapConfig(token).catch(() => null),
			getLdapServer(token).catch(() => null)
		]);

		const next = [...healthChecks];

		const setCheck = (id: string, patch: Partial<HealthCheck>) => {
			const idx = next.findIndex((check) => check.id === id);
			if (idx !== -1) next[idx] = { ...next[idx], ...patch };
		};

		if (!ollamaConfig?.ENABLE_OLLAMA_API) {
			setCheck('ollama', {
				state: 'disabled',
				detail: 'Disabled',
				href: '/admin/settings/connections'
			});
		} else {
			const url = ollamaConfig.OLLAMA_BASE_URLS?.[0];
			if (!url) {
				setCheck('ollama', {
					state: 'warning',
					detail: 'No connection configured',
					href: '/admin/settings/connections'
				});
			} else {
				try {
					await verifyOllamaConnection(token, {
						url,
						key: ollamaConfig.OLLAMA_API_CONFIGS?.[0]?.key ?? ''
					});
					setCheck('ollama', { state: 'ok', detail: 'Connected', href: '/admin/settings/connections' });
				} catch {
					setCheck('ollama', {
						state: 'error',
						detail: 'Unreachable',
						href: '/admin/settings/connections'
					});
				}
			}
		}

		if (!openaiConfig?.ENABLE_OPENAI_API) {
			setCheck('openai', {
				state: 'disabled',
				detail: 'Disabled',
				href: '/admin/settings/connections'
			});
		} else {
			const url = openaiConfig.OPENAI_API_BASE_URLS?.[0];
			const key = openaiConfig.OPENAI_API_KEYS?.[0] ?? '';
			const connectionConfig = openaiConfig.OPENAI_API_CONFIGS?.[0] ?? {};
			if (!url) {
				setCheck('openai', {
					state: 'warning',
					detail: 'No connection configured',
					href: '/admin/settings/connections'
				});
			} else {
				try {
					await verifyOpenAIConnection(token, { url, key, config: connectionConfig });
					setCheck('openai', {
						state: 'ok',
						detail: 'Connected',
						href: '/admin/settings/connections'
					});
				} catch {
					setCheck('openai', {
						state: 'error',
						detail: 'Unreachable',
						href: '/admin/settings/connections'
					});
				}
			}
		}

		const embeddingModel = embeddingConfig?.RAG_EMBEDDING_MODEL ?? '';
		if (!embeddingModel) {
			setCheck('embedding', {
				state: 'warning',
				detail: 'Not configured',
				href: '/admin/settings/documents?section=embedding'
			});
		} else {
			setCheck('embedding', {
				state: 'ok',
				detail: embeddingModel,
				secondaryDetail: formatEmbeddingSecondaryDetail({
					engine: embeddingConfig?.RAG_EMBEDDING_ENGINE,
					batchSize: embeddingConfig?.RAG_EMBEDDING_BATCH_SIZE
				}),
				href: '/admin/settings/documents?section=embedding'
			});
		}

		const vectorDbHref = '/admin/settings/documents?section=embedding';
		const vectorDbHealth = evaluateVectorDBHealth(
			vectorDbStatus,
			!!ragConfig?.BYPASS_EMBEDDING_AND_RETRIEVAL
		);
		setCheck('vector_db', {
			state: vectorDbHealth.state,
			detail: vectorDbHealth.detail,
			secondaryDetail: vectorDbHealth.secondaryDetail,
			href: vectorDbHref
		});

		const count = $models?.length ?? 0;

		if (ragConfig?.BYPASS_EMBEDDING_AND_RETRIEVAL) {
			setCheck('reranker', {
				state: 'disabled',
				detail: 'Bypass mode enabled',
				href: '/admin/settings/documents?section=retrieval'
			});
		} else if (!ragConfig?.ENABLE_RAG_HYBRID_SEARCH) {
			setCheck('reranker', {
				state: 'disabled',
				detail: 'Hybrid search off',
				href: '/admin/settings/documents?section=retrieval'
			});
		} else {
			const rerankModel = ragConfig?.RAG_RERANKING_MODEL ?? '';
			if (!rerankModel) {
				setCheck('reranker', {
					state: 'warning',
					detail: 'Not configured',
					href: '/admin/settings/documents?section=retrieval'
				});
			} else {
				setCheck('reranker', {
					state: 'ok',
					detail: rerankModel,
					secondaryDetail: formatRerankerSecondaryDetail({
						hybridEnabled: true,
						rerankEngine: ragConfig?.RAG_RERANKING_ENGINE
					}),
					href: '/admin/settings/documents?section=retrieval'
				});
			}
		}

		const webSearchHealth = evaluateWebSearchHealth(webSearchStatus);
		setCheck('web_search', {
			state: webSearchHealth.state,
			detail: webSearchHealth.detail,
			secondaryDetail: webSearchHealth.secondaryDetail,
			href: '/admin/settings/web'
		});

		const authHealth = evaluateAuthHealth({
			features: $config?.features,
			oauthProviders: $config?.oauth?.providers,
			enableLdap: ldapConfig?.ENABLE_LDAP ?? false,
			ldapServer,
			enableSignup: adminConfig?.ENABLE_SIGNUP
		});
		setCheck('authentication', {
			state: authHealth.state,
			detail: authHealth.detail,
			secondaryDetail: authHealth.secondaryDetail,
			href: '/admin/settings/authentication'
		});

		setCheck('models', {
			state: count > 0 ? 'ok' : 'warning',
			detail: count > 0 ? `${count} available` : 'No models loaded',
			href: '/admin/settings/models'
		});

		healthChecks = next;
	};

	$: quickActions = [
		{
			title: 'Manage Users',
			description: 'Accounts, roles, and groups',
			href: '/admin/users/overview'
		},
		{
			title: 'Model Connections',
			description: 'Ollama, OpenAI, and providers',
			href: '/admin/settings/connections'
		},
		{
			title: 'Manage Models',
			description: 'Access, defaults, and configuration',
			href: '/admin/settings/models'
		},
		{
			title: 'Authentication',
			description: 'Signup, OAuth, and access policies',
			href: '/admin/settings/authentication'
		},
		{
			title: 'View Analytics',
			description: 'Usage, models, and token stats',
			href: '/admin/analytics',
			hidden: !($config?.features?.enable_admin_analytics ?? true)
		},
		{
			title: 'Evaluation Results',
			description: 'Leaderboard and user feedback',
			href: '/admin/evaluations/leaderboard'
		},
		{
			title: 'Evaluation Settings',
			description: 'Arena models and rating configuration',
			href: '/admin/settings/evaluations'
		},
		{
			title: 'Functions',
			description: 'Filters and action pipelines',
			href: '/admin/functions'
		},
		{
			title: 'Database & Backup',
			description: 'Export config, chats, and database',
			href: '/admin/settings/database'
		},
		{
			title: 'Documents & RAG',
			description: 'Embedding, retrieval, and file settings',
			href: '/admin/settings/documents'
		},
		{
			title: 'General Settings',
			description: 'Features, version, and instance config',
			href: '/admin/settings/general'
		}
	].filter((action) => !action.hidden);

	$: statCards = [
		{
			label: 'Active Users (7d)',
			value: summary.total_users,
			href: '/admin/users/overview'
		},
		{
			label: 'Chats (7d)',
			value: summary.total_chats,
			href: ($config?.features?.enable_admin_analytics ?? true) ? '/admin/analytics' : null
		},
		{
			label: 'Messages (7d)',
			value: summary.total_messages,
			href: ($config?.features?.enable_admin_analytics ?? true) ? '/admin/analytics' : null
		},
		{
			label: 'Models Available',
			value: modelCount,
			href: '/admin/settings/models'
		}
	];

	onMount(async () => {
		const token = localStorage.token;
		const now = Math.floor(Date.now() / 1000);
		const weekAgo = now - 7 * 86400;

		modelCount = $models?.length ?? 0;

		const tasks: Promise<unknown>[] = [];

		if ($config?.features?.enable_admin_analytics ?? true) {
			tasks.push(
				getSummary(token, weekAgo, now).then((data) => {
					if (data) summary = data;
				})
			);
		}

		if ($config?.features?.enable_version_update_check) {
			tasks.push(
				getVersionUpdates(token)
					.then((version) => {
						latestVersion = version.latest;
						updateAvailable = compareVersion(version.latest, WEBUI_VERSION);
					})
					.catch(() => {
						updateAvailable = false;
					})
			);
		}

		tasks.push(checkConnectionsHealth(token));

		await Promise.allSettled(tasks);
		loading = false;
	});
</script>

<div class="w-full h-full min-h-0 overflow-y-auto overscroll-contain pb-2 px-[16px]">
	<AdminPageHeader
		breadcrumbs={[{ label: 'Admin Panel' }]}
		title="Overview"
		description="Instance health, quick stats, and common admin tasks."
	/>

	{#if loading}
		<div class="flex justify-center py-16">
			<Spinner className="size-5" />
		</div>
	{:else}
		{#if updateAvailable}
			<a
				href="https://github.com/open-webui/open-webui/releases/tag/v{latestVersion}"
				target="_blank"
				rel="noopener noreferrer"
				class="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-amber-200/60 bg-amber-50 px-4 py-3 text-sm text-amber-900 transition hover:bg-amber-100/80 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100 dark:hover:bg-amber-950/50"
			>
				<span>
					{$i18n.t('Update available')}: v{latestVersion}
					<span class="text-amber-700/80 dark:text-amber-200/70">
						({$i18n.t('current')}: v{WEBUI_VERSION})
					</span>
				</span>
				<ChevronRight className="size-4 shrink-0" />
			</a>
		{/if}

		<div class="mb-6">
			<div class="mb-2 text-sm font-medium">{$i18n.t('System Health')}</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-4 gap-3">
				{#each healthChecks as check (check.id)}
					{#if check.href}
						<a
							href={check.href}
							class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900 px-4 py-3 transition hover:bg-gray-50 dark:hover:bg-gray-850/40"
						>
							<div class="flex items-center gap-2">
								<span class="size-2 rounded-full shrink-0 {healthDotClass(check.state)}"></span>
								<div class="text-sm font-medium">{$i18n.t(check.label)}</div>
							</div>
							<div class="mt-1 pl-4 space-y-0.5">
								<div
									class="text-xs text-gray-500 dark:text-gray-500 {check.id === 'vector_db' ||
									check.id === 'web_search' ||
									check.id === 'authentication'
										? 'line-clamp-2'
										: 'truncate'}"
								>
									{check.detail}
								</div>
								{#if check.secondaryDetail}
									<div class="text-[11px] leading-4 text-gray-400 dark:text-gray-600 line-clamp-2">
										{check.secondaryDetail}
									</div>
								{/if}
							</div>
						</a>
					{:else}
						<div
							class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900 px-4 py-3"
						>
							<div class="flex items-center gap-2">
								<span class="size-2 rounded-full shrink-0 {healthDotClass(check.state)}"></span>
								<div class="text-sm font-medium">{$i18n.t(check.label)}</div>
							</div>
							<div class="mt-1 pl-4 space-y-0.5">
								<div
									class="text-xs text-gray-500 dark:text-gray-500 {check.id === 'vector_db' ||
									check.id === 'web_search' ||
									check.id === 'authentication'
										? 'line-clamp-2'
										: 'truncate'}"
								>
									{check.detail}
								</div>
								{#if check.secondaryDetail}
									<div class="text-[11px] leading-4 text-gray-400 dark:text-gray-600 line-clamp-2">
										{check.secondaryDetail}
									</div>
								{/if}
							</div>
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
			{#each statCards as card (card.label)}
				{#if card.href}
					<a
						href={card.href}
						class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900 px-4 py-3 transition hover:bg-gray-50 dark:hover:bg-gray-850/40"
					>
						<div class="text-2xl font-medium tabular-nums">{formatNumber(card.value)}</div>
						<div class="mt-1 text-xs text-gray-500 dark:text-gray-500">{$i18n.t(card.label)}</div>
					</a>
				{:else}
					<div
						class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900 px-4 py-3"
					>
						<div class="text-2xl font-medium tabular-nums">{formatNumber(card.value)}</div>
						<div class="mt-1 text-xs text-gray-500 dark:text-gray-500">{$i18n.t(card.label)}</div>
					</div>
				{/if}
			{/each}
		</div>

		<div class="mb-2 text-sm font-medium">{$i18n.t('Quick Actions')}</div>
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
			{#each quickActions as action (action.href)}
				<a
					href={action.href}
					class="group rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900 px-4 py-3 transition hover:bg-gray-50 dark:hover:bg-gray-850/40"
				>
					<div class="flex items-center justify-between gap-2">
						<div class="font-medium text-sm">{$i18n.t(action.title)}</div>
						<ChevronRight
							className="size-4 shrink-0 text-gray-400 transition group-hover:translate-x-0.5"
						/>
					</div>
					<div class="mt-1 text-xs text-gray-500 dark:text-gray-500">
						{$i18n.t(action.description)}
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>
