# [ADR-0001] Serverless Compute Platform on Google Cloud Run

* **Status**: accepted
* **Deciders**: Lead Architect, SecOps, Tech Lead
* **Date**: 2026-09-27
* **Superseded by**: N/A
* **Approved-by**: npintaux

## Context and Problem Statement

TaskFlow is an enterprise follow-the-sun task management service operating 24/7 across global time zones. The system must support 1,000 concurrent active users at launch with growth potential to 200,000 registered users, while meeting 99% availability SLO and keeping infrastructure costs modest and proportional to load. We need a modern, scalable compute platform to run the Flask backend and server-rendered web UI without heavy cluster management overhead.

## Decision Drivers

* **PRD Constraint C-1**: Backend must be implemented using Flask (Python) with server-rendered UI.
* **NFR-SCALE-1 & NFR-PERF-3**: Horizontal auto-scaling to handle 1,000 concurrent users without fixed capacity ceilings.
* **NFR-COST-1 & NFR-COST-2**: Elastic scale-to-zero capability to avoid 24/7 peak compute billing during off-peak hours.
* **NFR-OPS-1 & NFR-OPS-2**: Seamless blue/green and canary traffic splitting, zero-downtime rollouts, and built-in Cloud Logging and Cloud Monitoring integration.
* **Adversarial Mitigation (RES-001 & COS-002 & SIM-002)**: Prevent cold start latency spikes via minimum warm instances (min-instances=1), use request-based CPU allocation to control idle costs, and consolidate cohesive subsystems (`task_service` and `audit_service`) rather than microservice fragmentation.

## Considered Options

* **Option 1: Google Cloud Run** - Fully managed serverless container runtime with request-based auto-scaling and integrated revision management.
* **Option 2: Google Kubernetes Engine (GKE)** - Managed container orchestration platform offering fine-grained cluster control.
* **Option 3: Google Compute Engine (GCE) Managed Instance Groups (MIG)** - Virtual machine instances behind a load balancer with auto-scaler.

## Decision Outcome

Chosen option: **Option 1: Google Cloud Run**, because it natively packages our standard Flask container images, scales automatically from warm minimum instances up to hundreds of concurrent containers, eliminates cluster management toil, and integrates directly with Google Cloud IAM, Cloud Load Balancing, and Cloud Logging.

### Positive Consequences

* Rapid deployment cycles and automated traffic splitting across revisions.
* Native integration with Secret Manager and VPC Serverless Access.
* Modest cost envelope adhering to NFR-COST-1 through pay-per-request pricing and concurrency tuning (up to 80 requests per container).
* Elimination of Kubernetes node provisioning and OS patch management overhead.

### Negative Consequences / Trade-offs

* Container cold starts if scaling from zero, mitigated by keeping `min-instances=1` in primary active regions.
* Stateless execution model requires all persistent state and session data to reside in managed datastores.

## Pros and Cons of the Options

### Option 1: Google Cloud Run

* Good, because container-native packaging allows local Docker testing identical to production.
* Good, because request-based auto-scaling easily accommodates 1,000+ concurrent users.
* Good, because built-in revision management supports zero-downtime rolling deploys.
* Bad, because maximum request timeout is 60 minutes (acceptable for HTTP web services).

### Option 2: Google Kubernetes Engine (GKE)

* Good, because provides unlimited control over daemonsets, service meshes, and custom networking.
* Bad, because introduces significant control plane and node pool management overhead disproportionate to launch scale.
* Bad, because persistent cluster overhead violates NFR-COST-1 proportionality targets.

### Option 3: Google Compute Engine (GCE) Managed Instance Groups (MIG)

* Good, because mature VM-based infrastructure with customized kernels.
* Bad, because slower auto-scaling scale-out times (minutes vs. seconds for containers).
* Bad, because operational overhead for OS patching and configuration drift management.

## Links & References

* Official GCP Documentation: https://cloud.google.com/architecture/framework/system-design
* Official Cloud Run Overview: https://cloud.google.com/run/docs/overview
* Related PRD Requirements: C-1, NFR-SCALE-1, NFR-PERF-3, NFR-COST-1, NFR-COST-2
