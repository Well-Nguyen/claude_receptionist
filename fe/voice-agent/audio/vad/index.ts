// Energy-based VAD for P0 skeleton.
// Silero WASM integration replaces this in P1.
//
// Tracks RMS amplitude against a threshold to distinguish speech from silence.
// Fires onSpeechEnd (= utterance_end) exactly once per utterance via endFired guard.

export type VadConfig = {
  silenceMs: number;    // silence duration to trigger utterance end (default 800)
  minSpeechMs: number;  // minimum speech duration to count as real utterance (default 250)
  // threshold is RMS amplitude 0-1; P0 default ~0.02 (Silero uses probability, different scale)
  threshold: number;
  sampleRate: number;
};

const DEFAULTS: VadConfig = {
  silenceMs: 800,
  minSpeechMs: 250,
  threshold: 0.02,
  sampleRate: 16000,
};

export type VadCallbacks = {
  onSpeechStart?: () => void;
  onSpeechEnd: () => void;
};

export type VadHandle = {
  processChunk: (pcm: Int16Array) => void;
  reset: () => void;
};

type State = "idle" | "speaking" | "trailing_silence";

export function createVad(callbacks: VadCallbacks, config: Partial<VadConfig> = {}): VadHandle {
  const cfg: VadConfig = { ...DEFAULTS, ...config };

  const silenceSampleLimit = Math.round((cfg.silenceMs / 1000) * cfg.sampleRate);
  const minSpeechSampleLimit = Math.round((cfg.minSpeechMs / 1000) * cfg.sampleRate);

  let state: State = "idle";
  let speechSamples = 0;
  let silenceSamples = 0;
  let endFired = false;  // single-fire guard per utterance

  function rms(pcm: Int16Array): number {
    let sum = 0;
    for (let i = 0; i < pcm.length; i++) {
      const s = pcm[i] / 32768;
      sum += s * s;
    }
    return Math.sqrt(sum / pcm.length);
  }

  function processChunk(pcm: Int16Array): void {
    const isSpeech = rms(pcm) >= cfg.threshold;

    if (state === "idle") {
      if (isSpeech) {
        state = "speaking";
        speechSamples = pcm.length;
        silenceSamples = 0;
        endFired = false;
        if (speechSamples >= minSpeechSampleLimit) {
          callbacks.onSpeechStart?.();
        }
      }
    } else if (state === "speaking") {
      if (isSpeech) {
        const wasBeforeMin = speechSamples < minSpeechSampleLimit;
        speechSamples += pcm.length;
        if (wasBeforeMin && speechSamples >= minSpeechSampleLimit) {
          callbacks.onSpeechStart?.();
        }
      } else {
        state = "trailing_silence";
        silenceSamples = pcm.length;
      }
    } else {
      // trailing_silence
      if (isSpeech) {
        state = "speaking";
        speechSamples += pcm.length;
        silenceSamples = 0;
      } else {
        silenceSamples += pcm.length;
        if (silenceSamples >= silenceSampleLimit && !endFired) {
          if (speechSamples >= minSpeechSampleLimit) {
            endFired = true;
            callbacks.onSpeechEnd();
          }
          // reset whether we fire or discard (false start)
          state = "idle";
          speechSamples = 0;
          silenceSamples = 0;
        }
      }
    }
  }

  function reset(): void {
    state = "idle";
    speechSamples = 0;
    silenceSamples = 0;
    endFired = false;
  }

  return { processChunk, reset };
}
