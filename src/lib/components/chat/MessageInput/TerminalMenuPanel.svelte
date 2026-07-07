<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { settings, showSettings, terminalServers, selectedTerminalId, user } from '$lib/stores';
	import { getToolServersData } from '$lib/apis';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	$: systemTerminals = ($terminalServers ?? []).filter((t) => t.id);
	$: directTerminals = ($settings?.terminalServers ?? []).filter((s) => s.url);

	const refreshTerminalServersStore = async (servers: typeof directTerminals) => {
		const existingSystemTerminals = ($terminalServers ?? []).filter((t) => t.id);

		const activeTerminals = servers.filter((s) => s.enabled);
		if (activeTerminals.length > 0) {
			let data = await getToolServersData(
				activeTerminals.map((t) => ({
					url: t.url,
					auth_type: t.auth_type ?? 'bearer',
					key: t.key ?? '',
					path: t.path ?? '/openapi.json',
					config: { enable: true }
				}))
			);
			data = data.filter((d) => d && !d.error);
			terminalServers.set([...data, ...existingSystemTerminals]);
		} else {
			terminalServers.set(existingSystemTerminals);
		}
	};

	const selectDirect = async (terminal: (typeof directTerminals)[0]) => {
		const newId = $selectedTerminalId === terminal.url ? null : terminal.url;
		selectedTerminalId.set(newId);

		const updatedServers = ($settings?.terminalServers ?? []).map((s) => ({
			...s,
			enabled: newId !== null && s.url === terminal.url
		}));

		settings.set({
			...$settings,
			terminalServers: updatedServers
		});

		await refreshTerminalServersStore(updatedServers);
		dispatch('selected');
	};

	const selectSystem = async (terminal: (typeof systemTerminals)[0]) => {
		selectedTerminalId.set($selectedTerminalId === terminal.id ? null : terminal.id);

		if ($settings?.terminalServers?.some((s) => s.enabled)) {
			const updatedServers = ($settings.terminalServers ?? []).map((s) => ({
				...s,
				enabled: false
			}));
			settings.set({
				...$settings,
				terminalServers: updatedServers
			});
			await refreshTerminalServersStore(updatedServers);
		}

		dispatch('selected');
	};
</script>

{#if directTerminals.length > 0 && ($user?.role === 'admin' || ($user?.permissions?.features?.direct_tool_servers ?? true))}
	<div class="flex items-center justify-between px-3 py-1">
		<span class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">
			{$i18n.t('Direct')}
		</span>
		<Tooltip content={$i18n.t('Add Terminal')} placement="top">
			<button
				type="button"
				class="p-0.5 rounded-md text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition"
				on:click|stopPropagation={() => {
					dispatch('selected');
					showSettings.set('tools');
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
					/>
				</svg>
			</button>
		</Tooltip>
	</div>

	{#each directTerminals as terminal}
		<button
			type="button"
			class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl {$selectedTerminalId ===
			terminal.url
				? 'bg-gray-50 dark:bg-gray-800/50'
				: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
			on:click={() => selectDirect(terminal)}
		>
			<div class="flex flex-1 gap-2 items-center truncate">
				<Cloud className="size-4 shrink-0" strokeWidth="2" />
				<span class="truncate">{terminal.name || terminal.url.replace(/^https?:\/\//, '')}</span>
			</div>
			{#if $selectedTerminalId === terminal.url}
				<div class="shrink-0 text-emerald-600 dark:text-emerald-400">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			{/if}
		</button>
	{/each}

	{#if directTerminals.length > 0 && systemTerminals.length > 0}
		<hr class="border-gray-100 dark:border-gray-800 my-1" />
	{/if}
{/if}

{#if systemTerminals.length > 0}
	<div class="flex items-center justify-between px-3 py-1">
		<span class="text-[10px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">
			{$i18n.t('System')}
		</span>
		{#if $user?.role === 'admin'}
			<Tooltip content={$i18n.t('Add Terminal')} placement="top">
				<button
					type="button"
					class="p-0.5 rounded-md text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition"
					on:click|stopPropagation={() => {
						dispatch('selected');
						goto('/admin/settings/integrations');
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
						/>
					</svg>
				</button>
			</Tooltip>
		{/if}
	</div>

	{#each systemTerminals as terminal}
		<button
			type="button"
			class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl {$selectedTerminalId ===
			terminal.id
				? 'bg-gray-50 dark:bg-gray-800/50'
				: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
			on:click={() => selectSystem(terminal)}
		>
			<div class="flex flex-1 gap-2 items-center truncate">
				<Cloud className="size-4 shrink-0" strokeWidth="2" />
				<span class="truncate">{terminal.name || $i18n.t('Terminal')}</span>
			</div>
			{#if $selectedTerminalId === terminal.id}
				<div class="shrink-0 text-emerald-600 dark:text-emerald-400">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			{/if}
		</button>
	{/each}
{/if}
