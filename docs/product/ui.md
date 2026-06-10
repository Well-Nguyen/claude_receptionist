# UI — Product Contract

## Entry Point

`http://<device>:8000` — single kiosk browser tab, same LAN.

## Landing Page

- Bilingual greeting (Vietnamese + English).
- Two large buttons: **English** / **Tiếng Việt**.
- One tap → session enters GREETING within 300 ms → mic opens.
- Language fixed for the whole session.

## Session Layout (post-landing)

```
┌─────────────────────────────────────────────────────────┐
│  [Avatar]         │  [Dynamic Interaction Panel]         │
│  Static image     │  Room timeslots / appt cards /        │
│  Talking state    │  confirmation cards                   │
│  toggle later     │                                       │
├───────────────────┤                                       │
│  [Chat history]   │                                       │
│  transcript       │                                       │
│  scroll           │                                       │
└─────────────────────────────────────────────────────────┘
        [ End ]  [ Language switch ]
```

- **Left:** Avatar (static; talking-state toggle in P1+) + small chatbox (transcript history).
- **Right:** Dynamic interaction panel — updates per voice turn.
- **Bottom bar:** End button + language switch button.

## Theme

Red-on-white. High-contrast, readable at kiosk distance.

## Visual States

| State | UI indicator |
|-------|-------------|
| `LANDING` | Language selection buttons; no mic active. |
| `GREETING` | Avatar active; greeting audio plays; "listening soon" indicator. |
| `LISTENING` | Mic waveform / pulse animation; chatbox ready. |
| `THINKING` | Spinner / thinking indicator; transcript shows user text. |
| `SPEAKING` | Avatar talking-state toggle; audio progress; transcript shows assistant text. |

## Dynamic Interaction Panel

The right panel renders contextual cards pushed by the AI service via WS events:

| Context | Card content |
|---------|-------------|
| Room booking flow | Collected fields (title, room, time) as they fill; available slots list. |
| Appointment flow | Collected fields (name, phone, time); available slot. |
| Confirmation step | Final details card with Confirm / Change options (via voice). |
| After booking | Confirmation card with `booking_id` or `appointment_id`. |
| Idle / info flow | Blank or last KB result summary. |

## Session Control

- **End button:** immediate session reset to LANDING; clears all transient state.
- **Language switch:** visible but only active from LANDING (or after reset).
- **30 s idle:** session auto-resets to LANDING with visual countdown (last 10 s).

## Chatbox

- Scrollable transcript history for the current session.
- User utterances on right (or labeled "You"); assistant on left (or labeled "Kiosk").
- Transcript updates immediately on receipt of `transcript` WS event.

## Accessibility / Kiosk Constraints

- Touch-friendly button sizing (min 44 px tap targets).
- No keyboard assumed; all input is voice.
- Browser AEC enabled: `echoCancellation`, `noiseSuppression`, `autoGainControl`.
- No persistent local storage of PII across sessions.
