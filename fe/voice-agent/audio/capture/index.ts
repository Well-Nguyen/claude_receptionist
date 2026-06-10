// Mic capture at 16 kHz mono PCM.
// Uses ScriptProcessorNode (deprecated but universally supported).
// Upgrade to AudioWorkletNode in P1 if main-thread processing causes issues.

export type PcmChunkHandler = (int16: Int16Array) => void;

export type CaptureHandle = {
  stop: () => void;
};

export async function startCapture(onChunk: PcmChunkHandler): Promise<CaptureHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      channelCount: 1,
    },
    video: false,
  });

  // Request 16 kHz; browser resamples from device rate automatically.
  const ctx = new AudioContext({ sampleRate: 16000 });
  const source = ctx.createMediaStreamSource(stream);

  // bufferSize=2048 → ~128 ms chunks at 16 kHz, within 200 ms detection budget.
  // eslint-disable-next-line @typescript-eslint/no-deprecated
  const processor = ctx.createScriptProcessor(2048, 1, 1);

  // Mute the output so mic audio is not played back (avoids echo loop).
  const mute = ctx.createGain();
  mute.gain.value = 0;

  processor.onaudioprocess = (e) => {
    const f32 = e.inputBuffer.getChannelData(0);
    onChunk(float32ToInt16(f32));
  };

  source.connect(processor);
  processor.connect(mute);
  mute.connect(ctx.destination); // must reach destination to keep ScriptProcessorNode firing

  return {
    stop() {
      source.disconnect();
      processor.disconnect();
      mute.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      ctx.close();
    },
  };
}

function float32ToInt16(f32: Float32Array): Int16Array {
  const out = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    const s = Math.max(-1, Math.min(1, f32[i]));
    out[i] = s * (s < 0 ? 0x8000 : 0x7fff);
  }
  return out;
}
