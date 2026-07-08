export const DOCUMENT_SECTIONS = [
	{
		id: 'general',
		label: 'General',
		description: 'Content extraction, chunking, and document processing.'
	},
	{
		id: 'embedding',
		label: 'Embedding',
		description: 'Embedding model engine, batching, and vector storage.'
	},
	{
		id: 'retrieval',
		label: 'Retrieval',
		description: 'Query settings, reranking, and RAG templates.'
	},
	{
		id: 'files',
		label: 'Files',
		description: 'Upload limits, allowed extensions, and image compression.'
	},
	{
		id: 'integration',
		label: 'Integration',
		description: 'Google Drive and OneDrive connectors.'
	},
	{
		id: 'danger',
		label: 'Danger Zone',
		description: 'Reset storage and reindex knowledge vectors.'
	}
] as const;

export type DocumentSectionId = (typeof DOCUMENT_SECTIONS)[number]['id'];

export const DOCUMENT_SECTION_IDS = DOCUMENT_SECTIONS.map((section) => section.id);

export const isDocumentSection = (value: string | null): value is DocumentSectionId =>
	DOCUMENT_SECTION_IDS.includes(value as DocumentSectionId);
