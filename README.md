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

**Architecture build — B1 through B26 contracts implemented**

The repository is being built incrementally with explicit contracts, provider-neutral core components, and tests. B26 adds external integration ports for Calendar, Gmail, and Telegram without claiming live account connectivity.

### Current integration boundary

- Calendar: provider contract + service layer; adapter/OAuth connection still required.
- Gmail: provider contract + service layer; adapter/OAuth connection still required.
- Telegram: provider contract + service layer; adapter/bot credentials still required.
- External writes must continue through the existing Tool Execution Gateway and approval/governance controls.

Tests are added as implementation artifacts and are not described as passing unless they have been executed.
