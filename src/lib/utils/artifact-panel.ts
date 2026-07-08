import type { ArtifactContent } from '$lib/stores';
import type { AntArtifact } from '$lib/utils/ant-artifact';
import { isArtifactComplete } from '$lib/utils/ant-artifact';
import {
	buildStreamingHtmlPreview,
	buildStreamingPlaceholderPage
} from '$lib/utils/artifact-stream-preview';
import type { ArtifactCanvasTheme } from '$lib/utils/artifact-theme';
import { buildReactHtml } from '$lib/utils/react-artifact';

export const artifactToPanelContent = (
	artifact: AntArtifact,
	canvasTheme: ArtifactCanvasTheme = 'light'
): Omit<ArtifactContent, 'artifactId'> => {
	const complete = isArtifactComplete(artifact);
	const streaming = !complete;
	const base = {
		title: artifact.title,
		identifier: artifact.identifier,
		mimeType: artifact.type,
		complete,
		streaming
	};

	if (!artifact.artifactType) {
		return {
			...base,
			type: 'iframe',
			content: buildStreamingPlaceholderPage(
				artifact.title,
				complete ? 'Unsupported artifact type' : 'Building artifact…',
				canvasTheme
			)
		};
	}

	if (artifact.artifactType === 'react') {
		if (!complete) {
			return {
				...base,
				type: 'iframe',
				content: buildStreamingPlaceholderPage(
					artifact.title,
					'Writing React component…',
					canvasTheme
				),
				sourceCode: artifact.content
			};
		}

		return {
			...base,
			type: 'iframe',
			content: buildReactHtml(artifact.content, canvasTheme),
			sourceCode: artifact.content
		};
	}

	if (artifact.artifactType === 'iframe') {
		return {
			...base,
			type: 'iframe',
			content: complete
				? artifact.content
				: buildStreamingHtmlPreview(artifact.content, false, canvasTheme)
		};
	}

	if (artifact.artifactType === 'svg') {
		return {
			...base,
			type: 'svg',
			content: artifact.content
		};
	}

	return {
		...base,
		type: 'markdown',
		content: artifact.content
	};
};
