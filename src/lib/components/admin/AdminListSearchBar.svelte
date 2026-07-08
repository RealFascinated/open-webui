<script lang="ts">
	import { getContext } from 'svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let value = '';
	export let placeholder = 'Search';
	export let onInput: () => void = () => {};
	export let className = '';
	export let inputId = '';
</script>

<div
	class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30 {className}"
>
	<div class="px-3.5 flex flex-1 items-center w-full space-x-2 py-0.5">
		<div class="self-center ml-1 mr-1 text-gray-400 dark:text-gray-500">
			<Search className="size-3.5" />
		</div>
		{#if inputId}
			<label class="sr-only" for={inputId}>{$i18n.t(placeholder)}</label>
		{/if}
		<input
			id={inputId || undefined}
			class="w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
			bind:value
			on:input={onInput}
			placeholder={$i18n.t(placeholder)}
		/>
		{#if value}
			<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
				<button
					type="button"
					class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					aria-label={$i18n.t('Clear search')}
					on:click={() => {
						value = '';
						onInput();
					}}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			</div>
		{/if}
	</div>

	{#if $$slots.default}
		<slot />
	{/if}
</div>
