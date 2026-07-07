export type GeolocationResult =
	| { latitude: number; longitude: number; accuracy: number }
	| { error: 'denied' | 'unavailable' };

export function requestBrowserLocation(timeoutMs = 10000): Promise<GeolocationResult> {
	return new Promise((resolve) => {
		if (typeof navigator === 'undefined' || !navigator.geolocation) {
			resolve({ error: 'unavailable' });
			return;
		}

		navigator.geolocation.getCurrentPosition(
			(position) => {
				resolve({
					latitude: position.coords.latitude,
					longitude: position.coords.longitude,
					accuracy: position.coords.accuracy
				});
			},
			() => resolve({ error: 'denied' }),
			{ timeout: timeoutMs, maximumAge: 300_000, enableHighAccuracy: false }
		);
	});
}
