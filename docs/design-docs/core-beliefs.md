# Core Beliefs

## Agent Legibility

- Repository-local docs are more valuable than chat context.
- Short indexes and explicit contracts are preferable to long, blended guidance.
- If a design decision matters to implementation, it must be written down where an agent can find it.

## Engineering Biases

- Prefer deterministic, testable simulation behavior over convenience shortcuts.
- Prefer explicit domain terms from Magic rules over generic game-engine abstractions when they conflict.
- Prefer simple, inspectable Python modules over opaque frameworks.
- Prefer demo and example scripts that read as straight-line walkthroughs; avoid `__future__` imports, runtime dependency guards, and `__main__` wrappers unless a script genuinely needs them.
- Delay interface polish until core game semantics and contracts are stable.

## Documentation Discipline

- Plans are first-class artifacts.
- Contracts should state what is guaranteed and what is intentionally undefined.
- Open questions should be tracked explicitly instead of buried in prose.
