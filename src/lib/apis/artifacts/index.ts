import { WEBUI_API_BASE_URL } from '$lib/constants';

export type ArtifactItem = {
	id: string;
	user_id: string;
	chat_id: string | null;
	title: string | null;
	type: string;
	meta: string | null;
	created_at: number;
	updated_at: number;
};

export type ArtifactWithCode = ArtifactItem & { code: string };

export type StorageGetResult = { key: string; value: string; shared: boolean } | null;
export type StorageSetResult = { key: string; value: string; shared: boolean } | null;
export type StorageDeleteResult = { key: string; deleted: boolean; shared: boolean } | null;
export type StorageListResult = { keys: string[]; prefix: string | null; shared: boolean } | null;

// ── Artifact CRUD ────────────────────────────────────────────────────

export const publishArtifact = async (
	token: string,
	data: { chat_id?: string; title?: string; type: string; code: string; meta?: string }
): Promise<ArtifactWithCode | null> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/artifacts/publish`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res;
};

export const getArtifacts = async (token: string): Promise<ArtifactItem[]> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/artifacts/`, {
		headers: { authorization: `Bearer ${token}` }
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return [];
		});
	return res ?? [];
};

export const getArtifactById = async (
	token: string,
	id: string
): Promise<ArtifactWithCode | null> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/artifacts/${id}`, {
		headers: { authorization: `Bearer ${token}` }
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res;
};

export const updateArtifact = async (
	token: string,
	id: string,
	data: { title?: string; meta?: string }
): Promise<ArtifactItem | null> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/artifacts/${id}`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res;
};

export const deleteArtifact = async (token: string, id: string): Promise<boolean> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/artifacts/${id}`, {
		method: 'DELETE',
		headers: { authorization: `Bearer ${token}` }
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res?.deleted ?? false;
};

// ── Storage ──────────────────────────────────────────────────────────

export const getArtifactStorageItem = async (
	token: string,
	artifactId: string,
	key: string,
	scope: 'personal' | 'shared' = 'personal'
): Promise<StorageGetResult> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/artifacts/${artifactId}/storage/${encodeURIComponent(key)}?scope=${scope}`,
		{ headers: { authorization: `Bearer ${token}` } }
	)
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res;
};

export const setArtifactStorageItem = async (
	token: string,
	artifactId: string,
	key: string,
	value: string,
	scope: 'personal' | 'shared' = 'personal'
): Promise<StorageSetResult> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/artifacts/${artifactId}/storage/${encodeURIComponent(key)}?scope=${scope}`,
		{
			method: 'PUT',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ value })
		}
	)
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res;
};

export const deleteArtifactStorageItem = async (
	token: string,
	artifactId: string,
	key: string,
	scope: 'personal' | 'shared' = 'personal'
): Promise<StorageDeleteResult> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/artifacts/${artifactId}/storage/${encodeURIComponent(key)}?scope=${scope}`,
		{
			method: 'DELETE',
			headers: { authorization: `Bearer ${token}` }
		}
	)
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res;
};

export const listArtifactStorageItems = async (
	token: string,
	artifactId: string,
	prefix = '',
	scope: 'personal' | 'shared' = 'personal'
): Promise<StorageListResult> => {
	const params = new URLSearchParams({ scope });
	if (prefix) params.set('prefix', prefix);
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/artifacts/${artifactId}/storage?${params.toString()}`,
		{ headers: { authorization: `Bearer ${token}` } }
	)
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			return null;
		});
	return res;
};
