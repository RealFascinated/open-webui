/** Map Open-Meteo WMO weather codes to a representative emoji. */
export const weatherCodeToEmoji = (code?: number | null): string => {
	if (code == null) return '🌡️';

	if (code === 0) return '☀️';
	if (code <= 3) return '⛅';
	if (code <= 48) return '🌫️';
	if (code <= 57) return '🌦️';
	if (code <= 67) return '🌧️';
	if (code <= 77) return '❄️';
	if (code <= 82) return '🌧️';
	if (code <= 86) return '🌨️';
	if (code <= 99) return '⛈️';

	return '🌡️';
};
