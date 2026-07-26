<script lang="ts">
	import hljs from 'highlight.js';
	import {toast} from 'svelte-sonner';
	import {getContext, onMount, tick, onDestroy} from 'svelte';
	import {config, pyodideWorker as pyodideWorkerStore} from '$lib/stores';

	import {createPyodideWorker} from '$lib/pyodide/createPyodideWorker';
	import {executeCode} from '$lib/apis/utils';
	import {copyToClipboard, initMermaid, renderMermaidDiagram, renderVegaVisualization, unescapeHtml} from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';
	import equal from 'fast-deep-equal';

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import FloppyDisk from '$lib/components/icons/FloppyDisk.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let edit = true;

	export let onSave = (_e: Event) => {};
	export let onUpdate = (_e: Event) => {};
	export let onPreview = (_e: Event) => {};

	export let save = false;
	export let run = true;
	export let preview = false;
	export let collapsed = false;

	export let token;
	export let lang = '';
	export let code = '';
	export let done = true;
	export let attributes = {};

	export let className = '';
	export let editorClassName = '';
	export let stickyButtonsClassName = 'top-0';

	let localPyodideWorker = null;

	let _code = '';
	$: if (code) {
		updateCode();
	}

	const updateCode = () => {
		_code = code;
	};

	let _token = null;

	let renderHTML = null;
	let renderError = null;

	let executing = false;

	let stdout = null;
	let stderr = null;
	let result = null;
	let files = null;

	let copied = false;
	let saved = false;

	// ── Inline artifact preview ───────────────────────────────────────
	// When lang is html/svg and detectArtifacts is on, we replace the raw
	// code block with a clickable reference card (matching Claude's UX).
	// The code view is accessed via the Preview/Code toggle in the side panel.

	$: isArtifactLang =
		lang === 'html' || lang === 'svg' || (lang === 'xml' && code.includes('<svg'));

	$: showInlinePreview = isArtifactLang;

	/** Extract <title> from HTML, fall back to 'HTML Artifact' / 'SVG Artifact'. */
	const getArtifactTitle = (src: string, language: string): string => {
		const m = src.match(/<title[^>]*>([^<]+)<\/title>/i);
		if (m) return m[1].trim();
		return language === 'svg' ? 'SVG' : 'HTML';
	};

	$: displayLang = (lang || 'text').toLowerCase();
	$: artifactTitle = getArtifactTitle(code, lang);
	$: isPythonRunnable =
		($config?.features?.enable_code_execution ?? true) &&
		(displayLang === 'python' ||
			displayLang === 'py' ||
			(lang === '' && checkPythonCode(code)));

	const collapseCodeBlock = () => {
		collapsed = !collapsed;
	};

	const saveCode = () => {
		saved = true;

		code = _code;
		onSave(code);

		setTimeout(() => {
			saved = false;
		}, 1000);
	};

	const copyCode = async () => {
		copied = true;
		await copyToClipboard(_code);

		setTimeout(() => {
			copied = false;
		}, 1000);
	};

	const previewCode = () => {
		onPreview(code);
	};

	const checkPythonCode = (str) => {
		// Check if the string contains typical Python syntax characters
		const pythonSyntax = [
			'def ',
			'else:',
			'elif ',
			'try:',
			'except:',
			'finally:',
			'yield ',
			'lambda ',
			'assert ',
			'nonlocal ',
			'del ',
			'True',
			'False',
			'None',
			' and ',
			' or ',
			' not ',
			' in ',
			' is ',
			' with '
		];

		for (let syntax of pythonSyntax) {
			if (str.includes(syntax)) {
				return true;
			}
		}

		// If none of the above conditions met, it's probably not Python code
		return false;
	};

	const executePython = async (code) => {
		result = null;
		stdout = null;
		stderr = null;

		executing = true;

		if ($config?.code?.engine === 'jupyter') {
			const output = await executeCode(localStorage.token, code).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (output) {
				if (output['stdout']) {
					stdout = output['stdout'];
					const stdoutLines = stdout.split('\n');

					for (const [_idx, line] of stdoutLines.entries()) {
						if (line.startsWith('data:image/png;base64')) {
							if (files) {
								files.push({
									type: 'image/png',
									data: line
								});
							} else {
								files = [
									{
										type: 'image/png',
										data: line
									}
								];
							}

							if (stdout.includes(`${line}\n`)) {
								stdout = stdout.replace(`${line}\n`, ``);
							} else if (stdout.includes(`${line}`)) {
								stdout = stdout.replace(`${line}`, ``);
							}
						}
					}
				}

				if (output['result']) {
					result = output['result'];
					const resultLines = result.split('\n');

					for (const [_idx, line] of resultLines.entries()) {
						if (line.startsWith('data:image/png;base64')) {
							if (files) {
								files.push({
									type: 'image/png',
									data: line
								});
							} else {
								files = [
									{
										type: 'image/png',
										data: line
									}
								];
							}

							if (result.includes(`${line}\n`)) {
								result = result.replace(`${line}\n`, ``);
							} else if (result.includes(`${line}`)) {
								result = result.replace(`${line}`, ``);
							}
						}
					}
				}

				if (output['stderr']) stderr = output['stderr'];
			}

			executing = false;
		} else {
			executePythonAsWorker(code);
		}
	};

	const executePythonAsWorker = async (code) => {
		let packages = [
			/\bimport\s+requests\b|\bfrom\s+requests\b/.test(code) ? 'requests' : null,
			/\bimport\s+bs4\b|\bfrom\s+bs4\b/.test(code) ? 'beautifulsoup4' : null,
			/\bimport\s+numpy\b|\bfrom\s+numpy\b/.test(code) ? 'numpy' : null,
			/\bimport\s+pandas\b|\bfrom\s+pandas\b/.test(code) ? 'pandas' : null,
			/\bimport\s+matplotlib\b|\bfrom\s+matplotlib\b/.test(code) ? 'matplotlib' : null,
			/\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
			/\bimport\s+sklearn\b|\bfrom\s+sklearn\b/.test(code) ? 'scikit-learn' : null,
			/\bimport\s+scipy\b|\bfrom\s+scipy\b/.test(code) ? 'scipy' : null,
			/\bimport\s+re\b|\bfrom\s+re\b/.test(code) ? 'regex' : null,
			/\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
			/\bimport\s+sympy\b|\bfrom\s+sympy\b/.test(code) ? 'sympy' : null,
			/\bimport\s+tiktoken\b|\bfrom\s+tiktoken\b/.test(code) ? 'tiktoken' : null,
			/\bimport\s+pytz\b|\bfrom\s+pytz\b/.test(code) ? 'pytz' : null
		].filter(Boolean);

		console.log(packages);

		// Reuse the shared Pyodide worker when code interpreter is active,
		// so files written here are immediately visible in PyodideFileNav.
		// Otherwise fall back to a throwaway worker.
		const sharedWorker = $pyodideWorkerStore;
		const isShared = !!sharedWorker;
		const worker = sharedWorker ?? createPyodideWorker();

		if (!isShared) {
			localPyodideWorker = worker;
		}

		worker.postMessage({
			id: id,
			code: code,
			packages: packages
		});

		const timeoutId = setTimeout(() => {
			if (executing) {
				executing = false;
				stderr = 'Execution Time Limit Exceeded';
				if (!isShared) {
					worker.terminate();
					localPyodideWorker = null;
				}
			}
		}, 60000);

		const handler = (event: Event) => {
			// Ignore messages from other requests on the shared worker
			if (event.data?.id !== id) return;

			console.log('pyodideWorker.onmessage', event);
			const { id: _id, ...data } = event.data;

			console.log(_id, data);

			if (data['stdout']) {
				stdout = data['stdout'];
				const stdoutLines = stdout.split('\n');

				for (const [_idx, line] of stdoutLines.entries()) {
					if (line.startsWith('data:image/png;base64')) {
						if (files) {
							files.push({
								type: 'image/png',
								data: line
							});
						} else {
							files = [
								{
									type: 'image/png',
									data: line
								}
							];
						}

						if (stdout.includes(`${line}\n`)) {
							stdout = stdout.replace(`${line}\n`, ``);
						} else if (stdout.includes(`${line}`)) {
							stdout = stdout.replace(`${line}`, ``);
						}
					}
				}
			}

			if (data['result']) {
				result = data['result'];
				const resultLines = result.split('\n');

				for (const [_idx, line] of resultLines.entries()) {
					if (line.startsWith('data:image/png;base64')) {
						if (files) {
							files.push({
								type: 'image/png',
								data: line
							});
						} else {
							files = [
								{
									type: 'image/png',
									data: line
								}
							];
						}

						if (result.startsWith(`${line}\n`)) {
							result = result.replace(`${line}\n`, ``);
						} else if (result.startsWith(`${line}`)) {
							result = result.replace(`${line}`, ``);
						}
					}
				}
			}

			if (data['stderr']) stderr = data['stderr'];
			if (data['result']) result = data['result'];

			clearTimeout(timeoutId);
			worker.removeEventListener('message', handler);
			executing = false;

			// Signal PyodideFileNav to auto-refresh after execution
			window.dispatchEvent(new Event('pyodide:files'));
		};

		worker.addEventListener('message', handler);

		worker.onerror = (event: Event) => {
			console.log('pyodideWorker.onerror', event);
			clearTimeout(timeoutId);
			worker.removeEventListener('message', handler);
			executing = false;
		};
	};

	let mermaid = null;
	const renderMermaid = async (code) => {
		if (!mermaid) {
			mermaid = await initMermaid();
		}
		return await renderMermaidDiagram(mermaid, code);
	};

	const render = async () => {
		onUpdate(token);
		if (lang === 'mermaid' && (token?.raw ?? '').slice(-4).includes('```')) {
			try {
				renderHTML = await renderMermaid(code);
			} catch (error) {
				console.error('Failed to render mermaid diagram:', error);
				const errorMsg = error instanceof Error ? error.message : String(error);
				renderError = $i18n.t('Failed to render diagram') + `: ${errorMsg}`;
				renderHTML = null;
			}
		} else if (
			(lang === 'vega' || lang === 'vega-lite') &&
			(token?.raw ?? '').slice(-4).includes('```')
		) {
			try {
				renderHTML = await renderVegaVisualization(code, lang);
			} catch (error) {
				console.error('Failed to render Vega visualization:', error);
				const errorMsg = error instanceof Error ? error.message : String(error);
				renderError = $i18n.t('Failed to render visualization') + `: ${errorMsg}`;
				renderHTML = null;
			}
		}
	};

	$: if (token) {
		if (token.text !== _token?.text || token.raw !== _token?.raw) {
			_token = token;
		} else if (!equal(token, _token)) {
			_token = token;
		}
	}

	$: if (_token) {
		render();
	}

	$: if (attributes) {
		onAttributesUpdate();
	}

	const onAttributesUpdate = () => {
		if (attributes?.output) {
			try {
				const output = JSON.parse(unescapeHtml(attributes.output));
				stdout = output.stdout;
				stderr = output.stderr;
				result = output.result;
			} catch (error) {
				console.error('Error:', error);
			}
		}
	};

	onMount(async () => {
		if (token) {
			onUpdate(token);
		}
	});

	onDestroy(() => {
		if (localPyodideWorker) {
			localPyodideWorker.terminate();
			localPyodideWorker = null;
		}
	});
</script>

<div>
	<div class="relative {className} flex flex-col" dir="ltr">
		{#if ['mermaid', 'vega', 'vega-lite'].includes(lang)}
			{#if renderHTML}
				<SvgPanZoom
					className=" rounded-2xl max-h-fit overflow-hidden"
					svg={renderHTML}
					content={_token.text}
				/>
			{:else}
				<div class="p-3">
					{#if renderError}
						<div
							class="flex gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-2xl mb-2"
						>
							{renderError}
						</div>
					{/if}
					<pre>{code}</pre>
				</div>
			{/if}
	{:else if showInlinePreview}
		<!-- ── Inline artifact reference card (Claude-style) ─────────── -->
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
		<div
			class="group w-full flex items-center gap-3 px-3.5 py-3 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition-colors cursor-pointer my-1"
			on:click={() => onPreview(code)}
		>
			<!-- Icon -->
			<div class="shrink-0 flex items-center justify-center size-8 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
				<Cube className="size-4" />
			</div>

			<!-- Title + type -->
			<div class="flex-1 min-w-0">
				<div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate leading-snug">
					{artifactTitle}
				</div>
				<div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5 leading-none">
					{lang === 'svg' ? 'SVG image' : 'HTML page'}
				</div>
			</div>

			<!-- Chevron -->
			<div class="shrink-0 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors">
				<svg xmlns="http://www.w3.org/2000/svg" class="size-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"></path>
				</svg>
			</div>
		</div>
	{:else}
		<div
			class="code-block my-1.5 rounded-xl border border-gray-200/90 bg-[#f6f8fa] dark:border-gray-800 dark:bg-[#0d1117] {editorClassName}"
		>
			<div
				class="flex items-center justify-between gap-3 border-b border-gray-200/80 bg-[#eef1f4] px-3 py-2 dark:border-gray-800/80 dark:bg-[#161b22]"
			>
				<Tooltip content={displayLang} placement="top-start">
					<span
						class="max-w-[10rem] truncate rounded-md border border-gray-200/80 bg-white/80 px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide text-gray-600 dark:border-gray-700 dark:bg-gray-900/70 dark:text-gray-300"
					>
						{displayLang}
					</span>
				</Tooltip>

				<div class="flex shrink-0 items-center gap-0.5">
					<Tooltip content={collapsed ? $i18n.t('Expand') : $i18n.t('Collapse')}>
						<button
							class="code-block-action"
							aria-label={collapsed ? $i18n.t('Expand') : $i18n.t('Collapse')}
							on:click={collapseCodeBlock}
						>
							{#if collapsed}
								<ChevronDown className="size-3.5" strokeWidth="2" />
							{:else}
								<ChevronUp className="size-3.5" strokeWidth="2" />
							{/if}
						</button>
					</Tooltip>

					{#if isPythonRunnable}
						{#if executing}
							<span class="code-block-action cursor-not-allowed opacity-60" aria-live="polite">
								<Spinner className="size-3.5" />
							</span>
						{:else if run}
							<Tooltip content={$i18n.t('Run')}>
								<button
									class="code-block-action code-block-action-run"
									aria-label={$i18n.t('Run')}
									on:click={async () => {
										code = _code;
										await tick();
										executePython(code);
									}}
								>
									<CommandLine className="size-3.5" strokeWidth="2" />
								</button>
							</Tooltip>
						{/if}
					{/if}

					{#if save}
						<Tooltip content={saved ? $i18n.t('Saved') : $i18n.t('Save')}>
							<button
								class="code-block-action"
								aria-label={saved ? $i18n.t('Saved') : $i18n.t('Save')}
								on:click={saveCode}
							>
								{#if saved}
									<Check className="size-3.5 text-emerald-500" strokeWidth="2" />
								{:else}
									<FloppyDisk className="size-3.5" strokeWidth="2" />
								{/if}
							</button>
						</Tooltip>
					{/if}

					{#if preview && ['html', 'svg'].includes(lang)}
						<Tooltip content={$i18n.t('Preview')}>
							<button
								class="code-block-action"
								aria-label={$i18n.t('Preview')}
								on:click={previewCode}
							>
								<Cube className="size-3.5" />
							</button>
						</Tooltip>
					{/if}

					<Tooltip content={copied ? $i18n.t('Copied') : $i18n.t('Copy')}>
						<button class="code-block-action" aria-label={$i18n.t('Copy')} on:click={copyCode}>
							{#if copied}
								<Check className="size-3.5 text-emerald-500" strokeWidth="2" />
							{:else}
								<DocumentDuplicate className="size-3.5" strokeWidth="2" />
							{/if}
						</button>
					</Tooltip>
				</div>
			</div>

			{#if !collapsed}
				{#if edit}
					<div class="code-block-editor">
						<CodeEditor
							value={code}
							{id}
							{lang}
							onSave={() => {
								saveCode();
							}}
							onChange={(value) => {
								_code = value;
							}}
						/>
					</div>
				{:else}
					<pre
						class="code-block-pre hljs m-0 overflow-x-auto px-4 py-3.5 text-sm leading-6"
						class:code-block-pre-output={executing || stdout || stderr || result}
					><code class="language-{lang} whitespace-pre">
							{#if !done}
								{code}
							{:else if lang && hljs.getLanguage(lang)}
								<!-- eslint-disable-next-line svelte/no-at-html-tags -->
								{@html hljs.highlight(code, {
									language: lang,
									ignoreIllegals: true
								}).value}
							{:else}
								{code}
							{/if}</code></pre>
				{/if}
			{:else}
				<div class="px-4 py-3 text-xs italic text-gray-500 dark:text-gray-400">
					{$i18n.t('{{COUNT}} hidden lines', {
						COUNT: code.split('\n').length
					})}
				</div>
			{/if}

			{#if !collapsed}
				<div
					id="plt-canvas-{id}"
					class="max-w-full overflow-x-auto border-t border-gray-200/80 scrollbar-hidden dark:border-gray-800/80"
				></div>

				{#if executing || stdout || stderr || result || files}
					<div
						class="flex flex-col gap-2 border-t border-gray-200/80 bg-[#eef1f4] px-4 py-3 text-sm dark:border-gray-800/80 dark:bg-[#161b22]"
					>
						{#if executing}
							<div>
								<div class="mb-1 text-[10px] font-medium uppercase tracking-wider text-gray-500">
									{$i18n.t('STDOUT/STDERR')}
								</div>
								<div class="text-sm text-gray-700 dark:text-gray-300">{$i18n.t('Running...')}</div>
							</div>
						{:else}
							{#if stdout || stderr}
								<div>
									<div class="mb-1 text-[10px] font-medium uppercase tracking-wider text-gray-500">
										{$i18n.t('STDOUT/STDERR')}
									</div>
									<div
										class="overflow-y-auto whitespace-pre-wrap font-mono text-xs text-gray-800 dark:text-gray-200 {stdout?.split('\n')?.length > 100
											? 'max-h-96'
											: ''}"
									>
										{stdout || stderr}
									</div>
								</div>
							{/if}
							{#if result || files}
								<div>
									<div class="mb-1 text-[10px] font-medium uppercase tracking-wider text-gray-500">
										{$i18n.t('RESULT')}
									</div>
									{#if result}
										<div class="font-mono text-xs text-gray-800 dark:text-gray-200">{`${JSON.stringify(result)}`}</div>
									{/if}
									{#if files}
										<div class="flex flex-col gap-2">
											{#each files as file}
												{#if file.type.startsWith('image')}
													<img src={file.data} alt="Output" class="max-w-[36rem] w-full" />
												{/if}
											{/each}
										</div>
									{/if}
								</div>
							{/if}
						{/if}
					</div>
				{/if}
			{/if}
		</div>
		{/if}
	</div>
</div>

<style>
	.code-block-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.5rem;
		padding: 0.375rem;
		color: rgb(107 114 128);
		transition:
			color 150ms ease,
			background-color 150ms ease;
	}

	:global(.dark) .code-block-action {
		color: rgb(156 163 175);
	}

	.code-block-action:hover {
		background-color: rgb(229 231 235 / 0.7);
		color: rgb(31 41 55);
	}

	:global(.dark) .code-block-action:hover {
		background-color: rgb(55 65 81 / 0.7);
		color: rgb(243 244 246);
	}

	.code-block-action-run:hover {
		background-color: rgb(209 250 229 / 0.8);
		color: rgb(4 120 87);
	}

	:global(.dark) .code-block-action-run:hover {
		background-color: rgb(6 78 59 / 0.45);
		color: rgb(110 231 183);
	}

	.code-block :global(pre.hljs),
	.code-block-pre {
		background: transparent !important;
	}

	.code-block-editor :global(.cm-editor) {
		background: transparent !important;
	}

	.code-block-editor :global(.cm-scroller) {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono',
			'Courier New', monospace;
	}

	.code-block-pre-output {
		border-bottom-left-radius: 0;
		border-bottom-right-radius: 0;
	}
</style>
