<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { fly } from 'svelte/transition';

	import { user, tools as _tools, skills as _skills, toolServers } from '$lib/stores';

	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';

	import Knobs from '$lib/components/icons/Knobs.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import Keyframes from '$lib/components/icons/Keyframes.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Terminal from '$lib/components/icons/Terminal.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import MenuFlyoutPanel from './MenuFlyoutPanel.svelte';
	import ToolsMenuPanel from './ToolsMenuPanel.svelte';

	const i18n = getContext('i18n');

	export let tab = '';
	export let rootOnly = false;
	export let rootSection: 'all' | 'nav' | 'toggles' = 'all';
	export let active = false;
	export let activeSubmenu: string | null = null;

	export let selectedToolIds: string[] = [];
	export let selectedSkillIds: string[] = [];
	export const selectedModels: string[] = [];

	export let toggleFilters: { id: string; name: string; description?: string; icon?: string }[] =
		[];
	export let selectedFilterIds: string[] = [];

	export let showImageGenerationButton = false;
	export let imageGenerationEnabled = false;
	export let showCodeInterpreterButton = false;
	export let codeInterpreterEnabled = false;

	export let onShowValves: (...args: unknown[]) => unknown;

	let tools = null;
	let skills = null;

	let toolsTriggerElement: HTMLElement | null = null;
	let toolsFlyoutPanel: MenuFlyoutPanel | null = null;
	let toolsCloseTimer: ReturnType<typeof setTimeout> | null = null;

	$: toolsFlyoutOpen = activeSubmenu === 'tools';
	$: toolsMenuCount =
		($_tools ?? []).length + ($toolServers ?? []).filter((server) => server.info).length;
	$: showToolsNavButton = toolsMenuCount > 0 || tools !== null;

	$: if (!active) {
		if (activeSubmenu === 'tools') activeSubmenu = null;
	}

	const openToolsFlyout = () => {
		if (toolsCloseTimer) {
			clearTimeout(toolsCloseTimer);
			toolsCloseTimer = null;
		}
		activeSubmenu = 'tools';
		toolsFlyoutPanel?.updatePlacement();
	};

	const closeToolsFlyout = () => {
		if (toolsCloseTimer) clearTimeout(toolsCloseTimer);
		toolsCloseTimer = setTimeout(() => {
			if (activeSubmenu === 'tools') activeSubmenu = null;
			toolsCloseTimer = null;
		}, 120);
	};

	const toggleToolsFlyout = () => {
		if (toolsFlyoutOpen) {
			if (toolsCloseTimer) clearTimeout(toolsCloseTimer);
			toolsCloseTimer = null;
			activeSubmenu = null;
		} else {
			openToolsFlyout();
		}
	};

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

		selectedToolIds = selectedToolIds.filter((id) => Object.keys(tools).includes(id));

		if ($_skills === null) {
			await _skills.set(await getSkills(localStorage.token));
		}

		if ($_skills) {
			skills = $_skills
				.filter((skill) => skill.is_active)
				.reduce((a, skill) => {
					a[skill.id] = {
						name: skill.name,
						description: skill.description,
						enabled: selectedSkillIds.includes(skill.id),
						...skill
					};
					return a;
				}, {});
		}

		selectedSkillIds = selectedSkillIds.filter((id) => Object.keys(skills ?? {}).includes(id));
	};
</script>

{#if rootOnly && tab === ''}
	<div in:fly={{ x: -20, duration: 150 }}>
		{#if rootSection === 'all' || rootSection === 'nav'}
			{#if showToolsNavButton}
				<div bind:this={toolsTriggerElement} class="relative">
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						type="button"
						on:mouseenter={openToolsFlyout}
						on:mouseleave={closeToolsFlyout}
						on:click={toggleToolsFlyout}
					>
						<Wrench />

						<div class="flex items-center w-full justify-between">
							<div class="line-clamp-1">
								{$i18n.t('Tools')}
								<span class="ml-0.5 text-gray-500">{toolsMenuCount}</span>
							</div>

							<div class="text-gray-500">
								<ChevronRight />
							</div>
						</div>
					</button>

					<MenuFlyoutPanel
						bind:this={toolsFlyoutPanel}
						show={toolsFlyoutOpen}
						anchor={toolsTriggerElement}
						onMouseEnter={openToolsFlyout}
						onMouseLeave={closeToolsFlyout}
					>
						<ToolsMenuPanel
							active={toolsFlyoutOpen && active}
							bind:selectedToolIds
							{onShowValves}
						/>
					</MenuFlyoutPanel>
				</div>
			{:else if tools === null && (rootSection === 'all' || rootSection === 'nav')}
				<div class="py-4">
					<Spinner />
				</div>
			{/if}

			{#if skills && Object.keys(skills).length > 0}
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
					type="button"
					on:click={() => {
						activeSubmenu = null;
						tab = 'skills';
					}}
				>
					<Keyframes className="size-4" strokeWidth="1.75" />

					<div class="flex items-center w-full justify-between">
						<div class="line-clamp-1">
							{$i18n.t('Skills')}
							<span class="ml-0.5 text-gray-500">{Object.keys(skills).length}</span>
						</div>

						<div class="text-gray-500">
							<ChevronRight />
						</div>
					</div>
				</button>
			{/if}
		{/if}

		{#if rootSection === 'all' || rootSection === 'toggles'}
		{#if toggleFilters && toggleFilters.length > 0}
			{#each toggleFilters.sort( (a, b) => a.name.localeCompare( b.name, undefined, { sensitivity: 'base' } ) ) as filter (filter.id)}
				<Tooltip content={filter?.description} placement="top-start">
					<button
						class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
						type="button"
						on:click={() => {
							if (selectedFilterIds.includes(filter.id)) {
								selectedFilterIds = selectedFilterIds.filter((id) => id !== filter.id);
							} else {
								selectedFilterIds = [...selectedFilterIds, filter.id];
							}
						}}
					>
						<div class="flex-1 truncate">
							<div class="flex flex-1 gap-2 items-center">
								<div class="shrink-0">
									{#if filter?.icon}
										<div class="size-4 items-center flex justify-center">
											<img
												src={filter.icon}
												class="size-3.5 {filter.icon.includes('data:image/svg')
													? 'dark:invert-[80%]'
													: ''}"
												style="fill: currentColor;"
												alt={filter.name}
											/>
										</div>
									{:else}
										<Sparkles className="size-4" strokeWidth="1.75" />
									{/if}
								</div>

								<div class="truncate">{filter?.name}</div>
							</div>
						</div>

						{#if filter?.has_user_valves && ($user?.role === 'admin' || ($user?.permissions?.chat?.valves ?? true))}
							<div class="shrink-0">
								<Tooltip content={$i18n.t('Valves')}>
									<button
										class="self-center w-fit text-sm text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition rounded-full"
										type="button"
										on:click={(e) => {
											e.stopPropagation();
											e.preventDefault();
											onShowValves({
												type: 'function',
												id: filter.id
											});
										}}
									>
										<Knobs />
									</button>
								</Tooltip>
							</div>
						{/if}

						<div class="shrink-0">
							<Switch
								state={selectedFilterIds.includes(filter.id)}
								on:change={async () => {
									await tick();
								}}
							/>
						</div>
					</button>
				</Tooltip>
			{/each}
		{/if}

		{#if showImageGenerationButton}
			<Tooltip content={$i18n.t('Generate an image')} placement="top-start">
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
					aria-pressed={imageGenerationEnabled}
					aria-label={imageGenerationEnabled
						? $i18n.t('Disable Image Generation')
						: $i18n.t('Enable Image Generation')}
					type="button"
					on:click={() => {
						imageGenerationEnabled = !imageGenerationEnabled;
					}}
				>
					<div class="flex-1 truncate">
						<div class="flex flex-1 gap-2 items-center">
							<div class="shrink-0">
								<Photo className="size-4" strokeWidth="1.5" />
							</div>

							<div class="truncate">{$i18n.t('Image')}</div>
						</div>
					</div>

					<div class="shrink-0">
						<Switch
							state={imageGenerationEnabled}
							on:change={async () => {
								await tick();
							}}
						/>
					</div>
				</button>
			</Tooltip>
		{/if}

		{#if showCodeInterpreterButton}
			<Tooltip content={$i18n.t('Execute code for analysis')} placement="top-start">
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
					aria-pressed={codeInterpreterEnabled}
					aria-label={codeInterpreterEnabled
						? $i18n.t('Disable Code Interpreter')
						: $i18n.t('Enable Code Interpreter')}
					type="button"
					on:click={() => {
						codeInterpreterEnabled = !codeInterpreterEnabled;
					}}
				>
					<div class="flex-1 truncate">
						<div class="flex flex-1 gap-2 items-center">
							<div class="shrink-0">
								<Terminal className="size-3.5" strokeWidth="1.75" />
							</div>

							<div class="truncate">{$i18n.t('Code Interpreter')}</div>
						</div>
					</div>

					<div class="shrink-0">
						<Switch
							state={codeInterpreterEnabled}
							on:change={async () => {
								await tick();
							}}
						/>
					</div>
				</button>
			</Tooltip>
		{/if}
		{/if}
	</div>
{:else if !rootOnly && tab === 'skills' && skills}
	<div in:fly={{ x: 20, duration: 150 }}>
		<button
			class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
			type="button"
			on:click={() => {
				tab = '';
			}}
		>
			<ChevronLeft />

			<div class="flex items-center w-full justify-between">
				<div>
					{$i18n.t('Skills')}
					<span class="ml-0.5 text-gray-500">{Object.keys(skills).length}</span>
				</div>
			</div>
		</button>

		{#each Object.keys(skills) as skillId}
			<button
				class="relative flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50"
				type="button"
				on:click={async () => {
					skills[skillId].enabled = !skills[skillId].enabled;

					const state = skills[skillId].enabled;
					await tick();

					if (state) {
						selectedSkillIds = [...selectedSkillIds, skillId];
					} else {
						selectedSkillIds = selectedSkillIds.filter((id) => id !== skillId);
					}
				}}
			>
				<div class="flex-1 truncate">
					<div class="flex flex-1 gap-2 items-center">
						<Tooltip content={skills[skillId]?.name ?? ''} placement="top">
							<div class="shrink-0">
								<Keyframes className="size-4" strokeWidth="1.75" />
							</div>
						</Tooltip>
						<Tooltip content={skills[skillId]?.description ?? ''} placement="top-start">
							<div class="truncate">{skills[skillId].name}</div>
						</Tooltip>
					</div>
				</div>

				<div class="shrink-0">
					<Switch state={skills[skillId].enabled} />
				</div>
			</button>
		{/each}
	</div>
{/if}
