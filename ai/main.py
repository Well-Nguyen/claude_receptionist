from __future__ import annotations
import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from orchestrator.sentence_splitter import split_sentences
from orchestrator.state import SessionRegistry, SessionState
from orchestrator.stub_llm import stub_llm
from orchestrator.stub_stt import stub_stt
from orchestrator.stub_tts import stub_tts_b64
from shared.schemas.events import (
    AudioChunkEvent,
    SessionStartEvent,
    StateChangeEvent,
    TranscriptEvent,
)


registry = SessionRegistry()

_GREETINGS = {
    "en": "Hello! Welcome to the building. How can I help you today?",
    "vi": "Xin chào! Chào mừng bạn đến tòa nhà. Tôi có thể giúp gì cho bạn không?",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    gc_task = asyncio.create_task(registry.gc_loop())
    try:
        yield
    finally:
        gc_task.cancel()
        try:
            await gc_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="AI Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "sessions": len(registry)}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    session_id = str(uuid.uuid4())
    registry.add(session_id)

    await websocket.send_text(
        SessionStartEvent(session_id=session_id).model_dump_json()
    )

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            # binary frame: raw PCM audio (processed in US-P0-3+)
            if "bytes" in message and message["bytes"] is not None:
                pass
            # text frame: JSON control event
            elif "text" in message and message["text"] is not None:
                await _handle_event(session_id, message["text"], websocket)
    except WebSocketDisconnect:
        pass
    finally:
        registry.mark_disconnected(session_id)


async def _handle_event(session_id: str, raw: str, websocket: WebSocket) -> None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return

    event = payload.get("event")

    if event == "language_select":
        await _on_language_select(session_id, payload, websocket)
    elif event == "utterance_end":
        await _on_utterance_end(session_id, payload, websocket)
    elif event == "interrupt":
        await _on_interrupt(session_id, payload)


async def _on_utterance_end(
    session_id: str, payload: dict, websocket: WebSocket
) -> None:
    session = registry.get(session_id)
    if session is None or session.state != SessionState.LISTENING:
        return

    session.state = SessionState.THINKING
    await websocket.send_text(StateChangeEvent(state="THINKING").model_dump_json())

    transcript = stub_stt(b"")
    await websocket.send_text(
        TranscriptEvent(role="user", text=transcript, session_id=session_id).model_dump_json()
    )

    reply = stub_llm(transcript, session.language or "en")
    gen_id = str(uuid.uuid4())
    segments = split_sentences(reply, gen_id)

    session.state = SessionState.SPEAKING
    session.gen_id = gen_id
    await websocket.send_text(StateChangeEvent(state="SPEAKING").model_dump_json())

    task = asyncio.create_task(
        _run_generation(session, session_id, websocket, gen_id, segments, reply)
    )
    session.active_gen_task = task


async def _run_generation(
    session,
    session_id: str,
    websocket: WebSocket,
    gen_id: str,
    segments,
    reply: str,
) -> None:
    try:
        for seg in segments:
            await asyncio.sleep(0)  # yield so interrupt events can be processed
            if session.gen_id != gen_id:
                return
            audio_b64 = stub_tts_b64(seg.text)
            await websocket.send_text(
                AudioChunkEvent(seq=seg.seq, gen_id=gen_id, data=audio_b64).model_dump_json()
            )

        await websocket.send_text(
            TranscriptEvent(role="assistant", text=reply, session_id=session_id).model_dump_json()
        )
        session.state = SessionState.LISTENING
        await websocket.send_text(StateChangeEvent(state="LISTENING").model_dump_json())
    except asyncio.CancelledError:
        session.state = SessionState.LISTENING
        try:
            await websocket.send_text(StateChangeEvent(state="LISTENING").model_dump_json())
        except Exception:
            pass
    except Exception:
        # WebSocket closed or transport error while generation was in flight.
        session.state = SessionState.LISTENING


async def _on_interrupt(session_id: str, payload: dict) -> None:
    session = registry.get(session_id)
    if session is None or session.state != SessionState.SPEAKING:
        return

    gen_id = payload.get("gen_id")
    if not gen_id or gen_id != session.gen_id:
        return

    task = session.active_gen_task
    if task and not task.done():
        task.cancel()


async def _on_language_select(
    session_id: str, payload: dict, websocket: WebSocket
) -> None:
    session = registry.get(session_id)
    if session is None:
        return

    language = payload.get("language")
    if language not in ("en", "vi"):
        return

    # Language is immutable once chosen
    if session.language is not None:
        return

    session.language = language
    session.state = SessionState.GREETING
    await websocket.send_text(StateChangeEvent(state="GREETING").model_dump_json())

    # Stub greeting: transcript replaces audio until TTS is wired in US-P0-5
    greeting = _GREETINGS[language]
    await websocket.send_text(
        TranscriptEvent(
            role="assistant", text=greeting, session_id=session_id
        ).model_dump_json()
    )

    session.state = SessionState.LISTENING
    await websocket.send_text(StateChangeEvent(state="LISTENING").model_dump_json())


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AI_WS_PORT", "7700"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
