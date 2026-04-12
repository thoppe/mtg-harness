# Future Codex Skill: Card Introspection

## Purpose

Describe a future Codex skill that inspects incoming card additions and highlights rules or testing gaps before implementation.

## Intended Inputs

- One or more canonical card metadata files
- Existing rules coverage manifest
- Existing card coverage manifest

## Intended Outputs

- Candidate new rule families required by the cards
- Warnings about ambiguous or unusual oracle text
- Suggested edge-case tests
- Suggested updates to coverage manifests before coding starts

## Why This Is Useful

- It keeps new card additions honest about rules impact.
- It helps preserve the raw-vs-implemented separation.
- It gives agents a repeatable workflow for expanding support without silently widening scope.

## Current Status

This is a design note only. No live skill is added yet.
