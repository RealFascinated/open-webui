import { WEBUI_API_BASE_URL } from '$lib/constants';

const authHeaders = (token: string) => ({
	Accept: 'application/json',
	'Content-Type': 'application/json',
	authorization: `Bearer ${token}`
});

const handleResponse = async (res: Response) => {
	if (!res.ok) throw await res.json();
	return res.json();
};

export type MemoryRecord = {
	id: string;
	content: string;
	type?: 'user' | 'context';
	path?: string | null;
	meta?: {
		created_by?: 'manual' | 'tool' | 'background_review';
		chat_id?: string;
		message_id?: string;
		model?: string;
		always_include?: boolean;
	} | null;
	updated_at?: number;
	created_at?: number;
};

export type MemoryPathGroup = {
	path: string | null;
	type: string;
	count: number;
	updated_at: number;
	children: string[];
};

export const getMemories = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/`, {
		method: 'GET',
		headers: authHeaders(token)
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const addNewMemory = async (
	token: string,
	content: string,
	type = 'user',
	path = ''
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/add`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify({
			content,
			type,
			path
		})
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateMemoryById = async (
	token: string,
	id: string,
	content: string,
	type?: string,
	path?: string
) => {
	let error = null;
	const body = { content, ...(type ? { type } : {}), ...(path !== undefined ? { path } : {}) };

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/${id}/update`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(body)
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const searchMemories = async (
	token: string,
	params: {
		query?: string;
		type?: 'user' | 'context' | 'all';
		path?: string;
		memory_id?: string;
		project_id?: string;
		limit?: number;
	} = {}
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/search`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(params)
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const listMemoryPaths = async (
	token: string,
	params: {
		query?: string;
		type?: 'user' | 'context' | 'all';
		limit?: number;
	} = {}
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/paths`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(params)
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res as { paths: MemoryPathGroup[]; count: number };
};

export const readMemoryPath = async (
	token: string,
	params: {
		path: string;
		type?: 'user' | 'context' | 'all';
		include_children?: boolean;
		limit?: number;
	}
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/path`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(params)
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const consolidateMemories = async (token: string, model?: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/consolidate`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify(model ? { model } : {})
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const queryMemory = async (token: string, content: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/query`, {
		method: 'POST',
		headers: authHeaders(token),
		body: JSON.stringify({
			content
		})
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteMemoryById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/${id}`, {
		method: 'DELETE',
		headers: authHeaders(token)
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteMemoriesByUserId = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/delete/user`, {
		method: 'DELETE',
		headers: authHeaders(token)
	})
		.then(handleResponse)
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
