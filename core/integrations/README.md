# B26 — Calendar / Gmail / Telegram

B26 introduces provider-neutral integration ports for calendar, email, and messaging without pretending that external accounts are connected.

## Architecture

```
B24 Workflow Engine
        |
B25 Scheduler
        |
B26 Integration Ports
   /       |        \\
Calendar  Gmail   Telegram
   |        |         |
Provider adapters (external SDK/API)
```

## Contracts

- **CalendarProvider**: list, create, update, delete events.
- **GmailProvider**: search, get, create draft, send.
- **TelegramProvider**: send message.

The core only defines contracts and domain models. Provider SDKs, OAuth tokens, API clients, retries, rate limits, and webhook handling belong in adapter modules outside the core contracts.

## Safety invariant

B26 does not bypass the existing execution controls. Reading external data can be exposed as READ tools; writes such as creating events, sending email, or sending Telegram messages must flow through the Tool Execution Gateway and the approval/governance layer when required.

The repository currently has no confirmed Gmail or Google Calendar connection, and no Telegram connector was discovered. Therefore B26 deliberately does **not** claim live connectivity.

## Next adapter layer

When a provider is connected, implement an adapter that satisfies the corresponding port, add integration-specific contract tests, and map it to registered tools. Credentials must remain outside source control and outside domain models.
