# AHMED AI OS

Personal AI Operating System for knowledge, research, business, and daily life.

## Vision

AHMED AI OS is designed as a context-aware personal AI system that can remember relevant information, reason over projects and goals, use tools, prepare actions, request approval, and execute authorized workflows.

The project is inspired by the "second brain + agents + automation" concept, but is implemented as an extensible AI engineering system rather than a simple chatbot or prompt collection.

## Core principles

- **Context first:** make the user's work and knowledge machine-readable.
- **Memory is not just RAG:** separate semantic, episodic, procedural, project, decision, preference, and working memory.
- **Traceability:** important answers and actions should expose provenance.
- **Human in the loop:** distinguish reading, analysis, preparation, approval, and execution.
- **Model agnostic:** avoid hard-coupling the architecture to one LLM provider.
- **Small agents, strong orchestration:** add specialized agents only when they solve a concrete workflow.
- **Scientific integrity:** unsupported claims must not be presented as verified facts.

## Initial architecture

```text
User Interfaces
    -> Orchestrator
        -> Context / Memory
        -> Knowledge / Retrieval
        -> Agents
        -> Tools
        -> Approval / Permissions
        -> Workflows
        -> Execution
        -> Memory update
```

## Planned domains

- Personal context and memory
- Research and scientific workflow
- Business and marketing
- Daily planning
- Coding and software projects
- Knowledge ingestion and retrieval
- Tool integrations and automation

## Repository structure

```text
apps/        # API, web interface, workers
core/        # orchestration, agents, memory, retrieval, permissions
knowledge/   # ingestion and indexing
tools/       # external tool adapters
workflows/   # repeatable business/research/daily workflows
database/    # schema and migrations
prompts/     # versioned system prompts
evals/       # evaluation datasets and checks
docs/        # architecture and specifications
tests/       # automated tests
```

## Status

**Architecture build — evolving core domains; model runtime through B43**

The repository is being built incrementally with explicit contracts, provider-neutral core components, and tests. The model runtime includes B39 reliability/resilience, B40 usage and cost telemetry, B41 adaptive routing, B42 evaluation-derived quality signals, and B43 offline routing-policy optimization with statistical gates, audit history, explicit approval, and rollback. The benchmark workflow now includes a paired B32 runner, versioned evaluation-run export, a historical B39/B40/B42 feature collector with timestamp checks, and a proposal-only CLI; it does not auto-activate policies. B26 adds external integration ports for Calendar, Gmail, and Telegram without claiming live account connectivity. B27 adds the provider-neutral Business OS domain for CRM, sales, offers, deals, and campaigns.

### Current integration boundary

- Calendar: provider contract + service layer; adapter/OAuth connection still required.
- Gmail: provider contract + service layer; adapter/OAuth connection still required.
- Telegram: provider contract + service layer; adapter/bot credentials still required.
- External writes must continue through the existing Tool Execution Gateway and approval/governance controls.

Tests are added as implementation artifacts and are not described as passing unless they have been executed.
