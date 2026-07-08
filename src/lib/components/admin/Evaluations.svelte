<script>
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';

	import Leaderboard from './Evaluations/Leaderboard.svelte';
	import Feedbacks from './Evaluations/Feedbacks.svelte';
	import AdminSectionNav from './AdminSectionNav.svelte';
	import AdminPageHeader from './AdminPageHeader.svelte';
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
			{#if tab.id === 'leaderboard'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="size-4"
				>
					<path
						fill-rule="evenodd"
						d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm6 5.75a.75.75 0 0 1 1.5 0v3.5a.75.75 0 0 1-1.5 0v-3.5Zm-2.75 1.5a.75.75 0 0 1 1.5 0v2a.75.75 0 0 1-1.5 0v-2Zm-2 .75a.75.75 0 0 0-.75.75v.5a.75.75 0 0 0 1.5 0v-.5a.75.75 0 0 0-.75-.75Z"
						clip-rule="evenodd"
					></path>
				</svg>
			{:else if tab.id === 'feedback'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="size-4"
				>
					<path
						fill-rule="evenodd"
						d="M5.25 2A2.25 2.25 0 0 0 3 4.25v9a.75.75 0 0 0 1.183.613l1.692-1.195 1.692 1.195a.75.75 0 0 0 .866 0l1.692-1.195 1.693 1.195A.75.75 0 0 0 13 13.25v-9A2.25 2.25 0 0 0 10.75 2h-5.5Zm3.03 3.28a.75.75 0 0 0-1.06-1.06L4.97 6.47a.75.75 0 0 0 0 1.06l2.25 2.25a.75.75 0 0 0 1.06-1.06l-.97-.97h1.315c.76 0 1.375.616 1.375 1.375a.75.75 0 0 0 1.5 0A2.875 2.875 0 0 0 8.625 6.25H7.311l.97-.97Z"
						clip-rule="evenodd"
					></path>
				</svg>
			{/if}
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
