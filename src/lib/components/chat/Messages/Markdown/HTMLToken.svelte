<script lang="ts">
	import DOMPurify from 'dompurify';
	import type { Token } from 'marked';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { settings } from '$lib/stores';
	import { parseAntArtifacts } from '$lib/utils';
	import AntArtifactCard from './AntArtifactCard.svelte';

	export let id: string;
	export let token: Token;
	export let onPreview: Function = () => {};

	let html: string | null = null;

	$: text = token.type === 'html' ? token?.text : null;
	$: html = text ? DOMPurify.sanitize(text) : null;

	// Fallback for legacy/partial html tokens that still contain antArtifact
	$: antArtifacts = text ? parseAntArtifacts(text) : [];
	$: isAntArtifact = antArtifacts.length > 0;

	$: visualizationMatch = text?.match(/<visualization\s+([^>]*)>([\s\S]*?)<\/visualization>/i);
	$: visualizationAttrs = visualizationMatch?.[1] ?? '';
	$: visualizationContent = visualizationMatch?.[2]?.trim() ?? '';
	$: visualizationType = visualizationAttrs.match(/type="([^"]+)"/i)?.[1] ?? 'svg';
	$: visualizationHeight = visualizationAttrs.match(/height="(\d+)"/i)?.[1] ?? '300';
	$: isVisualization = Boolean(visualizationMatch);
</script>

{#if token.type === 'html' && isAntArtifact}
	{#each antArtifacts as artifact}
		<AntArtifactCard {artifact} {onPreview} />
	{/each}
{:else if token.type === 'html' && isVisualization}
	{#if visualizationType === 'html'}
		<iframe
			class="w-full my-2 rounded-xl border border-gray-100 dark:border-gray-800"
			style="height: {visualizationHeight}px"
			title="Visualization"
			srcdoc={visualizationContent}
			sandbox="allow-scripts allow-downloads{($settings?.iframeSandboxAllowForms ?? false)
				? ' allow-forms'
				: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}"
			referrerpolicy="strict-origin-when-cross-origin"
		></iframe>
	{:else}
		<div class="my-2 w-full overflow-x-auto">
			{@html DOMPurify.sanitize(visualizationContent, { USE_PROFILES: { svg: true, svgFilters: true } })}
		</div>
	{/if}
{:else if token.type === 'html'}
	{#if html && html.includes('<video')}
		{@const video = html.match(/<video[^>]*>([\s\S]*?)<\/video>/)}
		{@const videoSrc = video && video[1]}
		{#if videoSrc}
			<!-- svelte-ignore a11y-media-has-caption -->
			<video
				class="w-full my-2"
				src={videoSrc.replaceAll('&amp;', '&')}
				title="Video player"
				frameborder="0"
				referrerpolicy="strict-origin-when-cross-origin"
				controls
				allowfullscreen
			></video>
		{:else}
			{token.text}
		{/if}
	{:else if html && html.includes('<audio')}
		{@const audio = html.match(/<audio[^>]*>([\s\S]*?)<\/audio>/)}
		{@const audioSrc = audio && audio[1]}
		{#if audioSrc}
			<!-- svelte-ignore a11y-media-has-caption -->
			<audio
				class="w-full my-2"
				src={audioSrc.replaceAll('&amp;', '&')}
				title="Audio player"
				controls
			></audio>
		{:else}
			{token.text}
		{/if}
	{:else if token.text && token.text.match(/<iframe\s+[^>]*src="https:\/\/www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?[^"]*)?"[^>]*><\/iframe>/)}
		{@const match = token.text.match(
			/<iframe\s+[^>]*src="https:\/\/www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?[^"]*)?"[^>]*><\/iframe>/
		)}
		{@const ytId = match && match[1]}
		{#if ytId}
			<iframe
				class="w-full aspect-video my-2"
				src={`https://www.youtube.com/embed/${ytId}`}
				title="YouTube video player"
				frameborder="0"
				allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
				referrerpolicy="strict-origin-when-cross-origin"
				allowfullscreen
			>
			</iframe>
		{/if}
	{:else if token.text && token.text.includes('<iframe')}
		{@const match = token.text.match(/<iframe\s+[^>]*src="([^"]+)"[^>]*><\/iframe>/)}
		{@const iframeSrc = match && match[1]}
		{#if iframeSrc}
			<iframe
				class="w-full my-2"
				src={iframeSrc}
				title="Embedded content"
				frameborder="0"
				sandbox
				on:load={(e) => {
					try {
						e.currentTarget.style.height =
							e.currentTarget.contentWindow.document.body.scrollHeight + 20 + 'px';
					} catch {}
				}}
			></iframe>
		{:else}
			{token.text}
		{/if}
	{:else if token.text && token.text.includes('<status')}
		{@const match = token.text.match(/<status title="([^"]+)" done="(true|false)" ?\/?>/)}
		{@const statusTitle = match && match[1]}
		{@const statusDone = match && match[2] === 'true'}
		{#if statusTitle}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{statusDone === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 line-clamp-1 text-wrap"
				>
					{statusTitle}
				</div>
			</div>
		{:else}
			{token.text}
		{/if}
	{:else if token.text.includes(`<file type="html"`)}
		{@const match = token.text.match(/<file type="html" id="([^"]+)"/)}
		{@const fileId = match && match[1]}
		{#if fileId}
			<iframe
				class="w-full my-2"
				src={`${WEBUI_BASE_URL}/api/v1/files/${fileId}/content/html`}
				title="Content"
				frameborder="0"
				sandbox="allow-scripts allow-downloads{($settings?.iframeSandboxAllowForms ?? false)
					? ' allow-forms'
					: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}"
				referrerpolicy="strict-origin-when-cross-origin"
				allowfullscreen
				width="100%"
				on:load={(e) => {
					try {
						e.currentTarget.style.height =
							e.currentTarget.contentWindow.document.body.scrollHeight + 20 + 'px';
					} catch {}
				}}
			></iframe>
		{/if}
	{:else if token.text.trim().match(/^<br\s*\/?>$/i)}
		<br />
	{:else}
		{token.text}
	{/if}
{/if}
