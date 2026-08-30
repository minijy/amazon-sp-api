# Authentication and Authorization

Use this reference for LWA exchange, request headers, regional endpoints, grantless calls, restricted data, and credential handling.

## Current Authentication Model

Current SP-API calls no longer require AWS IAM credentials or AWS Signature Version 4. Older tutorials that request an IAM user/role, access key, secret access key, or SigV4 signing are obsolete for current SP-API authentication.

The ordinary request chain is:

```text
LWA client ID + client secret + refresh token
                  ↓ POST /auth/o2/token
short-lived LWA access token (normally 1 hour)
                  ↓ x-amz-access-token
regional SP-API endpoint
```

Official reference: [Connect to the SP-API](https://developer-docs.amazon.com/sp-api/docs/connecting-to-the-selling-partner-api)

## LWA Refresh-Token Exchange

Send form-encoded data to `https://api.amazon.com/auth/o2/token`:

```bash
curl --request POST 'https://api.amazon.com/auth/o2/token' \
  --header 'Content-Type: application/x-www-form-urlencoded;charset=UTF-8' \
  --data-urlencode 'grant_type=refresh_token' \
  --data-urlencode "refresh_token=$SP_API_REFRESH_TOKEN" \
  --data-urlencode "client_id=$SP_API_LWA_CLIENT_ID" \
  --data-urlencode "client_secret=$SP_API_LWA_CLIENT_SECRET"
```

Cache the access token in memory or an encrypted short-lived cache until shortly before expiry. Do not refresh once per business API request. Never log the returned token.

## Public-Application Authorization-Code Exchange

After validating OAuth `state` and receiving Amazon's short-lived authorization code at the exact registered redirect URI, exchange it server-side:

```bash
export SP_API_AUTHORIZATION_CODE='received-code'

python3 scripts/sp_api_client.py authorization-code \
  --redirect-uri 'https://your.example.com/amazon/oauth/callback' \
  --show-token
```

The initial response contains the seller refresh token. Capture it directly into a secret vault and bind it to the authorizing seller/application; do not send it to a browser or ordinary log. Never exchange a code before verifying the state value and intended tenant.

See [Website authorization workflow](https://developer-docs.amazon.com/sp-api/docs/website-authorization-workflow) and [Appstore authorization workflow](https://developer-docs.amazon.com/sp-api/docs/selling-partner-appstore-authorization-workflow).

## Grantless Access Tokens

Grantless operations use `grant_type=client_credentials` and a scope instead of a seller refresh token:

- `sellingpartnerapi::notifications` for grantless Notifications operations.
- `sellingpartnerapi::client_credential:rotation` for Application Management secret rotation.

```bash
python3 scripts/sp_api_client.py grantless-token \
  --scope 'sellingpartnerapi::notifications'
```

Grantless does not mean unauthenticated and does not authorize seller-specific data access.

Official reference: [Grantless operations](https://developer-docs.amazon.com/sp-api/docs/grantless-operations)

## Regional Endpoints

| Region | Production endpoint | Sandbox endpoint |
|---|---|---|
| `NA` | `https://sellingpartnerapi-na.amazon.com` | `https://sandbox.sellingpartnerapi-na.amazon.com` |
| `EU` | `https://sellingpartnerapi-eu.amazon.com` | `https://sandbox.sellingpartnerapi-eu.amazon.com` |
| `FE` | `https://sellingpartnerapi-fe.amazon.com` | `https://sandbox.sellingpartnerapi-fe.amazon.com` |

Choose the endpoint from the marketplace, not from server location. See [SP-API endpoints](https://developer-docs.amazon.com/sp-api/docs/sp-api-endpoints) and [Marketplace IDs](https://developer-docs.amazon.com/sp-api/docs/marketplace-ids).

## Business API Request Headers

Send at least:

```http
GET /sellers/v1/marketplaceParticipations HTTP/1.1
Host: sellingpartnerapi-na.amazon.com
x-amz-access-token: Atza|...
x-amz-date: 20260830T061500Z
user-agent: YourCompanyTool/1.0 (Language=Python/3.12)
Accept: application/json
```

Persist response `x-amzn-RequestId` for diagnostics. Observe `x-amzn-RateLimit-Limit` when returned. Do not place tokens in query strings.

## Restricted Data Tokens

Some restricted operations require a short-lived Restricted Data Token (RDT) from Tokens API `v2021-03-01`. The request names the exact HTTP method/path and permitted data elements. Use the returned RDT in `x-amz-access-token` for the matching restricted call.

```bash
python3 scripts/sp_api_client.py rdt \
  --region NA \
  --resource-method GET \
  --resource-path '/orders/v0/orders/123-1234567-1234567/address' \
  --data-element shippingAddress
```

Do not request a broad RDT. Bind it to the smallest resource set, do not persist it longer than required, and never log it.

Important version boundary: Orders API `v2026-01-01` uses role-based access for its `BUYER` and `RECIPIENT` included data and does not require the older per-request RDT workflow. Other restricted operations can still require RDT. Verify the specific operation reference.

- [Tokens API guide](https://developer-docs.amazon.com/sp-api/docs/tokens-api-use-case-guide)
- [Access PII for order items](https://developer-docs.amazon.com/sp-api/docs/get-authorization-to-access-pii-for-order-items)
- [Orders v0 to v2026 migration](https://developer-docs.amazon.com/sp-api/docs/orders-api-migration-guide)

## Credential Storage and Rotation

- Put client secrets and refresh tokens in a secrets manager, not source code or `.env` committed to Git.
- Separate sandbox and production secrets and seller authorizations.
- Bind each refresh token to application ID, seller identity, authorization date, and environment.
- Restrict token-decrypt permission to the service that exchanges it.
- Rotate LWA client secrets before expiration and support a controlled overlap window.
- Revoke and replace credentials immediately after suspected exposure.
- Redact authorization headers and form bodies in HTTP logging.

See [View application credentials](https://developer-docs.amazon.com/sp-api/docs/viewing-your-application-information-and-credentials) and [Application Management API](https://developer-docs.amazon.com/sp-api/docs/application-management-api-v2023-11-30-use-case-guide).

## Script Environment Variables

| Variable | Required for | Meaning |
|---|---|---|
| `SP_API_LWA_CLIENT_ID` | All token exchanges | LWA application client ID |
| `SP_API_LWA_CLIENT_SECRET` | All token exchanges | LWA client secret |
| `SP_API_REFRESH_TOKEN` | Seller-authorized token exchange | Private self-authorization or public seller refresh token |
| `SP_API_AUTHORIZATION_CODE` | Public OAuth initial exchange | Short-lived code received after seller authorization |
| `SP_API_ACCESS_TOKEN` | Optional direct calls | Externally managed LWA token or RDT |
| `SP_API_USER_AGENT` | Optional | Identifying application user agent |

The helper prints token metadata by default and reveals the token only with `--show-token`. Prefer piping JSON internally over printing secrets in terminals or CI logs.
