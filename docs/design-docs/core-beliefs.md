# Core Beliefs

## Agent Legibility

- Repository-local docs are more valuable than chat context.
- Short indexes and explicit contracts are preferable to long, blended guidance.
- If a design decision matters to implementation, it must be written down where an agent can find it.

## Engineering Biases

- Prefer deterministic, testable simulation behavior over convenience shortcuts.
- Prefer explicit domain terms from Magic rules over generic game-engine abstractions when they conflict.
- Prefer simple, inspectable Python modules over opaque frameworks.
- Delay interface polish until core game semantics and contracts are stable.

## Documentation Discipline

- Plans are first-class artifacts.
- Contracts should state what is guaranteed and what is intentionally undefined.
- Open questions should be tracked explicitly instead of buried in prose.
