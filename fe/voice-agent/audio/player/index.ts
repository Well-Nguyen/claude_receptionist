// Priority-queue audio player for domino TTS playback.
// Plays audio_chunk events strictly in seq order with no audible gap > 150 ms.
// AudioContext is created lazily on first enqueue (requires prior user gesture).

export type AudioChunk = { seq: number; gen_id: string; data: string };

export type PlayerHandle = {
  enqueue: (chunk: AudioChunk) => void;
  reset: () => void;
};

const SAMPLE_RATE = 24000;

export function createAudioPlayer(): PlayerHandle {
  let ctx: AudioContext | null = null;
  const pending = new Map<number, Float32Array<ArrayBuffer>>();
  let nextSeq = 0;
  let scheduleAt = 0; // ctx.currentTime when next chunk should start

  function getCtx(): AudioContext {
    if (!ctx || ctx.state === "closed") {
      ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
      scheduleAt = 0;
    }
    return ctx;
  }

  function tryPlay(): void {
    const ac = getCtx();
    while (pending.has(nextSeq)) {
      const samples = pending.get(nextSeq)!;
      pending.delete(nextSeq);
      nextSeq++;

      const buf = ac.createBuffer(1, samples.length, SAMPLE_RATE);
      buf.copyToChannel(samples, 0);

      const src = ac.createBufferSource();
      src.buffer = buf;
      src.connect(ac.destination);

      const now = ac.currentTime;
      const start = Math.max(now, scheduleAt);
      src.start(start);
      scheduleAt = start + buf.duration;
    }
  }

  function enqueue(chunk: AudioChunk): void {
    const f32 = b64PcmToFloat32(chunk.data);
    pending.set(chunk.seq, f32);
    tryPlay();
  }

  function reset(): void {
    pending.clear();
    nextSeq = 0;
    scheduleAt = 0;
    if (ctx && ctx.state !== "closed") {
      ctx.close();
      ctx = null;
    }
  }

  return { enqueue, reset };
}

function b64PcmToFloat32(b64: string): Float32Array<ArrayBuffer> {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const int16 = new Int16Array(bytes.buffer as ArrayBuffer);
  const f32 = new Float32Array(int16.length) as Float32Array<ArrayBuffer>;
  for (let i = 0; i < int16.length; i++) {
    f32[i] = int16[i] / (int16[i] < 0 ? 0x8000 : 0x7fff);
  }
  return f32;
}
