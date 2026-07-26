<script>
	import {onMount} from 'svelte';
	import {goto} from '$app/navigation';
	import {user} from '$lib/stores';

	import Dashboard from './Analytics/Dashboard.svelte';
	import AdminPageHeader from './AdminPageHeader.svelte';

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
		loaded = true;
	});
</script>

{#if loaded}
	<div class="w-full h-full min-h-0 overflow-y-auto overscroll-contain pb-2 px-[16px]">
		<AdminPageHeader
			breadcrumbs={[
				{ label: 'Admin Panel', href: '/admin' },
				{ label: 'Analytics' }
			]}
			title="Analytics"
			description="Monitor usage, model activity, and token consumption across your instance."
		/>

		<Dashboard />
	</div>
{/if}
