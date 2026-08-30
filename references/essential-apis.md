# Essential Supporting APIs and Operational Controls

Direct GET endpoints are not sufficient for a reliable integration. Use the following supporting APIs and controls where applicable.

## Tokens API

Tokens API `v2021-03-01` creates Restricted Data Tokens for operations that explicitly require restricted resources. It is a required security boundary, not a general data API.

```http
POST /tokens/2021-03-01/restrictedDataToken
```

Specify only the exact HTTP method/path and data elements required. Use the resulting RDT in `x-amz-access-token` for the matching call.

- [Tokens API guide](https://developer-docs.amazon.com/sp-api/docs/tokens-api-use-case-guide)
- [`createRestrictedDataToken` reference](https://developer-docs.amazon.com/sp-api/reference/createrestricteddatatoken)

Orders `v2026-01-01` is an important exception: its buyer and recipient data is role-controlled and does not use the older Orders `v0` RDT sequence. Other restricted operations can still require RDT.

## Notifications API

Notifications API `v1` reduces polling and should be used for supported events. It supports Amazon SQS and EventBridge destinations.

Direct management operations include:

- Destinations: `getDestinations`, `getDestination`, `createDestination`, `deleteDestination`.
- Subscriptions: `getSubscription`, `getSubscriptionById`, `createSubscription`, `deleteSubscriptionById`.

The GET operations are read-only. Create/delete operations mutate notification infrastructure and require explicit authorization.

Useful seller notification families include order changes, listing status/issues, offer/pricing changes, FBA inventory availability, account status, transaction updates, and application authorization changes. Verify the currently supported payload version and workflow before subscribing.

Design rules:

1. Use a durable SQS queue or EventBridge target with encryption and least-privilege policies.
2. Deduplicate by notification ID and make consumers idempotent.
3. Store raw evidence only as policy permits; normalize business identifiers separately.
4. Retry consumers with a dead-letter queue.
5. Keep polling/reconciliation because Amazon explicitly recommends a backup mechanism.
6. Handle deauthorization by disabling seller jobs and restricting retained data.

- [Notifications API](https://developer-docs.amazon.com/sp-api/docs/notifications-api)
- [Notification type values](https://developer-docs.amazon.com/sp-api/docs/notification-type-values)
- [SQS notification workflow](https://developer-docs.amazon.com/sp-api/docs/notifications-api-v1-use-case-guide)
- [Notifications API and its SQS/EventBridge workflows](https://developer-docs.amazon.com/sp-api/docs/notifications-api)

## Application Management API

Application Management API `v2023-11-30` supports programmatic LWA client-secret rotation. `rotateApplicationClientSecret` is grantless and uses scope `sellingpartnerapi::client_credential:rotation`.

The new credential is delivered to a preregistered SQS queue; it is not an ordinary synchronous JSON secret response. Configure encryption and access before calling rotation. Test on a draft/sandbox application and update the secret vault within the documented overlap period.

- [Application Management API guide](https://developer-docs.amazon.com/sp-api/docs/application-management-api-v2023-11-30-use-case-guide)
- [Rotate application credentials](https://developer-docs.amazon.com/sp-api/docs/rotate-your-applications-lwa-credentials)

Credential rotation is a production mutation. Do not invoke it merely because the integration is being reviewed.

## Usage Plans and Rate Limits

Each operation has its own token-bucket usage plan. The documented default is not necessarily the seller/application's actual plan.

- Read `x-amzn-RateLimit-Limit` when Amazon returns it.
- Treat `429` as throttling and honor `Retry-After` when present.
- Limit concurrency per seller/application/operation, not just globally.
- Add exponential backoff with jitter for `429`, `500`, and `503`.
- Bound attempts and surface persistent failures; do not retry every `4xx`.
- Prefer batches and consolidated included-data calls where they reduce billable calls and remain within payload limits.
- Account for current SP-API metered-call pricing when designing high-frequency polling.

- [Usage plans and rate limits](https://developer-docs.amazon.com/sp-api/docs/usage-plans-and-rate-limits-in-the-sp-api)
- [Optimize rate limits](https://developer-docs.amazon.com/sp-api/docs/strategies-to-optimize-rate-limits-for-your-application-workloads)
- [SP-API onboarding and metered-call fee references](https://developer-docs.amazon.com/sp-api/docs/onboarding-overview)

## Error Classification

| Status | Meaning/action |
|---|---|
| `400` | Fix parameters, casing, version, encoding, or unsupported filter; do not blind-retry |
| `401` | Access token missing/expired/invalid; refresh once, then fail safely |
| `403` | Check app role, seller authorization, marketplace/program eligibility, token type, and operation restrictions |
| `404` | Confirm region, path/version, seller ownership, and resource lifecycle |
| `409` | Resolve resource/state conflict according to the operation |
| `429` | Throttle using `Retry-After` and operation-scoped backoff |
| `500`, `503` | Bounded exponential retry with jitter; preserve request ID |

Always record `x-amzn-RequestId`, operation, version, seller reference, marketplace, attempt number, and sanitized error body.

- [Development tools and error-handling resources](https://developer-docs.amazon.com/sp-api/docs/development-tools)
- [Troubleshoot SP-API errors](https://developer-docs.amazon.com/sp-api/docs/troubleshooting-sp-api-errors)

## Synchronization Requirements

### Incremental windows

- Store UTC checkpoints per seller/marketplace/operation/filter.
- Use a small overlap and idempotent upserts to cover late updates.
- Advance the checkpoint only after all pages are durably processed.
- Keep the original lower/upper bounds constant across pages.

### Pagination

- Token names vary: `nextToken`, `pageToken`, or `paginationToken` depending on API/version.
- Response location also varies. Read the operation model.
- Do not decode and re-encode opaque tokens manually.
- Preserve original filters exactly and URL-encode the token once.
- Stop only when the response no longer contains a next token; some APIs can return empty pages with another token.

### Reconciliation

- Run periodic full or bounded lookback comparisons for business-critical orders, finance, inventory, and inbound shipments.
- Re-fetch unresolved identifiers directly.
- Distinguish source update time, retrieval time, and local processing time.
- Do not delete local data solely because it was absent from one incremental page.

### Finances-specific state

- Maintain two independent controls: a completed posted-time window checkpoint and an unresolved-deferred queue keyed by seller plus `transactionId`.
- Use a configurable overlap that exceeds the documented possible 48-hour recent-event lag. Advance the main checkpoint only after all pages for the fixed window are durable.
- Store the raw ISO 8601 value, normalized UTC instant, retrieval time, status, amount/currency, related identifiers, and deferred `deferralReason`/`maturityDate` when present.
- Revisit `DEFERRED` rows independently of the main watermark. Upsert a later `DEFERRED_RELEASED` state instead of inserting a second logical transaction.
- Use `TRANSACTION_UPDATE` as a low-latency signal to fetch or upsert details; polling remains the completeness mechanism because the notification represents a newly posted transaction and is not a full transaction record.

## Data Protection

- Request only the roles and `includedData` needed for the product.
- Classify buyer, recipient, tax, and shipping data before storage.
- Encrypt sensitive data in transit and at rest with scoped decrypt permissions.
- Apply policy-based retention and deletion, including backups.
- Block PII and credentials from logs, traces, prompts, analytics, test fixtures, and support exports.
- Audit access to restricted data and manual exports.
- Implement seller deauthorization and application deletion cleanup.

- [Data Protection Policy](https://developer-docs.amazon.com/sp-api/docs/data-protection-policy)
- [Acceptable Use Policy](https://developer-docs.amazon.com/sp-api/docs/acceptable-use-policy)
- [Safeguard sensitive credentials](https://developer-docs.amazon.com/sp-api/docs/safeguarding-sensitive-credentials-for-sp-api-applications)

## Version Governance

At implementation and at least before every production release:

1. Check [SP-API release notes](https://developer-docs.amazon.com/sp-api/docs/sp-api-release-notes).
2. Check [SP-API deprecation schedule](https://developer-docs.amazon.com/sp-api/docs/sp-api-deprecation-schedule).
3. Compare the pinned operation model with Amazon's [official OpenAPI model repository](https://github.com/amzn/selling-partner-api-models).
4. Run contract tests for parameters, response fields, pagination, and sandbox fixtures.
5. Treat undocumented fields as optional; do not build critical logic on them.
