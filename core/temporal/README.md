# Temporal & Event Intelligence — Brique 12

Brique 12 adds the time dimension to AHMED AI OS.

## Model

`EVENT + TIMESTAMP + ENTITY LINKS + TEMPORAL RELATIONS`

The layer represents tasks, meetings, decisions, milestones, deadlines, observations and transactions. Events retain timezone and provenance metadata where available.

The reference implementation supports deterministic timeline ordering, interval queries, current events, upcoming events, overdue deadlines and basic temporal relations.

No natural-language date parsing or automatic inference is performed here yet. Ambiguous dates should be resolved before creating an Event. Future work can add timezone-aware parsing, recurrence, temporal graph edges and event extraction from connected sources.
