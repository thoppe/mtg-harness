# Contract: Rules Implementation Lifecycle

## Purpose

Define how official raw rules text becomes simulator-supported engine behavior.

## Lifecycle States

- `raw`: official rules text has been fetched and stored locally with provenance.
- `indexed`: raw rules text has been segmented into addressable rules, sections, and glossary references.
- `mapped`: a rule or rule family is linked to one or more internal engine contracts.
- `implemented`: corresponding engine behavior exists and is covered by tests or executable examples.
- `deferred`: the rule is known but intentionally unsupported in the current simulator scope.

## Guarantees

- A rule is not considered supported merely because its raw text exists in the repository.
- Implemented rule support must name the relevant comprehensive-rules sections it covers.
- Deferred or unsupported rules must be machine-discoverable so agents and humans do not assume silent support.
- Engine contracts may simplify the official rules, but every simplification must be documented.

## Contract Boundary

- Official Comprehensive Rules text remains the external authority.
- Internal contracts define the simulator's implemented subset and operational semantics.
- Any divergence between official text and implemented behavior must be documented as either `deferred`, `simplified`, or `intentional v0 scope`.

## Open Questions

- Should lifecycle state live in a single manifest, rule-family manifests, or both?
- How granular should mapping be for broad rules like state-based actions and continuous effects?
