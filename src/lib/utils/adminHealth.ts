export type AdminHealthState = 'loading' | 'ok' | 'warning' | 'error' | 'disabled';

export type AdminHealthResult = {
	state: AdminHealthState;
	detail: string;
	secondaryDetail?: string;
};

type WebSearchStatus = {
	enabled?: boolean;
	engine?: string;
	engine_label?: string;
	configured?: boolean;
	healthy?: boolean;
	detail?: string;
	host?: string | null;
	error?: string | null;
};

type AuthFeatures = {
	auth?: boolean;
	auth_trusted_header?: boolean;
	enable_ldap?: boolean;
	enable_signup?: boolean;
	enable_login_form?: boolean;
};

type LdapServer = {
	host?: string;
	search_base?: string;
};

export function evaluateWebSearchHealth(status: WebSearchStatus | null): AdminHealthResult {
	if (!status) {
		return { state: 'warning', detail: 'Status unavailable' };
	}

	if (!status.enabled) {
		return { state: 'disabled', detail: 'Disabled' };
	}

	const label = status.engine_label ?? status.engine ?? 'Web search';

	if (!status.configured) {
		return {
			state: 'warning',
			detail: status.detail ?? 'Not configured',
			secondaryDetail: label
		};
	}

	if (!status.healthy) {
		return {
			state: 'error',
			detail: `${label} · Unreachable`,
			secondaryDetail: status.error ? String(status.error).slice(0, 120) : undefined
		};
	}

	const metaParts = [status.host].filter(Boolean);
	return {
		state: 'ok',
		detail: label,
		secondaryDetail: metaParts.length ? metaParts.join(' · ') : 'Configured'
	};
}

export function evaluateAuthHealth(params: {
	features: AuthFeatures | null | undefined;
	oauthProviders: Record<string, string> | null | undefined;
	enableLdap: boolean;
	ldapServer: LdapServer | null;
	enableSignup: boolean | null | undefined;
}): AdminHealthResult {
	const { features, oauthProviders, enableLdap, ldapServer, enableSignup } = params;

	if (features?.auth === false) {
		return { state: 'disabled', detail: 'Authentication disabled' };
	}

	const methods: string[] = [];
	const warnings: string[] = [];

	if (features?.auth_trusted_header) {
		methods.push('Trusted header');
	}

	if (features?.enable_login_form !== false) {
		methods.push('Local login');
	}

	const oauthNames = Object.values(oauthProviders ?? {}).filter(Boolean);
	if (oauthNames.length > 0) {
		methods.push(oauthNames.length === 1 ? `OAuth (${oauthNames[0]})` : `OAuth (${oauthNames.length})`);
	}

	if (enableLdap) {
		const host = ldapServer?.host?.trim();
		const searchBase = ldapServer?.search_base?.trim();

		if (!host || !searchBase) {
			warnings.push('LDAP incomplete');
			methods.push('LDAP');
		} else {
			methods.push('LDAP');
		}
	}

	const signupEnabled = enableSignup ?? features?.enable_signup ?? false;
	const secondaryParts: string[] = [];

	if (signupEnabled) {
		secondaryParts.push('Signups enabled');
	} else {
		secondaryParts.push('Signups disabled');
	}

	if (enableLdap && ldapServer?.host) {
		secondaryParts.push(ldapServer.host);
	}

	if (warnings.length > 0) {
		return {
			state: 'warning',
			detail: methods.length ? methods.join(' · ') : 'Incomplete configuration',
			secondaryDetail: warnings.join(' · ')
		};
	}

	if (methods.length === 0) {
		return {
			state: 'warning',
			detail: 'No login methods enabled',
			secondaryDetail: secondaryParts.join(' · ')
		};
	}

	return {
		state: 'ok',
		detail: methods.join(' · '),
		secondaryDetail: secondaryParts.join(' · ')
	};
}

export function formatEmbeddingSecondaryDetail(params: {
	engine?: string | null;
	batchSize?: number | null;
}): string | undefined {
	const parts: string[] = [];

	if (params.engine) {
		const engineLabel = params.engine
			.replace(/_/g, ' ')
			.replace(/\b\w/g, (char) => char.toUpperCase());
		parts.push(engineLabel);
	}

	if (params.batchSize != null && params.batchSize > 0) {
		parts.push(`batch ${params.batchSize}`);
	}

	return parts.length ? parts.join(' · ') : undefined;
}

export function formatRerankerSecondaryDetail(params: {
	hybridEnabled: boolean;
	rerankEngine?: string | null;
}): string | undefined {
	if (!params.hybridEnabled) {
		return undefined;
	}

	const parts = ['Hybrid search'];
	if (params.rerankEngine) {
		parts.push(params.rerankEngine);
	}

	return parts.join(' · ');
}

export type VectorDBStatus = {
	VECTOR_DB?: string;
	VECTOR_DB_LABEL?: string;
	healthy?: boolean;
	detail?: string;
	summary?: string | null;
	data_path?: string | null;
	host?: string | null;
	storage_size?: string | null;
	collection_count?: number | null;
	vector_count?: number | null;
	deployment?: string | null;
	error?: string | null;
};

export function evaluateVectorDBHealth(
	vectorDbStatus: VectorDBStatus | null,
	bypassMode = false
): AdminHealthResult {
	if (bypassMode) {
		return {
			state: 'disabled',
			detail: 'Bypass mode enabled',
			secondaryDetail: 'Vectors are not stored while bypass is active'
		};
	}

	if (!vectorDbStatus) {
		return { state: 'warning', detail: 'Status unavailable' };
	}

	const label = vectorDbStatus.VECTOR_DB_LABEL ?? vectorDbStatus.VECTOR_DB ?? 'Vector DB';

	if (vectorDbStatus.healthy) {
		const location = vectorDbStatus.detail ?? 'Connected';
		const metaParts = [vectorDbStatus.summary].filter(Boolean);

		if (vectorDbStatus.data_path && !vectorDbStatus.storage_size) {
			metaParts.push(vectorDbStatus.data_path);
		} else if (vectorDbStatus.host && !location.includes(vectorDbStatus.host)) {
			metaParts.push(vectorDbStatus.host);
		}

		return {
			state: 'ok',
			detail: `${label} · ${location}`,
			secondaryDetail: metaParts.join(' · ') || undefined
		};
	}

	return {
		state: 'error',
		detail: `${label} · Unreachable`,
		secondaryDetail: vectorDbStatus.error ? String(vectorDbStatus.error).slice(0, 120) : undefined
	};
}

export function vectorDBCardStatus(
	health: AdminHealthResult
): 'configured' | 'not_configured' | 'warning' | null {
	if (health.state === 'ok') return 'configured';
	if (health.state === 'disabled' || health.state === 'warning') return 'warning';
	if (health.state === 'error') return 'warning';
	return 'not_configured';
}
