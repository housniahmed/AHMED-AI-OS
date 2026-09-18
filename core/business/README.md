# B27 — Business OS

B27 provides the canonical business domain for leads, customers, offers, deals and campaigns.

## Architecture

```
Business Intent
     ↓
B27 Business OS
     ├── CRM: Lead → Customer
     ├── Sales: Offer → Deal
     ├── Marketing: Campaign
     └── Business Snapshot
          ↓
B23 Planning / B24 Workflows / B25 Scheduler
          ↓
B17 Tool Gateway
          ↓
External adapters (CRM / Ads / Shopify / Stripe / etc.)
```

B27 is the business domain layer, not a replacement for external systems. It contains no provider SDKs and does not send campaigns, charge customers, modify Shopify, or contact leads directly.

## Core invariant

Business facts must remain distinguishable from derived metrics and proposed actions. External writes must continue through the existing execution and approval controls.

## Current scope

- Lead lifecycle and qualification
- Customer records
- Offers and pricing metadata
- Deals and revenue snapshot
- Campaign metadata and lifecycle
- Repository abstraction

External CRM, advertising, ecommerce and payment adapters are intentionally deferred to integration-specific modules after their connections and authorization are established.
