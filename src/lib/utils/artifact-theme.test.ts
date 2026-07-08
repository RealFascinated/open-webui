import { describe, expect, it } from 'vitest';

import {
	injectArtifactCanvasTheme,
	resolveArtifactCanvasTheme,
	artifactCanvasBaseCss
} from './artifact-theme';

describe('resolveArtifactCanvasTheme', () => {
	it('maps explicit settings', () => {
		expect(resolveArtifactCanvasTheme('dark')).toBe('dark');
		expect(resolveArtifactCanvasTheme('oled-dark')).toBe('dark');
		expect(resolveArtifactCanvasTheme('light')).toBe('light');
	});
});

describe('injectArtifactCanvasTheme', () => {
	it('injects theme attributes and base styles into a full HTML document', () => {
		const html = `<!DOCTYPE html><html><head></head><body><p>Hi</p></body></html>`;
		const themed = injectArtifactCanvasTheme(html, 'dark');

		expect(themed).toContain('data-ows-artifact-theme="dark"');
		expect(themed).toContain('#0d0d0d');
		expect(themed).toContain('#f3f4f6');
	});

	it('updates an existing theme injection', () => {
		const once = injectArtifactCanvasTheme('<html><head></head><body></body></html>', 'dark');
		const twice = injectArtifactCanvasTheme(once, 'light');

		expect(twice).toContain('data-ows-artifact-theme="light"');
		expect(twice).toContain(artifactCanvasBaseCss('light'));
		expect(twice.match(/data-ows-artifact-theme/g)?.length).toBe(1);
	});
});
