# Code Examples

These examples use current LWA-only authentication. They do not contain AWS SigV4 code. Replace paths and parameters only after checking the current official operation reference.

## Environment

```bash
export SP_API_LWA_CLIENT_ID='amzn1.application-oa2-client.example'
export SP_API_LWA_CLIENT_SECRET='use-a-secret-manager-in-production'
export SP_API_REFRESH_TOKEN='Atzr|example'
export SP_API_USER_AGENT='YourCompanyDataSync/1.0 (Language=Python/3.12)'
```

Do not commit these values. Shell history, CI logs, process arguments, and debug HTTP logs can leak credentials.

## Exchange a Refresh Token

```python
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import os

body = urlencode({
    "grant_type": "refresh_token",
    "refresh_token": os.environ["SP_API_REFRESH_TOKEN"],
    "client_id": os.environ["SP_API_LWA_CLIENT_ID"],
    "client_secret": os.environ["SP_API_LWA_CLIENT_SECRET"],
}).encode()

request = Request(
    "https://api.amazon.com/auth/o2/token",
    data=body,
    headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
    method="POST",
)

with urlopen(request, timeout=30) as response:
    token = json.load(response)["access_token"]
```

Production code should cache the token until shortly before expiry, redact errors, and use bounded timeouts.

## Exchange a Public-App Authorization Code

After verifying OAuth `state` and tenant binding in the callback handler:

```bash
export SP_API_AUTHORIZATION_CODE='short-lived-code-from-amazon'

python3 scripts/sp_api_client.py authorization-code \
  --redirect-uri 'https://your.example.com/amazon/oauth/callback' \
  --show-token
```

The redirect URI must exactly match the value used in the authorization request and the registered application configuration. The command prints secrets only because `--show-token` is explicit; capture the refresh token directly into a vault and suppress terminal/CI logging.

## Get Seller Marketplace Participations

```bash
python3 scripts/sp_api_client.py get \
  --region NA \
  --path /sellers/v1/marketplaceParticipations
```

Equivalent Python call after obtaining `access_token`:

```python
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import json

request = Request(
    "https://sellingpartnerapi-na.amazon.com/sellers/v1/marketplaceParticipations",
    headers={
        "Accept": "application/json",
        "x-amz-access-token": access_token,
        "x-amz-date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "user-agent": "YourCompanyDataSync/1.0 (Language=Python/3.12)",
    },
)

with urlopen(request, timeout=30) as response:
    payload = json.load(response)
    request_id = response.headers.get("x-amzn-RequestId")
```

## Search Catalog Items

```bash
python3 scripts/sp_api_client.py get \
  --region NA \
  --path /catalog/2022-04-01/items \
  --query marketplaceIds=ATVPDKIKX0DER \
  --query identifiers=B08EXAMPLE \
  --query identifiersType=ASIN \
  --query includedData=summaries,images,identifiers
```

Do not send `keywords` together with `identifiers`.

## Retrieve One Seller Listing

URL-encode the SKU as a path segment:

```python
from urllib.parse import quote

seller_id = "A1SELLEREXAMPLE"
sku = quote("SKU/with spaces", safe="")
path = f"/listings/2021-08-01/items/{seller_id}/{sku}"
```

```bash
python3 scripts/sp_api_client.py get \
  --region NA \
  --path '/listings/2021-08-01/items/A1SELLEREXAMPLE/SKU%2Fwith%20spaces' \
  --query marketplaceIds=ATVPDKIKX0DER \
  --query includedData=summaries,attributes,issues,offers,fulfillmentAvailability
```

## Search Orders `v2026-01-01`

```bash
python3 scripts/sp_api_client.py get \
  --region NA \
  --path /orders/2026-01-01/orders \
  --query marketplaceIds=ATVPDKIKX0DER \
  --query lastUpdatedAfter=2026-08-29T00:00:00Z \
  --query includedData=PROCEEDS,FULFILLMENT,PACKAGES
```

Parameters are camelCase. Verify the required filters against the current Orders model. When following a pagination token, keep timestamp strings and all other filters unchanged.

Get one order with authorized buyer/recipient data:

```bash
python3 scripts/sp_api_client.py get \
  --region NA \
  --path '/orders/2026-01-01/orders/123-1234567-1234567' \
  --query includedData=BUYER,RECIPIENT,FULFILLMENT,PACKAGES
```

Only request PII-bearing groups when approved roles and the business use case require them.

## Retrieve FBA Inventory Summaries

```bash
python3 scripts/sp_api_client.py get \
  --region NA \
  --path /fba/inventory/v1/summaries \
  --query granularityType=Marketplace \
  --query granularityId=ATVPDKIKX0DER \
  --query marketplaceIds=ATVPDKIKX0DER \
  --query details=true
```

Consume returned pages promptly and checkpoint only after every page is durable.

## Retrieve Financial Transactions

```bash
python3 scripts/sp_api_client.py finances \
  --region NA \
  --posted-after 2026-08-01T00:00:00Z \
  --posted-before 2026-08-29T00:00:00Z \
  --marketplace-id ATVPDKIKX0DER \
  --show-metadata
```

The command validates offset-aware timestamps and the 180-day maximum window, then prints one response page without changing Amazon's data. Continue with `--next-token` while `payload.nextToken` is present, even if a page has no transactions; repeat the exact same bounds and filters.

Filter or reconcile a known deferred order:

```bash
python3 scripts/sp_api_client.py finances \
  --region NA \
  --related-identifier-name ORDER_ID \
  --related-identifier-value 123-1234567-1234567
```

Do not pass `--marketplace-id` for US MFN transactions. The current Amazon operation reference calls out that exception.

### Normalize timestamps without losing source evidence

```python
from datetime import datetime, timezone

def parse_sp_api_instant(raw: str) -> tuple[str, datetime]:
    candidate = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
    value = datetime.fromisoformat(candidate)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("SP-API date-time must contain Z or an explicit offset")
    return raw, value.astimezone(timezone.utc)

source_posted_date, posted_at_utc = parse_sp_api_instant(transaction["postedDate"])
retrieved_at_utc = datetime.now(timezone.utc)
```

Store both values. Render `posted_at_utc` in a marketplace/business zone only when displaying it; never use the machine's implicit local time.

### Keep deferred settlement state separate from the time checkpoint

```python
status = transaction.get("transactionStatus")
transaction_id = transaction["transactionId"]

upsert_transaction(transaction_id, transaction)
if status == "DEFERRED":
    deferred = next(
        (context for context in (transaction.get("contexts") or [])
         if context.get("contextType") == "DeferredContext"),
        {},
    )
    enqueue_deferred_recheck(
        transaction_id=transaction_id,
        maturity_date=deferred.get("maturityDate"),
        related_identifiers=transaction.get("relatedIdentifiers", []),
    )
elif status in {"RELEASED", "DEFERRED_RELEASED"}:
    resolve_deferred_recheck(transaction_id)
```

The context can also occur at item level, so production normalization should inspect transaction and item `contexts`. Treat `maturityDate` as scheduling input only; recognize release from `transactionStatus`. A rolling fetch window should overlap by more than the documented possible 48-hour lag, while the deferred queue continues revisiting older unresolved transactions.

## Generic Pagination Loop

Token placement varies by API, so configure the request token name and response extraction for the selected operation:

```python
query = {
    "marketplaceIds": "ATVPDKIKX0DER",
    "lastUpdatedAfter": "2026-08-29T00:00:00Z",
}

while True:
    page = client.get("/orders/2026-01-01/orders", query=query)
    upsert_orders(page.get("orders", []))

    token = page.get("pagination", {}).get("nextToken")
    if not token:
        break

    # The exact request parameter name is version-specific.
    query["paginationToken"] = token
```

Do not assume every response uses `payload.NextToken`; that shape is common in older generated SDKs but is not universal.

## Create an RDT for a Restricted Legacy Operation

```bash
python3 scripts/sp_api_client.py rdt \
  --region NA \
  --resource-method GET \
  --resource-path '/orders/v0/orders/123-1234567-1234567/address' \
  --data-element shippingAddress
```

The command does not print the RDT unless `--show-token` is supplied. To use a token stored in an environment variable:

```bash
export ORDER_ADDRESS_RDT='Atza|restricted-example'

python3 scripts/sp_api_client.py get \
  --region NA \
  --path '/orders/v0/orders/123-1234567-1234567/address' \
  --access-token-env ORDER_ADDRESS_RDT
```

Do not introduce this legacy Orders workflow into new `v2026-01-01` integrations.

## Retry Pattern

```python
import random
import time

retryable = {429, 500, 503}

for attempt in range(5):
    try:
        return call_sp_api()
    except SpApiHttpError as error:
        if error.status not in retryable or attempt == 4:
            raise
        delay = error.retry_after or min(30.0, 0.5 * (2 ** attempt))
        time.sleep(delay + random.uniform(0, delay * 0.2))
```

Production code must also enforce per-operation concurrency and log Amazon's request ID without logging credentials or restricted payloads.
