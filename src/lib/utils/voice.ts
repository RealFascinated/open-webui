export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'processing' | 'speaking';

export type VoiceVadSensitivity = 'low' | 'medium' | 'high';

export const DEFAULT_VOICE_SILENCE_TIMEOUT_MS = 2000;
export const DEFAULT_VOICE_VAD_SENSITIVITY: VoiceVadSensitivity = 'medium';

export function getVoiceSilenceTimeoutMs(
	settings?: { voiceSilenceTimeoutMs?: number | null } | null
): number {
	const value = settings?.voiceSilenceTimeoutMs;
	if (typeof value === 'number' && Number.isFinite(value)) {
		return Math.min(Math.max(Math.round(value), 500), 10000);
	}
	return DEFAULT_VOICE_SILENCE_TIMEOUT_MS;
}

export function getVoiceVadMinDecibels(
	sensitivity?: VoiceVadSensitivity | string | null
): number {
	switch (sensitivity) {
		case 'low':
			return -50;
		case 'high':
			return -60;
		default:
			return -55;
	}
}

export function getVoiceSoundThreshold(
	sensitivity?: VoiceVadSensitivity | string | null
): number {
	switch (sensitivity) {
		case 'low':
			return 0.035;
		case 'high':
			return 0.015;
		default:
			return 0.025;
	}
}

export function canUseStreamingStt(): boolean {
	if (typeof window === 'undefined') return false;
	return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
}

export function shouldUseStreamingStt(
	settings?: { voiceStreamingStt?: boolean | null } | null
): boolean {
	if (settings?.voiceStreamingStt === false) return false;
	return canUseStreamingStt();
}

export function getVoiceStateLabel(state: VoiceState, i18n: { t: (key: string) => string }): string {
	switch (state) {
		case 'listening':
			return i18n.t('Listening...');
		case 'transcribing':
			return i18n.t('Transcribing...');
		case 'processing':
			return i18n.t('Thinking...');
		case 'speaking':
			return i18n.t('Tap to interrupt');
		default:
			return i18n.t('Ready');
	}
}
