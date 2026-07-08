<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let title = '';
	export let description = '';
	export let status: 'configured' | 'not_configured' | 'warning' | null = null;
	export let className = '';
</script>

<div
	class="rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900 {className}"
>
	{#if title}
		<div class="px-4 pt-3.5 pb-2 border-b border-gray-100/30 dark:border-gray-850/30">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<div class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t(title)}</div>
					{#if description}
						<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-500">{$i18n.t(description)}</p>
					{/if}
				</div>
				{#if status === 'configured'}
					<span
						class="shrink-0 text-xs font-medium text-emerald-600 dark:text-emerald-400 whitespace-nowrap"
					>
						{$i18n.t('Configured')}
					</span>
				{:else if status === 'not_configured'}
					<span class="shrink-0 text-xs font-medium text-gray-400 whitespace-nowrap">
						{$i18n.t('Not configured')}
					</span>
				{:else if status === 'warning'}
					<span class="shrink-0 text-xs font-medium text-amber-600 dark:text-amber-400 whitespace-nowrap">
						{$i18n.t('Needs attention')}
					</span>
				{/if}
			</div>
		</div>
	{/if}

	<div class="px-4 py-3 space-y-2">
		<slot />
	</div>
</div>
