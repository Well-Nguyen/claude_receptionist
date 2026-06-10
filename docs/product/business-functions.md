# Business Functions — Product Contract

## Tool-Calling Model

All business actions are implemented as LLM tool calls. The AI service calls
the BE HTTP API when a tool is invoked. Voice slot-filling collects required
fields across turns. **Read-back confirmation is required before any commit.**

## Tool Catalog

### Information

**`search_knowledge_base(query: str) -> KBHit[]`**
- Full-text search on mock KB data.
- On match: agent answers grounded in returned content, in session language.
- On no match: agent says it doesn't have that information (no fabrication).

**`lookup_directory(query: str) -> DirectoryEntry[]`**
- Returns department, floor, location, contact.
- On ambiguous query: agent asks one clarifying question.

### Conversation Control

**`end_conversation(reason: str)`**
- Triggers farewell, closing line spoken, session resets to LANDING.
- On ambiguous "goodbye": agent confirms before ending.

### Meeting Room Booking (employees only)

```python
class EmployeeVerification(BaseModel):
    full_name: str
    employee_code: str

class MeetingBookingRequest(BaseModel):
    title: str
    room_name: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    participants: list[str] = []
    organizer_employee_code: str
```

**`verify_employee(full_name, employee_code) -> {verified: bool, employee_id}`**
- Must be called first for any room booking flow.
- `verified: false` → booking refused politely; not attempted.

**`get_room_status(date, time_range, room_name?) -> RoomSlot[]`**
- Returns available slots.
- Requested time taken → agent proposes closest viable slot(s) and asks employee to choose.

**`create_meeting(MeetingBookingRequest) -> {booking_id, status}`**
- Called only after explicit employee confirmation of slot.
- Success: confirm `booking_id` (voice + right panel).
- Failure: report failure, offer retry; no partial state persists.

### Visitor Appointment (general visitors)

```python
class AppointmentRequest(BaseModel):
    visitor_name: str
    phone_number: str
    desired_time: datetime
    purpose: str | None = None
```

**`check_appointment_availability(desired_time, ...) -> Slot[]`**
- Returns open slots around desired time.

**`create_appointment(AppointmentRequest) -> {appointment_id, status}`**
- Called only after explicit visitor confirmation.
- Success: confirm `appointment_id` (voice + right panel).
- Failure: report failure, offer retry.

## Slot-Filling Rules

- One missing required field per turn — agent does not ask for multiple fields at once.
- Spoken date/time → normalized to ISO 8601 → read back to confirm before use.
- Phone/employee code → digits only → read back to confirm.
- Names → read back character by character or phonetically if ambiguous.

## BE API Contract

All endpoints return `{ data, error, request_id }`.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/employees/verify` | Verify name + employee code |
| GET  | `/rooms/status` | Room availability |
| POST | `/rooms/book` | Create booking |
| GET  | `/appointments/availability` | Open appointment slots |
| POST | `/appointments` | Create appointment |
| GET  | `/kb/search` | Full-text knowledge base search |
| GET  | `/directory` | Department / building lookup |
| POST | `/sessions/log` | Usage session log |

**Mock data contract:** All 8 endpoints return schema-valid mock responses.
`/kb/search` returns ranked mock hits for any query.
When real systems are integrated, only the BE client/integration layer changes —
AI tool contracts and schemas do not change.

## Authorization Rules

- Meeting room booking: employee verification (`verify_employee`) must return
  `verified: true` before any room query or booking is attempted.
- Visitor appointment: no verification required.
- `end_conversation`: always available.
- `search_knowledge_base` / `lookup_directory`: always available.

## Interaction Panel (Right Panel) Sync

- During a booking flow: collected fields and proposed slots render on the right panel
  in sync with each voice turn.
- At confirmation step: a confirmation card with final details is shown before commit.
- After successful booking: confirmation card shows `booking_id` / `appointment_id`.
