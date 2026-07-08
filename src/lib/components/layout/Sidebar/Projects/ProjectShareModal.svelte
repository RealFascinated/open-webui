<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { getProjectById, updateProjectAccessById } from '$lib/apis/projects';
	import { user } from '$lib/stores';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group';
		principal_id: string;
		permission: 'read' | 'write';
	};

	export let show = false;
	export let project: unknown = null;

	let accessGrants: AccessGrant[] = [];
	let loading = false;

	// Fetch fresh folder data (with access_grants) when modal opens
	$: if (show && project?.id) {
		loadAccessGrants();
	}

	const loadAccessGrants = async () => {
		loading = true;
		try {
			const freshProject = await getProjectById(localStorage.token, project.id);
			if (freshProject) {
				accessGrants = freshProject.access_grants ?? [];
			}
		} catch (e) {
			console.error('Failed to load folder access grants', e);
			accessGrants = project?.access_grants ?? [];
		} finally {
			loading = false;
		}
	};

	const handleAccessChange = async () => {
		if (!project) return;
		try {
			const res = await updateProjectAccessById(localStorage.token, project.id, accessGrants);
			if (res) {
				accessGrants = res.access_grants ?? accessGrants;
			}
		} catch (e) {
			console.error('Failed to update folder access', e);
		}
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-3 pb-1">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Share')}: {project?.name ?? ''}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="w-full px-5 pb-4 dark:text-white">
			<AccessControl
				bind:accessGrants
				onChange={handleAccessChange}
				accessRoles={['read', 'write']}
				share={$user?.role === 'admin' || $user?.permissions?.sharing?.projects}
				sharePublic={false}
				shareUsers={$user?.role === 'admin' || $user?.permissions?.access_grants?.allow_users}
			/>
		</div>
	</div>
</Modal>
