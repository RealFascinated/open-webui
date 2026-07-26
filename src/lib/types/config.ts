export type PromptSuggestion = {
	content: string;
	title: [string, string];
};

export type AppConfigFeatures = {
	auth?: boolean;
	auth_trusted_header?: boolean;
	enable_api_keys?: boolean;
	enable_signup?: boolean;
	enable_login_form?: boolean;
	enable_signup_password_confirmation?: boolean;
	enable_ldap?: boolean;
	enable_websocket?: boolean;
	enable_password_change_form?: boolean;
	enable_version_update_check?: boolean;
	enable_pyodide_file_persistence?: boolean;
	enable_public_active_users_count?: boolean;
	enable_easter_eggs?: boolean;
	enable_projects?: boolean;
	project_max_file_count?: number;
	enable_channels?: boolean;
	enable_calendar?: boolean;
	enable_automations?: boolean;
	enable_notes?: boolean;
	enable_artifacts?: boolean;
	enable_web_search?: boolean;
	enable_web_search_confirmation?: boolean;
	web_search_confirmation_content?: string;
	enable_code_execution?: boolean;
	enable_code_interpreter?: boolean;
	enable_image_generation?: boolean;
	enable_autocomplete_generation?: boolean;
	enable_community_sharing?: boolean;
	enable_message_rating?: boolean;
	enable_user_webhooks?: boolean;
	enable_user_status?: boolean;
	enable_admin_export?: boolean;
	enable_admin_chat_access?: boolean;
	enable_admin_analytics?: boolean;
	enable_google_drive_integration?: boolean;
	enable_onedrive_integration?: boolean;
	enable_onedrive_personal?: boolean;
	enable_onedrive_business?: boolean;
	enable_memories?: boolean;
	enable_web_search_confirmation?: boolean;
	[key: string]: unknown;
};

export type AppConfig = {
	status: boolean;
	name: string;
	version: string;
	default_locale: string;
	default_models?: string;
	default_pinned_models?: string;
	default_prompt_suggestions?: PromptSuggestion[];
	onboarding?: boolean;
	user_count?: number;
	active_entries?: number;
	license_metadata?: Record<string, unknown> | null;
	features: AppConfigFeatures;
	oauth: {
		providers: Record<string, string>;
		auto_redirect?: boolean;
	};
	code?: {
		engine?: string;
		interpreter_engine?: string;
	};
	audio?: {
		tts?: {
			engine?: string;
			voice?: string;
			split_on?: string;
		};
		stt?: {
			engine?: string;
		};
	};
	file?: {
		max_size?: number;
		max_count?: number;
		image_compression?: {
			width?: number;
			height?: number;
		};
	};
	permissions?: Record<string, unknown>;
	google_drive?: {
		client_id?: string;
		api_key?: string;
	};
	onedrive?: {
		client_id_personal?: string;
		client_id_business?: string;
		sharepoint_url?: string;
		sharepoint_tenant_id?: string;
	};
	ui?: {
		pending_user_overlay_title?: string;
		pending_user_overlay_content?: string;
		response_watermark?: string;
		iframe_csp?: string;
	};
	metadata?: Record<string, unknown>;
	sharing?: Record<string, unknown>;
	[key: string]: unknown;
};
