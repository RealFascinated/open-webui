<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	import Selector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import { models, settings, mobile } from '$lib/stores';
	import {
		ensureDefaultThinkingPreference,
		getResolvedThink,
		getThinkingEffort,
		isThinkingEnabled,
		saveUserThinkingPreference,
		THINKING_EFFORT_OPTIONS,
		type ThinkingEffort
	} from '$lib/utils/thinking';

	const i18n = getContext('i18n');

	export let selectedModels: string[] = [''];
	export let disabled = false;

	const PANEL_WIDTH = 320;
	const SIDE_OFFSET = 8;
	const VIEWPORT_MARGIN = 16;

	let effortPanelOpen = false;
	let effortCloseTimer: ReturnType<typeof setTimeout> | null = null;
	let effortTriggerElement: HTMLElement | null = null;
	let effortFlyoutEl: HTMLElement | null = null;
	let effortPanelEl: HTMLElement | null = null;

	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	}

	const canOpenEffortAsSideFlyout = () => {
		if (!effortTriggerElement) return false;

		const rect = effortTriggerElement.getBoundingClientRect();
		const spaceRight = window.innerWidth - rect.right;
		const spaceLeft = rect.left;

		return (
			spaceRight >= PANEL_WIDTH + SIDE_OFFSET + VIEWPORT_MARGIN ||
			spaceLeft >= PANEL_WIDTH + SIDE_OFFSET + VIEWPORT_MARGIN
		);
	};

	const updateEffortPanelPlacement = () => {
		if (!effortTriggerElement || !effortFlyoutEl) return;

		const rect = effortTriggerElement.getBoundingClientRect();
		const contentWidth = effortPanelEl?.offsetWidth || PANEL_WIDTH;
		const contentHeight = effortFlyoutEl.offsetHeight || 0;
		const vw = window.innerWidth;
		const vh = window.innerHeight;

		effortFlyoutEl.style.position = 'fixed';
		effortFlyoutEl.style.zIndex = '10001';
		effortFlyoutEl.style.paddingLeft = '0';
		effortFlyoutEl.style.paddingRight = '0';
		effortFlyoutEl.style.bottom = 'auto';

		if (canOpenEffortAsSideFlyout()) {
			const rightSpace = vw - rect.right;
			if (rightSpace >= contentWidth + SIDE_OFFSET) {
				effortFlyoutEl.style.left = `${rect.right}px`;
				effortFlyoutEl.style.right = 'auto';
				effortFlyoutEl.style.paddingLeft = `${SIDE_OFFSET}px`;
			} else {
				effortFlyoutEl.style.right = `${vw - rect.left}px`;
				effortFlyoutEl.style.left = 'auto';
				effortFlyoutEl.style.paddingRight = `${SIDE_OFFSET}px`;
			}
		} else {
			const left = Math.max(
				VIEWPORT_MARGIN,
				Math.min(rect.left, vw - contentWidth - VIEWPORT_MARGIN)
			);
			effortFlyoutEl.style.left = `${left}px`;
			effortFlyoutEl.style.right = 'auto';
		}

		let top = rect.top;
		if (!canOpenEffortAsSideFlyout()) {
			const belowTop = rect.bottom + SIDE_OFFSET;
			const aboveTop = rect.top - contentHeight - SIDE_OFFSET;
			if (contentHeight > 0 && belowTop + contentHeight + VIEWPORT_MARGIN > vh && aboveTop >= VIEWPORT_MARGIN) {
				top = aboveTop;
			} else if (contentHeight > 0) {
				top = belowTop;
			}
		}

		if (contentHeight > 0) {
			if (top + contentHeight + VIEWPORT_MARGIN > vh) {
				top = vh - contentHeight - VIEWPORT_MARGIN;
			}
			if (top < VIEWPORT_MARGIN) {
				top = VIEWPORT_MARGIN;
			}
		}

		effortFlyoutEl.style.top = `${top}px`;
	};

	const openEffortPanel = async () => {
		if (effortCloseTimer) {
			clearTimeout(effortCloseTimer);
			effortCloseTimer = null;
		}
		effortPanelOpen = true;
		await tick();
		updateEffortPanelPlacement();
		setTimeout(updateEffortPanelPlacement, 50);
	};

	const closeEffortPanel = () => {
		if (effortCloseTimer) clearTimeout(effortCloseTimer);
		effortCloseTimer = setTimeout(() => {
			effortPanelOpen = false;
			effortCloseTimer = null;
		}, 120);
	};

	const toggleEffortPanel = () => {
		if (effortPanelOpen) {
			if (effortCloseTimer) clearTimeout(effortCloseTimer);
			effortCloseTimer = null;
			effortPanelOpen = false;
		} else {
			openEffortPanel();
		}
	};

	$: modelId = selectedModels[0] ?? '';
	$: resolvedThink = getResolvedThink($settings);
	$: thinkingEnabled = isThinkingEnabled(resolvedThink);
	$: currentEffort = getThinkingEffort(resolvedThink);
	$: effortSuffix = thinkingEnabled ? effortLabel(currentEffort) : '';

	const onModelChange = (id: string) => {
		if (!id || selectedModels[0] === id) return;
		selectedModels = [id, ...selectedModels.slice(1)];
	};

	onMount(() => {
		ensureDefaultThinkingPreference();
	});

	const effortLabel = (effort: string) => {
		if (effort === 'low') return $i18n.t('Low');
		if (effort === 'high') return $i18n.t('High');
		if (effort === 'max') return $i18n.t('Max');
		return $i18n.t('Medium');
	};

	const setThinkingEnabled = async (enabled: boolean) => {
		await saveUserThinkingPreference(enabled ? currentEffort : false);
	};

	const setEffort = async (effort: ThinkingEffort) => {
		await saveUserThinkingPreference(effort);
	};
</script>

<svelte:window
	on:resize={() => effortPanelOpen && updateEffortPanelPlacement()}
	on:scroll|capture={() => effortPanelOpen && updateEffortPanelPlacement()}
/>

<div class="relative self-center min-w-0 {$mobile ? 'shrink' : 'w-fit shrink-0'}">
	<Selector
		id="chat-composer"
		{disabled}
		value={modelId}
		onChange={onModelChange}
		placeholder={$i18n.t('Select a model')}
		className="w-[22rem]"
		containerClassName="relative {$mobile ? 'w-full min-w-0' : 'w-fit'}"
		triggerClassName="text-sm font-medium flex items-center gap-1 rounded-xl px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
		openTriggerClassName="bg-gray-50 dark:bg-gray-850"
		truncateTrigger={$mobile}
		suffix={effortSuffix}
		placement="top"
		items={$models.map((model) => ({
			value: model.id,
			label: model.name,
			model
		}))}
	>
		<svelte:fragment slot="footer">
			<div bind:this={effortTriggerElement} class="relative">
				<button
					class="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
					type="button"
					on:mouseenter={() => canOpenEffortAsSideFlyout() && openEffortPanel()}
					on:mouseleave={closeEffortPanel}
					on:click={toggleEffortPanel}
				>
					<span class="flex-1 text-left font-medium">{$i18n.t('Effort')}</span>
					<span class="text-gray-500 dark:text-gray-400">{effortLabel(currentEffort)}</span>
					<ChevronRight className="size-3.5 shrink-0 text-gray-400" strokeWidth="2" />
				</button>

				{#if effortPanelOpen}
					<div
						use:portal
						bind:this={effortFlyoutEl}
						role="presentation"
						on:mouseenter={openEffortPanel}
						on:mouseleave={closeEffortPanel}
					>
						<div
							bind:this={effortPanelEl}
							class="w-80 max-w-[calc(100vw-2rem)] min-w-0 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-850 shadow-lg overflow-hidden"
						>
							<div class="px-3.5 pt-3 pb-2 text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
								{$i18n.t(
									'Higher effort means more thorough responses, but takes longer and uses your limits faster.'
								)}
							</div>

							<div class="px-1.5 pb-1">
								{#each THINKING_EFFORT_OPTIONS as effort (effort)}
									<button
										class="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition {currentEffort ===
										effort
											? 'text-gray-900 dark:text-white'
											: 'text-gray-700 dark:text-gray-300'}"
										on:click={() => setEffort(effort)}
										type="button"
									>
										<span class="flex-1 text-left">{effortLabel(effort)}</span>
										{#if effort === 'medium'}
											<span
												class="rounded-md bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:text-gray-400"
											>
												{$i18n.t('Default')}
											</span>
										{/if}
										{#if currentEffort === effort}
											<Check className="size-4 shrink-0" strokeWidth="2.5" />
										{/if}
									</button>
								{/each}
							</div>

							<div class="border-t border-gray-100 dark:border-gray-800 px-3.5 py-3">
								<div class="flex items-center justify-between gap-3">
									<div class="min-w-0">
										<div class="text-sm font-medium text-gray-900 dark:text-white">
											{$i18n.t('Thinking')}
										</div>
										<div class="text-xs text-gray-500 dark:text-gray-400">
											{$i18n.t('Can think for more complex tasks.')}
										</div>
									</div>
									<Switch
										state={thinkingEnabled}
										on:change={(e) => setThinkingEnabled(e.detail)}
									/>
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</svelte:fragment>
	</Selector>
</div>
