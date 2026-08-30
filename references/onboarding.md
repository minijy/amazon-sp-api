# SP-API Developer and Application Onboarding

Use this reference when opening developer access, registering an app, selecting roles, or implementing seller authorization. Amazon now manages SP-API applications through the Solution Provider Portal.

## Choose the Application Type First

| Type | Intended users | Authorization | Publication |
|---|---|---|---|
| Private seller application | One seller organization | Self-authorization | No Appstore listing |
| Public seller application | Multiple independent sellers | Login with Amazon OAuth 2.0 | Amazon approval and Selling Partner Appstore listing |
| Private vendor application | One vendor organization | Self-authorization | No Appstore listing |

Private seller development requires a Professional selling account. The primary account user must complete registration. Do not register a public application merely to work around private-app authorization limits.

Official starting points:

- [Onboarding as a Developer](https://developer-docs.amazon.com/sp-api/docs/onboarding-overview)
- [SP-API Registration Overview](https://developer-docs.amazon.com/sp-api/docs/sp-api-registration-overview)
- [Solution Provider Portal](https://solutionproviderportal.amazon.com/)
- [SP-API policies and agreements](https://developer-docs.amazon.com/sp-api/docs/policies-and-agreements)
- [Selling Partner API roles](https://developer-docs.amazon.com/sp-api/docs/roles-in-the-selling-partner-api)

## End-to-End Opening Process

### 1. Prepare the application and security description

Document the real use case, seller population, data domains, data flows, retention, encryption, incident response, access control, and deletion process. Select only roles required by implemented operations. Restricted roles require stronger review because they expose PII.

Review Amazon's policies before answering the profile questionnaire. Provide original, accurate answers; do not paste generic policy language.

### 2. Create or use the Solution Provider Portal account

Sign in with the primary seller/developer account. For private seller applications, the seller account must be on a Professional plan.

Official reference: [Create a Solution Provider Portal account](https://developer-docs.amazon.com/sp-api/docs/onboarding-step-2-create-an-spp-account)

### 3. Complete the Developer Profile

Provide organization/contact details, data-access needs, roles, use cases, and security controls. Amazon can open a case requesting more information; monitor the administrator email and the portal.

- [Register as a private developer](https://developer-docs.amazon.com/sp-api/docs/register-as-a-private-developer)
- [Register as a public developer](https://developer-docs.amazon.com/sp-api/docs/register-as-a-public-developer)
- [Check developer registration status](https://developer-docs.amazon.com/sp-api/docs/checking-the-status-of-your-request-to-register-as-a-developer)
- [Selling Partner API roles and restricted-role requirements](https://developer-docs.amazon.com/sp-api/docs/roles-in-the-selling-partner-api)

### 4. Register a sandbox application

In Solution Provider Portal, choose **Develop Apps**, then **Add new app client**. Enter the application name/type, OAuth URLs for public applications, and the roles mapped from the planned operations.

- [Register your application](https://developer-docs.amazon.com/sp-api/docs/registering-your-application)
- [Register a sandbox application](https://developer-docs.amazon.com/sp-api/docs/onboarding-step-4-register-your-first-sandbox-application)

### 5. Obtain sandbox credentials and make the first call

From the application row, view sandbox LWA credentials and create a sandbox refresh token. Exchange it at the LWA token endpoint, then call a documented static or dynamic sandbox route.

- [Make your first SP-API sandbox call](https://developer-docs.amazon.com/sp-api/docs/onboarding-step-5-make-your-first-call-to-the-sp-api-sandbox)
- [SP-API sandbox](https://developer-docs.amazon.com/sp-api/docs/the-selling-partner-api-sandbox)
- [Using Postman for SP-API models](https://developer-docs.amazon.com/sp-api/docs/using-postman-for-selling-partner-api-models)

### 6. Implement authorization

For a private application, self-authorize it in the portal and securely store the resulting refresh token. For a public application, implement the OAuth authorization workflow with state validation, exact registered redirect URIs, authorization-code exchange, tenant binding, and secure refresh-token storage.

- [Authorize SP-API applications](https://developer-docs.amazon.com/sp-api/docs/authorizing-selling-partner-api-applications)
- [Website authorization workflow](https://developer-docs.amazon.com/sp-api/docs/website-authorization-workflow)
- [Appstore authorization workflow](https://developer-docs.amazon.com/sp-api/docs/selling-partner-appstore-authorization-workflow)

Public application refresh tokens must be tracked per selling partner authorization. Amazon's onboarding documentation states that public-app refresh tokens must be renewed annually; implement authorization-expiry reminders and reauthorization handling.

### 7. Register the production application

Promote/register the production application only after the authorization callback, token storage, direct API calls, throttling, audit logs, and data controls have been tested. Reconfirm production roles; adding roles later can require reauthorization.

- [Register your first production application](https://developer-docs.amazon.com/sp-api/docs/onboarding-step-7-register-your-first-production-application)
- [View application information and LWA credentials](https://developer-docs.amazon.com/sp-api/docs/viewing-your-application-information-and-credentials)

### 8. Test, publish, and operate

Public applications require Appstore listing approval. Private applications do not. Both need production monitoring, credential rotation, deauthorization handling, rate-limit management, and policy-compliant retention/deletion.

- [Publish an SP-API application](https://developer-docs.amazon.com/sp-api/docs/publish-an-sp-api-application)
- [Development tools](https://developer-docs.amazon.com/sp-api/docs/development-tools)
- [SP-API release notes](https://developer-docs.amazon.com/sp-api/docs/sp-api-release-notes)
- [SP-API deprecation schedule](https://developer-docs.amazon.com/sp-api/docs/sp-api-deprecation-schedule)

## Role Selection Worksheet

Map every requested operation to its official reference and role before submitting the profile. Typical seller-data roles include:

| Data domain | Common role |
|---|---|
| Listings and catalog contribution | Product Listing |
| Offer and competitive pricing | Pricing |
| Orders and inventory tracking | Inventory and Order Tracking |
| FBA inventory/inbound operations | Amazon Fulfillment |
| Financial transactions | Finance and Accounting |
| Review/return insights | Brand Analytics or Selling Partner Insights, where supported |

Role names and mappings can change. The operation reference is authoritative. Avoid requesting restricted roles until the application has a defined PII-dependent workflow and compliant controls.

## Registration Evidence to Retain

- Developer profile and submitted use-case version.
- Application ID, application type, roles, redirect URIs, and authorized marketplaces.
- Approval/case history and policy acknowledgements.
- Credential creation and rotation timestamps, never secret values in ordinary logs.
- Seller authorization identity, grant date, scope/roles, refresh-token vault reference, and revocation date.
