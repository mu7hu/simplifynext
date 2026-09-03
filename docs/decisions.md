# Architecture Decision Records (ADRs)

## ADR 1: SQLite for Persistent Organizational Memory
* **Context**: Need cross-cycle persistence so Cycle 6 is smarter than Cycle 1.
* **Decision**: Use SQLite with typed JSON fields for structured records.
* **Rationale**: Eliminates external server dependencies (Redis/Postgres), is 100% serverless, zero maintenance, and provides atomic transactions.

## ADR 2: Dual-Mode Execution (Bedrock + High-Fidelity Local Stubs)
* **Context**: Hackathon sandboxes have strict budget limits ($20 cap). Team members need to test offline.
* **Decision**: Central `ModelFactory` that serves `ChatBedrockConverse` when live AWS credentials exist, and deterministic stubs when `USE_STUB_MODELS=true`.
* **Rationale**: Zero AWS costs during development and testing, while production-ready for live Bedrock evaluation.

## ADR 3: First-Class `INSUFFICIENT_DATA` Verdict
* **Context**: Early-stage experiments with long evaluation windows (e.g. 30 days) often report 0 or 1 noisy conversions in early 14-day cycles.
* **Decision**: Mandate `INSUFFICIENT_DATA` and `HOLD` as first-class verdicts, guarding against premature cuts.
* **Rationale**: Prevents startups from prematurely abandoning high-value channels due to noise or observation latency.
