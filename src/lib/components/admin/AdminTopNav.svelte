<script lang="ts">
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { config } from '$lib/stores';

	import AdminTabIcon from './AdminTabIcon.svelte';

	const i18n = getContext('i18n');

	type NavItem = {
		id: string;
		label: string;
		href: string;
		isActive: (pathname: string) => boolean;
		hidden?: boolean;
	};

	$: navItems = [
		{
			id: 'overview',
			label: 'Overview',
			href: '/admin',
			isActive: (pathname) => pathname === '/admin' || pathname === '/admin/'
		},
		{
			id: 'users',
			label: 'Users',
			href: '/admin/users',
			isActive: (pathname) => pathname.includes('/admin/users')
		},
		{
			id: 'analytics',
			label: 'Analytics',
			href: '/admin/analytics',
			isActive: (pathname) => pathname.includes('/admin/analytics'),
			hidden: !($config?.features.enable_admin_analytics ?? true)
		},
		{
			id: 'evaluations',
			label: 'Evaluations',
			href: '/admin/evaluations',
			isActive: (pathname) => pathname.includes('/admin/evaluations')
		},
		{
			id: 'functions',
			label: 'Functions',
			href: '/admin/functions',
			isActive: (pathname) => pathname.includes('/admin/functions')
		},
		{
			id: 'settings',
			label: 'Settings',
			href: '/admin/settings',
			isActive: (pathname) => pathname.includes('/admin/settings')
		}
	] satisfies NavItem[];
</script>

<div
	class="flex gap-0.5 scrollbar-none overflow-x-auto w-fit max-w-full text-sm font-medium rounded-xl p-0.5 bg-gray-100/60 dark:bg-gray-900/60"
>
	{#each navItems as item (item.id)}
		{#if !item.hidden}
			{@const active = item.isActive($page.url.pathname)}
			<a
				draggable="false"
				class="min-w-fit px-2.5 sm:px-3 py-1.5 rounded-lg transition select-none flex items-center gap-2 {active
					? 'bg-white dark:bg-gray-850 text-gray-900 dark:text-white shadow-sm'
					: 'text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200'}"
				href={item.href}
			>
				<span
					class="shrink-0 flex items-center justify-center size-6 rounded-md {active
						? 'text-gray-900 dark:text-white'
						: 'text-gray-400 dark:text-gray-500'}"
				>
					<AdminTabIcon iconId={item.id} className="size-4" />
				</span>
				<span class="hidden sm:inline">{$i18n.t(item.label)}</span>
			</a>
		{/if}
	{/each}
</div>
