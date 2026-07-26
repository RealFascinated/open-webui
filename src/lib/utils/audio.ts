type AudioQueueEvent = 'stop' | 'empty-queue' | 'id-change';

interface AudioQueueStopDetail {
	event: AudioQueueEvent;
	id: string | null;
}

export type OnStoppedCallback = (detail: AudioQueueStopDetail) => void;

export class AudioQueue {
	private audio: HTMLAudioElement;
	private queue: string[] = [];
	private current: string | null = null;
	private readonly _onEnded = () => this.next();

	id: string | null = null;
	onStopped: OnStoppedCallback | null = null;

	constructor(audioElement: HTMLAudioElement) {
		this.audio = audioElement;
		this.audio.addEventListener('ended', this._onEnded);
	}

	setId(newId: string) {
		if (this.id === newId) return;

		this.#halt();
		this.id = newId;
		this.onStopped?.({ event: 'id-change', id: newId });
	}

	setPlaybackRate(rate: number) {
		this.audio.playbackRate = rate;
	}

	enqueue(url: string) {
		this.queue.push(url);
		this.#ensurePlayback();
	}

	play() {
		if (!this.current && this.queue.length > 0) {
			this.next();
		} else {
			void this.#playCurrent();
		}
	}

	next() {
		this.current = this.queue.shift() ?? null;

		if (this.current) {
			void this.#playCurrent();
		} else {
			this.#halt();
			this.onStopped?.({ event: 'empty-queue', id: this.id });
		}
	}

	stop() {
		this.#halt();
		this.onStopped?.({ event: 'stop', id: this.id });
	}

	isActive(): boolean {
		return Boolean(this.current) || this.queue.length > 0 || !this.audio.paused;
	}

	destroy() {
		this.audio.removeEventListener('ended', this._onEnded);
		this.#halt();
		this.onStopped = null;
	}

	/**
	 * Pause audio and clear queue without firing onStopped.
	 * Callers that need the callback should invoke it themselves.
	 */
	#halt() {
		this.audio.pause();
		this.audio.currentTime = 0;
		this.audio.muted = false;
		this.audio.removeAttribute('src');
		this.audio.load();
		this.queue = [];
		this.current = null;
	}

	#ensurePlayback() {
		if (!this.audio.paused) {
			return;
		}

		if (!this.current) {
			this.next();
			return;
		}

		// Recover from a failed play() that left a stale current item.
		if (this.audio.ended || this.audio.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
			this.current = null;
			this.next();
		}
	}

	#playCurrent() {
		if (!this.current) {
			return;
		}

		const url = this.current;
		this.audio.src = url;
		// Muted autoplay unlock: required for TTS after async streaming delays.
		this.audio.muted = true;

		const playPromise = this.audio.play();
		if (!playPromise) {
			this.audio.muted = false;
			return;
		}

		playPromise
			.then(() => {
				if (this.current === url) {
					this.audio.muted = false;
				}
			})
			.catch((error) => {
				console.error('Audio playback failed:', error);
				if (this.current === url) {
					this.current = null;
					this.next();
				}
			});
	}
}
