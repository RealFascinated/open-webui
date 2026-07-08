<script lang="ts">
	export let icon = '📭';
	export let title = '';
	export let description = '';
	export let className = '';
</script>

<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24 {className}">
	<div class="max-w-md text-center">
		<div class="text-3xl mb-3">{icon}</div>
		<div class="text-lg font-medium mb-1">{title}</div>
		{#if description}
			<div class="text-gray-500 text-center text-xs">{description}</div>
		{/if}
		<slot />
	</div>
</div>
