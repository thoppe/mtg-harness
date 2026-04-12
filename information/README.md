# Information Workspace

This directory holds external-source pull code, tests, and pulled artifacts.

## Layout

- `cards/`: pulled card metadata and image assets
- `rules/`: pulled rules artifacts

## Constraints

- Pull scripts and tests for external information should live under `information/`.
- Card metadata files and card image files must be stored in separate subdirectories.
- One file per card metadata record and one file per card image asset.
- Raw source presence does not imply gameplay support.
