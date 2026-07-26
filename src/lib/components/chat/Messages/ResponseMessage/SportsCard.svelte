<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let sports: {
		team?: string;
		league?: string;
		badge?: string;
		recent?: {
			opponent?: string;
			score?: string | null;
			date?: string;
			competition?: string;
		}[];
		upcoming?: {
			opponent?: string;
			date?: string;
			competition?: string;
		}[];
	} = {};

	let tab: 'recent' | 'upcoming' = 'recent';
</script>

<div
	class="rounded-2xl border border-gray-50 dark:border-gray-850 bg-white dark:bg-gray-900 overflow-hidden"
>
	<div class="px-4 py-3 flex items-center gap-3 border-b border-gray-50 dark:border-gray-850">
		{#if sports.badge}
			<img src={sports.badge} alt="" class="size-10 object-contain" />
		{/if}
		<div>
			<div class="text-sm font-medium text-gray-900 dark:text-gray-100">{sports.team}</div>
			{#if sports.league}
				<div class="text-xs text-gray-500 dark:text-gray-400">{sports.league}</div>
			{/if}
		</div>
	</div>

	<div class="flex border-b border-gray-50 dark:border-gray-850 text-xs">
		<button
			type="button"
			class="flex-1 py-2 {tab === 'recent'
				? 'text-gray-900 dark:text-gray-100 border-b-2 border-gray-900 dark:border-gray-100'
				: 'text-gray-500 dark:text-gray-400'}"
			on:click={() => (tab = 'recent')}
		>
			{$i18n.t('Recent Results')}
		</button>
		<button
			type="button"
			class="flex-1 py-2 {tab === 'upcoming'
				? 'text-gray-900 dark:text-gray-100 border-b-2 border-gray-900 dark:border-gray-100'
				: 'text-gray-500 dark:text-gray-400'}"
			on:click={() => (tab = 'upcoming')}
		>
			{$i18n.t('Upcoming')}
		</button>
	</div>

	<div class="px-4 py-2 space-y-2">
		{#if tab === 'recent'}
			{#each sports.recent ?? [] as match, idx (idx)}
				<div class="flex items-center justify-between text-sm py-1">
					<div class="min-w-0">
						<div class="text-gray-800 dark:text-gray-200 truncate">vs {match.opponent}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{match.competition}</div>
					</div>
					<div class="text-right shrink-0 ml-3">
						{#if match.score}
							<div class="font-medium text-gray-900 dark:text-gray-100">{match.score}</div>
						{/if}
						<div class="text-xs text-gray-500 dark:text-gray-400">{match.date}</div>
					</div>
				</div>
			{:else}
				<div class="text-xs text-gray-500 dark:text-gray-400 py-2">
					{$i18n.t('No recent results')}
				</div>
			{/each}
		{:else}
			{#each sports.upcoming ?? [] as match, idx (idx)}
				<div class="flex items-center justify-between text-sm py-1">
					<div class="min-w-0">
						<div class="text-gray-800 dark:text-gray-200 truncate">vs {match.opponent}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{match.competition}</div>
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 shrink-0 ml-3">{match.date}</div>
				</div>
			{:else}
				<div class="text-xs text-gray-500 dark:text-gray-400 py-2">
					{$i18n.t('No upcoming fixtures')}
				</div>
			{/each}
		{/if}
	</div>
</div>
