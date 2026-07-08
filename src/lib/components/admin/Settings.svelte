<script>
	import { getContext, tick, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	import { config } from '$lib/stores';
	import { getBackendConfig } from '$lib/apis';
	import Database from './Settings/Database.svelte';

	import Authentication from './Settings/Authentication.svelte';
	import General from './Settings/General.svelte';
	import Pipelines from './Settings/Pipelines.svelte';
	import Audio from './Settings/Audio.svelte';
	import Images from './Settings/Images.svelte';
	import Interface from './Settings/Interface.svelte';
	import Models from './Settings/Models.svelte';
	import Connections from './Settings/Connections.svelte';
	import Documents from './Settings/Documents.svelte';
	import WebSearch from './Settings/WebSearch.svelte';

	import Evaluations from './Settings/Evaluations.svelte';
	import CodeExecution from './Settings/CodeExecution.svelte';
	import Integrations from './Settings/Integrations.svelte';

	import AdminSectionNav from './AdminSectionNav.svelte';
	import AdminPageHeader from './AdminPageHeader.svelte';
	import SettingsTabIcon from './Settings/SettingsTabIcon.svelte';
	import {
		ALL_SETTINGS_TABS,
		SETTINGS_TAB_IDS,
		filterSettingsTabs,
		groupSettingsTabs
	} from './settingsTabs';

	const i18n = getContext('i18n');

	let selectedTab = 'general';

	$: selectedTab = $page.url.pathname.includes('/admin/settings/documents')
		? 'documents'
		: SETTINGS_TAB_IDS.includes($page.params.tab)
			? $page.params.tab
			: 'general';

	let search = '';
	let searchDebounceTimeout;
	let filteredSettings = ALL_SETTINGS_TABS;

	$: navGroups = groupSettingsTabs(filteredSettings);

	$: currentTab =
		ALL_SETTINGS_TABS.find((tab) => tab.id === selectedTab) ?? ALL_SETTINGS_TABS[0];

	const setFilteredSettings = () => {
		filteredSettings = filterSettingsTabs(search);
	};

	const searchDebounceHandler = () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		searchDebounceTimeout = setTimeout(() => {
			setFilteredSettings();
		}, 100);
	};

	onMount(() => {
		setFilteredSettings();
	});
</script>

<AdminSectionNav
	groups={navGroups}
	{selectedTab}
	showSearch={true}
	bind:search
	searchInputId="search-input-settings-modal"
	onSearchInput={searchDebounceHandler}
>
	<svelte:fragment slot="icon" let:tab>
		<SettingsTabIcon tabId={tab.id} />
	</svelte:fragment>

	<AdminPageHeader
		breadcrumbs={[
			{ label: 'Admin Panel', href: '/admin' },
			{ label: 'Settings', href: '/admin/settings' },
			{ label: currentTab.title }
		]}
		title={currentTab.title}
		description={currentTab.description}
	/>

	{#if selectedTab === 'general'}
			<General
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'authentication'}
			<Authentication />
		{:else if selectedTab === 'connections'}
			<Connections
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'models'}
			<Models />
		{:else if selectedTab === 'evaluations'}
			<Evaluations />
		{:else if selectedTab === 'integrations'}
			<Integrations />
		{:else if selectedTab === 'documents'}
			<Documents
				on:save={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'web'}
			<WebSearch
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'code-execution'}
			<CodeExecution
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'interface'}
			<Interface
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'audio'}
			<Audio
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'images'}
			<Images
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'db'}
			<Database
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'pipelines'}
			<Pipelines
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{/if}
</AdminSectionNav>
