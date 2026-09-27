# [ADR-0002] Relational and Audit Datastore on Google Cloud SQL for PostgreSQL

* **Status**: accepted
* **Deciders**: Lead Architect, SecOps, Tech Lead
* **Date**: 2026-09-27
* **Superseded by**: N/A
* **Approved-by**: npintaux

## Context and Problem Statement

TaskFlow requires a transactional storage engine for user profiles, tasks, assignments, state transitions, task history entries, and tamper-evident audit logs. The system must support strict ACID guarantees for task reassignments, multi-user authorization checks, soft-delete restorations, and fast filtered searches. Committed writes must never be lost (NFR-REL-3), and the database must survive zone failures with RPO <= 15m and RTO <= 1h (NFR-REL-4).

## Decision Drivers

* **FR-1, FR-4, FR-6**: Strong transactional consistency for task CRUD, ownership transfers, and append-only ordered history records.
* **NFR-REL-1 & NFR-REL-3**: 99% availability target and zero lost committed writes across zone disruptions.
* **NFR-REL-4**: RPO <= 15 minutes, RTO <= 1 hour for regional/zonal disruptions with point-in-time recovery (PITR).
* **NFR-COST-1 & NFR-COST-3**: Cost proportionality avoiding multi-thousand dollar distributed database baselines at launch.
* **Adversarial Mitigation (RES-002 & COS-001)**: Mitigate single-zone failure risk by requiring Cloud SQL Regional High Availability (HA) across multiple zones, while avoiding premature multi-region active-active datastores (Cloud Spanner) that introduce high idle costs and inter-region egress fees.

## Considered Options

* **Option 1: Google Cloud SQL for PostgreSQL (Regional HA)** - Fully managed relational database with automated multi-zone replication, automated failover, point-in-time recovery, and JSONB support.
* **Option 2: Google Cloud Spanner** - Globally distributed, horizontally scalable multi-region relational database with external consistency.
* **Option 3: Google Cloud Firestore** - Serverless NoSQL document database with multi-region replication.

## Decision Outcome

Chosen option: **Option 1: Google Cloud SQL for PostgreSQL (Regional HA)**, because PostgreSQL provides native ACID transactions essential for task ownership transfers and status workflows, structured query performance for user and team task filtering, and JSONB capabilities for schema-flexible history and audit payloads. Regional HA synchronously replicates data across two zones in the primary region, providing automatic sub-minute failover meeting RTO <= 1 hour and RPO = 0 for zone outages, at a fraction of Cloud Spanner's launch cost.

### Positive Consequences

* Full ACID transactional integrity prevents race conditions during concurrent task reassignments.
* Native JSONB column support allows storing before/after field changes in task history entries without schema migrations.
* Automated daily backups, 7-day transaction log retention, and point-in-time recovery (PITR) satisfying NFR-REL-4.
* Integration with Cloud SQL Auth Proxy enforces IAM-based database authentication and TLS 1.3 encryption in transit.

### Negative Consequences / Trade-offs

* Vertical scaling model requires scheduled maintenance for compute tier upgrades (though read replicas can handle query scaling).
* Storage capacity auto-increases monotonically and requires manual intervention for down-sizing.

## Pros and Cons of the Options

### Option 1: Google Cloud SQL for PostgreSQL (Regional HA)

* Good, because regional HA provides automatic zero-data-loss failover between zones.
* Good, because rich indexing (B-tree, GIN for JSONB and search) delivers p95 read latency < 300 ms.
* Good, because cost-efficient for 1,000 to 50,000 active users with smooth scale-up paths.
* Bad, because cross-region disaster recovery requires asynchronous read replica promotion.

### Option 2: Google Cloud Spanner

* Good, because true multi-region active-active synchronous replication worldwide.
* Bad, because minimum node provisioning cost exceeds launch budget by 10x, violating NFR-COST-1.
* Bad, because introduces unnecessary distributed system complexity for initial 1,000 concurrent user scale.

### Option 3: Google Cloud Firestore

* Good, because serverless auto-scaling and built-in multi-region replication.
* Bad, because lacks multi-table ACID transactional semantics and complex relational joins required for team filtering and audit aggregation.
* Bad, because query filtering capabilities are more restrictive than relational SQL.

## Links & References

* Official GCP Documentation: https://cloud.google.com/architecture/framework/reliability
* Cloud SQL High Availability Configuration: https://cloud.google.com/sql/docs/postgres/high-availability
* Related PRD Requirements: FR-1, FR-6, FR-7, NFR-REL-1, NFR-REL-3, NFR-REL-4, NFR-COST-1
