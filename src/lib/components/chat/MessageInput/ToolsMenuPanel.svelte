<script lang="ts">
	import { getContext, tick } from 'svelte';

	import { user, tools as _tools, toolServers } from '$lib/stores';

	import { initiateOAuthRedirect } from '$lib/apis/configs';
	import { deleteOAuthSession } from '$lib/apis/auths';
	import { getTools } from '$lib/apis/tools';

	import { toast } from 'svelte-sonner';

	import Knobs from '$lib/components/icons/Knobs.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import LinkSlash from '$lib/components/icons/LinkSlash.svelte';

	const i18n = getContext('i18n');

	export let active = false;
	export let selectedToolIds: string[] = [];
	export let onShowValves: (...args: unknown[]) => unknown;

	let tools = null;

	$: if (active) {
		init();
	}

	const init = async () => {
		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}

		if ($_tools) {
			tools = $_tools.reduce((a, tool) => {
				a[tool.id] = {
					name: tool.name,
					description: tool.meta.description,
					enabled: selectedToolIds.includes(tool.id),
					...tool
				};
				return a;
			}, {});
		}

		if ($toolServers) {
			for (const serverIdx in $toolServers) {
				const server = $toolServers[serverIdx];
				if (server.info) {
					tools[`direct_server:${serverIdx}`] = {
						name: server?.info?.title ?? server.url,
						description: server.info.description ?? '',
						enabled: selectedToolIds.includes(`direct_server:${serverIdx}`)
					};
				}
			}
		}

		selectedToolIds = selectedToolIds.filter((id: string) => Object.keys(tools ?? {}).includes(id));
	};
</script>

{#if tools}
	{#each Object.keys(tools) as toolId}
		<button
			class="relative flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
			type="button"
			on:click={async (e) => {
				if (!(tools[toolId]?.authenticated ?? true)) {
					e.preventDefault();

					const parts = toolId.split(':');
					initiateOAuthRedirect({
						id: toolId,
						serverId: parts.at(-1) ?? toolId,
						authType: parts.length > 1 ? (parts[0] === 'server' ? parts[1] : parts[0]) : null
					});
				} else {
					tools[toolId].enabled = !tools[toolId].enabled;

					const state = tools[toolId].enabled;
					await tick();

					if (state) {
						selectedToolIds = [...selectedToolIds, toolId];
					} else {
						selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
					}
				}
			}}
		>
			{#if !(tools[toolId]?.authenticated ?? true)}
				<div class="absolute inset-0 opacity-50 rounded-xl cursor-pointer z-10"></div>
			{/if}
			<div class="flex-1 truncate">
				<div class="flex flex-1 gap-2 items-center">
					<Tooltip content={tools[toolId]?.name ?? ''} placement="top">
						<div class="shrink-0">
							<Wrench />
						</div>
					</Tooltip>
					<Tooltip content={tools[toolId]?.description ?? ''} placement="top-start">
						<div class="truncate">{tools[toolId].name}</div>
					</Tooltip>
				</div>
			</div>

			{#if (tools[toolId]?.authenticated ?? true) && toolId.startsWith('server:mcp:')}
				<div class="shrink-0">
					<Tooltip content={$i18n.t('Disconnect OAuth')}>
						<button
							class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
							type="button"
							on:click={async (e) => {
								e.stopPropagation();
								e.preventDefault();

								const parts = toolId.split(':');
								const serverId = parts.at(-1) ?? toolId;
								const provider = `mcp:${serverId}`;

								try {
									await deleteOAuthSession(localStorage.token, provider);
									toast.success($i18n.t('OAuth session disconnected'));

									_tools.set(await getTools(localStorage.token));
									selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
									await init();
								} catch (err) {
									toast.error(err ?? $i18n.t('Failed to disconnect'));
								}
							}}
						>
							<LinkSlash className="size-3.5" />
						</button>
					</Tooltip>
				</div>
			{/if}

			{#if tools[toolId]?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
				<div class="shrink-0">
					<Tooltip content={$i18n.t('Valves')}>
						<button
							class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
							type="button"
							on:click={(e) => {
								e.stopPropagation();
								e.preventDefault();
								onShowValves({
									type: 'tool',
									id: toolId
								});
							}}
						>
							<Knobs />
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="shrink-0">
				<Switch state={tools[toolId].enabled} />
			</div>
		</button>
	{/each}
{:else}
	<div class="py-4">
		<Spinner />
	</div>
{/if}
