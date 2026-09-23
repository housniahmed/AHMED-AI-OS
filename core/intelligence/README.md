# Model Intelligence Runtime

B36 adds a strict model-backed planning adapter on top of the existing B8 Model Router.

ModelRouter -> ModelAgentPlanner -> B6 AgentRuntime -> PROPOSE -> B17 ToolExecutionGateway -> B33 Security + B18 Governance.

ModelAgentPlanner sends the request plus bounded structured context to the routed reasoning model and accepts only a JSON proposal containing observations and explicit actions. It never executes tools.

The composition root accepts an optional ModelRouter. When one is supplied, the planner becomes model-backed automatically. When none is supplied, the system remains explicitly provider-free through NoOpPlanner.

This keeps the architecture honest: adding the model runtime does not bypass approval, governance, security, or the tool gateway.

The existing ModelProvider contract remains the integration boundary for OpenAI, Anthropic, local models, or another provider. Provider credentials and SDKs should stay outside the core contracts.
