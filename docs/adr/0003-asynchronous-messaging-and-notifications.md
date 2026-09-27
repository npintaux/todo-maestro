# [ADR-0003] Asynchronous Messaging and Notification Ingestion on Google Cloud Pub/Sub

* **Status**: accepted
* **Deciders**: Lead Architect, SecOps, Tech Lead
* **Date**: 2026-09-27
* **Superseded by**: N/A
* **Approved-by**: npintaux

## Context and Problem Statement

TaskFlow requires decoupling real-time user-facing task operations from secondary downstream workloads, specifically: dispatching email/inbox notifications for handoffs and deadlines (FR-10), streaming tamper-evident audit records to immutable cold storage (FR-7, NFR-COST-3), and evaluating approaching deadlines. Direct synchronous invocation of email gateways or audit streamers during task writes adds latency and introduces cascading failure risks.

## Decision Drivers

* **FR-10**: Asynchronous notification dispatch when tasks are shared/redirected or deadlines approach.
* **NFR-PERF-2**: Task write operations must maintain p95 latency < 500 ms without waiting for external email or audit export sinks.
* **NFR-REL-5**: Graceful degradation: notification worker slowdowns must never block core task CRUD.
* **Adversarial Mitigation (SIM-001)**: Prevent over-engineering by restricting Pub/Sub strictly to asynchronous out-of-band notification events and audit streaming, ensuring core task CRUD remains purely transactional in Cloud SQL.

## Considered Options

* **Option 1: Google Cloud Pub/Sub** - Fully managed, serverless, at-least-once distributed messaging service with push subscriptions to Cloud Run workers.
* **Option 2: Redis Pub/Sub / Celery via Google Cloud Memorystore** - In-memory broker requiring dedicated VM/instance provisioning and cluster management.
* **Option 3: Synchronous Direct In-Process Dispatch** - In-process execution of notifications within the Flask HTTP request cycle.

## Decision Outcome

Chosen option: **Option 1: Google Cloud Pub/Sub**, because it offers serverless auto-scaling with zero maintenance overhead, at-least-once delivery guarantees with exponential backoff and dead-letter queues, and native push integration with Cloud Run endpoints. To preserve simplicity (SIM-001), core task CRUD transactions commit synchronously in Cloud SQL, and only non-blocking side effects are published to Pub/Sub topics.

### Positive Consequences

* Decouples user-facing HTTP request-response latency from third-party notification delivery services.
* Built-in dead-letter queues (DLQ) allow inspecting and replaying failed notification deliveries.
* Scale-to-zero pricing model aligns with NFR-COST-1 (no dedicated cluster idle fees).
* Pub/Sub at-least-once semantics combined with idempotent notification handlers guarantee delivery resilience.

### Negative Consequences / Trade-offs

* Consumers must implement idempotent deduplication to handle potential duplicate event deliveries.
* Event payload ordering is not strictly guaranteed without explicit message ordering keys.

## Pros and Cons of the Options

### Option 1: Google Cloud Pub/Sub

* Good, because zero-maintenance serverless architecture scales automatically with volume spikes.
* Good, because push subscriptions trigger Cloud Run endpoints directly with IAM authentication.
* Good, because dead-letter topics isolate poison pill messages without service disruption.
* Bad, because at-least-once delivery requires consumer idempotency keys.

### Option 2: Redis Pub/Sub / Celery via Google Cloud Memorystore

* Good, because sub-millisecond in-memory dispatch latency.
* Bad, because requires provisioning a continuous Memorystore instance, incurring fixed idle monthly costs.
* Bad, because default Redis Pub/Sub lacks persistent message durable storage across server restarts.

### Option 3: Synchronous Direct In-Process Dispatch

* Good, because extremely simple implementation with no external queue dependencies.
* Bad, because external email gateway outages directly fail user task creation or updates, violating NFR-REL-5.
* Bad, because network latency to email providers degrades write response times, violating NFR-PERF-2.

## Links & References

* Official GCP Documentation: https://cloud.google.com/architecture/framework/system-design
* Google Cloud Pub/Sub Architecture: https://cloud.google.com/pubsub/docs/overview
* Related PRD Requirements: FR-7, FR-10, NFR-PERF-2, NFR-REL-5, NFR-COST-1
