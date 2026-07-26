<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let followUps: string[] = [];
	export let onClick: (followUp: string) => void = () => {};
	export let disabled = false;
	export let variant: 'list' | 'chips' = 'list';

	let clicked: string | null = null;

	$: useChips =
		variant === 'chips' ||
		(followUps.length > 0 && followUps.every((followUp) => followUp.length <= 80));

	const handleClick = (followUp: string) => {
		if (disabled || clicked) return;
		clicked = followUp;
		onClick(followUp);
	};
</script>

{#if followUps.length > 0}
	<div class="mt-4">
		<div class="text-sm font-medium">
			{$i18n.t('Follow up')}
		</div>

		{#if useChips}
			<div class="mt-2.5 flex flex-wrap gap-2">
				{#each followUps as followUp, idx (idx)}
					<button
						type="button"
						class="px-3 py-1.5 rounded-full text-sm border transition-colors
							{clicked === followUp
							? 'border-gray-900 dark:border-gray-100 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900'
							: clicked
								? 'border-gray-200 dark:border-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed opacity-50'
								: 'border-gray-200 dark:border-gray-800 hover:border-gray-400 dark:hover:border-gray-600 text-gray-600 dark:text-gray-400'}"
						disabled={disabled || (clicked !== null && clicked !== followUp)}
						aria-label={$i18n.t('Follow up: {{question}}', { question: followUp })}
						on:click={() => handleClick(followUp)}
					>
						{followUp}
					</button>
				{/each}
			</div>
		{:else}
			<div class="flex flex-col text-left gap-1 mt-1.5">
				{#each followUps as followUp, idx (idx)}
					<Tooltip content={followUp} placement="top-start" className="line-clamp-1">
						<button
							type="button"
							class="py-1.5 bg-transparent text-left text-sm flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white transition cursor-pointer w-full"
							disabled={disabled}
							on:click={() => onClick(followUp)}
							aria-label={$i18n.t('Follow up: {{question}}', { question: followUp })}
						>
							<div class="line-clamp-1">
								{followUp}
							</div>
						</button>
					</Tooltip>

					{#if idx < followUps.length - 1}
						<hr class="border-gray-50 dark:border-gray-850/30" />
					{/if}
				{/each}
			</div>
		{/if}
	</div>
{/if}
