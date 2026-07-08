<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { getVectorDBStatus } from '$lib/apis/retrieval';
	import { formatNumber } from '$lib/utils';
	import { type VectorDBStatus } from '$lib/utils/adminHealth';

	import AdminSettingsCard from './AdminSettingsCard.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let bypassMode = false;
	export let className = 'mb-3';

	let loading = true;
	let vectorDbStatus: VectorDBStatus | null = null;

	$: label = vectorDbStatus?.VECTOR_DB_LABEL ?? vectorDbStatus?.VECTOR_DB ?? 'Vector DB';
	$: cardStatus = bypassMode
		? 'warning'
		: !vectorDbStatus
			? null
			: vectorDbStatus.healthy
				? 'configured'
				: 'warning';

	const loadStatus = async () => {
		loading = true;
		vectorDbStatus = await getVectorDBStatus(localStorage.token).catch(() => null);
		loading = false;
	};

	onMount(loadStatus);

	const formatCount = (value: number | null | undefined) => {
		if (value == null) return '—';
		return formatNumber(value);
	};

	const deploymentLabel = (deployment: string | null | undefined) => {
		if (!deployment) return null;
		if (deployment === 'local') return 'Local';
		if (deployment === 'remote') return 'Remote';
		return deployment.charAt(0).toUpperCase() + deployment.slice(1);
	};

	$: deployment = deploymentLabel(vectorDbStatus?.deployment);
	$: locationDetail = vectorDbStatus?.host ?? vectorDbStatus?.data_path ?? null;
	$: subtitle = [label, vectorDbStatus?.healthy ? deployment : 'Unreachable'].filter(Boolean).join(' · ');
</script>

<AdminSettingsCard
	title="Vector Database"
	description="Connection health and stored vector statistics."
	status={loading ? null : cardStatus}
	className={className}
>
	{#if loading}
		<div class="flex justify-center py-4">
			<Spinner className="size-4" />
		</div>
	{:else if bypassMode}
		<div class="text-xs text-gray-500 dark:text-gray-500">
			{$i18n.t('Bypass mode is enabled. Embeddings and retrieval are skipped, so vectors are not stored.')}
		</div>
	{:else if !vectorDbStatus}
		<div class="text-xs text-gray-500 dark:text-gray-500">
			{$i18n.t('Status unavailable')}
		</div>
	{:else if !vectorDbStatus.healthy}
		<div class="space-y-2">
			<div class="text-xs font-medium text-gray-800 dark:text-gray-200">{subtitle}</div>
			{#if vectorDbStatus.error}
				<div
					class="rounded-xl border border-red-200/50 bg-red-50/50 px-3 py-2 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300"
				>
					{vectorDbStatus.error}
				</div>
			{/if}
		</div>
	{:else}
		<div class="space-y-2.5">
			<div class="text-xs text-gray-500 dark:text-gray-500">{subtitle}</div>

			<div class="grid grid-cols-3 gap-2">
				<div class="rounded-xl border border-gray-100/30 dark:border-gray-850/30 px-3 py-2">
					<div class="text-[11px] text-gray-400 dark:text-gray-600">
						{$i18n.t('Collections')}
					</div>
					<div class="mt-0.5 text-sm font-medium tabular-nums">
						{formatCount(vectorDbStatus.collection_count)}
					</div>
				</div>

				<div class="rounded-xl border border-gray-100/30 dark:border-gray-850/30 px-3 py-2">
					<div class="text-[11px] text-gray-400 dark:text-gray-600">
						{$i18n.t('Vectors')}
					</div>
					<div class="mt-0.5 text-sm font-medium tabular-nums">
						{formatCount(vectorDbStatus.vector_count)}
					</div>
				</div>

				<div class="rounded-xl border border-gray-100/30 dark:border-gray-850/30 px-3 py-2">
					<div class="text-[11px] text-gray-400 dark:text-gray-600">
						{$i18n.t('Storage')}
					</div>
					<div class="mt-0.5 text-sm font-medium">
						{vectorDbStatus.storage_size ?? '—'}
					</div>
				</div>
			</div>

			{#if locationDetail && locationDetail !== deployment}
				<div class="text-[11px] leading-4 text-gray-400 dark:text-gray-600 break-all">
					{locationDetail}
				</div>
			{/if}
		</div>
	{/if}

	{#if !loading && !bypassMode}
		<button
			type="button"
			class="mt-2.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
			on:click={loadStatus}
		>
			{$i18n.t('Refresh status')}
		</button>
	{/if}
</AdminSettingsCard>
