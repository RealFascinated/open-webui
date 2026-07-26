<script lang="ts">
	import { getContext } from 'svelte';

	import { weatherCodeToEmoji } from '$lib/utils/weatherIcons';

	const i18n = getContext('i18n');

	export let weather: {
		location?: string;
		temperature?: number;
		temperature_unit?: string;
		feels_like?: number;
		humidity?: number;
		wind_speed?: number;
		wind_speed_unit?: string;
		description?: string;
		weather_code?: number;
		time?: string;
	} = {};

	$: weatherEmoji = weatherCodeToEmoji(weather.weather_code);
	$: temperatureUnit = weather.temperature_unit ?? '°C';
</script>

<div
	class="rounded-2xl border border-gray-50 dark:border-gray-850 bg-white dark:bg-gray-900 overflow-hidden"
>
	<div class="px-4 py-3.5">
		<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{weather.location}</div>
		<div class="flex items-end gap-3">
			<div class="text-3xl leading-none" aria-hidden="true" title={weather.description}>
				{weatherEmoji}
			</div>
			<div class="text-3xl font-semibold text-gray-900 dark:text-gray-100 leading-none">
				{weather.temperature ?? '—'}{temperatureUnit}
			</div>
			<div class="text-sm text-gray-600 dark:text-gray-300 pb-0.5">{weather.description}</div>
		</div>
		<div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
			{#if weather.feels_like != null}
				<span
					>{$i18n.t('Feels like {{TEMP}}', {
						TEMP: `${weather.feels_like}${temperatureUnit}`
					})}</span
				>
			{/if}
			{#if weather.humidity != null}
				<span>{$i18n.t('Humidity {{VALUE}}%', { VALUE: weather.humidity })}</span>
			{/if}
			{#if weather.wind_speed != null}
				<span
					>{$i18n.t('Wind {{SPEED}} {{UNIT}}', {
						SPEED: weather.wind_speed,
						UNIT: weather.wind_speed_unit ?? 'km/h'
					})}</span
				>
			{/if}
		</div>
	</div>
</div>
