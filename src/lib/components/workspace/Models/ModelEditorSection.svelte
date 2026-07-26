<script lang="ts">
	import { getContext } from 'svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let title = '';
	export let description = '';
	export let status: string | null = null;
	export let collapsible = false;
	export let open = true;

	const toggle = () => {
		if (collapsible) {
			open = !open;
		}
	};
</script>

<section {id} class="scroll-mt-20 rounded-2xl border border-gray-100/30 dark:border-gray-850/30 bg-white dark:bg-gray-900">
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="px-4 pt-3.5 pb-2 border-b border-gray-100/30 dark:border-gray-850/30 {collapsible
			? 'cursor-pointer'
			: ''}"
		on:click={toggle}
		on:keydown={(e) => {
			if (collapsible && (e.key === 'Enter' || e.key === ' ')) {
				e.preventDefault();
				toggle();
			}
		}}
	>
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<div class="text-sm font-medium text-gray-900 dark:text-gray-100">{$i18n.t(title)}</div>
				{#if description}
					<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-500">{$i18n.t(description)}</p>
				{/if}
			</div>

			<div class="flex items-center gap-2 shrink-0">
				{#if status}
					<span
						class="text-[11px] font-medium px-2 py-0.5 rounded-md bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200 tabular-nums"
					>
						{status}
					</span>
				{/if}

				{#if collapsible}
					<div class="text-gray-400">
						{#if open}
							<ChevronUp className="size-3.5" />
						{:else}
							<ChevronDown className="size-3.5" />
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>

	{#if !collapsible || open}
		<div class="px-4 py-3 space-y-3">
			<slot />
		</div>
	{/if}
</section>
