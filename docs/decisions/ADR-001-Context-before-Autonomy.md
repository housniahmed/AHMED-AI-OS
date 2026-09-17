# ADR-001 — Context Before Autonomy

**Status:** Accepted  
**Date:** 2026-09-17

## Context

AHMED AI OS is intended to evolve from a personal knowledge assistant into a tool-using agent system. Starting with autonomous actions before the context, provenance, and permission layers are stable would make errors difficult to diagnose and evaluate.

## Decision

Build the system in this order:

1. canonical user context;
2. persistent memory and provenance;
3. retrieval and grounded responses;
4. goal/project/task model;
5. tool capability and permission model;
6. agent orchestration;
7. controlled execution;
8. selective autonomy.

## Consequences

Positive:

- easier debugging;
- auditable behavior;
- safer tool integration;
- measurable evaluation;
- less coupling between memory, reasoning, and actions.

Trade-off:

The first versions will appear less autonomous than a prototype that immediately connects many tools. This is deliberate: autonomy is added after the foundations can be evaluated.
