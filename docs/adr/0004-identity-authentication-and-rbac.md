# [ADR-0004] Identity Authentication and Server-Side RBAC

* **Status**: accepted
* **Deciders**: Lead Architect, SecOps, Tech Lead
* **Date**: 2026-09-27
* **Superseded by**: N/A
* **Approved-by**: npintaux

## Context and Problem Statement

TaskFlow requires authenticating corporate users worldwide and enforcing strict authorization boundaries across four primary roles: Employee, Team Lead, Auditor, and Administrator. Users must only access tasks they own or have been explicitly granted view/edit rights to (FR-5). Administrators manage user lifecycles (FR-9) but must not view task content, while auditors possess read-only access to tamper-evident audit logs (FR-7). In accordance with Constraint C-3, TaskFlow must integrate with corporate SSO rather than reinventing authentication.

## Decision Drivers

* **PRD Constraint C-3**: Integrate with existing corporate identity provider rather than managing custom credential stores.
* **FR-2 & FR-5**: Multi-user identity attribution on every request with strict server-side authorization enforcement.
* **FR-7 & FR-9**: Role segregation: Employee, Lead, Auditor (read-only audit search), Administrator (user provisioning/deactivation).
* **NFR-SEC-1 & NFR-SEC-2**: Zero Trust authentication with server-side validation; clients are never trusted for access decisions.

## Considered Options

* **Option 1: Google Cloud Identity-Aware Proxy (IAP) with Corporate OIDC SSO and Flask Server-Side RBAC** - Perimeter-level authentication via IAP headers (`X-Goog-Authenticated-User-Email`, `X-Goog-IAP-JWT-Assertion`) combined with standard OAuth2 Bearer tokens and application-level role-based access control.
* **Option 2: Standalone Custom Password Store with PBKDF2/bcrypt** - Internal user authentication table storing hashed passwords within TaskFlow database.
* **Option 3: External Commercial SaaS Auth (Auth0 / Okta)** - Third-party hosted identity service handling sign-in widgets and token issuance.

## Decision Outcome

Chosen option: **Option 1: Google Cloud Identity-Aware Proxy (IAP) with Corporate OIDC SSO and Flask Server-Side RBAC**, because it satisfies Constraint C-3 by delegating enterprise credentials to Google Cloud / Corporate Identity, verifies cryptographically signed JWT assertions at the application layer, and enforces deterministic RBAC permissions in Flask middleware without trusting client claims.

### Positive Consequences

* Enterprise SSO integration eliminates local credential theft and password reset maintenance overhead.
* Cryptographic signature verification of IAP JWT assertions prevents header spoofing across perimeter boundaries.
* Server-side permission decorators (`@require_permission`, `@require_role`) enforce granular access control on every route.
* Seamless user deactivation (FR-9): revoking access in the identity provider instantly blocks sign-in across all sessions.

### Negative Consequences / Trade-offs

* Local development and unit testing require a mock authentication middleware / test client fixture simulating OIDC headers and Bearer tokens.
* Integration relies on correct perimeter network configuration to ensure Cloud Run accepts requests only through IAP/Load Balancer.

## Pros and Cons of the Options

### Option 1: Google Cloud Identity-Aware Proxy (IAP) with Corporate OIDC SSO and Flask Server-Side RBAC

* Good, because complies with PRD C-3 by leveraging enterprise corporate identity.
* Good, because cryptographically signed JWT headers guarantee user identity without perimeter tampering.
* Good, because centralized session revocation supports immediate offboarding (FR-9).
* Bad, because local testing requires mock token middleware.

### Option 2: Standalone Custom Password Store with PBKDF2/bcrypt

* Good, because completely self-contained for offline development.
* Bad, because directly violates PRD Constraint C-3 ("integrate rather than reinvent identity").
* Bad, because increases attack surface and compliance burden for password hashing, resets, and brute-force protection.

### Option 3: External Commercial SaaS Auth (Auth0 / Okta)

* Good, because rich hosted UI screens and MFA capabilities.
* Bad, because adds external vendor subscription fees and monthly active user charges violating NFR-COST-1.
* Bad, because introduces an external dependency outside the Google Cloud perimeter.

## Links & References

* Official GCP Documentation: https://cloud.google.com/architecture/framework/security
* Cloud Identity-Aware Proxy Overview: https://cloud.google.com/iap/docs/concepts-overview
* Related PRD Requirements: C-3, FR-2, FR-5, FR-7, FR-9, NFR-SEC-1, NFR-SEC-2
