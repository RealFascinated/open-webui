<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	export let map: {
		lat?: number;
		lng?: number;
		zoom?: number;
		label?: string;
		markers?: { lat: number; lng: number; label?: string }[];
	} = {};

	type LeafletMarker = {
		addTo: (map: LeafletMap) => LeafletMarker;
		bindPopup: (label: string) => void;
	};

	type LeafletMap = {
		remove: () => void;
		setView: (coords: [number, number], zoom: number) => LeafletMap;
	};

	type LeafletNamespace = {
		map: (el: HTMLElement) => LeafletMap;
		marker: (coords: [number, number]) => LeafletMarker;
		tileLayer: (
			url: string,
			opts: Record<string, string | number>
		) => { addTo: (map: LeafletMap) => void };
	};

	let mapContainer: HTMLDivElement;
	let mapInstance: LeafletMap | null = null;

	const getLeaflet = (): LeafletNamespace | undefined =>
		(window as Window & { L?: LeafletNamespace }).L;

	const loadLeaflet = async () => {
		if (getLeaflet()) return;

		if (!document.querySelector('link[data-leaflet-css]')) {
			const link = document.createElement('link');
			link.rel = 'stylesheet';
			link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
			link.setAttribute('data-leaflet-css', 'true');
			document.head.appendChild(link);
		}

		if (!document.querySelector('script[data-leaflet-js]')) {
			await new Promise<void>((resolve, reject) => {
				const script = document.createElement('script');
				script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
				script.setAttribute('data-leaflet-js', 'true');
				script.onload = () => resolve();
				script.onerror = () => reject(new Error('Failed to load Leaflet'));
				document.head.appendChild(script);
			});
		}
	};

	const initMap = async () => {
		if (!mapContainer || map.lat == null || map.lng == null) return;

		await loadLeaflet();
		const L = getLeaflet();
		if (!L) return;

		if (mapInstance) {
			mapInstance.remove();
			mapInstance = null;
		}

		mapInstance = L.map(mapContainer).setView([map.lat, map.lng], map.zoom ?? 13);

		L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
			attribution: '&copy; OpenStreetMap contributors',
			maxZoom: 19
		}).addTo(mapInstance);

		for (const marker of map.markers ?? [{ lat: map.lat, lng: map.lng, label: map.label }]) {
			const m = L.marker([marker.lat, marker.lng]).addTo(mapInstance);
			if (marker.label) {
				m.bindPopup(marker.label);
			}
		}
	};

	onMount(() => {
		initMap();
	});

	onDestroy(() => {
		if (mapInstance) {
			mapInstance.remove();
			mapInstance = null;
		}
	});

	$: if (mapContainer && map.lat != null && map.lng != null) {
		initMap();
	}
</script>

<div
	class="my-2 rounded-2xl border border-gray-50 dark:border-gray-850 bg-white dark:bg-gray-900 overflow-hidden"
>
	{#if map.label}
		<div class="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-50 dark:border-gray-850">
			{map.label}
		</div>
	{/if}
	<div bind:this={mapContainer} class="w-full h-64 z-0"></div>
</div>
