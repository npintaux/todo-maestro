# Traceability Matrix: PRD User Stories to Subsystems

> **Status**: `FROZEN / BINDING MATRIX (Gate 0.5)`  
> **Source**: Lead Cloud Architect (`/architect-design`)  
> **Contractual Inputs**: [`docs/PRD.md`](file:///home/user/todo-maestro/docs/PRD.md), [`docs/architecture.md`](file:///home/user/todo-maestro/docs/architecture.md)

This matrix maps every User Story from `docs/PRD.md` to the implementing subsystem declared in `docs/architecture.md`. Every story must be served by at least one subsystem, and every subsystem must serve at least one story (no orphaned stories, no speculative subsystems).

| Story ID | Subsystem(s) | Description |
|---|---|---|
| US-1 | task_service | Capture a task (CRUD, status, priority, due date) |
| US-2 | task_service | Work and complete a task (lifecycle status machine, task history) |
| US-3 | task_service | Follow-the-sun handoff (share permissions and ownership transfer) |
| US-4 | task_service | Team lead rebalances work (team filtering and task reassignment) |
| US-5 | audit_service | Auditor investigates and exports trail (immutable audit search and export) |
| US-6 | task_service, audit_service | Recover a deleted task (soft-delete, restore, and audit verification) |
| US-7 | task_service, audit_service | Administrator offboards a user (account deactivation, orphan task surfacing, and audit) |
| US-8 | task_service | Task deadline and handoff notifications (alert records and Pub/Sub event dispatch) |
