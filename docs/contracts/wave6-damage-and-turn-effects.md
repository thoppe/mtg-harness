# Contract: Wave 6 Damage And Turn Effects

## Purpose

Define the smallest deterministic extensions required by the ten Portal Wave 6
cards. This contract applies only to the named oracle IDs recorded by the
coverage manifest when they are promoted with implementation and tests.

## Wave 6A: X Damage And Divided Damage

- `Blaze` (`0596920f-9946-42f4-a03b-24aab67f9f1b`) stores its explicit,
  nonnegative declared X in the stack entry and deals exactly that much damage
  to one legal creature or player target. Planeswalkers are absent from the
  v0 slice, so its printed "any target" means a creature or player only.
- `Earthquake` (`9a40614b-50a3-422c-849e-53c8b7d3d204`) stores X and applies
  that damage as one packet to every creature without Flying and to each
  player, then performs the ordinary state-based-action checkpoint. It has no
  targets.
- `Forked Lightning` (`66107cfd-4bdb-4266-a650-940743555ea4`) stores one to
  three distinct creature targets and one positive integer allocation for each
  target. The allocations sum to four at cast time. At resolution, damage for
  each still-legal target uses its immutable allocation; it is not reassigned
  if another target becomes illegal. If every required target is illegal, the
  spell is countered on resolution under the ordinary target rule.

These cards reuse the X-payment snapshot from `costs-and-x-values.md`. They do
not introduce arbitrary target schemas, damage redirection, prevention, or
planeswalkers.

## Wave 6B: Sacrifice, Snapshot Values, And Mass Destruction

- `Wicked Pact` (`39e21a5a-b278-478a-854c-17695c0f6246`) requires exactly two
  distinct nonblack creature targets. It destroys each target still legal on
  resolution, then its caster loses five life. If both required targets are
  illegal, the whole spell is countered and no life is lost.
- `Final Strike` (`4d98aea2-b4ff-4903-ba28-a53fbfaad6b1`) requires the caster
  to sacrifice one controlled creature while casting and target the opposing
  player. The sacrificed creature's power is captured before it leaves the
  battlefield, and that immutable value is the resolution damage. It is a
  second name-scoped sacrifice cost beside Natural Order, not a general
  sacrifice-cost facility.
- `Devastation` (`052838cb-dcf0-46f5-82b1-c3ed863b42b7`) destroys every
  creature and land in one resolution batch, then runs one state-based-action
  checkpoint. It reuses the declared global creature and land destruction
  paths; it does not add regeneration or replacement-effect support.

## Wave 6C: Next-Turn Restrictions

- `Exhaustion` (`0e7b9caf-8285-4386-98bc-9a809827f447`) records a
  target-player, one-next-untap restriction. During that player's next untap
  step, that player's creatures and lands remain tapped; all other untap
  behavior remains unchanged. The marker is consumed whether or not any
  affected permanent is tapped.
- `False Peace` (`7962db58-dbd9-4b94-8a21-a1625da4c384`) records a
  target-player, one-next-turn combat skip. That next turn transitions from
  precombat main directly to postcombat main, emits the ordinary transition
  events, and consumes the marker. It does not skip main phases or future
  turns.
- `Taunt` (`24cf7fad-233b-49fd-b2a1-a29e3e30041c`) records the target player,
  the caster to attack, and the target player's next-turn identity. During
  that turn's attacker declaration, every creature the target player controls
  that can legally attack that caster must be declared as an attacker. Existing
  restrictions, summoning sickness, and evasion legality still apply. The
  marker expires at that turn's cleanup whether or not combat occurred.

The three markers are serializable state keyed to an upcoming turn/untap
occurrence, not generic continuous effects, skip-turn handling, or delayed
trigger dispatch.

## Wave 6D: Extra Turn And Delayed Loss

`Last Chance` (`360039a5-1cbd-4ee3-8f94-21b5348e106a`) appends exactly one
extra turn for its caster immediately after the current turn. It records that
specific queued turn as lethal. At the beginning of that extra turn's end
step, the caster loses the game before ordinary end-step priority or cleanup.
The queue entry and terminal transition are replay-visible. This is a
name-scoped delayed-turn outcome, not generic extra-turn ordering or a general
trigger framework.

## Replay And Testing Guarantees

- Stack entries preserve declared X, ordered targets, divided-damage
  allocations, and Final Strike's sacrificed-power snapshot.
- Accepted next-turn markers and queued extra-turn metadata are explicit state
  and action/event-log data; replay never infers them from wall-clock order.
- Tests cover payment rejection, duplicate/zero/incorrect divided allocations,
  partial and total target illegality, lethal SBA outcomes, marker consumption,
  skipped combat, forced attacks, extra-turn insertion, and Last Chance's
  terminal end-step timing.

## Name-Scoped Boundary

Wave 6 does not add generic multiple-target selection, arbitrary sacrifice
costs, prevention, redirection, planeswalkers, global turn skipping, generic
delayed triggers, or arbitrary extra-turn queue manipulation.
