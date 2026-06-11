from __future__ import annotations
import asyncio
import base64
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from orchestrator.sentence_splitter import split_sentences
from orchestrator.state import LatencyRecord, SessionRegistry, SessionState, SESSION_IDLE_TIMEOUT_S
from orchestrator.stub_llm import stub_llm
from services.model_registry import registry as model_registry
from shared.schemas.events import (
    AudioChunkEvent,
    SessionStartEvent,
    StateChangeEvent,
    TranscriptEvent,
    VadConfigEvent,
)


def _build_vad_config_event() -> VadConfigEvent:
    return VadConfigEvent(
        silence_ms=int(os.getenv("VAD_SILENCE_MS", "800")),
        min_speech_ms=int(os.getenv("VAD_MIN_SPEECH_MS", "250")),
        threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
        barge_in_min_ms=int(os.getenv("BARGE_IN_MIN_MS", "300")),
    )

logger = logging.getLogger(__name__)


registry = SessionRegistry()

_GREETINGS = {
    "en": "Hello! Welcome to the building. How can I help you today?",
    "vi": "Xin chào! Chào mừng bạn đến tòa nhà. Tôi có thể giúp gì cho bạn không?",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_registry.load()
    gc_task = asyncio.create_task(registry.gc_loop())
    try:
        yield
    finally:
        gc_task.cancel()
        try:
            await gc_task
        except asyncio.CancelledError:
            pass
        model_registry.close()


app = FastAPI(title="AI Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "sessions": len(registry)}


@app.get("/config/vad")
async def get_vad_config() -> dict:
    return {
        "silence_ms": int(os.getenv("VAD_SILENCE_MS", "800")),
        "min_speech_ms": int(os.getenv("VAD_MIN_SPEECH_MS", "250")),
        "threshold": float(os.getenv("VAD_THRESHOLD", "0.5")),
        "barge_in_min_ms": int(os.getenv("BARGE_IN_MIN_MS", "300")),
    }


@app.get("/sessions/{session_id}/latency")
async def get_latency(session_id: str) -> dict:
    session = registry.get(session_id)
    if session is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="session not found")
    records = [
        {
            "turn_id": r.turn_id,
            "utterance_end_ms": r.utterance_end_ms,
            "stt_done_ms": r.stt_done_ms,
            "llm_first_token_ms": r.llm_first_token_ms,
            "tts_first_audio_ms": r.tts_first_audio_ms,
            "fe_first_play_ms": r.fe_first_play_ms,
        }
        for r in session.latency_log
    ]
    return {"session_id": session_id, "turns": records}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    session_id = str(uuid.uuid4())
    registry.add(session_id)

    await websocket.send_text(
        SessionStartEvent(session_id=session_id).model_dump_json()
    )
    await websocket.send_text(_build_vad_config_event().model_dump_json())

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            # Reset idle timer on every incoming frame
            session = registry.get(session_id)
            if session:
                _reset_idle_timer(session, session_id, websocket)
            # binary frame: raw 16 kHz mono Int16 PCM from FE capture
            if "bytes" in message and message["bytes"] is not None:
                if session and session.state == SessionState.LISTENING:
                    session.pcm_buffer.append(message["bytes"])
            # text frame: JSON control event
            elif "text" in message and message["text"] is not None:
                await _handle_event(session_id, message["text"], websocket)
    except WebSocketDisconnect:
        pass
    finally:
        registry.mark_disconnected(session_id)


def _reset_session(session) -> None:
    if session.active_gen_task and not session.active_gen_task.done():
        session.active_gen_task.cancel()
    session.active_gen_task = None
    if session.idle_timer_task and not session.idle_timer_task.done():
        session.idle_timer_task.cancel()
    session.idle_timer_task = None
    session.state = SessionState.LANDING
    session.language = None
    session.gen_id = str(uuid.uuid4())
    session.pcm_buffer.clear()


async def _idle_timer(
    session_id: str, websocket: WebSocket, timeout: float = SESSION_IDLE_TIMEOUT_S
) -> None:
    await asyncio.sleep(timeout)
    session = registry.get(session_id)
    if session is None:
        return
    _reset_session(session)
    try:
        await websocket.send_text(StateChangeEvent(state="LANDING").model_dump_json())
    except Exception:
        pass


def _reset_idle_timer(session, session_id: str, websocket: WebSocket) -> None:
    if session.idle_timer_task and not session.idle_timer_task.done():
        session.idle_timer_task.cancel()
    session.idle_timer_task = asyncio.create_task(
        _idle_timer(session_id, websocket)
    )


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
    elif event == "session_end":
        await _on_session_end(session_id, websocket)
    elif event == "latency_report":
        _on_latency_report(session_id, payload)


async def _on_utterance_end(
    session_id: str, payload: dict, websocket: WebSocket
) -> None:
    session = registry.get(session_id)
    if session is None or session.state != SessionState.LISTENING:
        return

    turn_id = str(uuid.uuid4())
    rec = LatencyRecord(session_id=session_id, turn_id=turn_id)
    rec.utterance_end_ms = time.time() * 1000

    session.state = SessionState.THINKING
    await websocket.send_text(StateChangeEvent(state="THINKING").model_dump_json())

    pcm = b"".join(session.pcm_buffer)
    session.pcm_buffer.clear()
    stt = model_registry.stt_for(session.language or "en")
    transcript = await asyncio.get_event_loop().run_in_executor(None, stt.transcribe, pcm)
    rec.stt_done_ms = time.time() * 1000
    await websocket.send_text(
        TranscriptEvent(role="user", text=transcript, session_id=session_id).model_dump_json()
    )

    reply = stub_llm(transcript, session.language or "en")
    rec.llm_first_token_ms = time.time() * 1000

    gen_id = str(uuid.uuid4())
    segments = split_sentences(reply, gen_id)

    session.state = SessionState.SPEAKING
    session.gen_id = gen_id
    await websocket.send_text(StateChangeEvent(state="SPEAKING").model_dump_json())

    session.latency_log.append(rec)

    task = asyncio.create_task(
        _run_generation(session, session_id, websocket, gen_id, segments, reply, rec)
    )
    session.active_gen_task = task


async def _run_generation(
    session,
    session_id: str,
    websocket: WebSocket,
    gen_id: str,
    segments,
    reply: str,
    rec: LatencyRecord | None = None,
) -> None:
    try:
        first_chunk = True
        for seg in segments:
            await asyncio.sleep(0)  # yield so interrupt events can be processed
            if session.gen_id != gen_id:
                return
            tts = model_registry.tts_for(session.language or "en")
            pcm_out = await asyncio.get_event_loop().run_in_executor(None, tts.synthesize, seg.text)
            audio_b64 = base64.b64encode(pcm_out).decode()
            if first_chunk:
                if rec is not None:
                    rec.tts_first_audio_ms = time.time() * 1000
                    logger.info(json.dumps({
                        "event": "latency_turn",
                        "session_id": session_id,
                        "turn_id": rec.turn_id,
                        "utterance_end_ms": rec.utterance_end_ms,
                        "stt_done_ms": rec.stt_done_ms,
                        "llm_first_token_ms": rec.llm_first_token_ms,
                        "tts_first_audio_ms": rec.tts_first_audio_ms,
                    }))
                first_chunk = False
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


def _on_latency_report(session_id: str, payload: dict) -> None:
    session = registry.get(session_id)
    if session is None:
        return
    turn_id = payload.get("turn_id")
    fe_ms = payload.get("fe_first_play_ms")
    if not turn_id or fe_ms is None:
        return
    for rec in session.latency_log:
        if rec.turn_id == turn_id:
            rec.fe_first_play_ms = float(fe_ms)
            logger.info(json.dumps({
                "event": "latency_turn_complete",
                "session_id": session_id,
                "turn_id": turn_id,
                "fe_first_play_ms": rec.fe_first_play_ms,
            }))
            break


async def _on_session_end(session_id: str, websocket: WebSocket) -> None:
    session = registry.get(session_id)
    if session is None:
        return
    _reset_session(session)
    await websocket.send_text(StateChangeEvent(state="LANDING").model_dump_json())


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
