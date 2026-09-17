# AHMED AI OS — User Context Schema V1

**Status:** Draft / implementation baseline  
**Version:** 1.0  
**Date:** 2026-09-17

## 1. Purpose

This schema defines the canonical representation of user context. It is intentionally separate from conversation history and from document embeddings.

The context model answers: **who is the user, what matters now, what is known, how should the system behave, and where did the information come from?**

## 2. Core entities

```text
User
├── Identity
├── Roles
├── Skills
├── Preferences
├── Constraints
├── Goals
│   └── Projects
│       └── Tasks
├── Memories
├── Decisions
├── Procedures
└── Resources
```

## 3. Canonical JSON shape

```json
{
  "user": {
    "id": "string",
    "display_name": "string",
    "timezone": "IANA timezone",
    "locale": "BCP-47 locale"
  },
  "roles": [],
  "skills": [],
  "preferences": [],
  "constraints": [],
  "goals": [],
  "projects": [],
  "memories": [],
  "decisions": [],
  "procedures": [],
  "resources": []
}
```

The JSON shape is a transport/document model, not necessarily the physical SQL layout.

## 4. Provenance requirements

Any persistent fact that can influence an answer or action should support provenance.

```json
{
  "source": {
    "type": "user_input | file | conversation | integration | system",
    "ref": "string",
    "captured_at": "timestamp"
  }
}
```

The source must not be silently fabricated. If provenance is unavailable, the object should explicitly record that it is missing.

## 5. Memory requirements

Persistent memory should include:

```json
{
  "id": "uuid",
  "type": "semantic | episodic | procedural | project | decision | preference",
  "content": "string",
  "status": "active | superseded | archived | needs_verification",
  "confidence": 0.0,
  "source": {},
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

`confidence` is not an objective truth probability. It is metadata about system confidence and must not be presented as experimental statistical evidence.

## 6. Decisions

A decision should preserve rationale and consequences.

```json
{
  "id": "uuid",
  "title": "string",
  "decision": "string",
  "rationale": "string",
  "alternatives_considered": [],
  "status": "active | reversed | superseded",
  "created_at": "timestamp",
  "source": {}
}
```

## 7. Goals and projects

Goals represent desired outcomes. Projects represent organized work toward those outcomes.

A project should support:

- objective
- status
- priority
- start date
- target date
- milestones
- tasks
- related documents
- related decisions
- stakeholders

## 8. Preferences

Preferences must distinguish explicit preferences from inferred patterns.

```text
origin = explicit | inferred
```

Inferred preferences should never silently override an explicit preference.

## 9. Constraints

Constraints include rules that should affect planning and execution, such as:

- time constraints
- tool restrictions
- safety restrictions
- workflow rules
- research-integrity rules

## 10. Context selection

The context engine should not inject the entire user profile into every prompt. It should construct a task-specific context using:

```text
current task
+
relevant goals/projects
+
relevant memories
+
relevant procedures
+
relevant constraints
+
required provenance
```

## 11. Temporal semantics

Facts can change. Therefore, the schema distinguishes:

- `created_at` — when the record was created.
- `updated_at` — last metadata/content update.
- `valid_from` — beginning of validity when known.
- `valid_until` — end of validity when known.

Historical records should normally be superseded rather than overwritten when preserving the history is useful.

## 12. Privacy classification

All context objects should eventually carry a privacy class, for example:

```text
public
internal
private
restricted
secret
```

The exact policy and enforcement mechanism will be defined before external integrations are enabled.

## 13. V1 implementation rule

The initial implementation should prioritize correctness, provenance, explicit state, and testability over advanced autonomous behavior.
