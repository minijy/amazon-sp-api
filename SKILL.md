---
name: amazon-sp-api
description: Integrate, review, or troubleshoot Amazon Seller Central Selling Partner API (SP-API) applications, including developer onboarding, LWA authorization, direct JSON data retrieval, restricted-data access, pagination, throttling, and notifications. Use for seller account, catalog, listings, orders, pricing, inventory, finance, fees, sales, fulfillment, or SP-API authentication work. Do not route Amazon Ads API, AWS retail services, or Vendor Central-only integrations here unless explicitly adapting the scope.
---

# Amazon SP-API

Build Seller Central integrations against Amazon Selling Partner API using current official API versions and least-privilege roles. Prefer direct JSON operations and event notifications. Do not default to Reports, Feeds, Data Kiosk, or other asynchronous document-generation workflows when a direct operation satisfies the requirement.

## Route the Task

- For developer registration, application creation, role selection, self-authorization, or public OAuth setup, read [references/onboarding.md](references/onboarding.md).
- For LWA tokens, grantless scopes, RDT, endpoints, credentials, or request headers, read [references/authentication.md](references/authentication.md) and use [scripts/sp_api_client.py](scripts/sp_api_client.py).
- For seller data retrieval, choose operations from [references/data-apis.md](references/data-apis.md). Verify the linked official reference before coding.
- For notifications, application-secret rotation, error handling, usage plans, or operational requirements, read [references/essential-apis.md](references/essential-apis.md).
- For runnable request patterns, pagination, and integration examples, read [references/code-examples.md](references/code-examples.md).

## Establish the Integration Boundary

Confirm these facts before implementation:

1. Seller application, vendor application, or public service for multiple sellers. This skill defaults to seller applications.
2. Private self-authorization or public OAuth authorization.
3. Target marketplaces and their SP-API region: `NA`, `EU`, or `FE`.
4. Required data domains and corresponding application roles.
5. Whether buyer/recipient PII is actually necessary. Request restricted roles only for a justified use case.
6. Static sandbox, dynamic sandbox, or production.
7. Polling cadence, notification support, rate limits, retention, and downstream storage.
8. Current API version in the official reference and deprecation schedule.

Do not assume older examples are current. In particular, current SP-API requests use LWA access tokens and no longer require AWS IAM credentials or AWS Signature Version 4. Orders API `v2026-01-01` is the current seller order API; do not start a new integration on Orders `v0`.

## Core Workflow

1. Map business data requirements to the smallest set of SP-API roles and direct operations.
2. Complete developer/app registration and obtain LWA client credentials plus the appropriate refresh token or public OAuth authorization.
3. Exchange the refresh token for a short-lived LWA access token.
4. Resolve the correct regional endpoint and marketplace IDs.
5. Call direct operations with `x-amz-access-token`, `x-amz-date`, and an identifying `user-agent`.
6. Persist `x-amzn-RequestId`, rate-limit headers, cursor/checkpoint state, and retrieval window metadata.
7. Page using the operation's exact token name and preserve all other query arguments byte-equivalently where the API requires it.
8. Apply bounded retries for `429`, `500`, and `503`, honoring `Retry-After` when present and adding jitter.
9. Prefer Notifications API for change events, but retain a polling/reconciliation path because notifications can be delayed or unavailable.
10. Validate in sandbox, then perform a deliberate production-readiness review.

## Data Retrieval Rules

- Use the newest non-deprecated API version supported for the operation.
- Treat Amazon operation names, paths, parameter case, pagination token names, and included-data values as version-specific.
- Use UTC ISO 8601 timestamps. Preserve the exact timestamp and filter set across paginated calls.
- Keep one checkpoint per seller, marketplace, operation, and filter set.
- Deduplicate by stable Amazon identifiers and update timestamps; do not assume page delivery is exactly once.
- Allow overlap in incremental time windows and upsert results to avoid missing late updates.
- Capture amount and currency together and use exact decimal handling downstream.
- Minimize PII collection and enforce Amazon's Data Protection Policy, retention, access, encryption, and deletion requirements.
- Never print or commit client secrets, refresh tokens, access tokens, RDTs, buyer data, or recipient data.

## Script Usage

The standard-library Python helper exchanges tokens and performs generic JSON requests:

```bash
export SP_API_LWA_CLIENT_ID='...'
export SP_API_LWA_CLIENT_SECRET='...'
export SP_API_REFRESH_TOKEN='...'

python3 scripts/sp_api_client.py token
python3 scripts/sp_api_client.py get \
  --region NA \
  --path /sellers/v1/marketplaceParticipations

python3 scripts/sp_api_client.py finances \
  --region NA \
  --posted-after 2026-08-01T00:00:00Z \
  --posted-before 2026-08-29T00:00:00Z
```

Use `--sandbox` only with documented sandbox parameters. Use `--access-token-env` to supply an RDT or externally managed access token without exposing it on the command line. The helper does not store tokens and does not implement legacy SigV4 signing.

## Required Design or Review Output

Produce the artifacts relevant to the request:

- Application type, authorization path, regions, marketplaces, and required roles.
- Direct operation inventory with API versions, paths, official links, pagination, and rate-limit considerations.
- Credential and token lifecycle, including refresh-token ownership and client-secret rotation.
- Incremental synchronization checkpoints, deduplication, retry, and reconciliation strategy.
- PII classification and restricted-role/RDT decision.
- Notification subscriptions plus fallback polling.
- Sandbox and production verification plan.

## Authorization and Safety Boundary

Registration guidance, local code generation, offline tests, and read-only sandbox calls are within ordinary implementation scope. Do not create or modify production listings, acknowledge/ship orders, create fulfillment shipments, rotate live credentials, delete subscriptions, or perform any other production mutation without explicit authorization for that action. Data retrieval permission does not imply permission to mutate seller state.

## Exclusions

- Amazon Advertising API uses a different platform and authorization model.
- Reports, Feeds, and Data Kiosk are asynchronous bulk/document workflows and are intentionally not the primary catalog here.
- Vendor Retail Procurement and Vendor Direct Fulfillment APIs are outside the seller-first scope; add a separate reference when a Vendor Central use case is requested.
- Scraping Seller Central pages is not a substitute for SP-API.
