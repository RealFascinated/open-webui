import { describe, expect, it } from 'vitest';

import {
	hasAntArtifactActivity,
	hasAntArtifactOpenTag,
	hasStreamingAntArtifact,
	parseAntArtifacts,
	parseAntArtifactsForStream,
	scanAntArtifactBlocks
} from './ant-artifact';
import { buildStreamingHtmlPreview, stripStreamingScripts } from './artifact-stream-preview';
import { artifactToPanelContent } from './artifact-panel';

describe('ant-artifact streaming parser', () => {
	it('parses a complete artifact block', () => {
		const text = `<antArtifact identifier="demo" type="text/html" title="Demo">
<p>Hello</p>
</antArtifact>`;

		expect(parseAntArtifacts(text)).toHaveLength(1);
		expect(parseAntArtifacts(text)[0]).toMatchObject({
			identifier: 'demo',
			title: 'Demo',
			complete: true,
			content: '<p>Hello</p>'
		});
	});

	it('parses an in-progress artifact block at the end of the stream', () => {
		const text = `<antArtifact identifier="demo" type="text/html" title="Demo">
<div class="hero">`;

		const blocks = parseAntArtifactsForStream(text);
		expect(blocks).toHaveLength(1);
		expect(blocks[0]).toMatchObject({
			identifier: 'demo',
			complete: false,
			content: '<div class="hero">'
		});
		expect(parseAntArtifacts(text)).toHaveLength(0);
	});

	it('detects activity before the closing tag arrives', () => {
		const partial = `<antArtifact identifier="demo" type="text/html" title="Demo">
<body>`;

		expect(hasAntArtifactOpenTag(partial)).toBe(true);
		expect(hasAntArtifactActivity(partial)).toBe(true);
		expect(hasStreamingAntArtifact(partial)).toBe(true);
	});

	it('parses multiple blocks with one still streaming', () => {
		const text = `<antArtifact identifier="one" type="text/html" title="One">
done
</antArtifact>

<antArtifact identifier="two" type="text/html" title="Two">
<div>`;

		const blocks = scanAntArtifactBlocks(text);
		expect(blocks).toHaveLength(2);
		expect(blocks[0].complete).toBe(true);
		expect(blocks[1].complete).toBe(false);
	});
});

describe('artifact streaming preview', () => {
	it('strips scripts from in-progress HTML previews', () => {
		const html = '<div>Hi</div><script>alert(1)</script>';
		expect(stripStreamingScripts(html)).toBe('<div>Hi</div>');
		expect(buildStreamingHtmlPreview(html, false)).toContain('<div>Hi</div>');
		expect(buildStreamingHtmlPreview(html, false)).not.toContain('alert');
	});

	it('builds a react placeholder while streaming', () => {
		const panel = artifactToPanelContent({
			identifier: 'app',
			type: 'application/vnd.ant.react',
			title: 'App',
			content: 'export default function App() {',
			artifactType: 'react',
			complete: false
		});

		expect(panel.streaming).toBe(true);
		expect(panel.sourceCode).toContain('export default');
		expect(panel.content).toContain('Writing React component');
	});
});
