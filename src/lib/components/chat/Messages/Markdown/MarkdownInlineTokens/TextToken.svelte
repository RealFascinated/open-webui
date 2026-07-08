<script lang="ts">
	export let token;
	export let done = true;

	$: raw = token?.raw ?? '';
</script>

{#if done}
	{raw}
{:else}
	{@const lastSpaceIdx = raw.lastIndexOf(' ')}
	{#if lastSpaceIdx === -1}
		<span class="fade-in-token">{raw}</span>
	{:else}
		{raw.slice(0, lastSpaceIdx + 1)}<span class="fade-in-token">{raw.slice(lastSpaceIdx + 1)}</span>
	{/if}
{/if}
