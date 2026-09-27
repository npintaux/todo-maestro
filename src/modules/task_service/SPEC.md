# Specification: Task Management Subsystem (`task_service`)

> **Status**: `FROZEN / SUBSYSTEM BLUEPRINT (Gate 2)`  
> **Source**: Subsystem Tech Lead (`/lead-decompose`)  
> **Contractual Inputs**: [`docs/PRD.md`](file:///home/user/todo-maestro/docs/PRD.md), [`docs/architecture.md`](file:///home/user/todo-maestro/docs/architecture.md), [`openapi.yaml`](file:///home/user/todo-maestro/src/modules/task_service/openapi.yaml)  
> **Selected Domain Pattern**: `state-machine`

---

## 1. Subsystem Overview & Responsibilities

The `task_service` subsystem encapsulates core task CRUD, lifecycle status workflows, follow-the-sun handoffs, permission sharing, task reassignment, soft-deletion/restoration, user account administration, and in-app notifications.

* **Served PRD Stories**: `US-1` (Capture a task), `US-2` (Work and complete a task), `US-3` (Follow-the-sun handoff), `US-4` (Team lead rebalances work), `US-6` (Recover a deleted task), `US-7` (Administrator offboards a user), `US-8` (Task deadline and handoff notifications).
* **Pattern**: `state-machine` governing formal status progression (`open → in-progress → done`), task soft-deletion/restoration, and event publication.
* **Domain Layout**:
  - `src/modules/task_service/domain/models.py` (Task, TaskShare, TaskHistory, Notification, User entities)
  - `src/modules/task_service/domain/state_machine.py` (TaskStateMachine defining valid transitions and guards)
  - `src/modules/task_service/domain/events.py` (Domain event definitions: TaskCreated, TaskTransitioned, TaskShared, TaskReassigned)
  - `src/modules/task_service/adapters/memory_task_repo.py` (In-memory repository for unit testing)
  - `src/modules/task_service/entrypoints/routes.py` (Flask REST API routes matching openapi.yaml)
  - `src/modules/task_service/frontend/` (Flask server-rendered Jinja templates and token-only CSS conforming to ui-spec.json)

---

## 2. Domain Rules & Invariants

* **R1 (Task Lifecycle FSM)**: Tasks transition deterministically:
  - `open` -> `in_progress` (on work started)
  - `in_progress` -> `done` (on work completed)
  - `done` -> `open` (on reopen)
  - Any direct transition `open` -> `done` without starting work is prohibited.
* **R2 (Soft-Delete & 30-Day Retention)**: Deleted tasks have `is_deleted = True`. They remain recoverable via `/v1/tasks/{id}/restore` within 30 days. After 30 days, or if already deleted, deletion behavior enforces strict boundary retention.
* **R3 (Owner & Share Authorization)**: Only the task owner or users granted `edit` permission can modify task details or status. Only the owner can share the task or transfer ownership. Non-owners and non-collaborators receive 403 Forbidden.
* **R4 (Follow-the-Sun Handoff)**: Transferring ownership or adding shares triggers an asynchronous notification to the target user and an append-only task history entry recording the actor, recipient, and UTC timestamp.
* **R5 (Team Lead Reassignment)**: Users with the `lead` role can reassign tasks belonging to team members, recording before/after owner values in task history.
* **R6 (Administrator Offboarding & Orphan Preservation)**: Deactivating a user account (`/v1/users/{id}/status`) immediately blocks sign-in. Any active (`open` or `in_progress`) tasks owned by the deactivated user are surfaced via `/v1/tasks/orphaned` and can be reassigned by Admins or Team Leads.

---

## 3. Architecture & Pattern Conformance

The subsystem implements the `state-machine` pattern:
* `src/modules/task_service/domain/state_machine.py`: Encapsulates valid transitions, guards (ensuring user permissions and non-deleted state), and side-effects (generating history entries and notification events).
