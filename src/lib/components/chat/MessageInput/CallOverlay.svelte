<script lang="ts">
	import {config, models, settings, showCallOverlay, TTSWorker, audioQueue, type Model} from '$lib/stores';
	import {get} from 'svelte/store';
	import type {Writable} from 'svelte/store';
	import {onMount, tick, getContext, onDestroy, createEventDispatcher} from 'svelte';

	const dispatch = createEventDispatcher();

	import {blobToFile} from '$lib/utils';
	import {
		getVoiceSilenceTimeoutMs,
		getVoiceVadMinDecibels,
		getVoiceSoundThreshold,
		shouldUseStreamingStt,
		getVoiceStateLabel,
		type VoiceState
	} from '$lib/utils/voice';
	import {generateEmoji} from '$lib/apis';
	import {synthesizeOpenAISpeech, transcribeAudio} from '$lib/apis/audio';
	import type {ChatFile} from '$lib/types/chat';
	import type {KokoroWorker} from '$lib/workers/KokoroWorker';

	import {toast} from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VideoInputMenu from './CallOverlay/VideoInputMenu.svelte';
	
	import {WEBUI_API_BASE_URL} from '$lib/constants';

	const i18n = getContext('i18n');

	type VideoInputDevice = MediaDeviceInfo | { deviceId: string; label: string };
	type ChatStartEvent = CustomEvent<{ id: string }>;
	type ChatContentEvent = CustomEvent<{ id: string; content: string }>;
	type ChatFinishEvent = CustomEvent<{ id: string; content?: string }>;

	export let eventTarget: EventTarget;
	export let submitPrompt: (
		prompt: string,
		options?: { _raw?: boolean }
	) => void | Promise<unknown>;
	export let stopResponse: () => void | Promise<void>;
	export let files: ChatFile[] = [];
	export let chatId: string | null = null;
	export let modelId: string | null = null;

	type SpeechRecognitionResultLike = {
		isFinal: boolean;
		0?: { transcript?: string };
	};

	type SpeechRecognitionEventLike = {
		resultIndex: number;
		results: SpeechRecognitionResultLike[];
	};

	type BrowserSpeechRecognition = {
		continuous: boolean;
		interimResults: boolean;
		lang: string;
		onresult: ((event: SpeechRecognitionEventLike) => void) | null;
		onend: (() => void) | null;
		onerror: (() => void) | null;
		start: () => void;
		stop: () => void;
	};

	type SpeechRecognitionWindow = Window & {
		SpeechRecognition?: new () => BrowserSpeechRecognition;
		webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
	};

	let voiceState: VoiceState = 'listening';
	let userTranscript = '';
	let assistantTranscript = '';
	let streamingFinalTranscript = '';
	let speechRecognition: BrowserSpeechRecognition | null = null;
	const playedSentences = new Set<string>();

	$: silenceTimeoutMs = getVoiceSilenceTimeoutMs($settings);
	$: vadMinDecibels = getVoiceVadMinDecibels($settings?.voiceVadSensitivity);
	$: soundThreshold = getVoiceSoundThreshold($settings?.voiceVadSensitivity);
	$: statusLabel = muted
		? $i18n.t('Muted')
		: getVoiceStateLabel(voiceState, $i18n);

	let wakeLock: WakeLockSentinel | null = null;

	let model: Model | null = null;

	let loading = false;
	let confirmed = false;
	let assistantSpeaking = false;
	let muted = false;

	let emoji: string | null = null;
	let camera = false;
	let cameraStream: MediaStream | null = null;

	let chatStreaming = false;
	let rmsLevel = 0;
	let hasStartedSpeaking = false;
	let mediaRecorder: MediaRecorder | false = false;
	let audioStream: MediaStream | null = null;
	let audioChunks: Blob[] = [];

	let videoInputDevices: VideoInputDevice[] = [];
	let selectedVideoInputDeviceId: string | null = null;

	const getVideoInputDevices = async () => {
		const devices = await navigator.mediaDevices.enumerateDevices();
		videoInputDevices = devices.filter((device) => device.kind === 'videoinput');

		if ('getDisplayMedia' in navigator.mediaDevices) {
			videoInputDevices = [
				...videoInputDevices,
				{
					deviceId: 'screen',
					label: 'Screen Share'
				}
			];
		}

		console.log(videoInputDevices);
		if (selectedVideoInputDeviceId === null && videoInputDevices.length > 0) {
			const savedDeviceId = localStorage.getItem('selectedVideoInputDeviceId');
			if (savedDeviceId && videoInputDevices.some((d) => d.deviceId === savedDeviceId)) {
				selectedVideoInputDeviceId = savedDeviceId;
			} else {
				selectedVideoInputDeviceId = videoInputDevices[0].deviceId;
			}
		}
	};

	const startCamera = async () => {
		await getVideoInputDevices();

		if (cameraStream === null) {
			camera = true;
			await tick();
			try {
				await startVideoStream();
			} catch (err) {
				console.error('Error accessing webcam: ', err);
			}
		}
	};

	const startVideoStream = async () => {
		const video = document.getElementById('camera-feed') as HTMLVideoElement | null;
		if (video) {
			if (selectedVideoInputDeviceId === 'screen') {
				cameraStream = await navigator.mediaDevices.getDisplayMedia({
					video: {
						cursor: 'always'
					} as DisplayMediaStreamOptions['video'],
					audio: false
				});
			} else {
				cameraStream = await navigator.mediaDevices.getUserMedia({
					video: {
						deviceId: selectedVideoInputDeviceId ? { exact: selectedVideoInputDeviceId } : undefined
					}
				});
			}

			if (cameraStream) {
				await getVideoInputDevices();
				video.srcObject = cameraStream;
				await video.play();
			}
		}
	};

	const stopVideoStream = async () => {
		if (cameraStream) {
			const tracks = cameraStream.getTracks();
			tracks.forEach((track: MediaStreamTrack) => track.stop());
		}

		cameraStream = null;
	};

	const takeScreenshot = (): string | undefined => {
		const video = document.getElementById('camera-feed') as HTMLVideoElement | null;
		const canvas = document.getElementById('camera-canvas') as HTMLCanvasElement | null;

		if (!canvas || !video) {
			return;
		}

		const context = canvas.getContext('2d');
		if (!context) {
			return;
		}

		// Make the canvas match the video dimensions
		canvas.width = video.videoWidth;
		canvas.height = video.videoHeight;

		// Draw the image from the video onto the canvas
		context.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);

		// Convert the canvas to a data base64 URL and console log it
		const dataURL = canvas.toDataURL('image/png');
		console.log(dataURL);

		return dataURL;
	};

	const stopCamera = async () => {
		await stopVideoStream();
		camera = false;
	};


	const submitTranscript = async (text: string) => {
		const trimmed = text.trim();
		if (!trimmed) {
			voiceState = 'listening';
			return;
		}

		userTranscript = trimmed;
		assistantTranscript = '';
		playedSentences.clear();
		voiceState = 'processing';

		await submitPrompt(trimmed, { _raw: true });
	};

	const transcribeHandler = async (audioBlob: Blob) => {
		voiceState = 'transcribing';

		const streamingText = streamingFinalTranscript.trim();
		if (streamingText) {
			streamingFinalTranscript = '';
			userTranscript = '';
			await submitTranscript(streamingText);
			return;
		}

		if (!audioBlob || audioBlob.size < 100) {
			voiceState = 'listening';
			return;
		}

		await tick();
		const file = blobToFile(audioBlob, 'recording.wav');
		const language =
			typeof $settings?.audio?.stt?.language === 'string'
				? $settings.audio.stt.language
				: undefined;

		const res = await transcribeAudio(localStorage.token, file, language).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res?.text) {
			await submitTranscript(res.text);
		} else {
			voiceState = 'listening';
		}
	};

	const stopRecordingCallback = async (_continue = true) => {
		if ($showCallOverlay) {
			console.log('%c%s', 'color: red; font-size: 20px;', '🚨 stopRecordingCallback 🚨');

			// deep copy the audioChunks array
			const _audioChunks = audioChunks.slice(0);

			audioChunks = [];
			mediaRecorder = false;

			if (_continue) {
				startRecording();
			}

			if (confirmed) {
				loading = true;
				emoji = null;
				stopStreamingStt();

				if (cameraStream) {
					const imageUrl = takeScreenshot();

					if (imageUrl) {
						files = [
							{
								type: 'image',
								url: imageUrl
							}
						];
					}
				}

				const audioBlob = new Blob(_audioChunks, { type: 'audio/wav' });
				await transcribeHandler(audioBlob);

				confirmed = false;
				loading = false;
			}
		} else {
			audioChunks = [];
			mediaRecorder = false;

			if (audioStream) {
				const tracks = audioStream.getTracks();
				tracks.forEach((track: MediaStreamTrack) => track.stop());
			}
			audioStream = null;
		}
	};


	const stopStreamingStt = () => {
		if (!speechRecognition) return;
		try {
			speechRecognition.onresult = null;
			speechRecognition.onend = null;
			speechRecognition.onerror = null;
			speechRecognition.stop();
		} catch {
			// ignore
		}
		speechRecognition = null;
	};

	const startStreamingStt = () => {
		if (!shouldUseStreamingStt($settings)) return;
		const speechWindow = window as SpeechRecognitionWindow;
		const SpeechRecognitionCtor =
			speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
		if (!SpeechRecognitionCtor) return;

		stopStreamingStt();
		streamingFinalTranscript = '';
		userTranscript = '';

		const recognition = new SpeechRecognitionCtor() as BrowserSpeechRecognition;
		recognition.continuous = true;
		recognition.interimResults = true;
		recognition.lang = localStorage.getItem('locale') || 'en-US';

		recognition.onresult = (event: SpeechRecognitionEventLike) => {
			let interim = '';
			for (let i = event.resultIndex; i < event.results.length; i++) {
				const result = event.results[i];
				const transcript = result[0]?.transcript ?? '';
				if (result.isFinal) {
					streamingFinalTranscript += transcript;
				} else {
					interim += transcript;
				}
			}
			userTranscript = `${streamingFinalTranscript}${interim}`.trim();
		};

		recognition.onerror = () => {
			stopStreamingStt();
		};

		try {
			recognition.start();
			speechRecognition = recognition;
		} catch {
			speechRecognition = null;
		}
	};

	const startRecording = async () => {
		if ($showCallOverlay) {
			if (!audioStream) {
				audioStream = await navigator.mediaDevices.getUserMedia({
					audio: {
						echoCancellation: true,
						noiseSuppression: true,
						autoGainControl: true
					}
				});
			}

			if (audioStream) {
				// hardware track muting disabled to prevent backend translation errors with malformed WebM files
			}

			mediaRecorder = new MediaRecorder(audioStream);

			mediaRecorder.onstart = () => {
				console.log('Recording started');
				audioChunks = [];
			};

			mediaRecorder.ondataavailable = (event: BlobEvent) => {
				if (hasStartedSpeaking) {
					audioChunks.push(event.data);
				}
			};

			mediaRecorder.onstop = (e: Event) => {
				console.log('Recording stopped', audioStream, e);
				stopRecordingCallback();
			};

			voiceState = 'listening';
			analyseAudio(audioStream);
			startStreamingStt();
		}
	};

	const stopAudioStream = async () => {
		stopStreamingStt();
		try {
			if (mediaRecorder) {
				mediaRecorder.stop();
			}
		} catch (error) {
			console.log('Error stopping audio stream:', error);
		}

		if (!audioStream) return;

		audioStream.getAudioTracks().forEach(function (track: MediaStreamTrack) {
			track.stop();
		});

		audioStream = null;
	};

	// Function to calculate the RMS level from time domain data
	const calculateRMS = (data: Uint8Array) => {
		let sumSquares = 0;
		for (let i = 0; i < data.length; i++) {
			const normalizedValue = (data[i] - 128) / 128; // Normalize the data
			sumSquares += normalizedValue * normalizedValue;
		}
		return Math.sqrt(sumSquares / data.length);
	};

	const analyseAudio = (stream: MediaStream) => {
		const audioContext = new AudioContext();
		const audioStreamSource = audioContext.createMediaStreamSource(stream);

		const analyser = audioContext.createAnalyser();
		analyser.minDecibels = vadMinDecibels;
		audioStreamSource.connect(analyser);

		const bufferLength = analyser.frequencyBinCount;

		const timeDomainData = new Uint8Array(analyser.fftSize);

		let lastSoundTime = Date.now();
		hasStartedSpeaking = false;

		console.log('🔊 Sound detection started', lastSoundTime, hasStartedSpeaking);

		const detectSound = () => {
			const processFrame = () => {
				if (!mediaRecorder || !$showCallOverlay) {
					return;
				}

				const pauseVad =
					muted ||
					loading ||
					voiceState === 'processing' ||
					voiceState === 'transcribing' ||
					(assistantSpeaking && !($settings?.voiceInterruption ?? false));

				if (pauseVad) {
					rmsLevel = 0;
					window.requestAnimationFrame(processFrame);
					return;
				}

				analyser.minDecibels = vadMinDecibels;
				analyser.maxDecibels = -30;

				analyser.getByteTimeDomainData(timeDomainData);

				// Calculate RMS level from time domain data
				rmsLevel = calculateRMS(timeDomainData);

				const hasSound = rmsLevel > soundThreshold;
				if (hasSound) {
					if (mediaRecorder && mediaRecorder.state !== 'recording') {
						mediaRecorder.start();
					}

					if (!hasStartedSpeaking) {
						hasStartedSpeaking = true;
						stopAllAudio();
					}

					lastSoundTime = Date.now();
				}

				// Start silence detection only after initial speech/noise has been detected
				if (hasStartedSpeaking) {
					if (Date.now() - lastSoundTime > silenceTimeoutMs) {
						confirmed = true;

						if (mediaRecorder) {
							mediaRecorder.stop();
							return;
						}
					}
				}

				window.requestAnimationFrame(processFrame);
			};

			window.requestAnimationFrame(processFrame);
		};

		detectSound();
	};

	let finishedMessages: Record<string, boolean> = {};
	let currentMessageId: string | null = null;
	let currentUtterance: SpeechSynthesisUtterance | null = null;

	const getVoiceId = (): string | undefined => {
		const modelMeta = model?.info?.meta as { tts?: { voice?: string } } | undefined;
		const modelVoice = modelMeta?.tts?.voice;
		if (typeof modelVoice === 'string') {
			return modelVoice;
		}
		const settingsVoice =
			typeof $settings?.audio?.tts?.voice === 'string' ? $settings.audio.tts.voice : undefined;
		const configVoice =
			typeof $config?.audio?.tts?.voice === 'string' ? $config.audio.tts.voice : undefined;
		const defaultVoice =
			typeof $settings?.audio?.tts?.defaultVoice === 'string'
				? $settings.audio.tts.defaultVoice
				: undefined;

		if (defaultVoice === configVoice) {
			return settingsVoice ?? configVoice;
		}
		return configVoice;
	};

	const speakSpeechSynthesisHandler = (content: string) => {
		if ($showCallOverlay) {
			return new Promise((resolve) => {
				let voices = [];
				const getVoicesLoop = setInterval(async () => {
					voices = await speechSynthesis.getVoices();
					if (voices.length > 0) {
						clearInterval(getVoicesLoop);

						const voiceId = getVoiceId();
						const voice = voices?.filter((v) => v.voiceURI === voiceId)?.at(0) ?? undefined;

						currentUtterance = new SpeechSynthesisUtterance(content);
						currentUtterance.rate =
							typeof $settings?.audio?.tts?.playbackRate === 'number'
								? $settings.audio.tts.playbackRate
								: 1;

						if (voice) {
							currentUtterance.voice = voice;
						}

						speechSynthesis.speak(currentUtterance);
						currentUtterance.onend = async (e: Event) => {
							await new Promise((r) => setTimeout(r, 200));
							resolve(e);
						};
					}
				}, 100);
			});
		} else {
			return Promise.resolve();
		}
	};

	const stopAllAudio = async () => {
		assistantSpeaking = false;
		if (voiceState === 'speaking') {
			voiceState = 'listening';
		}

		if (chatStreaming) {
			await stopResponse();
		}

		get(audioQueue)?.stop();

		if (currentUtterance) {
			speechSynthesis.cancel();
			currentUtterance = null;
		}
	};


	const enqueueSentenceForTts = async (content: string, messageId: string) => {
		const sentence = content.trim();
		if (!sentence || playedSentences.has(sentence)) return;
		playedSentences.add(sentence);

		const queue = get(audioQueue);
		if (!queue) return;

		queue.setId(messageId);
		queue.setPlaybackRate(
			typeof $settings?.audio?.tts?.playbackRate === 'number' ? $settings.audio.tts.playbackRate : 1
		);
		queue.onStopped = () => {
			assistantSpeaking = false;
			if (voiceState === 'speaking') {
				voiceState = 'listening';
			}
		};

		assistantSpeaking = true;
		voiceState = 'speaking';
		assistantTranscript = assistantTranscript
			? `${assistantTranscript} ${sentence}`
			: sentence;

		if ($settings?.showEmojiInCall ?? false) {
			const generatedEmoji = await generateEmoji(
				localStorage.token,
				modelId ?? '',
				sentence,
				chatId ?? ''
			);
			if (generatedEmoji) {
				emoji = generatedEmoji;
			}
		}

		if (($config?.audio?.tts?.engine ?? '') === '') {
			await speakSpeechSynthesisHandler(sentence);
			if (!get(audioQueue)?.isActive()) {
				assistantSpeaking = false;
				if (voiceState === 'speaking') {
					voiceState = 'listening';
				}
			}
			return;
		}

		if ($settings?.audio?.tts?.engine === 'browser-kokoro') {
			const worker = get(TTSWorker as Writable<KokoroWorker | null>);
			if (!worker) return;
			const url = await worker.generate({ text: sentence, voice: getVoiceId() ?? '' }).catch(() => null);
			if (url) queue.enqueue(url);
			return;
		}

		const res = await synthesizeOpenAISpeech(localStorage.token, getVoiceId() ?? '', sentence).catch(
			() => null
		);
		if (!res) return;
		const blob = await res.blob();
		queue.enqueue(URL.createObjectURL(blob));
	};

	const chatStartHandler = async (e: Event) => {
		const { id } = (e as ChatStartEvent).detail;
		chatStreaming = true;
		currentMessageId = id;
		assistantTranscript = '';
		playedSentences.clear();
		voiceState = 'processing';
	};

	const chatEventHandler = async (e: Event) => {
		const { id, content } = (e as ChatContentEvent).detail;
		if (currentMessageId !== id) return;
		await enqueueSentenceForTts(content, id);
	};

	const chatFinishHandler = async (e: Event) => {
		const { id, content } = (e as ChatFinishEvent).detail;
		finishedMessages[id] = true;
		chatStreaming = false;
		if (typeof content === 'string' && content.trim()) {
			assistantTranscript = content.trim();
		}
		if (!get(audioQueue)?.isActive()) {
			assistantSpeaking = false;
			voiceState = 'listening';
		}
	};


	const toggleMute = () => {
		muted = !muted;
		if (!muted) {
			voiceState = 'listening';
		}
		if (muted && hasStartedSpeaking) {
			// Abort the ongoing recording so it doesn't accidentally send a partial sentence
			hasStartedSpeaking = false;
			confirmed = false;
			audioChunks = [];
			if (mediaRecorder && mediaRecorder.state === 'recording') {
				mediaRecorder.stop();
			}
		}
	};

	let wasAssistantSpeaking = false;
	$: {
		if (assistantSpeaking && !wasAssistantSpeaking) {
			wasAssistantSpeaking = true;
		} else if (!assistantSpeaking && wasAssistantSpeaking) {
			wasAssistantSpeaking = false;
			// Auto unmute when AI finishes speaking
			if (muted) {
				muted = false;
			}
		}
	}

	const handleKeydown = (e: KeyboardEvent) => {
		// Only handle M key when not typing in an input/textarea
		if (e.key === 'm' || e.key === 'M') {
			const target = e.target as HTMLElement;
			if (
				target.tagName !== 'INPUT' &&
				target.tagName !== 'TEXTAREA' &&
				!target.isContentEditable
			) {
				e.preventDefault();
				toggleMute();
			}
		}
	};

	onMount(() => {
		const setWakeLock = async () => {
			try {
				wakeLock = await navigator.wakeLock.request('screen');
			} catch (err) {
				// The Wake Lock request has failed - usually system related, such as battery.
				console.log(err);
			}

			if (wakeLock) {
				// Add a listener to release the wake lock when the page is unloaded
				wakeLock.addEventListener('release', () => {
					// the wake lock has been released
					console.log('Wake Lock released');
				});
			}
		};

		const init = async () => {
			if ('wakeLock' in navigator) {
				await setWakeLock();

				document.addEventListener('visibilitychange', async () => {
					// Re-request the wake lock if the document becomes visible
					if (wakeLock !== null && document.visibilityState === 'visible') {
						await setWakeLock();
					}
				});
			}

			model = $models.find((m) => m.id === modelId) ?? null;

			startRecording();

			eventTarget.addEventListener('chat:start', chatStartHandler);
			eventTarget.addEventListener('chat', chatEventHandler);
			eventTarget.addEventListener('chat:finish', chatFinishHandler);

			document.addEventListener('keydown', handleKeydown);
		};

		void init();

		return () => {
			void (async () => {
				await stopAllAudio();

				stopAudioStream();

				eventTarget.removeEventListener('chat:start', chatStartHandler);
				eventTarget.removeEventListener('chat', chatEventHandler);
				eventTarget.removeEventListener('chat:finish', chatFinishHandler);

				document.removeEventListener('keydown', handleKeydown);

				await tick();

				await stopAllAudio();

				await stopRecordingCallback(false);
				await stopCamera();
			})();
		};
	});

	onDestroy(() => {
		void (async () => {
			await stopAllAudio();
			await stopRecordingCallback(false);
			await stopCamera();

			await stopAudioStream();
			eventTarget.removeEventListener('chat:start', chatStartHandler);
			eventTarget.removeEventListener('chat', chatEventHandler);
			eventTarget.removeEventListener('chat:finish', chatFinishHandler);

			document.removeEventListener('keydown', handleKeydown);


			await tick();

			await stopAllAudio();
		})();
	});</script>

{#if $showCallOverlay}
	<div class="max-w-lg w-full h-full max-h-[100dvh] flex flex-col justify-between p-3 md:p-6">
		{#if camera}
			<button
				type="button"
				class="flex justify-center items-center w-full h-20 min-h-20"
				on:click={() => {
					if (assistantSpeaking) {
						stopAllAudio();
					}
				}}
			>
				{#if emoji}
					<div
						class="  transition-all rounded-full"
						style="font-size:{rmsLevel * 100 > 4
							? '4.5'
							: rmsLevel * 100 > 2
								? '4.25'
								: rmsLevel * 100 > 1
									? '3.75'
									: '3.5'}rem;width: 100%; text-align:center;"
					>
						{emoji}
					</div>
				{:else if voiceState === 'processing' || voiceState === 'speaking' || assistantSpeaking}
					<svg
						class="size-12 text-gray-900 dark:text-gray-400"
						viewBox="0 0 24 24"
						fill="currentColor"
						xmlns="http://www.w3.org/2000/svg"
						><style>
							.spinner_qM83 {
								animation: spinner_8HQG 1.05s infinite;
							}
							.spinner_oXPr {
								animation-delay: 0.1s;
							}
							.spinner_ZTLf {
								animation-delay: 0.2s;
							}
							@keyframes spinner_8HQG {
								0%,
								57.14% {
									animation-timing-function: cubic-bezier(0.33, 0.66, 0.66, 1);
									transform: translate(0);
								}
								28.57% {
									animation-timing-function: cubic-bezier(0.33, 0, 0.66, 0.33);
									transform: translateY(-6px);
								}
								100% {
									transform: translate(0);
								}
							}
						</style><circle class="spinner_qM83" cx="4" cy="12" r="3"></circle><circle
							class="spinner_qM83 spinner_oXPr"
							cx="12"
							cy="12"
							r="3"></circle><circle class="spinner_qM83 spinner_ZTLf" cx="20" cy="12" r="3"></circle></svg
					>
				{:else}
					<div
						class=" {rmsLevel * 100 > 4
							? ' size-[4.5rem]'
							: rmsLevel * 100 > 2
								? ' size-16'
								: rmsLevel * 100 > 1
									? 'size-14'
									: 'size-12'}  transition-all rounded-full bg-cover bg-center bg-no-repeat"
						style={`background-image: url('${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}&voice=true');`}
					></div>
				{/if}
				<!-- navbar -->
			</button>
		{/if}

		<div class="flex justify-center items-center flex-1 h-full w-full max-h-full">
			{#if !camera}
				<button
					type="button"
					on:click={() => {
						if (assistantSpeaking) {
							stopAllAudio();
						}
					}}
				>
					{#if emoji}
						<div
							class="  transition-all rounded-full"
							style="font-size:{rmsLevel * 100 > 4
								? '13'
								: rmsLevel * 100 > 2
									? '12'
									: rmsLevel * 100 > 1
										? '11.5'
										: '11'}rem;width:100%;text-align:center;"
						>
							{emoji}
						</div>
					{:else if voiceState === 'processing' || voiceState === 'speaking' || assistantSpeaking}
						<svg
							class="size-44 text-gray-900 dark:text-gray-400"
							viewBox="0 0 24 24"
							fill="currentColor"
							xmlns="http://www.w3.org/2000/svg"
							><style>
								.spinner_qM83 {
									animation: spinner_8HQG 1.05s infinite;
								}
								.spinner_oXPr {
									animation-delay: 0.1s;
								}
								.spinner_ZTLf {
									animation-delay: 0.2s;
								}
								@keyframes spinner_8HQG {
									0%,
									57.14% {
										animation-timing-function: cubic-bezier(0.33, 0.66, 0.66, 1);
										transform: translate(0);
									}
									28.57% {
										animation-timing-function: cubic-bezier(0.33, 0, 0.66, 0.33);
										transform: translateY(-6px);
									}
									100% {
										transform: translate(0);
									}
								}
							</style><circle class="spinner_qM83" cx="4" cy="12" r="3"></circle><circle
								class="spinner_qM83 spinner_oXPr"
								cx="12"
								cy="12"
								r="3"></circle><circle class="spinner_qM83 spinner_ZTLf" cx="20" cy="12" r="3"></circle></svg
						>
					{:else}
						<div
							class=" {rmsLevel * 100 > 4
								? ' size-52'
								: rmsLevel * 100 > 2
									? 'size-48'
									: rmsLevel * 100 > 1
										? 'size-44'
										: 'size-40'} transition-all rounded-full bg-cover bg-center bg-no-repeat"
							style={`background-image: url('${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}&voice=true');`}
						></div>
					{/if}
				</button>
			{:else}
				<div class="relative flex video-container w-full max-h-full pt-2 pb-4 md:py-6 px-2 h-full">
					<video
						id="camera-feed"
						autoplay
						class="rounded-2xl h-full min-w-full object-cover object-center"
						playsinline
					></video>

					<canvas id="camera-canvas" style="display:none;"></canvas>

					<div class=" absolute top-4 md:top-8 left-4">
						<button
							type="button"
							class="p-1.5 text-white cursor-pointer backdrop-blur-xl bg-black/10 rounded-full"
							aria-label={$i18n.t('Close camera')}
							on:click={() => {
								stopCamera();
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-6"
							>
								<path
									d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"></path>
							</svg>
						</button>
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col items-center gap-3 pb-4 w-full px-2">
			<div class="w-full max-w-md space-y-2 text-center">
				<div class="text-sm font-medium">{statusLabel}</div>
				{#if userTranscript}
					<div class="text-xs text-gray-600 dark:text-gray-300 line-clamp-3">
						<span class="font-medium">{$i18n.t('You')}:</span> {userTranscript}
					</div>
				{/if}
				{#if assistantTranscript}
					<div class="text-xs text-gray-600 dark:text-gray-300 line-clamp-4">
						<span class="font-medium">{$i18n.t('Assistant')}:</span> {assistantTranscript}
					</div>
				{/if}
			</div>
			<button
				type="button"
				class="z-10"
				on:click={() => {
					if (assistantSpeaking) {
						stopAllAudio();
					}
				}}
			>
				<div class="line-clamp-1 text-xs text-gray-500 dark:text-gray-400">
					{assistantSpeaking ? $i18n.t('Tap to interrupt') : ''}
				</div>
			</button>

			<div class="flex items-center justify-center gap-4 z-10">
				{#if camera}
					<VideoInputMenu
						devices={videoInputDevices}
						on:change={async (e) => {
							console.log(e.detail);
							selectedVideoInputDeviceId = e.detail;
							localStorage.setItem('selectedVideoInputDeviceId', e.detail);
							await stopVideoStream();
							await startVideoStream();
						}}
					>
						<button class="p-3 rounded-full bg-gray-50 dark:bg-gray-900" type="button" aria-label={$i18n.t('Switch camera')}>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-5"
							>
								<path
									fill-rule="evenodd"
									d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.433a.75.75 0 0 0 0-1.5H3.989a.75.75 0 0 0-.75.75v4.242a.75.75 0 0 0 1.5 0v-2.43l.31.31a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm1.23-3.723a.75.75 0 0 0 .219-.53V2.929a.75.75 0 0 0-1.5 0V5.36l-.31-.31A7 7 0 0 0 3.239 8.188a.75.75 0 1 0 1.448.389A5.5 5.5 0 0 1 13.89 6.11l.311.31h-2.432a.75.75 0 0 0 0 1.5h4.243a.75.75 0 0 0 .53-.219Z"
									clip-rule="evenodd"></path>
							</svg>
						</button>
					</VideoInputMenu>
				{:else}
					<Tooltip content={$i18n.t('Camera')}>
						<button
							class="p-3 rounded-full bg-gray-50 dark:bg-gray-900"
							type="button"
							aria-label={$i18n.t('Camera')}
							on:click={async () => {
								await navigator.mediaDevices.getUserMedia({ video: true });
								startCamera();
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z"></path>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z"></path>
							</svg>
						</button>
					</Tooltip>
				{/if}

				<Tooltip content={muted ? $i18n.t('Unmute') + ' (M)' : $i18n.t('Mute') + ' (M)'}>
					<button
						class="p-3 rounded-full transition-colors duration-200 {muted
							? 'bg-red-500 text-white'
							: 'bg-gray-50 dark:bg-gray-900'}"
						type="button"
						aria-label={muted ? $i18n.t('Unmute') : $i18n.t('Mute')}
						on:click={toggleMute}
					>
						{#if muted}
							<!-- Mic Off icon -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z"></path>
								<line
									x1="3"
									y1="3"
									x2="21"
									y2="21"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linecap="round"></line>
							</svg>
						{:else}
							<!-- Mic On icon -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z"></path>
							</svg>
						{/if}
					</button>
				</Tooltip>

				<button
					class="p-3 rounded-full bg-gray-50 dark:bg-gray-900"
					aria-label={$i18n.t('End call')}
					on:click={async () => {
						await stopAudioStream();
						await stopVideoStream();

						console.log(audioStream);
						console.log(cameraStream);

						showCallOverlay.set(false);
						dispatch('close');
					}}
					type="button"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-5"
					>
						<path
							d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"></path>
					</svg>
				</button>
			</div>
		</div>
	</div>
{/if}
