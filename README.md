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

**Phase 0 — Architecture bootstrap**

The repository is intentionally starting from an empty baseline so that the architecture can be built incrementally with explicit decisions and evaluation criteria.
