# Augury hosted workflow

Open https://d2b62i37fl26ui.cloudfront.net/ and sign in or register and confirm your email.

1. Complete Founder Brief. Save persists the company, pitch, budget, goals, profile, channel exclusions and preferences to your account's DynamoDB workspace.
2. Select **Save and start planning**. The supervisor assigns the next cycle number and queues a Lambda worker. Agent Activity displays persisted node starts and completions.
3. The Strategist calls Amazon Bedrock, validates the allocation and repairs invalid proposals within a bounded retry limit. The Content agent calls Bedrock to generate channel-specific creative.
4. Approval displays that saved plan and its content. Request a revision to send feedback to the Strategist, or approve the reviewed version. The resumed worker executes the exact approved plan without regenerating it.
5. The market simulator generates campaign telemetry. Measurement computes comparable metrics; the Bedrock Analyst evaluates them. The ledger and founder digest persist the results and learning.
6. Dashboard, Analytics and Activity read the selected run from AWS. Refresh and sign-in reload the same workspace. The cycle-history selector switches between the latest 20 runs.
7. Return to Founder Brief to start another cycle after completion. Prior cycle learning is loaded into hey gthe next Strategist prompt.

## What is live

Authentication, workspace persistence, scheduling, approval, event history, plan generation, content generation, analysis and report storage run on AWS. All three agents use `amazon.nova-lite-v1:0` through Bedrock in `us-east-1`. Hosted deployments explicitly set `UseStubModels=false`; failures are surfaced without silently substituting stub model responses. Nova structured responses are schema-validated, with bounded correction attempts.

Campaign execution remains an explicitly labelled market simulation. Generated outcomes are not evidence of actual ad performance, and no advertising accounts are connected or charged. Dashboard totals are calculated from that cycle's generated telemetry, not hardcoded demo data. The digest is a deterministic rendering of the saved plan, metrics and Bedrock analysis.

New accounts start with no brief or runs. Legacy shared demo data is not presented as that account's history. No default LedgerAI company, Cycle 5 plan, demo content fixture, chart series or canned activity timeline is loaded by the website.

## Verification

Verified on 7 September 2026: 100 regression tests passed. The deployed browser test completed two real Bedrock cycles, including brief save/refresh, plan revision, approval, persisted activity, analysis, digest, prior-cycle learning, session recovery and mobile overflow checks. No browser JavaScript errors were recorded.

Offline regression suite: `python -m pytest -q` (install the project's `dev` dependencies). The tests deliberately use mocks locally; this does not change the hosted model mode.

Explicit live browser test: set `PLAYWRIGHT_MODULE` to your installed Playwright module path, then pipe `python scripts/qa_account.py create` into `node tests/browser_hosted.cjs`. This creates a disposable Cognito account without sending email, runs real Bedrock cycles, and deletes the account at the end. It incurs normal AWS inference usage. Screenshots and the result report are generated under ignored `artifacts/`. Credentials must not be logged or committed.

Deploy the Python package with AWS SAM using `UseStubModels=false`, then run `python scripts/deploy_frontend.py --profile simplifynext --region us-east-1`. The deployment configuration preserves the live model setting. Frontend assets are served with revalidation and CloudFront invalidation.
