import { ALL_SETTINGS_TABS, SETTINGS_SECTIONS } from '$lib/components/admin/settingsTabs';
import { DOCUMENT_SECTIONS } from '$lib/components/admin/Settings/documentsSections';

export type AdminSearchItem = {
	id: string;
	title: string;
	description: string;
	href: string;
	category: string;
	keywords: string[];
};

const ADMIN_PAGES: AdminSearchItem[] = [
	{
		id: 'admin-overview',
		title: 'Overview',
		description: 'Instance health, quick stats, and common admin tasks.',
		href: '/admin',
		category: 'Admin',
		keywords: ['overview', 'home', 'dashboard', 'health', 'stats']
	},
	{
		id: 'admin-users-overview',
		title: 'Users Overview',
		description: 'User accounts, roles, and activity.',
		href: '/admin/users/overview',
		category: 'Users',
		keywords: ['users', 'accounts', 'roles', 'pending']
	},
	{
		id: 'admin-users-groups',
		title: 'User Groups',
		description: 'Groups and permission presets.',
		href: '/admin/users/groups',
		category: 'Users',
		keywords: ['groups', 'permissions', 'access', 'presets']
	},
	{
		id: 'admin-analytics',
		title: 'Analytics',
		description: 'Usage, models, and token statistics.',
		href: '/admin/analytics',
		category: 'Admin',
		keywords: ['analytics', 'usage', 'tokens', 'messages', 'chats']
	},
	{
		id: 'admin-evaluations-leaderboard',
		title: 'Evaluation Leaderboard',
		description: 'Model arena results and rankings.',
		href: '/admin/evaluations/leaderboard',
		category: 'Evaluations',
		keywords: ['evaluations', 'leaderboard', 'arena', 'ratings']
	},
	{
		id: 'admin-evaluations-feedback',
		title: 'Evaluation Feedback',
		description: 'User feedback on model responses.',
		href: '/admin/evaluations/feedback',
		category: 'Evaluations',
		keywords: ['feedback', 'evaluations', 'votes', 'ratings']
	},
	{
		id: 'admin-functions',
		title: 'Functions',
		description: 'Filters and action pipelines.',
		href: '/admin/functions',
		category: 'Admin',
		keywords: ['functions', 'filters', 'pipelines', 'actions']
	},
	{
		id: 'admin-settings',
		title: 'Settings',
		description: 'All admin configuration pages.',
		href: '/admin/settings',
		category: 'Settings',
		keywords: ['settings', 'configuration', 'admin']
	}
];

const sectionLabelById = Object.fromEntries(SETTINGS_SECTIONS.map((s) => [s.id, s.label]));

export const buildAdminSearchIndex = (options?: {
	enableAdminAnalytics?: boolean;
}): AdminSearchItem[] => {
	const items: AdminSearchItem[] = [...ADMIN_PAGES];

	if (options?.enableAdminAnalytics === false) {
		const hidden = new Set(['admin-analytics']);
		for (let i = items.length - 1; i >= 0; i--) {
			if (hidden.has(items[i].id)) items.splice(i, 1);
		}
	}

	for (const tab of ALL_SETTINGS_TABS) {
		items.push({
			id: `settings-${tab.id}`,
			title: tab.title,
			description: tab.description,
			href: tab.route,
			category: `Settings · ${sectionLabelById[tab.section] ?? tab.section}`,
			keywords: [...tab.keywords, tab.title.toLowerCase(), tab.id]
		});
	}

	for (const section of DOCUMENT_SECTIONS) {
		items.push({
			id: `documents-${section.id}`,
			title: `Documents · ${section.label}`,
			description: section.description,
			href: `/admin/settings/documents?section=${section.id}`,
			category: 'Settings · Retrieval',
			keywords: ['documents', section.id, section.label.toLowerCase(), 'rag', 'embedding']
		});
	}

	return items;
};

const normalize = (value: string) => value.toLowerCase().trim();

export const filterAdminSearch = (
	query: string,
	items: AdminSearchItem[],
	limit = 12
): AdminSearchItem[] => {
	const q = normalize(query);
	if (!q) return items.slice(0, limit);

	const terms = q.split(/\s+/).filter(Boolean);

	const scored = items
		.map((item) => {
			const haystack = normalize(
				[item.title, item.description, item.category, ...item.keywords].join(' ')
			);
			let score = 0;

			for (const term of terms) {
				if (normalize(item.title).startsWith(term)) score += 12;
				else if (normalize(item.title).includes(term)) score += 8;
				else if (haystack.includes(term)) score += 3;
				else return null;
			}

			return { item, score };
		})
		.filter((entry): entry is { item: AdminSearchItem; score: number } => entry !== null)
		.sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title));

	return scored.slice(0, limit).map((entry) => entry.item);
};

const ADMIN_SEARCH_RECENTS_KEY = 'open-webui-admin-search-recents';
const ADMIN_SEARCH_RECENTS_MAX = 8;

type StoredAdminSearchRecent = Pick<AdminSearchItem, 'id' | 'title' | 'description' | 'href' | 'category'>;

export const getAdminSearchRecents = (): StoredAdminSearchRecent[] => {
	if (typeof localStorage === 'undefined') return [];

	try {
		const raw = localStorage.getItem(ADMIN_SEARCH_RECENTS_KEY);
		if (!raw) return [];
		const parsed = JSON.parse(raw);
		return Array.isArray(parsed) ? parsed : [];
	} catch {
		return [];
	}
};

export const recordAdminSearchVisit = (item: AdminSearchItem) => {
	if (typeof localStorage === 'undefined') return;

	const entry: StoredAdminSearchRecent = {
		id: item.id,
		title: item.title,
		description: item.description,
		href: item.href,
		category: item.category
	};

	const next = [
		entry,
		...getAdminSearchRecents().filter((recent) => recent.id !== item.id)
	].slice(0, ADMIN_SEARCH_RECENTS_MAX);

	localStorage.setItem(ADMIN_SEARCH_RECENTS_KEY, JSON.stringify(next));
};

export const getRecentAdminSearchResults = (
	index: AdminSearchItem[],
	limit = ADMIN_SEARCH_RECENTS_MAX
): AdminSearchItem[] => {
	const recents = getAdminSearchRecents();
	const byId = new Map(index.map((item) => [item.id, item]));

	return recents
		.map((recent) => byId.get(recent.id) ?? recent)
		.slice(0, limit);
};
