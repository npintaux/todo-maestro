# Specification: Audit & Compliance Subsystem (`audit_service`)

> **Status**: `FROZEN / SUBSYSTEM BLUEPRINT (Gate 2)`  
> **Source**: Subsystem Tech Lead (`/lead-decompose`)  
> **Contractual Inputs**: [`docs/PRD.md`](file:///home/user/todo-maestro/docs/PRD.md), [`docs/architecture.md`](file:///home/user/todo-maestro/docs/architecture.md), [`openapi.yaml`](file:///home/user/todo-maestro/src/modules/audit_service/openapi.yaml)  
> **Selected Domain Pattern**: `repository-service`

---

## 1. Subsystem Overview & Responsibilities

The `audit_service` subsystem provides tamper-evident, append-only audit event persistence, query, and export capabilities satisfying enterprise compliance obligations (FR-7, NFR-SEC-4, NFR-SEC-6).

* **Served PRD Stories**: `US-5` (Auditor investigates), `US-6` (Audit verification of restored tasks), `US-7` (Audit trail for user offboarding).
* **Pattern**: `repository-service` separating domain models and query logic from physical persistence mechanisms.
* **Domain Layout**:
  - `src/modules/audit_service/domain/models.py` (AuditEvent, AuditQuery, AuditExport entities)
  - `src/modules/audit_service/domain/repository.py` (AuditRepository interface)
  - `src/modules/audit_service/domain/service.py` (AuditService business coordinator)
  - `src/modules/audit_service/adapters/memory_repository.py` (In-memory repository for unit testing)
  - `src/modules/audit_service/entrypoints/routes.py` (Flask REST blueprint conforming to openapi.yaml)

---

## 2. Domain Rules & Invariants

* **R1 (Append-Only Invariant)**: Audit records cannot be modified or deleted through any service API or SQL endpoint. Any attempt to update or delete returns an error.
* **R2 (Actor & Timestamp Integrity)**: Every audit record must capture `actor_id`, `action`, `target_type`, `target_id`, and a UTC ISO-8601 timestamp generated at ingestion time.
* **R3 (Auditor Scoping)**: Querying audit logs (`GET /v1/audit/events`) and exporting trails (`POST /v1/audit/export`) require the `auditor` role; requests without this role are rejected with 403 Forbidden.
* **R4 (Export Integrity)**: Export batches must include an `export_id`, generation timestamp, total count, and the exact sequence of matching records.

---

## 3. Architecture & Pattern Conformance

The subsystem implements the `repository-service` architecture:
* `src/modules/audit_service/domain/repository.py`: Defines the abstract data access contract for storing and querying immutable audit events.
* `src/modules/audit_service/domain/service.py`: Enforces authorization rules, validates event payloads, coordinates search filtering, and generates audit exports.
