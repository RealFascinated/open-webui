type ModelInfoLike = {
	meta?: {
		hidden?: boolean;
	};
};

export const getAvailableModelIds = (
	models: ReadonlyArray<{ id: string; info?: unknown }>,
	{ includeHidden = false }: { includeHidden?: boolean } = {}
): string[] => {
	return models
		.filter((model) => {
			if (includeHidden) {
				return true;
			}

			const meta = (model.info as ModelInfoLike | undefined)?.meta;
			return !(meta?.hidden ?? false);
		})
		.map((model) => model.id);
};

export const resolveSelectedModels = (
	candidateModelIds: string[],
	availableModelIds: string[],
	defaultModelIds: string[] = []
): string[] => {
	const resolved = candidateModelIds.filter(
		(modelId) => modelId && availableModelIds.includes(modelId)
	);

	if (resolved.length > 0) {
		return resolved;
	}

	const explicitSelection = candidateModelIds.filter((modelId) => modelId);

	// Keep an explicit user choice while the model list is still loading.
	if (explicitSelection.length > 0 && availableModelIds.length === 0) {
		return explicitSelection;
	}

	if (defaultModelIds.length > 0) {
		const defaultModels = defaultModelIds.filter((modelId) => availableModelIds.includes(modelId));
		if (defaultModels.length > 0) {
			return defaultModels;
		}
	}

	if (availableModelIds.length > 0) {
		return [availableModelIds[0]];
	}

	return [''];
};
