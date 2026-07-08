<script>
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { page } from '$app/stores';

	import UserList from './Users/UserList.svelte';
	import Groups from './Users/Groups.svelte';
	import AdminSectionNav from './AdminSectionNav.svelte';
	import AdminPageHeader from './AdminPageHeader.svelte';
	import AdminTabIcon from './AdminTabIcon.svelte';

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
			<AdminTabIcon iconId={tab.id === 'overview' ? 'users' : tab.id} />
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
