export const DEFAULT_PERMISSIONS = {
	workspace: {
		knowledge: false,
		prompts: false,
		tools: false,
		skills: false,
		prompts_import: false,
		prompts_export: false,
		tools_import: false,
		tools_export: false,
		skills_import: false,
		skills_export: false
	},
	sharing: {
		knowledge: false,
		public_knowledge: false,
		prompts: false,
		public_prompts: false,
		tools: false,
		public_tools: false,
		skills: false,
		public_skills: false,
		notes: false,
		public_notes: false,
		folders: false,
		public_chats: false,
		public_calendars: false
	},
	access_grants: {
		allow_users: true
	},
	chat: {
		file_upload: true,
		web_upload: true,
		delete: true,
		delete_message: true,
		continue_response: true,
		regenerate_response: true,
		rate_response: true,
		edit: true,
		share: true,
		export: true,
		import: true,
		stt: true,
		tts: true,
		call: true,
		temporary: true,
		temporary_enforced: false
	},
	features: {
		api_keys: false,
		notes: true,
		channels: true,
		folders: true,
		direct_tool_servers: false,
		web_search: true,
		image_generation: true,
		code_interpreter: true,
		memories: true,
		automations: false,
		calendar: true,
		webhooks: false
	},
	settings: {
		interface: true
	}
} as const;
