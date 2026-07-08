import { describe, expect, it } from 'vitest';
import {
	buildMemoryPathTree,
	memoryMatchesPath,
	memoryProvenanceLabel,
	ungroupedMemoryCount
} from './memory-ui';

describe('memory-ui', () => {
	it('builds a nested path tree with counts', () => {
		const tree = buildMemoryPathTree([
			{ id: '1', content: 'a', path: 'projects/p1/decisions' },
			{ id: '2', content: 'b', path: 'projects/p1/decisions' },
			{ id: '3', content: 'c', path: 'core/preferences' }
		]);

		const projectsNode = tree.find((node) => node.fullPath === 'projects');
		expect(projectsNode?.children[0]?.fullPath).toBe('projects/p1');
		expect(projectsNode?.children[0]?.children[0]?.count).toBe(2);

		const coreNode = tree.find((node) => node.fullPath === 'core');
		expect(coreNode?.children[0]?.fullPath).toBe('core/preferences');
		expect(coreNode?.children[0]?.count).toBe(1);
	});

	it('filters memories by selected path', () => {
		const memories = [
			{ id: '1', content: 'a', path: 'projects/p1/decisions' },
			{ id: '2', content: 'b', path: null }
		];

		expect(memoryMatchesPath(memories[0], 'projects/p1')).toBe(true);
		expect(memoryMatchesPath(memories[1], '__ungrouped__')).toBe(true);
		expect(ungroupedMemoryCount(memories)).toBe(1);
	});

	it('maps provenance labels', () => {
		const i18n = { t: (key: string) => key };
		expect(memoryProvenanceLabel({ created_by: 'background_review' }, i18n)).toBe('Auto-saved');
		expect(memoryProvenanceLabel({ created_by: 'tool' }, i18n)).toBe('From chat');
		expect(memoryProvenanceLabel({ created_by: 'manual' }, i18n)).toBe('Manual');
	});
});
