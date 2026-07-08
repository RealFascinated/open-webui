<script>
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { page } from '$app/stores';

	import UserList from './Users/UserList.svelte';
	import Groups from './Users/Groups.svelte';
	import AdminSectionNav from './AdminSectionNav.svelte';
	import AdminPageHeader from './AdminPageHeader.svelte';

	const i18n = getContext('i18n');

	const userTabs = [
		{
			id: 'overview',
			href: '/admin/users/overview',
			label: 'Overview',
			description: 'Manage user accounts, roles, and access.'
		},
		{
			id: 'groups',
			href: '/admin/users/groups',
			label: 'Groups',
			description: 'Organize users and configure group permissions.'
		}
	];

	let selectedTab;
	$: selectedTab = ['overview', 'groups'].includes($page.params.tab)
		? $page.params.tab
		: 'overview';

	$: currentTab = userTabs.find((tab) => tab.id === selectedTab) ?? userTabs[0];

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}

		loaded = true;
	});
</script>

{#if loaded}
	<AdminSectionNav tabs={userTabs} {selectedTab}>
		<svelte:fragment slot="icon" let:tab>
			{#if tab.id === 'overview'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="size-4"
				>
					<path
						d="M8.5 4.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0ZM10.9 12.006c.11.542-.348.994-.9.994H2c-.553 0-1.01-.452-.902-.994a5.002 5.002 0 0 1 9.803 0ZM14.002 12h-1.59a2.556 2.556 0 0 0-.04-.29 6.476 6.476 0 0 0-1.167-2.603 3.002 3.002 0 0 1 3.633 1.911c.18.522-.283.982-.836.982ZM12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"
					></path>
				</svg>
			{:else if tab.id === 'groups'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="size-4"
				>
					<path
						d="M8 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM3.156 11.763c.16-.629.44-1.21.813-1.72a2.5 2.5 0 0 0-2.725 1.377c-.136.287.102.58.418.58h1.449c.01-.077.025-.156.045-.237ZM12.847 11.763c.02.08.036.16.046.237h1.446c.316 0 .554-.293.417-.579a2.5 2.5 0 0 0-2.722-1.378c.374.51.653 1.09.813 1.72ZM14 7.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM3.5 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM5 13c-.552 0-1.013-.455-.876-.99a4.002 4.002 0 0 1 7.753 0c.136.535-.324.99-.877.99H5Z"
					></path>
				</svg>
			{/if}
		</svelte:fragment>

		<AdminPageHeader
			breadcrumbs={[
				{ label: 'Admin Panel', href: '/admin' },
				{ label: 'Users', href: '/admin/users' },
				{ label: currentTab.label }
			]}
			title={currentTab.label}
			description={currentTab.description}
		/>

		{#if selectedTab === 'overview'}
			<UserList />
		{:else if selectedTab === 'groups'}
			<Groups />
		{/if}
	</AdminSectionNav>
{/if}
