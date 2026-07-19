# Contract: Wave 7 Abilities And Prevention

## Purpose

Define the smallest deterministic extensions required by the thirty-eight
`Portal` Wave 7 cards. This contract applies only to the named oracle IDs
recorded by the coverage manifest when they are promoted with implementation
and tests. It deliberately reuses the stack, combat, choice, and temporary
characteristic contracts instead of introducing a general rules-text parser.

## Wave 7A: Attacked-Player Instants And Combat Prevention

`Assassin's Blade` (`76da2150-34b9-4483-99df-131e1c5468d5`), `Blessed
Reversal` (`70e0b676-61a2-4dcf-8f61-d9281467ed43`), `Command of
Unsummoning` (`fd57dfa5-f29d-4b79-8748-c34a73efb7f0`), `Deep Wood`
(`3f01f627-9fbd-470b-8001-974784ccf421`), `Defiant Stand`
(`05e61628-cdae-4664-b866-be438fb3a6ba`), `Harsh Justice`
(`fe4bee2c-f03f-44a4-94a4-55a06bcd0ad8`), and `Scorching Winds`
(`db025c94-1182-412e-9665-b5ae89d26616`) may be cast only by a player who
has been attacked in the current combat and only in that combat's
declare-attackers priority window. Their declared targets are checked again
at resolution under the ordinary target rule.

- Assassin's Blade destroys one legal nonblack attacking creature.
- Blessed Reversal gains its caster three life for each creature attacking
  that caster when it resolves.
- Command of Unsummoning returns one or two distinct legal attacking creature
  targets to their owners' hands. Each still-legal target resolves
  independently; all-illegal targets counter the spell.
- Deep Wood creates one caster-bound, current-turn prevention record. Each
  damage packet that an attacking creature would deal to that caster for the
  rest of the turn is prevented; it neither redirects damage nor prevents
  damage to other objects or players.
- Defiant Stand grants one target creature +1/+3 through cleanup and untaps
  it on resolution.
- Harsh Justice creates one caster-bound, current-turn retaliation record. If
  an attacking creature deals combat damage to that caster, it creates a
  delayed trigger with the attacking creature's controller and that packet's
  dealt amount captured. That trigger is put on the stack after the current
  damage/SBA operation and deals that much damage to the captured controller
  on resolution. It does not apply to noncombat damage, damage to a different
  player, or damage that was prevented.
- Scorching Winds deals one damage to each creature attacking the caster at
  resolution, then runs one ordinary SBA checkpoint.

This subwave is not a general instant-timing, prevention, damage replacement,
or damage-trigger framework.

## Wave 7B: Bounded Trigger Dispatch

Wave 7 generalizes the existing Alabaster stack entry only into explicit,
registered trigger schemas. A supported triggering event records all
last-known source identity and event-specific snapshots before the relevant
zone change completes. After the current spell, ability, or state-based
action finishes, pending triggers are placed on the stack in active-player,
then nonactive-player order; within one player's simultaneous triggers, the
controller chooses their order through an explicit pending decision. A
triggered entry resolves through ordinary priority and is independent of its
source's later zone or controller changes unless its printed effect requires
that source to remain in a particular zone.

Only these source/event schemas are supported:

- Attack: Charging Bandits (`0c67133b-be15-47d7-8cf6-79987a42044d`) gets
  +2/+0; Charging Paladin (`6cccf44e-c05e-4239-b643-54b559c98552`) gets
  +0/+3; Seasoned Marshal (`0c7239bf-dc8a-4d79-867e-7a4225568c49`) may tap
  one target creature; and Thing from the Deep
  (`9542bd7f-bb99-4b59-a4e3-b88ed9f798bf`) requires its controller to
  sacrifice an Island or sacrifice it.
- Enters: Dread Reaper (`bd73ab86-0ac9-4ce0-be41-f4ad257e74f6`), Ebon
  Dragon (`12e4d2bd-83e9-4120-a2e8-0645c0ed2387`), Fire Dragon
  (`349d8ef9-e07a-416f-a5b1-2c2be6bb322d`), Fire Imp
  (`5bd806e7-3f9b-4bb4-9708-f87a578f531e`), Gravedigger
  (`1a2030cc-d7ee-4059-b2d7-fb95ea8e267b`), Ingenious Thief
  (`73ea2949-5812-478d-8f09-00743ce4d40f`), Man-o'-War
  (`67a3541c-8408-40c8-b44f-90035b860f57`), Mercenary Knight
  (`ed5429bb-233a-4528-bf7d-df5f6b192b1c`), Owl Familiar
  (`099a5835-da6c-4e03-ad3e-aeb448897fed`), Pillaging Horde
  (`ad07cb55-cc4f-40be-b16a-bd3d3ca94249`), Plant Elemental
  (`e822bf3d-3a29-4a02-9ae8-e2830ce70f15`), Primeval Force
  (`f4170db0-3adf-4744-b0ec-e889c713bb93`), Serpent Assassin
  (`3bc7d3a7-ddb4-4eaa-882e-404d8f2926fb`), Serpent Warrior
  (`fe249f27-db6c-4826-836e-a04efb1a3eaa`), Spiritual Guardian
  (`d03860b4-c663-4230-9200-6b89fa849ae7`), Thundering Wurm
  (`cdab50a8-1e02-4ba5-8c09-e2837e7652f7`), Thundermare
  (`58fa33fd-02a4-4ec9-9226-82594cfec363`), Venerable Monk
  (`5c5cfa6d-857f-44a9-80f7-46f016ef71e4`), and Wood Elves
  (`8973bd99-20f8-4867-90ef-50392147ee1b`).
- Dies: Endless Cockroaches (`9f31dbb1-c350-46f8-bd1d-9f23a073d2f1`), Fire
  Snake (`e96542ed-1931-4da1-9d9e-d10878c4ae6b`), Noxious Toad
  (`2fdc484e-b3c3-4f4e-99a1-26a1134aa1cd`), and Undying Beast
  (`5ae03181-a436-4bad-be3a-6c9f6c0ed4d6`).

ETB and dies triggers occur once per qualifying zone change, including a
creature that immediately dies to a state-based action. A source that leaves
and later re-enters is a fresh object and triggers again. Trigger choices,
including optional targets and mandatory “unless” payments, are requested only
when their entry resolves; no hidden choice leaks into public events.

## Wave 7C: Trigger Effects, Costs, And Choices

The Wave 7B schemas resolve only as follows:

- Dread Reaper and Serpent Warrior cause their controller to lose five or
  three life respectively. Spiritual Guardian and Venerable Monk gain their
  controller four or two life respectively.
- Ebon Dragon may target an opponent; on resolution a selected opponent with a
  nonempty hand chooses one card to discard through an affected-player-owned
  continuation. Ingenious Thief looks at one target player's hand using the
  existing controller-visible inspection event.
- Fire Dragon targets one creature and deals an immutable resolution-time
  count of its controller's Mountains. Fire Imp deals two damage to one target
  creature. Serpent Assassin may destroy one target nonblack creature.
- Gravedigger may return one target creature card from its controller's
  graveyard to that hand. Man-o'-War may return one target creature to its
  owner's hand. Wood Elves privately searches its controller's library for
  one Forest card, puts it onto the battlefield, then shuffles under the
  existing search contract.
- Owl Familiar draws one card, then requires its controller to discard one
  card if able through a chooser-owned hand decision. Pillaging Horde randomly
  discards one card from a nonempty controller hand using exactly one
  deterministic RNG selection; if its hand is empty it sacrifices itself.
- Mercenary Knight and Thundering Wurm each let their controller choose a
  qualifying creature or land card from hand to discard; Plant Elemental and
  Primeval Force let its controller sacrifice one or three controlled Forests;
  Thing from the Deep lets its controller sacrifice one controlled Island.
  If the required eligible payment is not chosen or cannot be paid, the
  triggering creature is sacrificed. Each is a trigger-resolution choice, not
  a casting additional cost.
- Thundermare taps every other creature at resolution. Noxious Toad makes its
  opponent choose one card to discard through an affected-player-owned
  continuation when that player's hand is nonempty. Fire Snake destroys one
  target land. Endless Cockroaches returns its expected graveyard
  object to its owner's hand; Undying Beast puts that expected graveyard object
  on top of its owner's library. If either expected object has left that
  graveyard, its trigger resolves with no effect.

## Wave 7D: Activated Nonmana Abilities And Counters

Capricious Sorcerer (`09fe624f-c66a-46e4-a9af-7e3c3ca1a4e3`), King's Assassin
(`4e3f89e2-2be6-4b96-b81c-007b6840af82`), and Stern Marshal
(`00602959-e9a1-4706-a1cb-70156a6fc713`) introduce one shared, bounded
activated-nonmana path. Their controller may activate the printed ability only
during that controller's turn before attackers are declared, only while the
source is an untapped creature that controller controls, and only if the
source has been under that controller's control continuously since the start
of that controller's most recent turn. Tapping the source is paid at activation
and the ability becomes a stack entry; it is not a spell card and remains
independent of its source after activation. Wave 7 does not extend the existing
Haste support to tap-ability timing because no promoted tap-ability source has
that keyword.

- Capricious Sorcerer deals one damage to one legal creature or player target.
- King's Assassin destroys one legal tapped creature target.
- Stern Marshal grants one legal creature target +2/+2 through cleanup.

`Mystic Denial` (`d2bd23a6-4f77-4d6e-bf8f-339cb7a4184d`) may counter one
target creature or sorcery spell while that target is on the stack. It moves
the countered spell from stack to its owner's graveyard without resolution and
does not counter abilities, instants, or triggers. This is a name-scoped
counterspell predicate, not broad stack interaction.

## Replay And Testing Guarantees

- Trigger and activated-ability stack entries retain source controller,
  source/card/object identity, event-time snapshots, declared targets, and
  expected graveyard identity where required.
- Replay records trigger creation, trigger ordering decisions, ability
  activation, target selection, prevention/replacement application, counters,
  and every consumed RNG cursor without exposing private hand or library
  identities.
- Tests cover APNAP trigger order, same-source re-entry, source departure
  before resolution, optional and mandatory choices, unable-to-pay sacrifices,
  tapped/summoning-sick activation rejection, response/counter timing,
  all-illegal target resolution, prevention versus retaliation, and terminal
  state-based outcomes.

## Name-Scoped Boundary

Wave 7 does not add a general rules-text interpreter, arbitrary triggered or
activated abilities, generic replacement effects, general counterspells,
multi-player priority, damage redirection, regeneration, or persistent hidden
information visibility.

## Completed Trigger-Resolution Choice Increment

The supported Wave 7 optional, target-bearing, search, post-draw discard, and
pay-or-sacrifice triggers now suspend resolution with one chooser-owned
`PendingDecision`. Decisions distinguish object options from player options,
snapshot object identity at the trigger-resolution boundary, and revalidate
zone and identity before applying the continuation. Stale targets resolve with
no effect; stale or declined payments take the unpaid source-sacrifice branch.

Public request and resolution events expose decision metadata, option scope,
and counts but do not expose hidden hand or library identities. Wood Elves
shuffles after a selected, declined, or stale search. Primeval Force accepts
only zero or exactly three distinct Forest selections. The trigger stack entry
is removed when resolution suspends, and `triggered_ability_resolved` is
emitted only after the continuation completes.

The verified increment and its regression matrix are recorded in
`docs/exec-plans/active/003-wave7-trigger-resolution-choices.md` and
`engine/tests/test_wave7_trigger_choices.py`.

## Completed Trigger Discard Choice Correction

Ebon Dragon and Noxious Toad no longer select the first card in deterministic
hand order. Their affected player chooses exactly one snapshotted hand object,
with hand-zone and object-identity revalidation. Empty hands resolve without a
decision, and Ebon Dragon retains its separate optional controller-owned
opponent choice.

The bounded correction is recorded in
`docs/exec-plans/active/007-wave7-trigger-discard-choices.md`.
