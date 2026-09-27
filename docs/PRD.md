# PRD — TaskFlow: an enterprise "follow-the-sun" task service

| | |
|---|---|
| **Product** | TaskFlow |
| **Document status** | Frozen — input to the architecture phase |
| **Owner** | Platform Productivity team |
| **Version** | 1.0 |
| **Audience** | Architecture & engineering (this is the requirements input to `architecture-decompose`) |

---

## 1. Overview

TaskFlow is an **internal, multi-user task-management service** for a large,
globally distributed company. Employees create and track their own work items and
hand work to colleagues across time zones as the working day moves around the
globe ("follow the sun"). Every task carries a full history, and every user
interaction is written to an immutable audit log for compliance and
troubleshooting.

TaskFlow is delivered as an **HTTP/JSON API with a thin server-rendered web UI**,
built as a **Flask** application (see §7). This document is the frozen requirements
input; it deliberately describes *what* the system must do and *how well*, not the
implementation.

## 2. Goals & non-goals

### Goals
- Give every employee one reliable place to capture, organise, and complete tasks.
- Make cross-timezone handoff of work a first-class action (share / reassign).
- Provide a trustworthy record: per-task history and a tamper-evident audit log.
- Operate 24/7 at global scale within a defined cost envelope.

### Non-goals (v1)
- Real-time collaborative editing (live cursors / instant multi-device sync).
- Native mobile applications (responsive web is sufficient).
- Project-management features beyond tasks: Gantt charts, sprints, time tracking.
- Third-party integrations (calendar, chat) — designed-for later, not built in v1.

## 3. Personas & users

- **Employee (primary user)** — creates and manages their own tasks; sends/shares
  tasks to colleagues; consumes tasks handed to them.
- **Team lead** — everything an employee can do, plus views tasks shared within
  their team and reassigns work during handoffs.
- **Auditor / compliance officer** — read-only access to audit logs and task
  history across the organisation; cannot modify tasks.
- **System administrator** — manages user lifecycle (provision/deactivate),
  monitors health, and operates the service. Does not read task *content* by
  default.

## 4. User journeys

> At least five end-to-end journeys the system must support.

### UJ-1 — Capture a task
A signed-in employee opens TaskFlow, creates a task with a title, optional notes,
optional due date, and priority, and sees it appear immediately in their "My
tasks" list. *(Covers FR-1, FR-3.)*

### UJ-2 — Work and complete a task
An employee edits a task's details, changes its status through
`open → in-progress → done`, and later reopens it if needed. Each change is
recorded in the task's history with who/when/what. *(Covers FR-1, FR-5, FR-6.)*

### UJ-3 — Follow-the-sun handoff (share / redirect)
At the end of their day, an APAC employee **redirects** an unfinished task to a
colleague in EMEA. The colleague receives the task in their inbox with the full
history attached, becomes the new owner (or a collaborator, depending on the
handoff type), and the original owner retains visibility. *(Covers FR-2, FR-4,
FR-6, FR-7.)*

### UJ-4 — Team lead rebalances work
A team lead views all tasks shared within their team, filters by status and
assignee, and reassigns overdue tasks from an overloaded colleague to another.
Every reassignment is captured in history and the audit log. *(Covers FR-4, FR-5,
FR-6, FR-7.)*

### UJ-5 — Auditor investigates
An auditor opens the audit console, searches interactions by user, task, or time
window, and reconstructs exactly who did what to a given task and when — including
shares, reassignments, edits, and deletions. They can export the trail. *(Covers
FR-6, FR-7, FR-8.)*

### UJ-6 — Recover a deleted task
An employee deletes a task by mistake and, within the retention window, restores
it (soft delete). The deletion and restoration both appear in history and the
audit log. *(Covers FR-1, FR-6, FR-7.)*

### UJ-7 — Administrator offboards a user
An administrator deactivates a departing employee. The user can no longer sign in;
their still-open tasks are surfaced for reassignment so no work is orphaned, and
the offboarding is audited. *(Covers FR-2, FR-4, FR-7, FR-9.)*

## 5. Functional requirements

- **FR-1 Task CRUD.** A signed-in user can **create, view, modify, and delete**
  tasks. A task has: title, optional notes, optional due date, priority, status
  (`open`, `in-progress`, `done`), owner, and timestamps. Deletion is a **soft
  delete** with a retention window before permanent removal.
- **FR-2 Multi-user accounts.** Users authenticate; every request is attributed to
  a user identity. The system supports the full organisation's user base (see
  NFR scale targets).
- **FR-3 List & filter.** A user can list tasks they own or that are shared with
  them, and filter/sort by status, due date, priority, and assignee.
- **FR-4 Share & redirect.** A user can **share** a task with another user (grant
  view or edit access) and **redirect/reassign** a task (transfer ownership). Both
  the original and new parties retain appropriate visibility per the handoff type.
  Handoffs work across teams and time zones.
- **FR-5 Authorization.** A user may only read or modify tasks they own or have
  been granted access to; edit/reassign requires the corresponding permission.
  Auditors are read-only; administrators manage users, not task content.
- **FR-6 Task history.** Every task keeps an ordered, immutable **history** of its
  changes (field edits, status transitions, shares, reassignments, delete/restore)
  with actor, timestamp, and before/after values.
- **FR-7 Audit log.** Every security- or data-relevant **user interaction**
  (sign-in, task CRUD, share, reassign, permission change, export, admin action)
  is written to a **tamper-evident, append-only audit log**, queryable by user,
  task, action type, and time range, with export.
- **FR-8 Search.** Users can search their accessible tasks by text; auditors can
  search the audit log across the organisation.
- **FR-9 User lifecycle.** Administrators can provision and deactivate users;
  deactivating a user blocks sign-in and surfaces their open tasks for
  reassignment.
- **FR-10 Notifications.** When a task is shared/redirected to a user, or a task
  with a due date is within 24 hours of its deadline, the relevant users are
  notified (email is acceptable for v1; the design must not preclude other
  channels).

## 6. Non-functional requirements (Google Cloud Well-Architected Framework)

NFRs are organised by the pillars of the **Google Cloud Well-Architected
Framework**. The architecture must reason about the system through each pillar.

### 6.0 Scale & shape targets (drive every pillar below)
- **Follow-the-sun, 24/7.** The service is used around the clock across global time
  zones; there is no natural low-traffic maintenance window that is quiet
  everywhere.
- **NFR-SCALE-1 Concurrency.** Support **1,000 concurrent active users** at launch
  without degradation.
- **NFR-SCALE-2 Growth.** Architect to grow to **200,000 registered users** (the
  entire employee base) without a re-architecture; the launch design need not
  provision for peak 200k concurrency but must not structurally preclude it.
- **NFR-SCALE-3 Data growth.** Task history and audit logs grow monotonically and
  must remain queryable as they reach tens of millions of records.

### 6.1 Reliability
- **NFR-REL-1 Availability.** **99% monthly availability** target for the API
  (≈ 7h 18m error budget per 30-day month), measured on successful responses to
  authenticated requests.
- **NFR-REL-2 24/7 operation.** No full-service maintenance downtime; changes are
  rolled out without taking the service offline for all regions at once.
- **NFR-REL-3 Durability.** No **committed** task change, history entry, or audit
  record may be lost; data survives the failure of a single node/zone.
- **NFR-REL-4 Recovery.** RPO ≤ 15 minutes, RTO ≤ 1 hour for a regional
  disruption. Backups are tested/restorable.
- **NFR-REL-5 Graceful degradation.** Non-critical features (e.g. notifications)
  may degrade without taking down core task CRUD.

### 6.2 Security, privacy & compliance
- **NFR-SEC-1 AuthN.** All access is authenticated; passwords, if used, are stored
  only as salted hashes; support for the company SSO/identity provider is expected.
- **NFR-SEC-2 AuthZ.** Authorization is enforced **server-side** on every request;
  clients are never trusted for access decisions (see FR-5).
- **NFR-SEC-3 In transit & at rest.** All traffic over TLS; task content, history,
  and audit logs encrypted at rest.
- **NFR-SEC-4 Auditability.** The audit log (FR-7) is append-only and tamper-
  evident; no secret material or task content appears in application/system logs.
- **NFR-SEC-5 Privacy.** A user's task content is visible only to that user, users
  they shared with, and auditors/administrators acting in their role; least
  privilege throughout.
- **NFR-SEC-6 Data retention.** History and audit logs are retained for a defined
  compliance period; soft-deleted tasks are purged after their retention window.

### 6.3 Operational excellence
- **NFR-OPS-1 Observability.** The service exposes health/readiness checks,
  structured logs, metrics (latency, error rate, saturation), and traces for key
  flows.
- **NFR-OPS-2 Deployability.** Deploy and roll back without downtime for additive
  changes; schema changes are backward-compatible / expand-contract.
- **NFR-OPS-3 Runbooks.** Common failures (region loss, DB failover, notification
  backlog) have documented, tested operational responses.
- **NFR-OPS-4 Configurability.** Environment-specific configuration and secrets are
  externalised, not baked into artifacts.

### 6.4 Performance & scalability
- **NFR-PERF-1 Read latency.** p95 < 300 ms for read/list operations at the launch
  concurrency target.
- **NFR-PERF-2 Write latency.** p95 < 500 ms for task create/update/share.
- **NFR-PERF-3 Horizontal scale.** The request-serving tier scales horizontally
  (stateless services); no single instance is a scaling ceiling.
- **NFR-PERF-4 Global responsiveness.** Latency is acceptable for users worldwide
  (follow-the-sun); the design accounts for user geography.

### 6.5 Cost optimization
- **NFR-COST-1 Proportionality.** Run within a modest budget appropriate to the
  launch scale; avoid premium managed services the scale does not justify.
- **NFR-COST-2 Elasticity.** Capacity tracks demand (scale down off-peak per
  region) so 24/7 operation does not mean 24/7 peak spend.
- **NFR-COST-3 Storage tiering.** Cold history/audit data can move to cheaper
  storage while remaining queryable within stated latencies.

## 7. Constraints & assumptions

- **C-1 Framework.** The backend **must be implemented using Flask** (Python). The
  web UI is server-rendered from the same application unless the architecture
  justifies otherwise.
- **C-2 Cloud.** Target deployment is Google Cloud; reason about NFRs using the
  Google Cloud Well-Architected Framework (§6).
- **C-3 Identity.** Assume an existing corporate identity provider is available for
  SSO; TaskFlow integrates rather than reinventing identity.
- **A-1 Notifications.** v1 may start with email only; the design must leave room
  for additional channels.
- **A-2 Regions.** "Follow the sun" implies a globally distributed user base;
  whether that requires multi-region active-active vs. a single region with global
  access is an **architecture decision to justify** against the availability, cost,
  and latency NFRs.

## 8. Data model (indicative, not prescriptive)

- **User** — identity, display name, role (employee / lead / auditor / admin),
  status (active / deactivated).
- **Task** — id, title, notes, due date, priority, status, owner, soft-delete
  flag, timestamps.
- **Share/Assignment** — task ↔ user grant with permission (view / edit) and type
  (share vs. ownership transfer).
- **HistoryEntry** — task id, actor, timestamp, action, before/after (immutable).
- **AuditEvent** — actor, timestamp, action, target, context (append-only,
  tamper-evident).

The architecture is free to refine these; they exist to make requirements
concrete.

## 9. Success metrics

- **Adoption:** ≥ 60% of employees active weekly within two quarters of rollout.
- **Reliability:** meet the 99% monthly availability target; stay within error
  budget.
- **Handoff:** median cross-timezone task handoff completes (shared → acknowledged)
  in < 1 business day.
- **Trust:** 100% of data-relevant interactions present and queryable in the audit
  log; zero lost committed writes.

## 10. Out of scope (restated)

Real-time collaborative editing, native mobile apps, PM features beyond tasks, and
third-party integrations are explicitly out of scope for v1 (see §2).
