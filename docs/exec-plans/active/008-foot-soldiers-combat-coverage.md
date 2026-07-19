# Execution Plan: Foot Soldiers Combat Coverage

## Goal

Close the recorded coverage gap for Foot Soldiers by proving that the promoted
vanilla creature participates in the ordinary attacker, combat-damage, and
replay paths after being cast through normal turns.

## Scope

- Use only the already active Foot Soldiers and basic-land source scope.
- Cast Foot Soldiers through the existing four-Plains creature path.
- Advance to a later turn so the ordinary entered-this-turn attack restriction
  has expired.
- Declare Foot Soldiers as an unblocked attacker and verify its printed power
  is applied to the defending player's life total.
- Verify the attack declaration identifies the attacking object and the public
  replay tail records the applied player damage.
- Do not widen card, source, keyword, combat, or state-based-action scope.

## Verification

- Add one focused combat regression test.
- Run the focused test, the complete engine suite, and the information suite.
- Parse all coverage YAML and run `git diff --check`.

## Resume Here

After this coverage correction is complete, resume from
`docs/exec-plans/active/002-source-strategy-and-coverage-plan.md` and select the
smallest remaining recorded in-slice limitation or manifest-backed `Portal`
increment.
