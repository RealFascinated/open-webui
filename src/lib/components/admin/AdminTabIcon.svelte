<script lang="ts">
	import Home from '$lib/components/icons/Home.svelte';
	import Users from '$lib/components/icons/Users.svelte';
	import UserGroup from '$lib/components/icons/UserGroup.svelte';
	import Star from '$lib/components/icons/Star.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Component from '$lib/components/icons/Component.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Computer from '$lib/components/icons/Computer.svelte';
	import Mic from '$lib/components/icons/Mic.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import QueueList from '$lib/components/icons/QueueList.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';

	export let iconId = '';
	export let className = 'size-4';
	export let strokeWidth = '1.75';
</script>

{#if iconId === 'overview'}
	<Home {className} {strokeWidth} />
{:else if iconId === 'users' || iconId === 'groups'}
	{#if iconId === 'groups'}
		<UserGroup className={className} strokeWidth={strokeWidth} />
	{:else}
		<Users className={className} strokeWidth={strokeWidth} />
	{/if}
{:else if iconId === 'analytics'}
	<svg
		xmlns="http://www.w3.org/2000/svg"
		fill="none"
		viewBox="0 0 24 24"
		stroke-width={strokeWidth}
		stroke="currentColor"
		aria-hidden="true"
		class={className}
	>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
		/>
	</svg>
{:else if iconId === 'evaluations' || iconId === 'leaderboard'}
	<Star className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'feedback'}
	<ChatBubble {className} {strokeWidth} />
{:else if iconId === 'functions'}
	<CommandLine className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'settings'}
	<Cog6 className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'general'}
	<AdjustmentsHorizontal className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'authentication'}
	<LockClosed {className} {strokeWidth} />
{:else if iconId === 'connections'}
	<Cloud className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'models'}
	<Cube className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'integrations'}
	<Component {className} {strokeWidth} />
{:else if iconId === 'documents'}
	<Document {className} {strokeWidth} />
{:else if iconId === 'web'}
	<GlobeAlt className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'code-execution'}
	<CommandLine className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'interface'}
	<Computer className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'audio'}
	<Mic {className} {strokeWidth} />
{:else if iconId === 'images'}
	<Photo className={className} strokeWidth={strokeWidth} />
{:else if iconId === 'pipelines'}
	<QueueList {className} {strokeWidth} />
{:else if iconId === 'db'}
	<Database {className} {strokeWidth} />
{/if}
