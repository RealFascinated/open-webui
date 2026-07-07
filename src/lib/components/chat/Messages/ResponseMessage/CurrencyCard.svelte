<script lang="ts">
	export let currency: {
		from?: string;
		to?: string;
		amount?: number;
		result?: number;
		rate?: number;
		inverse_rate?: number;
		updated?: string;
	} = {};

	const commonPairs = ['EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF'];

	$: otherPairs = commonPairs.filter((c) => c !== currency.from && c !== currency.to).slice(0, 4);
</script>

<div
	class="my-2 rounded-2xl border border-gray-50 dark:border-gray-850 bg-white dark:bg-gray-900 px-4 py-3.5"
>
	<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">
		{currency.amount} {currency.from} → {currency.to}
	</div>
	<div class="text-2xl font-semibold text-gray-900 dark:text-gray-100">
		{currency.result} {currency.to}
	</div>
	<div class="mt-2 text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
		{#if currency.rate != null}
			<div>1 {currency.from} = {currency.rate} {currency.to}</div>
		{/if}
		{#if currency.inverse_rate != null}
			<div>1 {currency.to} = {currency.inverse_rate} {currency.from}</div>
		{/if}
		{#if currency.updated}
			<div class="pt-1">Rates updated {currency.updated}</div>
		{/if}
	</div>
	{#if otherPairs.length > 0 && currency.from}
		<div class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-850 flex flex-wrap gap-2">
			{#each otherPairs as code}
				<span class="text-xs px-2 py-0.5 rounded-full bg-gray-50 dark:bg-gray-850 text-gray-500 dark:text-gray-400">
					{currency.from}/{code}
				</span>
			{/each}
		</div>
	{/if}
</div>
