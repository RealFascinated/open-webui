export type SettingsTab = {
	id: string;
	title: string;
	description: string;
	section: string;
	route: string;
	keywords: string[];
};

export const SETTINGS_SECTIONS = [
	{ id: 'platform', label: 'Platform' },
	{ id: 'ai', label: 'AI & Models' },
	{ id: 'retrieval', label: 'Retrieval' },
	{ id: 'integrations', label: 'Integrations' },
	{ id: 'experience', label: 'Experience' },
	{ id: 'quality', label: 'Quality' }
] as const;

export const ALL_SETTINGS_TABS: SettingsTab[] = [
	{
		id: 'general',
		title: 'General',
		description: 'Instance version, feature flags, and core configuration.',
		section: 'platform',
		route: '/admin/settings/general',
		keywords: [
			'general',
			'admin',
			'settings',
			'version',
			'update',
			'language',
			'theme',
			'data',
			'users',
			'roles',
			'ldap',
			'authentication',
			'reverse proxy',
			'webhook',
			'community',
			'channels'
		]
	},
	{
		id: 'authentication',
		title: 'Authentication',
		description: 'Login, signup, OAuth, LDAP, and user access policies.',
		section: 'platform',
		route: '/admin/settings/authentication',
		keywords: [
			'authentication',
			'auth',
			'login',
			'signup',
			'ldap',
			'oauth',
			'oidc',
			'sso',
			'roles',
			'groups',
			'identity'
		]
	},
	{
		id: 'db',
		title: 'Database',
		description: 'Export, import, and manage database backups.',
		section: 'platform',
		route: '/admin/settings/db',
		keywords: ['database', 'export', 'import', 'backup', 'chats', 'users']
	},
	{
		id: 'connections',
		title: 'Connections',
		description: 'Configure Ollama, OpenAI, and other model provider connections.',
		section: 'ai',
		route: '/admin/settings/connections',
		keywords: [
			'connections',
			'ollama',
			'openai',
			'api',
			'base url',
			'key'
		]
	},
	{
		id: 'models',
		title: 'Models',
		description: 'Manage available models, access, and default settings.',
		section: 'ai',
		route: '/admin/settings/models',
		keywords: [
			'models',
			'pull',
			'delete',
			'create',
			'edit',
			'modelfile',
			'gguf',
			'import',
			'export'
		]
	},
	{
		id: 'pipelines',
		title: 'Pipelines',
		description: 'Pipeline filters, valves, and middleware configuration.',
		section: 'ai',
		route: '/admin/settings/pipelines',
		keywords: ['pipelines', 'workflows', 'filters', 'valves', 'middleware']
	},
	{
		id: 'documents',
		title: 'Documents',
		description: 'RAG, embeddings, document processing, and vector storage.',
		section: 'retrieval',
		route: '/admin/settings/documents?section=general',
		keywords: [
			'documents',
			'files',
			'rag',
			'knowledge',
			'upload',
			'embedding',
			'vector db',
			'chunk',
			'overlap',
			'splitter',
			'pdf',
			'ocr',
			'tika',
			'docling',
			'unstructured'
		]
	},
	{
		id: 'web',
		title: 'Web Search',
		description: 'Web search providers, loaders, and URL extraction.',
		section: 'retrieval',
		route: '/admin/settings/web',
		keywords: [
			'web search',
			'google',
			'bing',
			'duckduckgo',
			'serp',
			'searxng',
			'moojeh',
			'yacy',
			'serper',
			'serply',
			'tavily',
			'exa',
			'perplexity',
			'firecrawl'
		]
	},
	{
		id: 'integrations',
		title: 'Integrations',
		description: 'Tool servers, terminal connections, and external knowledge sources.',
		section: 'integrations',
		route: '/admin/settings/integrations',
		keywords: [
			'tools',
			'integrations',
			'plugins',
			'extensions',
			'functions',
			'openapi',
			'server',
			'knowledge',
			'vector db',
			'qdrant',
			'rag',
			'retrieval',
			'sources'
		]
	},
	{
		id: 'code-execution',
		title: 'Code Execution',
		description: 'Python sandbox, code interpreter, and execution settings.',
		section: 'integrations',
		route: '/admin/settings/code-execution',
		keywords: ['code execution', 'python', 'sandbox', 'compiler', 'jupyter', 'interpreter']
	},
	{
		id: 'interface',
		title: 'Interface',
		description: 'UI behavior, banners, tasks, and prompt suggestions.',
		section: 'experience',
		route: '/admin/settings/interface',
		keywords: [
			'interface',
			'ui',
			'appearance',
			'banners',
			'tasks',
			'prompt suggestions',
			'title generation',
			'tags'
		]
	},
	{
		id: 'audio',
		title: 'Audio',
		description: 'Speech-to-text and text-to-speech configuration.',
		section: 'experience',
		route: '/admin/settings/audio',
		keywords: [
			'audio',
			'voice',
			'speech',
			'tts',
			'stt',
			'whisper',
			'deepgram',
			'azure',
			'openai',
			'elevenlabs'
		]
	},
	{
		id: 'images',
		title: 'Images',
		description: 'Image generation providers and editing settings.',
		section: 'experience',
		route: '/admin/settings/images',
		keywords: [
			'images',
			'generation',
			'dalle',
			'stable diffusion',
			'comfyui',
			'automatic1111',
			'gemini'
		]
	},
	{
		id: 'evaluations',
		title: 'Evaluation Settings',
		description: 'Configure model arena, ratings, and evaluation features.',
		section: 'quality',
		route: '/admin/settings/evaluations',
		keywords: ['evaluations', 'feedback', 'rating', 'arena', 'leaderboard', 'preference']
	}
];

export const SETTINGS_TAB_IDS = ALL_SETTINGS_TABS.map((tab) => tab.id);

export const filterSettingsTabs = (search: string) => {
	const searchTerm = search.toLowerCase().trim();

	return ALL_SETTINGS_TABS.filter(
		(tab) =>
			search === '' ||
			tab.title.toLowerCase().includes(searchTerm) ||
			tab.keywords.some((keyword) => keyword.includes(searchTerm))
	);
};

export const groupSettingsTabs = (tabs: SettingsTab[]) =>
	SETTINGS_SECTIONS.map((section) => ({
		...section,
		tabs: tabs
			.filter((tab) => tab.section === section.id)
			.map((tab) => ({
				id: tab.id,
				href: tab.route,
				label: tab.title
			}))
	})).filter((section) => section.tabs.length > 0);
