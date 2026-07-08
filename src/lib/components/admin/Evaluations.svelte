<script>
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';

	import Leaderboard from './Evaluations/Leaderboard.svelte';
	import Feedbacks from './Evaluations/Feedbacks.svelte';
	import AdminSectionNav from './AdminSectionNav.svelte';
	import AdminPageHeader from './AdminPageHeader.svelte';
	import AdminTabIcon from './AdminTabIcon.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	const evaluationTabs = [
		{
			id: 'leaderboard',
			href: '/admin/evaluations/leaderboard',
			label: 'Leaderboard',
			description: 'View model rankings and preference comparisons from user evaluations.'
		},
		{
			id: 'feedback',
			href: '/admin/evaluations/feedback',
			label: 'Feedback',
			description: 'Review ratings and feedback submitted by users.'
		}
	];

	let selectedTab;
	$: selectedTab = ['leaderboard', 'feedback'].includes($page.params.tab)
		? $page.params.tab
		: 'leaderboard';

	$: currentTab = evaluationTabs.find((tab) => tab.id === selectedTab) ?? evaluationTabs[0];

	let loaded = false;

	onMount(() => {
		loaded = true;
	});
</script>

{#if loaded}
	<AdminSectionNav tabs={evaluationTabs} {selectedTab}>
		<svelte:fragment slot="icon" let:tab>
			<AdminTabIcon iconId={tab.id} />
		</svelte:fragment>

		<AdminPageHeader
			breadcrumbs={[
				{ label: 'Admin Panel', href: '/admin' },
				{ label: 'Evaluations', href: '/admin/evaluations' },
				{ label: currentTab.label }
			]}
			title={currentTab.label}
			description={currentTab.description}
		/>

		<a
			href="/admin/settings/evaluations"
			class="mb-4 flex items-center justify-between gap-3 rounded-xl border border-gray-100/30 dark:border-gray-850/30 bg-gray-50/80 dark:bg-gray-900/50 px-3.5 py-2.5 text-sm transition hover:bg-gray-100 dark:hover:bg-gray-850/60"
		>
			<span class="text-gray-600 dark:text-gray-300">
				{$i18n.t('Configure arena models and ratings in Evaluation Settings')}
			</span>
			<ChevronRight className="size-4 shrink-0 text-gray-400" />
		</a>

		{#if selectedTab === 'leaderboard'}
			<Leaderboard />
		{:else if selectedTab === 'feedback'}
			<Feedbacks />
		{/if}
	</AdminSectionNav>
{/if}
