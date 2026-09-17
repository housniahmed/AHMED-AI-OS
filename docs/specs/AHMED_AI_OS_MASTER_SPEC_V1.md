# AHMED AI OS — Master Specification V1

**Status:** Draft / Architecture baseline  
**Version:** 1.0  
**Date:** 2026-09-17

## 1. Purpose

AHMED AI OS is a personal AI operating system designed to unify context, memory, knowledge, goals, projects, agents, tools, workflows, and human approvals.

It is not intended to be a generic chatbot. The system should progressively become a reliable operational layer around the user's work, research, business, software projects, and daily planning.

## 2. Design principles

### 2.1 Context first

The system must build a structured model of the user and their work before adding autonomous behavior.

### 2.2 Memory is multi-layered

The initial memory model contains:

1. Semantic memory — relatively stable facts and knowledge.
2. Episodic memory — events and past interactions.
3. Procedural memory — how a workflow should be performed.
4. Project memory — project-specific state, artifacts, milestones, and history.
5. Decision memory — decisions, rationale, and consequences.
6. Preference memory — explicit and validated user preferences.
7. Working memory — temporary context required for a current task.

### 2.3 Provenance and traceability

A memory, retrieved fact, or important generated conclusion should retain its source where technically possible.

### 2.4 Human control

The system must distinguish:

- READ — retrieve information.
- ANALYZE — transform or reason over information.
- PREPARE — create a draft or proposed action.
- APPROVE — obtain explicit human authorization.
- EXECUTE — perform a real-world action.

No high-impact side effect should be silently inferred from a conversational suggestion.

### 2.5 Model agnostic

LLM providers are implementation details behind an abstraction. The orchestration layer must not depend on a single provider-specific API.

### 2.6 Scientific integrity

For research workflows, the system must explicitly distinguish verified evidence, inference, proposal, and missing verification. It must never invent references, DOI, data, results, or experimental conclusions.

## 3. Logical architecture

```text
                        USER
                         |
             Web / Chat / Voice / Messaging
                         |
                         v
                +-------------------+
                | AI INTERFACE      |
                +---------+---------+
                          |
                          v
                +-------------------+
                | ORCHESTRATOR      |
                | intent / planning |
                | routing / policy  |
                +---------+---------+
                          |
          +---------------+---------------+
          |               |               |
          v               v               v
   +-------------+  +-------------+  +-------------+
   | MEMORY      |  | AGENTS      |  | TOOLS       |
   +------+------+  +------+------+  +------+------+ 
          |               |               |
          +---------------+---------------+
                          |
                          v
                 +-----------------+
                 | KNOWLEDGE / RAG |
                 +--------+--------+
                          |
                          v
                 +-----------------+
                 | MODEL ROUTER    |
                 +--------+--------+
                          |
                          v
                 +-----------------+
                 | PLAN / PROPOSE  |
                 +--------+--------+
                          |
                          v
                 +-----------------+
                 | APPROVAL LAYER  |
                 +--------+--------+
                          |
                          v
                 +-----------------+
                 | EXECUTION       |
                 +--------+--------+
                          |
                          v
                 +-----------------+
                 | MEMORY UPDATE   |
                 +-----------------+
```

## 4. Core domains

### 4.1 Personal context

- identity
- roles
- skills
- preferences
- constraints
- communication patterns

### 4.2 Goals and projects

```text
Goal
  -> Objective
      -> Project
          -> Milestone
              -> Task
```

### 4.3 Knowledge

Documents, notes, papers, web research, code, structured data, and other approved sources.

### 4.4 Memory

Memory objects must include provenance and lifecycle information where appropriate.

### 4.5 Agents

Initial candidate agents:

- Orchestrator
- Research Agent
- Business Agent
- Daily Agent
- Coding Agent
- Scientific Integrity / Research Guardian

Agents should remain narrow and composable.

### 4.6 Tools

Initial tool categories:

- filesystem / documents
- web retrieval
- calendar
- email
- GitHub
- structured databases
- external APIs

## 5. Research integrity layer

The Research Guardian should evaluate a claim through a pipeline such as:

```text
CLAIM
  -> source retrieval
  -> source validation
  -> claim/source alignment
  -> contradiction check
  -> verification status
```

Expected statuses:

- SUPPORTED
- PARTIALLY_SUPPORTED
- UNSUPPORTED
- REQUIRES_VERIFICATION

The system must not convert a missing source into a fabricated citation.

## 6. Memory object baseline

Every persistent memory object should be designed to support, where applicable:

- `id`
- `memory_type`
- `content`
- `source_type`
- `source_ref`
- `created_at`
- `updated_at`
- `valid_from`
- `valid_until`
- `confidence`
- `status`
- `project_id`
- `tags`

The exact database schema will be defined in a dedicated data-model specification before implementation.

## 7. Retrieval strategy

The initial retrieval engine should support hybrid retrieval:

- semantic/vector retrieval
- lexical/keyword retrieval
- metadata filtering
- structured database queries
- reranking

A simple vector-only RAG pipeline is not considered sufficient as the final architecture.

## 8. Security and permissions

Every tool call should have an explicit capability definition. Examples:

```text
calendar.read
calendar.create
email.read
email.draft
email.send
github.read
github.create_branch
github.create_pr
```

High-impact capabilities should require approval by default.

## 9. Initial stack

Proposed baseline:

- Python / FastAPI for backend services
- PostgreSQL for primary persistence
- pgvector for initial vector retrieval
- Redis for caching and asynchronous work where needed
- Next.js for the web application
- LangGraph or an equivalent explicit stateful orchestration layer
- MCP/API adapters for external tools where appropriate
- Docker for local reproducibility
- OpenTelemetry-compatible observability

These are provisional architectural choices and must be validated against implementation constraints before production adoption.

## 10. Delivery phases

### Phase 0 — Architecture

- repository bootstrap
- specifications
- data model
- security model
- evaluation strategy

### Phase 1 — Brain

- document ingestion
- knowledge base
- persistent memory
- grounded chat

### Phase 2 — Daily

- calendar
- tasks
- project state
- daily briefing

### Phase 3 — Research

- papers
- references
- evidence tracking
- Research Guardian

### Phase 4 — Business

- clients
- leads
- campaigns
- analytics
- business workflows

### Phase 5 — Agents

- planning
- tool use
- approvals
- execution

### Phase 6 — Controlled autonomy

```text
EVENT
 -> AGENT
 -> REASON
 -> PLAN
 -> APPROVAL
 -> ACTION
 -> VERIFY
 -> MEMORY
```

## 11. Evaluation philosophy

The project should be evaluated on measurable properties, not on subjective impressions alone.

Key categories:

- retrieval correctness
- citation/provenance correctness
- memory precision and recall
- task completion
- tool-call correctness
- policy/permission compliance
- hallucination rate on defined benchmark tasks
- latency and cost
- human intervention rate

Evaluation datasets must use real project examples only when they are safe and appropriate to store in the repository; otherwise use synthetic or redacted fixtures.

## 12. Next implementation milestone

**Milestone 01: Personal Context Model**

Deliverables:

1. `USER_CONTEXT_SCHEMA`
2. initial PostgreSQL schema
3. memory object schema
4. provenance model
5. permission/capability model
6. seed context fixtures
7. architecture tests

No autonomous execution will be added before the core context and permission models are stable enough to evaluate.
