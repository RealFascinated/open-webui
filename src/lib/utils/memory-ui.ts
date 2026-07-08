import type { MemoryRecord } from '$lib/apis/memories';

export type MemoryPathNode = {
	name: string;
	fullPath: string;
	count: number;
	children: MemoryPathNode[];
};

export const memoryProvenanceLabel = (
	meta: MemoryRecord['meta'],
	i18n: { t: (key: string) => string }
) => {
	const source = meta?.created_by;
	if (source === 'background_review') return i18n.t('Auto-saved');
	if (source === 'tool') return i18n.t('From chat');
	return i18n.t('Manual');
};

export const memoryProvenanceClass = (meta: MemoryRecord['meta']) => {
	const source = meta?.created_by;
	if (source === 'background_review') {
		return 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-200';
	}
	if (source === 'tool') {
		return 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-200';
	}
	return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300';
};

export const buildMemoryPathTree = (memories: MemoryRecord[]): MemoryPathNode[] => {
	const root: Record<string, MemoryPathNode & { childMap: Record<string, MemoryPathNode> }> = {};

	for (const memory of memories) {
		if (!memory.path) continue;
		const parts = memory.path.split('/').filter(Boolean);
		let current = root;

		for (let index = 0; index < parts.length; index += 1) {
			const part = parts[index];
			const fullPath = parts.slice(0, index + 1).join('/');
			if (!current[part]) {
				current[part] = {
					name: part,
					fullPath,
					count: 0,
					children: [],
					childMap: {}
				};
			}
			if (index === parts.length - 1) {
				current[part].count += 1;
			}
			current = current[part].childMap;
		}
	}

	const toNodes = (
		nodes: Record<string, MemoryPathNode & { childMap: Record<string, MemoryPathNode> }>
	): MemoryPathNode[] =>
		Object.values(nodes)
			.map((node) => ({
				name: node.name,
				fullPath: node.fullPath,
				count: node.count,
				children: toNodes(node.childMap)
			}))
			.sort((a, b) => a.name.localeCompare(b.name));

	return toNodes(root);
};

export const memoryMatchesPath = (memory: MemoryRecord, selectedPath: string | null) => {
	if (!selectedPath) return true;
	if (selectedPath === '__ungrouped__') return !memory.path;
	return memory.path === selectedPath || (memory.path?.startsWith(`${selectedPath}/`) ?? false);
};

export const ungroupedMemoryCount = (memories: MemoryRecord[]) =>
	memories.filter((memory) => !memory.path).length;
