# System Composition Root

The system composition root builds one coherent dependency graph shared by the API and other interfaces.

Identity, Business, Security, Governance, Retrieval, Context, Agent, Orchestrator, Conversation, and the Tool Gateway are instantiated from one container.

The agent runtime now receives the B17 ToolExecutionGateway as its execution adapter. The orchestrator propagates the authenticated/request user ID into that execution boundary, so B33 Security and B18 Governance receive the same user identity used by B15 Identity and B16 Orchestration.

The bootstrap deliberately uses an empty retriever and no-op planner when no external providers are injected. This keeps the application runnable without pretending that an LLM or vector database is configured.

High-risk execution still passes through the existing B6 approval policy and B18 governance boundary. Durable approval state, resumable post-approval execution, and external model/retrieval providers remain explicit future integrations.
