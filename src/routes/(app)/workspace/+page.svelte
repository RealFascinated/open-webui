<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import type { SessionUser } from '$lib/stores';
	import { onMount } from 'svelte';

	const getWorkspaceHome = (sessionUser: SessionUser | undefined) => {
		if (!sessionUser) {
			return '/';
		}

		if (sessionUser.role === 'admin' || sessionUser.permissions?.workspace?.knowledge) {
			return '/workspace/knowledge';
		}

		if (sessionUser.permissions?.workspace?.prompts) {
			return '/workspace/prompts';
		}

		if (sessionUser.permissions?.workspace?.tools) {
			return '/workspace/tools';
		}

		if (sessionUser.permissions?.workspace?.skills) {
			return '/workspace/skills';
		}

		return '/';
	};

	onMount(() => {
		goto(getWorkspaceHome($user));
	});
</script>
