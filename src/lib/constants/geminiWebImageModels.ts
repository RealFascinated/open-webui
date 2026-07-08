export const GEMINI_WEB_IMAGE_MODELS = [
	{ id: 'gemini-3-flash', name: 'Fast' },
	{ id: 'gemini-3-flash-thinking', name: 'Thinking' },
	{ id: 'gemini-3-pro', name: 'Pro' },
	{ id: 'gemini-3-flash-plus', name: 'Fast (Google AI Plus)' },
	{ id: 'gemini-3-flash-thinking-plus', name: 'Thinking (Google AI Plus)' },
	{ id: 'gemini-3-pro-plus', name: 'Pro (Google AI Plus)' },
	{ id: 'gemini-3-flash-advanced', name: 'Fast (Google AI Advanced)' },
	{ id: 'gemini-3-flash-thinking-advanced', name: 'Thinking (Google AI Advanced)' },
	{ id: 'gemini-3-pro-advanced', name: 'Pro (Google AI Advanced)' }
];

export const DEFAULT_GEMINI_WEB_IMAGE_MODEL = 'gemini-3-flash';

const OPENAI_IMAGE_MODEL_IDS = new Set(['dall-e-2', 'dall-e-3', 'gpt-image-1', 'gpt-image-1.5']);

export const isOpenAIImageModelId = (modelId: string | null | undefined) =>
	!!modelId && OPENAI_IMAGE_MODEL_IDS.has(modelId);

export const defaultModelForImageEngine = (engine: string | null | undefined) => {
	switch (engine) {
		case 'gemini_web':
			return DEFAULT_GEMINI_WEB_IMAGE_MODEL;
		case 'gemini':
			return 'imagen-3.0-generate-002';
		case 'openai':
			return 'dall-e-3';
		default:
			return '';
	}
};
