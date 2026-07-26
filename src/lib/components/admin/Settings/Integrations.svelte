<script lang="ts">
	import {toast} from 'svelte-sonner';
	import {onMount, getContext} from 'svelte';
	import {getModels as _getModels} from '$lib/apis';
	import type {Writable} from 'svelte/store';
	import type {i18n as i18nType} from 'i18next';
	const i18n = getContext<Writable<i18nType>>('i18n');

	import {terminalServers} from '$lib/stores';
	import {getTerminalServers} from '$lib/apis/terminal';
	import {WEBUI_API_BASE_URL} from '$lib/constants';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Connection from '$lib/components/chat/Settings/Tools/Connection.svelte';
import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';
	import AddTerminalServerModal from '$lib/components/AddTerminalServerModal.svelte';
	import ExternalKnowledge from './ExternalKnowledge.svelte';
	import AdminSaveBar from '../AdminSaveBar.svelte';
	import AdminSettingsCard from '../AdminSettingsCard.svelte';

	import {getToolServerConnections, setToolServerConnections, getTerminalServerConnections, setTerminalServerConnections} from '$lib/apis/configs';

	type ToolServerConnection = Record<string, unknown>;
	type TerminalConnection = {
		id?: string;
		url?: string;
		name?: string;
		key?: string;
		enabled?: boolean;
		[key: string]: unknown;
	};

	let servers: ToolServerConnection[] | null = null;
	let showConnectionModal = false;

	// Terminal server admin connections
	let terminalConnections: TerminalConnection[] = [];
	let showAddTerminalModal = false;
	let editTerminalIdx: number | null = null;

	let dirty = false;
	let saving = false;
	let initialSnapshot = '';

	const snapshot = () => JSON.stringify({ servers, terminalConnections });

	$: if (initialSnapshot && servers !== null) {
		dirty = snapshot() !== initialSnapshot;
	}

	const refreshSnapshot = () => {
		initialSnapshot = snapshot();
		dirty = false;
	};

	const addConnectionHandler = async (server: ToolServerConnection) => {
		servers = [...(servers ?? []), server];
		await updateHandler();
	};

	const updateHandler = async () => {
		const res = await setToolServerConnections(localStorage.token, {
			TOOL_SERVER_CONNECTIONS: servers
		}).catch((_err) => {
			toast.error($i18n.t('Failed to save connections'));
			return null;
		});

		if (res) {
			toast.success($i18n.t('Connections saved successfully'));
			refreshSnapshot();
		}
	};

	const saveTerminalServers = async () => {
		const res = await setTerminalServerConnections(localStorage.token, {
			TERMINAL_SERVER_CONNECTIONS: terminalConnections
		}).catch((_err) => {
			toast.error($i18n.t('Failed to save terminal servers'));
			return null;
		});

		if (res) {
			toast.success($i18n.t('Terminal servers saved'));

			// Refresh the terminalServers store so changes are reflected immediately
			// Preserve user direct terminals, refresh system terminals from backend
			const existingDirectTerminals = (($terminalServers ?? []) as TerminalConnection[]).filter(
				(t) => !t.id
			);
			const systemTerminals = await getTerminalServers(localStorage.token);
			const systemEntries = systemTerminals.map((t) => ({
				id: t.id,
				url: `${WEBUI_API_BASE_URL}/terminals/${t.id}`,
				name: t.name,
				key: localStorage.token
			}));
			terminalServers.set([...existingDirectTerminals, ...systemEntries] as unknown);
			refreshSnapshot();
		}
	};

	const addTerminalConnection = (server: TerminalConnection) => {
		terminalConnections = [
			...terminalConnections,
			{ ...server, id: server.id ?? crypto.randomUUID() }
		];
		saveTerminalServers();
	};

	const updateTerminalConnection = (idx: number, updated: TerminalConnection) => {
		terminalConnections = terminalConnections.map((c, i) =>
			i === idx ? { ...c, ...updated, id: updated.id ?? c.id } : c
		);
		saveTerminalServers();
	};

	const removeTerminalConnection = (idx: number) => {
		terminalConnections = terminalConnections.filter((_, i) => i !== idx);
		saveTerminalServers();
	};

	const loadData = async () => {
		const res = await getToolServerConnections(localStorage.token);
		servers = res.TOOL_SERVER_CONNECTIONS as ToolServerConnection[];

		try {
			const terminalRes = await getTerminalServerConnections(localStorage.token);
			if (terminalRes?.TERMINAL_SERVER_CONNECTIONS) {
				terminalConnections = terminalRes.TERMINAL_SERVER_CONNECTIONS as TerminalConnection[];
			}
		} catch {
			// Not configured yet
		}

		refreshSnapshot();
	};

	const saveAllHandler = async () => {
		saving = true;
		await updateHandler();
		await saveTerminalServers();
		saving = false;
	};

	const discardHandler = async () => {
		await loadData();
	};

	onMount(loadData);
</script>

<AddToolServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<AddTerminalServerModal
	bind:show={showAddTerminalModal}
	edit={editTerminalIdx !== null}
	connection={editTerminalIdx !== null ? terminalConnections[editTerminalIdx] : null}
	onSubmit={(c: TerminalConnection) => {
		if (editTerminalIdx !== null) {
			updateTerminalConnection(editTerminalIdx, c);
			editTerminalIdx = null;
		} else {
			addTerminalConnection(c);
		}
	}}
	onDelete={() => {
		if (editTerminalIdx !== null) {
			removeTerminalConnection(editTerminalIdx);
			editTerminalIdx = null;
		}
	}}
/>

<form class="flex flex-col text-sm">
	<div>
		{#if servers !== null}
			<AdminSettingsCard
				title="Tool Servers"
				description="OpenAPI-compatible external tool and function servers."
				className="mb-3"
			>
					<div class="mb-2.5 flex flex-col w-full justify-between">
						<div class="flex justify-between items-center mb-0.5">
							<div class="font-medium">{$i18n.t('External Tool Servers')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									on:click={() => {
										showConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1">
							{#each servers ?? [] as server, idx}
								<Connection
									bind:connection={server}
									onSubmit={() => {
										updateHandler();
									}}
									onDelete={() => {
										servers = (servers ?? []).filter((_, i) => i !== idx);
										updateHandler();
									}}
								/>
							{/each}
						</div>

						{#if (servers ?? []).length === 0}
							<div class="text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('No tool server connections configured.')}
							</div>
						{/if}

						<div class="my-1.5">
							<div class="text-xs text-gray-500">
								{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
							</div>
						</div>
					</div>
			</AdminSettingsCard>

			<AdminSettingsCard
				title="Open Terminal"
				description="Remote terminal instances for file browsing and shell tools."
				className="mb-3"
			>
					<div class="flex justify-end mb-1">
							<Tooltip content={$i18n.t('Add Connection')}>
								<button
									class="px-1"
									on:click={() => {
										editTerminalIdx = null;
										showAddTerminalModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1.5">
							{#each terminalConnections as connection, idx}
								<div class="flex w-full gap-2 items-center">
									<Tooltip className="w-full relative" content={''} placement="top-start">
										<div class="flex w-full">
											<div
												class="flex-1 relative flex gap-1.5 items-center {connection?.enabled ===
												false
													? 'opacity-50'
													: ''}"
											>
												<Tooltip content={$i18n.t('Terminal')}>
													<Cloud className="size-4" strokeWidth="1.5" />
												</Tooltip>

												<div class="outline-hidden w-full bg-transparent text-sm">
													{connection.name || connection.url || $i18n.t('New Terminal')}
												</div>
											</div>
										</div>
									</Tooltip>

									<div class="flex gap-1 items-center">
										<Tooltip content={$i18n.t('Configure')}>
											<button
												class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
												on:click={() => {
													editTerminalIdx = idx;
													showAddTerminalModal = true;
												}}
												type="button"
											>
												<Cog6 />
											</button>
										</Tooltip>

										<Tooltip
											content={connection?.enabled !== false
												? $i18n.t('Enabled')
												: $i18n.t('Disabled')}
										>
											<Switch
												state={connection?.enabled !== false}
												on:change={() => {
													terminalConnections = terminalConnections.map((c, i) =>
														i === idx ? { ...c, enabled: !(c?.enabled !== false) } : c
													);
													saveTerminalServers();
												}}
											/>
										</Tooltip>
									</div>
								</div>
							{/each}
						</div>

						{#if terminalConnections.length === 0}
							<div class="text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('No terminal connections configured.')}
							</div>
						{/if}

						<div class="mt-1.5">
							<div class="text-xs text-gray-500">
								{$i18n.t(
									'Connect to Open Terminal instances. All users will have access to file browsing and terminal tools through these servers.'
								)}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-300 mt-1">
								<a
									class="underline"
									href="https://github.com/open-webui/open-terminal"
									target="_blank">{$i18n.t('Learn more about Open Terminal')} ↗</a
								>
							</div>
						</div>
			</AdminSettingsCard>

			<AdminSettingsCard
				title="Knowledge"
				description="External knowledge base API integrations."
			>
					<ExternalKnowledge />
			</AdminSettingsCard>
		{:else}
			<div class="flex h-full justify-center py-16">
				<Spinner className="size-6" />
			</div>
		{/if}
	</div>

	{#if servers !== null}
		<AdminSaveBar {dirty} {saving} onSave={saveAllHandler} onDiscard={discardHandler} />
	{/if}
</form>
