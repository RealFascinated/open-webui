<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Image from '$lib/components/common/Image.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';
	import { settings } from '$lib/stores';
	import type { MessageRichFields } from '$lib/utils/messageRichContent';
	import { isQuestionInMessage } from '$lib/utils/messageRichContent';

	import WeatherCard from './WeatherCard.svelte';
	import OptionsCard from './OptionsCard.svelte';
	import CurrencyCard from './CurrencyCard.svelte';
	import MapCard from './MapCard.svelte';
	import SportsCard from './SportsCard.svelte';
	import RichCardSource from './RichCardSource.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let message: MessageRichFields & { id: string; content?: string };
	export let assistantText = '';
	export let isLastMessage = false;
	export let showQuestionOnOptions = true;
	export let toolSourcePrefix = '';
	export let autoScroll = true;

	$: mediaFiles =
		message.files?.filter((file: string) => ['image', 'file'].includes(file.type ?? '')) ?? [];
	$: hasMedia = mediaFiles.length > 0;
	$: hasEmbeds = Boolean(message.embeds?.length);
	$: richItemCount =
		(hasMedia ? 1 : 0) +
		(hasEmbeds ? 1 : 0) +
		(message.weather ? 1 : 0) +
		(message.currency ? 1 : 0) +
		(message.map ? 1 : 0) +
		(message.sports ? 1 : 0) +
		(message.options ? 1 : 0);
	$: showOptionsQuestion =
		showQuestionOnOptions &&
		Boolean(message.options?.question) &&
		!isQuestionInMessage(message.options?.question ?? '', assistantText);

	let hasScrolledIntoView = false;

	const isNearBottom = () => {
		const container = document.getElementById('messages-container');
		if (!container) return true;

		return container.scrollHeight - container.scrollTop <= container.clientHeight + 150;
	};

	const scrollIntoViewIfNeeded = async () => {
		if (!isLastMessage || hasScrolledIntoView || !autoScroll) return;
		if (!isNearBottom()) return;

		await tick();
		setTimeout(() => {
			const element = document.getElementById(`${message.id}-rich-results`);
			if (!element) return;
			element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
			hasScrolledIntoView = true;
		}, 100);
	};

	onMount(() => {
		scrollIntoViewIfNeeded();
	});

	$: if (isLastMessage && richItemCount > 0) {
		scrollIntoViewIfNeeded();
	}

	const getToolSourceId = (toolName: string) =>
		toolSourcePrefix ? `${toolSourcePrefix}-${toolName}` : '';
</script>

<div
	id="{message.id}-rich-results"
	class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-850 space-y-2"
>
	{#if richItemCount > 1}
		<div class="text-xs font-medium text-gray-400 dark:text-gray-500">
			{$i18n.t('Results')}
		</div>
	{/if}

	{#if hasMedia}
		<div
			class="w-full flex overflow-x-auto gap-2 flex-wrap"
			dir={$settings?.chatDirection ?? 'auto'}
		>
			{#each mediaFiles as file}
				<div>
					{#if file.type === 'image' || (file?.content_type ?? '').startsWith('image/')}
						<Image src={file.url} alt={message.content ?? ''} />
					{:else}
						<FileItem
							item={file}
							url={file.url}
							name={file.name}
							type={file.type}
							size={file?.size}
							small={true}
						/>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	{#if hasEmbeds}
		<div class="w-full flex overflow-x-auto gap-2 flex-wrap" id={`${message.id}-embeds-container`}>
			{#each message.embeds ?? [] as embed, idx}
				<div class="my-2 w-full" id={`${message.id}-embeds-${idx}`}>
					<FullHeightIframe
						src={embed}
						allowScripts={true}
						allowForms={true}
						allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
						allowPopups={true}
					/>
				</div>
			{/each}
		</div>
	{/if}

	{#if message.weather}
		<RichCardSource toolName="weather_fetch" sourceId={getToolSourceId('weather_fetch')} />
		<WeatherCard weather={message.weather} />
	{/if}

	{#if message.currency}
		<RichCardSource toolName="currency_convert" sourceId={getToolSourceId('currency_convert')} />
		<CurrencyCard currency={message.currency} disabled={!isLastMessage} />
	{/if}

	{#if message.map}
		<RichCardSource toolName="map_display" sourceId={getToolSourceId('map_display')} />
		<MapCard map={message.map} />
	{/if}

	{#if message.sports}
		<RichCardSource toolName="sports_scores" sourceId={getToolSourceId('sports_scores')} />
		<SportsCard sports={message.sports} />
	{/if}

	{#if message.options}
		<RichCardSource toolName="present_options" sourceId={getToolSourceId('present_options')} />
		<OptionsCard
			options={message.options}
			disabled={!isLastMessage}
			showQuestion={showOptionsQuestion}
		/>
	{/if}
</div>
