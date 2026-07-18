# Contract: Agent Workflow And Change Staging

## Purpose

Define the repository-level collaboration and commit discipline for changes that
expand or correct declared rules and card support.

## Collaboration Requirements

- Agents must use subagents for independent, bounded work whenever concurrency
  is available. Suitable work includes separate source/contract audits,
  implementation and test reconnaissance, manifest consistency checks, and
  review of a completed change.
- Delegation must have a concrete deliverable and a clear file or behavior
  boundary. The coordinating agent remains responsible for reconciling results
  and verifying the final integrated change.
- Do not delegate work whose result depends on an in-progress edit from another
  agent unless that dependency is explicitly sequenced. Avoid overlapping edits
  to the same files.
- When no independent bounded work exists, proceed serially rather than
  manufacturing parallel tasks.

## Rule And Card Change Staging

- For card work, follow the active plan's card-expansion freshness check and
  stage the source artifacts, manifests, contracts, engine behavior, and tests
  that describe one coherent support increment together.
- For rule work, stage the affected rule contract, coverage declaration,
  implementation, and regression or trace tests together.
- After a coherent rule or card stage has been verified, agents may commit it
  without asking for an additional commit confirmation. This standing authority
  does not override an explicit user instruction to avoid commits, to combine
  stages, or to use a particular branch or review workflow.
- Before an autonomous commit, inspect the worktree, verify the stage with the
  relevant targeted tests plus any proportionate broader checks, and ensure the
  commit contains no unrelated user changes.
- Keep each autonomous commit focused, imperative in its message, and readily
  reversible. Do not wait to bundle several verified rule or card increments
  into one commit merely to reduce commit count.

## Boundaries

- This contract grants commit authority only for repository-local, verified
  rule and card work. It does not authorize pushes, pull requests, deployment,
  external writes, destructive operations, or changes outside the requested
  scope.
- The active execution plan and the relevant domain contracts remain the source
  of truth for what a coherent stage must contain.

## Goal Continuity And Blocked Status

- An unfinished implementation plan is active work, not a blocker. Agents must
  continue with the next safe, bounded stage rather than ending a task merely
  because additional implementation, tests, or verification remain.
- A repeated task-continuation prompt, a partial-progress handoff, or a need
  for more time is never evidence that a goal is blocked.
- Before reporting or recording a goal as blocked, an agent must identify a
  concrete external dependency that prevents *all* meaningful progress (for
  example: unavailable required credentials, missing user-owned source data,
  or a required product decision with materially different outcomes).
- When a real blocker exists, the handoff must name the exact dependency, the
  safe checks already attempted, and the smallest decision or state change
  needed to resume. Do not classify uncertainty, incomplete test coverage, or
  a large remaining backlog as a blocker.
- Partial updates belong in progress commentary. A final handoff is reserved
  for a completed objective, a genuine external blocker, or an explicit user
  request for status; it must not replace the next planned implementation
  stage.
