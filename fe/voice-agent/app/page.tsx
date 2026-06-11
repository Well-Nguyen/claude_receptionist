"use client";

import { useEffect, useRef, useState } from "react";
import Landing from "@/pages/Landing";
import { createWsClient, WsClient } from "@/ws/client";
import { startCapture, CaptureHandle } from "@/audio/capture";
import { createVad } from "@/audio/vad";
import { createAudioPlayer, PlayerHandle } from "@/audio/player";

type AppState = "connecting" | "landing" | "greeting" | "listening" | "thinking" | "speaking";

type Transcript = { role: "user" | "assistant"; text: string };

const WS_URL =
  process.env.NEXT_PUBLIC_AI_WS_URL ?? "ws://localhost:7700/ws";

export default function Page() {
  const [appState, setAppState] = useState<AppState>("connecting");
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const sessionIdRef = useRef<string | null>(null);
  const wsRef = useRef<WsClient | null>(null);
  const playerRef = useRef<PlayerHandle | null>(null);
  const currentGenIdRef = useRef<string | null>(null);

  useEffect(() => {
    const client = createWsClient(WS_URL, {
      onOpen: () => {
        // wait for session_start before showing landing
      },
      onClose: () => setAppState("connecting"),
      onEvent: (e) => {
        if (e.event === "session_start") {
          sessionIdRef.current = e.session_id;
          playerRef.current?.reset();
          setTranscripts([]);
          setAppState("landing");
        } else if (e.event === "state_change") {
          const s = e.state.toLowerCase() as AppState;
          setAppState(s);
        } else if (e.event === "transcript") {
          setTranscripts((prev) => [...prev, { role: e.role, text: e.text }]);
        } else if (e.event === "audio_chunk") {
          currentGenIdRef.current = e.gen_id;
          if (!playerRef.current) {
            playerRef.current = createAudioPlayer();
          }
          playerRef.current.enqueue({ seq: e.seq, gen_id: e.gen_id, data: e.data });
        }
      },
    });
    wsRef.current = client;
    return () => client.close();
  }, []);

  function handleLanguageSelect(lang: "en" | "vi") {
    const sid = sessionIdRef.current;
    if (!sid || !wsRef.current) return;
    wsRef.current.send({ event: "language_select", session_id: sid, language: lang });
    // optimistic: show greeting immediately, server will confirm with state_change
    setAppState("greeting");
  }

  // Start mic capture + VAD only while LISTENING.
  useEffect(() => {
    if (appState !== "listening") return;

    let captureHandle: CaptureHandle | null = null;
    let cancelled = false;
    let voiceActive = false;

    const vad = createVad({
      onSpeechStart: () => {
        voiceActive = true;
      },
      onSpeechEnd: () => {
        voiceActive = false;
        const sid = sessionIdRef.current;
        if (sid && wsRef.current) {
          wsRef.current.send({ event: "utterance_end", session_id: sid });
        }
      },
    });

    startCapture((pcm) => {
      vad.processChunk(pcm);
      if (voiceActive && wsRef.current) {
        wsRef.current.sendBinary(pcm.buffer as ArrayBuffer);
      }
    })
      .then((h) => {
        if (cancelled) {
          h.stop();
        } else {
          captureHandle = h;
        }
      })
      .catch((err) => {
        console.error("Mic access error:", err);
      });

    return () => {
      cancelled = true;
      captureHandle?.stop();
      vad.reset();
    };
  }, [appState]);

  // Barge-in: mic capture during SPEAKING to detect user speech ≥ BARGE_IN_MIN_MS.
  useEffect(() => {
    if (appState !== "speaking") return;

    let captureHandle: CaptureHandle | null = null;
    let cancelled = false;
    let fired = false;

    const vad = createVad({
      onSpeechStart: () => {
        if (fired) return;
        fired = true;
        playerRef.current?.reset();
        const sid = sessionIdRef.current;
        const genId = currentGenIdRef.current;
        if (sid && genId && wsRef.current) {
          wsRef.current.send({ event: "interrupt", gen_id: genId });
        }
      },
      onSpeechEnd: () => {},
    }, {
      minSpeechMs: 300,
      threshold: 0.04, // raised threshold: AEC guard against agent audio bleed
    });

    startCapture((pcm) => {
      vad.processChunk(pcm);
    })
      .then((h) => {
        if (cancelled) {
          h.stop();
        } else {
          captureHandle = h;
        }
      })
      .catch((err) => {
        console.error("Barge-in mic error:", err);
      });

    return () => {
      cancelled = true;
      captureHandle?.stop();
      vad.reset();
    };
  }, [appState]);

  if (appState === "connecting") {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", color: "#c0392b", fontSize: "1.5rem" }}>
        Connecting…
      </div>
    );
  }

  if (appState === "landing") {
    return <Landing onLanguageSelect={handleLanguageSelect} />;
  }

  // GREETING / LISTENING / THINKING / SPEAKING
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", color: "#c0392b" }}>
      <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid #eee", display: "flex", alignItems: "center", gap: "1rem" }}>
        <span style={{ fontSize: "1.25rem", fontWeight: 700, textTransform: "uppercase" }}>{appState}</span>
        <span style={{ fontSize: "0.85rem", color: "#888" }}>Session: {sessionIdRef.current?.slice(0, 8)}</span>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "1rem 1.5rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {transcripts.map((t, i) => (
          <div
            key={i}
            style={{
              alignSelf: t.role === "user" ? "flex-end" : "flex-start",
              background: t.role === "user" ? "#c0392b" : "#f0f0f0",
              color: t.role === "user" ? "#fff" : "#222",
              padding: "0.5rem 0.9rem",
              borderRadius: "1rem",
              maxWidth: "70%",
              fontSize: "1rem",
            }}
          >
            {t.text}
          </div>
        ))}
      </div>
    </div>
  );
}
