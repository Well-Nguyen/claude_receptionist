export type AppEvent =
  | { event: "session_start"; session_id: string; language: string | null }
  | { event: "state_change"; state: string }
  | { event: "transcript"; role: "user" | "assistant"; text: string; session_id: string }
  | { event: "audio_chunk"; seq: number; gen_id: string; data: string };

export type WsHandlers = {
  onEvent: (e: AppEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
};

export type WsClient = {
  send: (payload: object) => void;
  sendBinary: (buffer: ArrayBuffer) => void;
  close: () => void;
};

export function createWsClient(url: string, handlers: WsHandlers): WsClient {
  const ws = new WebSocket(url);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => handlers.onOpen?.();
  ws.onclose = () => handlers.onClose?.();

  ws.onmessage = (msg) => {
    if (typeof msg.data !== "string") return;
    try {
      const e = JSON.parse(msg.data) as AppEvent;
      handlers.onEvent(e);
    } catch {
      // ignore malformed frames
    }
  };

  return {
    send: (payload) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload));
      }
    },
    sendBinary: (buffer) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(buffer);
      }
    },
    close: () => ws.close(),
  };
}
