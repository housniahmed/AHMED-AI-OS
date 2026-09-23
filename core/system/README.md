# System Composition Root

The system composition root builds one coherent dependency graph shared by the API and other interfaces.

Identity, Business, Security, Governance, Retrieval, Context, Agent, Orchestrator, Conversation, and the Tool Gateway are instantiated from one container.

The bootstrap deliberately uses an empty retriever and no-op planner when no external providers are injected. This keeps the application runnable without pretending that an LLM or vector database is configured.

The ToolExecutionGateway remains the B17 execution boundary and receives the B33 Security and B18 Governance services. The provider-free agent proposes no actions, so no tool can execute accidentally.

The next production integration is to inject real retrieval/planning providers and a request-scoped gateway executor while preserving this composition root.
