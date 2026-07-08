<script lang="ts">
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { config } from '$lib/stores';

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
	class="flex gap-1 scrollbar-none overflow-x-auto w-fit max-w-full text-sm font-medium rounded-lg"
>
	{#each navItems as item (item.id)}
		{#if !item.hidden}
			<a
				draggable="false"
				class="min-w-fit px-3 py-1.5 rounded-lg transition select-none flex items-center gap-1.5 {item.isActive(
					$page.url.pathname
				)
					? 'bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-white font-medium'
					: 'text-gray-500 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-900/60'}"
				href={item.href}
			>
				<span class="shrink-0 size-4">
					{#if item.id === 'overview'}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
							<path
								d="M8.5 4.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0ZM10.9 12.006c.11.542-.348.994-.9.994H2c-.553 0-1.01-.452-.902-.994a5.002 5.002 0 0 1 9.803 0ZM14.002 12h-1.59a2.556 2.556 0 0 0-.04-.29 6.476 6.476 0 0 0-1.167-2.603 3.002 3.002 0 0 1 3.633 1.911c.18.522-.283.982-.836.982ZM12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"
							/>
						</svg>
					{:else if item.id === 'users'}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
							<path
								d="M8 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM3.156 11.763c.16-.629.44-1.21.813-1.72a2.5 2.5 0 0 0-2.725 1.377c-.136.287.102.58.418.58h1.449c.01-.077.025-.156.045-.237ZM12.847 11.763c.02.08.036.16.046.237h1.446c.316 0 .554-.293.417-.579a2.5 2.5 0 0 0-2.722-1.378c.374.51.653 1.09.813 1.72ZM14 7.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0ZM3.5 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM5 13c-.552 0-1.013-.455-.876-.99a4.002 4.002 0 0 1 7.753 0c.136.535-.324.99-.877.99H5Z"
							/>
						</svg>
					{:else if item.id === 'analytics'}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
							<path
								d="M2 13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5v-11A1.5 1.5 0 0 0 12.5 1h-9A1.5 1.5 0 0 0 2 2.5v11ZM3.5 2.5h9v11h-9v-11ZM5 11V8.5h1.5V11H5Zm2.5 0V6h1.5v5H7.5ZM11 11V4.5H12.5V11H11Z"
							/>
						</svg>
					{:else if item.id === 'evaluations'}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm6 5.75a.75.75 0 0 1 1.5 0v3.5a.75.75 0 0 1-1.5 0v-3.5Zm-2.75 1.5a.75.75 0 0 1 1.5 0v2a.75.75 0 0 1-1.5 0v-2Zm-2 .75a.75.75 0 0 0-.75.75v.5a.75.75 0 0 0 1.5 0v-.5a.75.75 0 0 0-.75-.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					{:else if item.id === 'functions'}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
							<path
								fill-rule="evenodd"
								d="M2 3.5A1.5 1.5 0 0 1 3.5 2h2.879a1.5 1.5 0 0 1 1.06.44l2.122 2.12a1.5 1.5 0 0 0 1.06.44H13.5A1.5 1.5 0 0 1 15 6.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 2 13.5v-10Zm3.5-1h-.379l2.122 2.122a1.5 1.5 0 0 0 1.06.44H13.5v7h-11V3.5Zm2.25 4.25a.75.75 0 0 0 0 1.5h4.5a.75.75 0 0 0 0-1.5h-4.5Z"
								clip-rule="evenodd"
							/>
						</svg>
					{:else if item.id === 'settings'}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
							<path
								fill-rule="evenodd"
								d="M8 1a2.75 2.75 0 0 0-2.65 2 1 1 0 0 1-.853.853A2.75 2.75 0 0 0 1 8c0 .96.49 1.8 1.23 2.3a1 1 0 0 1 0 1.4A2.75 2.75 0 0 0 1 14a2.75 2.75 0 0 0 2.65-2 1 1 0 0 1 .853-.853A2.75 2.75 0 0 0 8 15a2.75 2.75 0 0 0 2.65-2 1 1 0 0 1 .853-.853A2.75 2.75 0 0 0 15 8a2.75 2.75 0 0 0-2.65-2 1 1 0 0 1-.853-.853A2.75 2.75 0 0 0 8 1Zm0 4.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z"
								clip-rule="evenodd"
							/>
						</svg>
					{/if}
				</span>
				<span class="hidden sm:inline">{$i18n.t(item.label)}</span>
			</a>
		{/if}
	{/each}
</div>
