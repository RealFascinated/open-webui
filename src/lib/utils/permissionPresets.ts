import { DEFAULT_PERMISSIONS } from '$lib/constants/permissions';

type PermissionsShape = typeof DEFAULT_PERMISSIONS;

const clone = (): PermissionsShape => structuredClone(DEFAULT_PERMISSIONS);

export const PERMISSION_PRESET_IDS = ['default_user', 'power_user', 'read_only'] as const;

export type PermissionPresetId = (typeof PERMISSION_PRESET_IDS)[number];

export const PERMISSION_PRESETS: Record<
	PermissionPresetId,
	{ label: string; description: string; permissions: PermissionsShape }
> = {
	default_user: {
		label: 'Default User',
		description: 'Standard permissions for new users.',
		permissions: clone()
	},
	power_user: {
		label: 'Power User',
		description: 'Full workspace access with sharing and chat capabilities.',
		permissions: {
			...clone(),
			workspace: {
				knowledge: true,
				prompts: true,
				tools: true,
				skills: true,
				prompts_import: true,
				prompts_export: true,
				tools_import: true,
				tools_export: true,
				skills_import: true,
				skills_export: true
			},
			sharing: {
				knowledge: true,
				public_knowledge: false,
				prompts: true,
				public_prompts: false,
				tools: true,
				public_tools: false,
				skills: true,
				public_skills: false,
				notes: true,
				public_notes: false,
				projects: true,
				public_chats: false,
				public_calendars: false
			},
			features: {
				api_keys: true,
				notes: true,
				channels: true,
				projects: true,
				direct_tool_servers: true,
				web_search: true,
				image_generation: true,
				code_interpreter: true,
				memories: true,
				automations: true,
				calendar: true,
				webhooks: true
			},
			settings: {
				interface: true
			}
		}
	},
	read_only: {
		label: 'Read-only',
		description: 'View and chat only — no workspace editing or destructive actions.',
		permissions: {
			...clone(),
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
				projects: false,
				public_chats: false,
				public_calendars: false
			},
			chat: {
				file_upload: false,
				web_upload: false,
				delete: false,
				delete_message: false,
				continue_response: true,
				regenerate_response: true,
				rate_response: true,
				edit: false,
				share: false,
				export: false,
				import: false,
				stt: true,
				tts: true,
				call: true,
				temporary: false,
				temporary_enforced: false
			},
			features: {
				api_keys: false,
				notes: true,
				channels: true,
				projects: true,
				direct_tool_servers: false,
				web_search: true,
				image_generation: false,
				code_interpreter: false,
				memories: false,
				automations: false,
				calendar: true,
				webhooks: false
			},
			settings: {
				interface: false
			}
		}
	}
};
