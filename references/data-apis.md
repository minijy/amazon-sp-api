# Direct Seller Data APIs

This catalog prioritizes operations that return JSON directly. It intentionally excludes Reports, Feeds, Data Kiosk queries, invoice/document downloads, labels, and other file-generation workflows.

Always open the linked official guide/reference before implementation. API versions, roles, parameters, marketplaces, rate limits, and pricing can change independently.

## Recommended Core Coverage

| Domain | Current API | Principal direct operations | Typical use |
|---|---|---|---|
| Seller account | Sellers `v1` | `getMarketplaceParticipations` | Seller marketplaces and participation status |
| Amazon catalog | Catalog Items `v2022-04-01` | `searchCatalogItems`, `getCatalogItem` | ASIN facts, dimensions, images, identifiers, relationships, ranks |
| Seller listings | Listings Items `v2021-08-01` | `searchListingsItems`, `getListingsItem` | Seller SKU attributes, offers, issues, status, fulfillment availability |
| Listing schemas | Product Type Definitions `v2020-09-01` | `searchDefinitionsProductTypes`, `getDefinitionsProductType` | Product-type requirements and schemas |
| Listing eligibility | Listings Restrictions `v2021-08-01` | `getListingsRestrictions` | ASIN listing restrictions |
| Orders | Orders `v2026-01-01` | `searchOrders`, `getOrder` | Orders, items, buyer/recipient, proceeds, expenses, fulfillment, packages |
| Competitive pricing | Product Pricing `v2022-05-01` | `getCompetitiveSummary`, `getFeaturedOfferExpectedPriceBatch` | Competitive summary and featured-offer expected prices |
| FBA inventory | FBA Inventory `v1` | `getInventorySummaries` | Fulfillable, inbound, reserved, unfulfillable and researching quantities |
| Finance | Finances `v2024-06-19` | `listTransactions` | Released/deferred transaction detail by time or identifier |
| Sales aggregation | Sales `v1` | `getOrderMetrics` | Aggregated order count, units and sales metrics |
| Fee estimate | Product Fees `v0` | `getMyFeesEstimateForASIN`, `getMyFeesEstimateForSKU`, `getMyFeesEstimates` | Direct JSON fee estimates; POST is used because the query has a body |
| FBA inbound | Fulfillment Inbound `v2024-03-20` | `listInboundPlans`, `getInboundPlan`, `listInboundPlanItems`, `getShipment`, `listShipmentItems` and related list/get operations | Inbound plan and shipment state |

## 1. Seller Account and Marketplaces

Start every seller integration with `getMarketplaceParticipations`:

```http
GET /sellers/v1/marketplaceParticipations
```

Use the result to establish seller marketplace participation. Do not hard-code one marketplace merely from the regional endpoint.

- [Sellers API guide](https://developer-docs.amazon.com/sp-api/docs/sellers-api)
- [`getMarketplaceParticipations` reference](https://developer-docs.amazon.com/sp-api/reference/getmarketplaceparticipations)
- [Marketplace IDs](https://developer-docs.amazon.com/sp-api/docs/marketplace-ids)

## 2. Catalog Items

Catalog Items describes the shared Amazon catalog keyed by ASIN; it is not the seller's own listing state.

```http
GET /catalog/2022-04-01/items
GET /catalog/2022-04-01/items/{asin}
```

Use `includedData` only for required datasets: `attributes`, `classifications`, `dimensions`, `identifiers`, `images`, `productTypes`, `relationships`, `salesRanks`, `summaries`, or vendor-only details. Search allows identifiers or keywords, not both in one request. Identifier search supports limited batches; keyword search is paginated and capped by the API.

- [Catalog Items API guide](https://developer-docs.amazon.com/sp-api/docs/catalog-items-api)
- [Catalog Items `v2022-04-01` reference](https://developer-docs.amazon.com/sp-api/docs/catalog-items-api-v2022-04-01-reference)

## 3. Listings Items and Product Definitions

Listings Items represents a seller's SKU contribution and its issues/status.

```http
GET /listings/2021-08-01/items/{sellerId}/{sku}
GET /listings/2021-08-01/items/{sellerId}
```

Request only necessary `includedData`, commonly `summaries`, `attributes`, `issues`, `offers`, and `fulfillmentAvailability`. URL-encode seller SKUs as one path segment; do not double-encode them.

Use Product Type Definitions to interpret listing attributes and requirements; use Listings Restrictions to determine whether an ASIN can be listed in a marketplace.

- [Listings Items API](https://developer-docs.amazon.com/sp-api/docs/listings-items-api)
- [Manage product listings](https://developer-docs.amazon.com/sp-api/docs/manage-product-listings-guide)
- [Product Type Definitions API](https://developer-docs.amazon.com/sp-api/docs/product-type-definitions-api)
- [Listings Restrictions API](https://developer-docs.amazon.com/sp-api/docs/listings-restrictions-api)

This skill covers the GET operations. `putListingsItem`, `patchListingsItem`, and `deleteListingsItem` mutate production listings and require separate explicit authorization.

## 4. Orders `v2026-01-01`

Use the current Orders API:

```http
GET /orders/2026-01-01/orders
GET /orders/2026-01-01/orders/{orderId}
```

`searchOrders` retrieves by created/updated windows and filters. `getOrder` retrieves one order. Items are consolidated into the response, and `includedData` can request `BUYER`, `RECIPIENT`, `PROCEEDS`, `EXPENSE`, `PROMOTION`, `CANCELLATION`, `FULFILLMENT`, and `PACKAGES` as authorized.

Key rules:

- Use camelCase parameters for `v2026-01-01`; do not copy PascalCase `v0` parameters.
- Use one unchanged UTC filter set across pagination and pass the returned pagination token exactly once encoded.
- Request only required included-data groups; PII is role-controlled.
- Orders older than two years are generally unavailable, with documented marketplace exceptions.
- Treat Orders `v0` as migration-only. Its main read operations are deprecated and scheduled for removal; do not build a new sync on it.

- [Orders API guide](https://developer-docs.amazon.com/sp-api/docs/orders-api)
- [Orders `v2026-01-01` official model](https://github.com/amzn/selling-partner-api-models/blob/main/models/orders-api-model/orders_2026-01-01.json)
- [Orders migration guide](https://developer-docs.amazon.com/sp-api/docs/orders-api-migration-guide)

## 5. Product Pricing

Use the current `v2022-05-01` operations:

- `getCompetitiveSummary`: competitive summary and featured buying options for ASIN/marketplace inputs.
- `getFeaturedOfferExpectedPriceBatch`: expected featured-offer pricing for batches of seller SKUs.

Legacy Product Pricing `v0` operations remain only where the current API does not yet replace the required data. Do not use the removed `CompetitivePriceThreshold`; use current competitive-price/reference-price fields and verify Japan-specific behavior.

- [Product Pricing API](https://developer-docs.amazon.com/sp-api/docs/product-pricing-api-v0-use-case-guide)
- [Product Pricing `v2022-05-01` reference](https://developer-docs.amazon.com/sp-api/docs/product-pricing-api-v2022-05-01-reference)

## 6. FBA Inventory

```http
GET /fba/inventory/v1/summaries
```

`getInventorySummaries` returns marketplace-level FBA inventory such as fulfillable, inbound, reserved, unfulfillable, and researching quantities. Use `granularityType=Marketplace` with the marketplace ID and page using the returned token. Amazon documentation notes that pagination tokens can be short-lived; follow the current reference and consume pages promptly.

- [FBA Inventory API](https://developer-docs.amazon.com/sp-api/docs/fba-inventory-api)
- [`getInventorySummaries` reference](https://developer-docs.amazon.com/sp-api/reference/getinventorysummaries)

## 7. Financial Transactions

```http
GET /finances/2024-06-19/transactions
```

Use `listTransactions` as the primary direct-data replacement for Seller Central's transaction-detail view and transaction-data report. Its unified transaction model covers order proceeds, refunds, fees, commissions, adjustments, reimbursements, and nested amount `breakdowns` without creating a report document. It supports a posted time range or the filterable related identifiers `ORDER_ID` and `FINANCIAL_EVENT_GROUP_ID`.

### Query constraints

- `postedAfter` is inclusive and is required unless a related identifier is supplied. It must be more than two minutes before the request.
- `postedBefore` is exclusive, must be later than `postedAfter`, and must also be more than two minutes before the request. If the two bounds are more than 180 days apart, Amazon returns an empty response. This is a per-query window limit, not evidence of a two-year retention limit.
- Keep both timestamp strings and every other filter unchanged when following `nextToken`. Pages can be empty while still returning a token; continue until the token is absent.
- The documented default usage plan is `0.5` requests/second with burst `10`; use the response rate-limit header as the effective value.
- For US MFN transactions, the current operation reference says not to supply `marketplaceId`.

### Timestamp handling

`postedDate`, deferred `maturityDate`, payment dates, and time-range contexts use ISO 8601 date-time strings. The schema does not promise that every transaction timestamp is already expressed in the application's or marketplace's local zone.

- Accept only timestamps containing `Z` or an explicit offset. Parse them as aware instants, preserve the raw source string, and store a normalized UTC value for comparison and checkpoints.
- Convert to a marketplace or business time zone only in the presentation/reporting layer. Never strip an offset or attach the server's local zone to a naive value.
- Store `postedDate` separately from retrieval and local processing times. Use `postedDate` for API-window membership, not the order date, shipment date, statement date, or ingestion time.
- Keep the original inclusive lower bound and exclusive upper bound for auditability and pagination replay.

### Delayed and deferred transactions

Financial events might omit orders from the most recent 48 hours. In addition, `DEFERRED` is a business state, not a request delay or an error:

- `RELEASED` means currently released; `DEFERRED` means currently deferred; `DEFERRED_RELEASED` means it was deferred and was later released. Upsert by `transactionId` so a later status can replace the earlier state.
- A deferred context can provide `deferralReason` and `maturityDate`. Treat `maturityDate` as an expected release date, not proof that funds have been released; the status remains authoritative.
- Keep unresolved deferred transactions in a work queue. Re-query using `ORDER_ID` or `FINANCIAL_EVENT_GROUP_ID` when present; otherwise replay the original bounded posted-time bucket. Stop only after observing a released status or applying an explicit business retention/escalation policy.
- Run overlapping incremental windows beyond the documented recent-event delay and a periodic longer reconciliation. `TRANSACTION_UPDATE` can trigger a prompt fetch when a new transaction is posted, but its payload is not a complete ledger and the documentation does not promise it for every later deferred-status change.
- Reconcile amounts by currency and related identifiers rather than assuming one transaction per order. Do not recognize a `DEFERRED` amount as available cash merely because it exists in the API.

- [Finances API](https://developer-docs.amazon.com/sp-api/docs/finances-api)
- [`listTransactions` reference](https://developer-docs.amazon.com/sp-api/reference/listtransactions)
- [Get latest transactions](https://developer-docs.amazon.com/sp-api/docs/get-latest-transactions)
- [Finances `v2024-06-19` official model](https://github.com/amzn/selling-partner-api-models/blob/main/models/finances-api-model/finances_2024-06-19.json)

## 8. Sales Metrics

```http
GET /sales/v1/orderMetrics
```

`getOrderMetrics` returns aggregated metrics for a time interval and granularity. Use it for dashboards and trend summaries, not as a source of individual order truth. Check marketplace/program support and respect the maximum interval/granularity combinations in the current model.

- [Sales API guide](https://developer-docs.amazon.com/sp-api/docs/sales-api)
- [Sales API official model](https://github.com/amzn/selling-partner-api-models/blob/main/models/sales-api-model/sales.json)

## 9. Product Fee Estimates

These operations return JSON directly even though they use POST because the estimate input is structured:

- `getMyFeesEstimateForASIN`
- `getMyFeesEstimateForSKU`
- `getMyFeesEstimates` for a supported batch

Fee estimates are not settlement truth. Store request identifier, marketplace, price, shipping, currency, timestamp, and response. Actual fees can differ; reconcile with Finances data.

- [Product Fees API](https://developer-docs.amazon.com/sp-api/docs/product-fees-api)
- [Estimate fees for an ASIN](https://developer-docs.amazon.com/sp-api/docs/get-product-fee-estimates-asin)
- [`getMyFeesEstimateForSKU` reference](https://developer-docs.amazon.com/sp-api/reference/getmyfeesestimateforsku)

## 10. Fulfillment Inbound Retrieval

Use `v2024-03-20` for current FBA inbound workflows. Direct read operations include:

- Plans: `listInboundPlans`, `getInboundPlan`, `listInboundPlanItems`, `listInboundPlanBoxes`, `listInboundPlanPallets`.
- Packing and placement: `listPackingOptions`, `listPackingGroupItems`, `listPackingGroupBoxes`, `listPlacementOptions`, `listPrepDetails`.
- Shipments: `getShipment`, `listShipmentItems`, `listShipmentBoxes`, `listShipmentPallets`, `listDeliveryWindowOptions`, `listTransportationOptions`.
- Asynchronous operation state: `getInboundOperationStatus`.

Do not include label, bill-of-lading, or delivery-document endpoints in the direct-data catalog. Generation/confirmation/update operations are mutations and require explicit authorization.

- [Fulfillment Inbound API](https://developer-docs.amazon.com/sp-api/docs/fulfillment-inbound-api)
- [Fulfillment Inbound `v2024-03-20` reference](https://developer-docs.amazon.com/sp-api/docs/fulfillment-inbound-api-v2024-03-20-reference)
- [Fulfillment Inbound rate limits](https://developer-docs.amazon.com/sp-api/docs/fulfillment-inbound-api-rate-limits)

## Conditional Direct-Data Domains

Add these only when the seller's program and marketplace require them:

| Domain | Direct retrieval operations | Official guide |
|---|---|---|
| Customer review/return insight | Item/browse-node review topics and trends, browse-node return topics/trends | [Customer Feedback API](https://developer-docs.amazon.com/sp-api/docs/customer-feedback-api) |
| Subscribe & Save | `getSellingPartnerMetrics`, `listOfferMetrics`, `listOffers` | [Replenishment API](https://developer-docs.amazon.com/sp-api/docs/replenishment-api) |
| Multi-location inventory | `getSupplySources`, `getSupplySource` | [Supply Sources API](https://developer-docs.amazon.com/sp-api/docs/supply-sources-api) |
| Multi-channel fulfillment | `getFulfillmentOrder`, `listAllFulfillmentOrders`, `getPackageTrackingDetails`, feature/inventory queries | [Fulfillment Outbound API](https://developer-docs.amazon.com/sp-api/docs/fulfillment-outbound-api) |
| Amazon Warehousing and Distribution | `listInventory`, inbound shipment/status retrieval | [AWD API](https://developer-docs.amazon.com/sp-api/docs/amazon-warehousing-and-distribution-api) |
| Seller-fulfilled shipping | shipment, rates, tracking, access-point and account queries where supported | [Shipping API v2](https://developer-docs.amazon.com/amazon-shipping/docs/shipping-api-v2-reference) |

Program availability, roles, regional support, and API versions must be checked before adding these domains.

## Explicitly Excluded Bulk/Document Interfaces

Do not recommend the following unless the user specifically needs bulk history or data unavailable through direct APIs:

- Reports API document generation/download.
- Feeds API document upload and processing.
- Data Kiosk asynchronous GraphQL query/document retrieval.
- Invoice, shipping-label, bill-of-lading, packing-slip, or other binary/document download operations.

When a direct API cannot meet volume, history, or dataset requirements, explain the gap and obtain agreement before expanding to a bulk/document workflow.
