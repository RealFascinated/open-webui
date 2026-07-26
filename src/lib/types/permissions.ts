import type { DEFAULT_PERMISSIONS } from '$lib/constants/permissions';

type DeepMutable<T> = T extends object
	? { -readonly [K in keyof T]: DeepMutable<T[K]> }
	: T;

/** Fully-resolved permissions object matching DEFAULT_PERMISSIONS shape. */
export type DefaultPermissions = DeepMutable<typeof DEFAULT_PERMISSIONS>;

export type UserWorkspacePermissions = DefaultPermissions['workspace'];
export type UserSharingPermissions = DefaultPermissions['sharing'];
export type UserAccessGrantPermissions = DefaultPermissions['access_grants'];
export type UserChatPermissions = DefaultPermissions['chat'];
export type UserFeaturePermissions = DefaultPermissions['features'];
export type UserSettingsPermissions = DefaultPermissions['settings'];

/** Partial permissions as received from API or parent components. */
export type UserPermissions = {
	workspace?: Partial<UserWorkspacePermissions>;
	sharing?: Partial<UserSharingPermissions>;
	access_grants?: Partial<UserAccessGrantPermissions>;
	chat?: Partial<UserChatPermissions>;
	features?: Partial<UserFeaturePermissions>;
	settings?: Partial<UserSettingsPermissions>;
};
