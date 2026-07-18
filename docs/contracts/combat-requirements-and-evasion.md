# Contract: Combat Requirements And Evasion

## Purpose

Keep combat action enumeration and submitted declarations subject to the same
evasion and requirement rules.

## Required v0+ Rules

- A creature without haste cannot attack during the turn it entered its
  controller's battlefield; haste is an explicit exception.
- Generic landwalk checks the defending player's battlefield for the named land
  subtype and prevents blocks when present.
- A requirement such as “all creatures able to block target creature do so” is
  represented in combat state, considered by legal-action enumeration, and
  revalidated on submitted blockers.

## Guardrail

Do not implement a card with a combat requirement by mutating one caller's
legal-action list only; submitted actions must reject the same illegal result.
